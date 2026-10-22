"""Bounded capture → recognition pipeline with an atomic discontinuity gate."""
from collections import deque
import threading
import time
import math
import cv2
from app.models.schemas import Frame
from app.services.camera_service import open_capture
from app.services.video_service import frame_timestamp, video_source
from app.services.face_matcher import FaceMatcher
from app.services.tracker import Tracker
from app.services.session_manager import SessionManager


class Latest:
    def __init__(self):
        self.condition = threading.Condition()
        self.item = None

    def put(self, item):
        with self.condition:
            self.item = item
            self.condition.notify()

    def take(self, timeout=0.2):
        with self.condition:
            if self.item is None:
                self.condition.wait(timeout)
            item, self.item = self.item, None
            return item

    def peek(self):
        with self.condition:
            return self.item

    def clear(self):
        with self.condition:
            self.item = None


class Pipeline:
    def __init__(self, db, engine, settings, notify=lambda message: None):
        self.db, self.engine, self.settings, self.notify = db, engine, settings, notify
        self.gate = threading.RLock()
        self.epoch = 0
        self.commands = deque()
        self.wake = threading.Event()
        self.stopping = threading.Event()
        self.inbox, self.raw, self.results = Latest(), Latest(), Latest()
        self.session = None
        self.ended_epoch = None
        self.matcher = FaceMatcher(db.gallery(), settings.similarity)
        self.state = {"playing": False, "kind": "", "position": 0.0, "duration": 0.0, "source": "", "fps": 0.0}
        self.capture_thread = threading.Thread(target=self._capture, name="capture", daemon=True)
        self.recognition_thread = threading.Thread(target=self._recognize, name="recognition", daemon=True)
        self.capture_thread.start()
        self.recognition_thread.start()

    def _invalidate(self):
        self.epoch += 1
        self.inbox.clear()
        self.raw.clear()
        self.results.clear()
        if self.session:
            self.session.close()
            self.session = None

    def command(self, name, value=None):
        with self.gate:
            # This gate also guards committing results. Work already running cannot
            # write a log or publish a frame after this invalidation.
            if name in ("open_camera", "open_video", "seek", "stop", "logging"):
                self._invalidate()
            self.commands.append((name, value, self.epoch))
        self.wake.set()

    def reload_gallery(self):
        matcher = FaceMatcher(self.db.gallery(), self.settings.similarity)
        with self.gate:
            self._invalidate()
            # Existing capture uses the new epoch on its next iteration.
            self.matcher = matcher

    def snapshot(self):
        with self.gate:
            return dict(self.state)

    def _capture(self):
        cap = None
        kind, source, duration, fps = "", "", 0.0, 25.0
        playing, logging, speed, single = False, False, 1.0, False
        next_due = time.monotonic()
        index = 0
        last_inference = -float("inf")
        try:
            while not self.stopping.is_set():
                with self.gate:
                    commands = list(self.commands)
                    self.commands.clear()
                for name, value, cmd_epoch in commands:
                    if name in ("open_camera", "open_video", "stop"):
                        if cap:
                            cap.release()
                            cap = None
                        playing = False
                        if name == "stop":
                            with self.gate:
                                self.state.update(playing=False, position=0.0)
                            continue
                        kind = "camera" if name == "open_camera" else "video"
                        try:
                            source = f"camera:{value}" if kind == "camera" else video_source(value, self.stopping.is_set)
                            cap = open_capture(value, kind == "camera")
                            if kind == "video":
                                fps = float(cap.get(cv2.CAP_PROP_FPS))
                                frames = float(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                                if not math.isfinite(fps) or fps <= 0 or not math.isfinite(frames) or frames <= 0:
                                    raise ValueError("Video thiếu FPS/số khung hình hợp lệ; hãy chuyển sang MP4 CFR bằng FFmpeg.")
                                duration = frames / fps
                            else:
                                fps, duration = 30.0, 0.0
                            index, playing, single = 0, True, False
                            last_inference = -float("inf")
                            with self.gate:
                                self.state.update(kind=kind, source=source, duration=duration, position=0.0)
                            self.notify("Đã mở " + ("camera" if kind == "camera" else "video"))
                        except Exception as exc:
                            if cap:
                                cap.release()
                                cap = None
                            self.notify(str(exc))
                    elif name == "play":
                        playing = bool(value) and cap is not None
                    elif name == "seek" and cap and kind == "video":
                        target = min(max(float(value), 0), max(0, duration-1/fps))
                        if not cap.set(cv2.CAP_PROP_POS_MSEC, target * 1000):
                            self.notify("Backend không hỗ trợ tua video này")
                        index = max(0, round(cap.get(cv2.CAP_PROP_POS_FRAMES)))
                        single = True
                        last_inference = -float("inf")
                    elif name == "speed":
                        speed = float(value)
                    elif name == "logging":
                        logging = bool(value)
                        last_inference = -float("inf")
                    next_due = time.monotonic()
                with self.gate:
                    self.state["playing"] = playing
                    epoch = self.epoch
                    if self.commands:
                        continue
                if cap is None or (not playing and not single):
                    self.wake.wait(0.05)
                    self.wake.clear()
                    continue
                delay = next_due - time.monotonic()
                if delay > 0 and not single:
                    self.wake.wait(min(delay, 0.05))
                    self.wake.clear()
                    continue
                ok, image = cap.read()
                if not ok:
                    playing = False
                    # Flush pending final recognition before closing, in recognizer order.
                    self.ended_epoch = epoch
                    self.notify("Kết thúc video" if kind == "video" else "Không đọc được camera")
                    continue
                stamp = time.time() if kind == "camera" else frame_timestamp(cap.get(cv2.CAP_PROP_POS_MSEC), index, fps)
                clock = time.monotonic() if kind == "camera" else stamp
                frame = Frame(epoch, image, kind, source, stamp, clock, duration, logging)
                with self.gate:
                    if epoch == self.epoch:
                        self.raw.put(frame)
                        self.state["position"] = stamp if kind == "video" else 0
                        interval = 1 / self.settings.recognition_hz
                        if time.monotonic()-last_inference >= interval or single:
                            self.inbox.put(frame)
                            last_inference = time.monotonic()
                single = False
                index += 1
                next_due = max(next_due + 1/(fps*speed), time.monotonic() - 1/fps)
        except Exception as exc:
            self.notify(f"Luồng đọc hình: {exc}")
        finally:
            if cap:
                cap.release()

    def _recognize(self):
        tracker, tracked_epoch = Tracker(), -1
        while not self.stopping.is_set():
            item = self.inbox.take()
            if item is None:
                with self.gate:
                    if self.ended_epoch == self.epoch and self.session:
                        self.session.close()
                        self.session = None
                continue
            if isinstance(item, tuple):
                with self.gate:
                    if item[1] == self.epoch and self.session:
                        self.session.close()
                        self.session = None
                continue
            frame = item
            started = time.monotonic()
            try:
                if tracked_epoch != frame.epoch:
                    tracker, tracked_epoch = Tracker(), frame.epoch
                detections = self.engine.detect(frame.image)
                with self.gate:
                    if frame.epoch != self.epoch:
                        continue
                    labels = tracker.update(detections, self.matcher, frame.clock)
                    if frame.logging:
                        if self.session is None:
                            self.session = SessionManager(self.db, frame.source_type, frame.source_id, self.settings.absence_seconds)
                        self.session.observe([(f.match.person_id, f.match.name) for f in labels if f.match.person_id], frame.timestamp, frame.clock)
                    rate = 1 / max(time.monotonic()-started, 1e-6)
                    self.results.put((frame, labels, rate))
                    self.state["fps"] = rate
            except Exception as exc:
                self.notify(f"Nhận diện: {exc}")
                # Avoid a hot error loop while allowing setup from the settings page.
                self.stopping.wait(0.5)

    def shutdown(self, timeout=10):
        self.stopping.set()
        self.wake.set()
        self.inbox.put(None)
        self.capture_thread.join(timeout)
        self.recognition_thread.join(timeout)
        if self.capture_thread.is_alive() or self.recognition_thread.is_alive():
            return False
        with self.gate:
            if self.session:
                self.session.close()
                self.session = None
        return True

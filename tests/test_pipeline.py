"""Real OpenCV synthetic-video I/O; deterministic detector, no physical camera."""
import threading
import time
import cv2
import numpy as np
import pytest
from app.config import Settings
from app.models.schemas import Detection, Frame
from app.workers.pipeline import Pipeline


def eventually(predicate, timeout=4):
    until = time.monotonic()+timeout
    while time.monotonic() < until:
        if predicate():
            return
        time.sleep(0.01)
    assert predicate(), "Timed out waiting for asynchronous pipeline"


class FakeEngine:
    def __init__(self, vector):
        self.vector = vector
        self.backend, self.warning = "test CPU adapter", ""

    def detect(self, image):
        return [Detection((2,2,50,50), self.vector)]


@pytest.fixture
def clip(tmp_path):
    path = tmp_path/"clip.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 20, (64,64))
    assert writer.isOpened()
    for i in range(80):
        writer.write(np.full((64,64,3), i, np.uint8))
    writer.release()
    return path


@pytest.fixture
def pipeline(db, person, vector, tmp_path):
    db.add_reference(person, "reference.jpg", vector)
    settings = Settings(recognition_hz=20, image_dir=str(tmp_path))
    p = Pipeline(db, FakeEngine(vector), settings)
    yield p
    assert p.shutdown()


def test_preview_pause_seek_speed_and_log_replay(pipeline, clip, db):
    p = pipeline
    p.command("open_video", str(clip))
    eventually(lambda: p.snapshot()["position"] >= .2)
    assert not db.history(), "Preview must never write history"
    p.command("play", False)
    eventually(lambda: not p.snapshot()["playing"])
    time.sleep(.1)
    paused = p.snapshot()["position"]
    time.sleep(.15)
    assert p.snapshot()["position"] == paused
    p.command("seek", 2)
    eventually(lambda: p.raw.peek() is not None and p.raw.peek().timestamp >= 1.9)
    epoch = p.epoch
    assert p.raw.peek().epoch == epoch
    p.command("logging", True)
    p.command("speed", 2)
    p.command("play", True)
    eventually(lambda: len(db.history()) == 1)
    p.command("play", False)
    p.command("seek", 1.8)
    p.command("play", True)
    time.sleep(.3)
    p.command("stop")
    assert len(db.history()) == 1
    row = db.history()[0]
    assert row["source_type"] == "video"
    assert 0 <= row["first_seen"] <= row["last_seen"] <= 4


def test_inflight_seek_cannot_publish_or_log_old_frame(db, person, vector, tmp_path):
    entered, release = threading.Event(), threading.Event()
    class SlowEngine(FakeEngine):
        def detect(self, image):
            entered.set()
            release.wait(3)
            return super().detect(image)
    db.add_reference(person, "ref.jpg", vector)
    p = Pipeline(db, SlowEngine(vector), Settings())
    try:
        image = np.zeros((64,64,3), np.uint8)
        p.inbox.put(Frame(p.epoch, image, "video", "clip", 100, 100, 200, True))
        assert entered.wait(2)
        old = p.epoch
        p.command("seek", 10)
        assert p.epoch > old
        release.set()
        time.sleep(.15)
        assert p.results.peek() is None
        assert not db.history()
    finally:
        release.set()
        assert p.shutdown()


def test_capture_open_and_logging_commands_can_be_queued_together(pipeline, clip, db):
    pipeline.command("open_video", str(clip))
    pipeline.command("logging", True)
    eventually(lambda: len(db.history()) == 1)
    assert pipeline.snapshot()["kind"] == "video"


def test_eof_flushes_last_successful_observation(pipeline, clip, db):
    pipeline.command("open_video", str(clip))
    pipeline.command("logging", True)
    pipeline.command("speed", 2)
    eventually(lambda: pipeline.snapshot()["position"] > 3.8)
    eventually(lambda: bool(db.history()) and db.history()[0]["status"] == "closed")
    assert db.history()[0]["last_seen"] > 3


def recognize_frame(pipeline, stamp, image, detections, logging=True):
    pipeline.engine.detect = lambda _: detections
    frame = Frame(pipeline.epoch, image, "video", "occlusion-clip", stamp, stamp, 200, logging)
    pipeline.inbox.put(frame)
    eventually(lambda: pipeline.results.peek() is not None and pipeline.results.peek()[0] is frame)
    return pipeline.results.peek()[1]


def test_occlusion_continues_history_until_visual_departure(pipeline, db, vector, occlusion_scene):
    known = [Detection((80, 30, 130, 80), vector)]
    assert recognize_frame(pipeline, 0, occlusion_scene(), known)[0].match.person_id is None
    assert recognize_frame(pipeline, .2, occlusion_scene(), known)[0].match.person_id
    unknown = [Detection((84, 30, 134, 80), np.roll(vector, 1))]
    assert recognize_frame(pipeline, .4, occlusion_scene(4, True), unknown)[0].tracked
    assert recognize_frame(pipeline, .6, occlusion_scene(8, True), [])[0].tracked
    assert recognize_frame(pipeline, .8, occlusion_scene(12, True), [])[0].tracked
    assert not recognize_frame(pipeline, 1, occlusion_scene(present=False), [])
    pipeline.command("stop")
    rows = db.history()
    assert len(rows) == 1
    assert rows[0]["first_seen"] == .2
    assert rows[0]["last_seen"] == .8
    assert rows[0]["status"] == "closed"


def test_tracking_and_history_continue_without_timeout_when_status_hidden(pipeline, db, vector, occlusion_scene):
    pipeline.settings.show_tracking_status = False
    known = [Detection((80, 30, 130, 80), vector)]
    recognize_frame(pipeline, 0, occlusion_scene(), known)
    recognize_frame(pipeline, .2, occlusion_scene(), known)
    for stamp in range(1, 151):
        labels = recognize_frame(pipeline, stamp, occlusion_scene(4, True), [])
        assert len(labels) == 1
        assert labels[0].match.person_id
        assert labels[0].tracked
    assert not recognize_frame(pipeline, 151, occlusion_scene(present=False), [])
    pipeline.command("stop")
    rows = db.history()
    assert len(rows) == 1
    assert rows[0]["last_seen"] == 150


def test_fast_motion_and_head_shake_continue_one_history_session(pipeline, db, vector, occlusion_scene):
    known = [Detection((80, 30, 130, 80), vector)]
    recognize_frame(pipeline, 0, occlusion_scene(), known)
    recognize_frame(pipeline, .2, occlusion_scene(), known)
    unknown = np.roll(vector, 1)
    for stamp, dx in ((.4, 60), (.6, -30), (.8, 70)):
        labels = recognize_frame(pipeline, stamp, occlusion_scene(dx, True), [])
        assert len(labels) == 1
        assert labels[0].match.person_id
        assert labels[0].tracked
        assert labels[0].bbox[0] == pytest.approx(80+dx, abs=3)
    # Return to the center, then move only the head while the torso stays put.
    recognize_frame(pipeline, 1, occlusion_scene(), known)
    image = occlusion_scene()
    image[30:80] = 0
    image[30:80, 115:165] = occlusion_scene()[30:80, 80:130]
    labels = recognize_frame(pipeline, 1.2, image, [Detection((115, 30, 165, 80), unknown)])
    assert len(labels) == 1
    assert labels[0].match.person_id
    assert labels[0].tracked
    assert not recognize_frame(pipeline, 1.4, occlusion_scene(present=False), [])
    pipeline.command("stop")
    rows = db.history()
    assert len(rows) == 1
    assert rows[0]["first_seen"] == .2
    assert rows[0]["last_seen"] == 1.2


@pytest.mark.parametrize("action", ["seek", "stop", "logging", "reload_gallery"])
def test_discontinuity_clears_occlusion_identity(pipeline, vector, occlusion_scene, action):
    known = [Detection((80, 30, 130, 80), vector)]
    recognize_frame(pipeline, 0, occlusion_scene(), known)
    recognize_frame(pipeline, .2, occlusion_scene(), known)
    assert recognize_frame(pipeline, .4, occlusion_scene(4, True), [])[0].tracked
    if action == "reload_gallery":
        pipeline.reload_gallery()
    else:
        pipeline.command(action, .5 if action == "seek" else False)
    assert not recognize_frame(pipeline, .6, occlusion_scene(8, True), [], logging=False)


def test_inflight_visual_tracking_cannot_publish_after_seek(pipeline, vector, occlusion_scene, monkeypatch):
    from app.services.tracker import Tracker

    known = [Detection((80, 30, 130, 80), vector)]
    recognize_frame(pipeline, 0, occlusion_scene(), known)
    recognize_frame(pipeline, .2, occlusion_scene(), known)
    entered, release = threading.Event(), threading.Event()
    update = Tracker.update

    def slow_update(self, *args, **kwargs):
        entered.set()
        release.wait(3)
        return update(self, *args, **kwargs)

    monkeypatch.setattr(Tracker, "update", slow_update)
    pipeline.engine.detect = lambda _: []
    frame = Frame(pipeline.epoch, occlusion_scene(4, True), "video", "occlusion-clip", .4, .4, 200, True)
    pipeline.inbox.put(frame)
    try:
        assert entered.wait(2)
        pipeline.command("seek", 10)
        release.set()
        time.sleep(.1)
        assert pipeline.results.peek() is None
        assert pipeline.db.history()[0]["last_seen"] == .2
    finally:
        release.set()

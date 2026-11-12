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


@pytest.mark.parametrize("invalidate", ["seek", "gallery"])
def test_occluded_person_updates_presence_and_session_until_invalidation(db, person, vector, invalidate):
    class CoverEngine(FakeEngine):
        covered = False

        def detect(self, image):
            return [] if self.covered else [Detection((100, 40, 180, 120), self.vector)]

    db.add_reference(person, "ref.jpg", vector)
    engine = CoverEngine(vector)
    p = Pipeline(db, engine, Settings())
    image = np.zeros((300, 400, 3), np.uint8)
    image[40:240, 100:180] = np.random.default_rng(42).integers(40, 240, (200, 80, 3), dtype=np.uint8)

    def recognize(clock):
        p.inbox.put(Frame(p.epoch, image.copy(), "video", "clip", clock, clock, 10, True))
        eventually(lambda: p.results.peek() is not None and p.results.peek()[0].timestamp == clock)
        return p.results.peek()[1]

    try:
        recognize(0)
        assert recognize(.2)[0].match.person_id == person
        engine.covered = True
        image[40:120, 100:180] = 80
        labels = recognize(.4)
        assert labels[0].tracked and labels[0].match.person_id == person
        if invalidate == "seek":
            p.command("seek", .6)
        else:
            p.reload_gallery()
        assert db.history()[0]["last_seen"] == .4
        assert recognize(.6) == []
    finally:
        assert p.shutdown()


def test_inflight_tracking_releases_gate_and_cannot_publish_old_frame(db, person, vector, monkeypatch):
    from app.services.tracker import Tracker
    entered, release = threading.Event(), threading.Event()
    original = Tracker.update

    def slow_tracking(self, *args, **kwargs):
        entered.set()
        assert release.wait(3)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Tracker, "update", slow_tracking)
    db.add_reference(person, "ref.jpg", vector)
    p = Pipeline(db, FakeEngine(vector), Settings())
    try:
        image = np.zeros((64, 64, 3), np.uint8)
        p.inbox.put(Frame(p.epoch, image, "video", "clip", 1, 1, 10, True))
        assert entered.wait(2)
        p.command("seek", 2)
        release.set()
        time.sleep(.15)
        assert p.results.peek() is None
        assert not db.history()
    finally:
        release.set()
        assert p.shutdown()

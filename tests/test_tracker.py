"""Identity transitions and real sparse optical flow, without face models."""
import cv2
import numpy as np
import pytest
from app.models.schemas import Detection
from app.services.face_matcher import FaceMatcher
from app.services.tracker import Tracker


@pytest.fixture
def matcher(vector):
    return FaceMatcher([{"person_id": "a", "name": "A", "embedding": vector},
                        {"person_id": "b", "name": "B", "embedding": np.roll(vector, 1)}])


@pytest.fixture
def subject():
    rng = np.random.default_rng(42)
    image = np.zeros((300, 400, 3), np.uint8)
    image[40:240, 100:180] = rng.integers(40, 240, (200, 80, 3), dtype=np.uint8)
    return image


def shifted(image, dx, dy=0):
    return cv2.warpAffine(image, np.float32([[1, 0, dx], [0, 1, dy]]), (image.shape[1], image.shape[0]))


def confirm(tracker, matcher, vector, image=None):
    known = Detection((100, 40, 180, 120), vector)
    assert tracker.update([known], matcher, 0, image)[0].match.person_id is None
    assert tracker.update([known], matcher, .2, image)[0].match.person_id == "a"
    return known


@pytest.mark.parametrize("size", [(400, 300), (1600, 1200)])
def test_fully_covered_face_tracks_torso_and_reacquires(matcher, vector, subject, size):
    def render(image):
        return cv2.resize(image, size)

    scale = size[0] / 400
    tracker = Tracker()
    box = tuple(v*scale for v in (100, 40, 180, 120))
    known = Detection(box, vector)
    tracker.update([known], matcher, 0, render(subject))
    assert tracker.update([known], matcher, .2, render(subject))[0].match.person_id == "a"
    covered = subject.copy()
    covered[40:120, 100:180] = 80
    for step in range(1, 8):
        labels = tracker.update([], matcher, .2+step*.2, render(shifted(covered, step*4, step*2)))
        assert len(labels) == 1
        assert labels[0].match.person_id == "a"
        assert labels[0].tracked
        assert labels[0].bbox == pytest.approx(tuple(v*scale for v in (
            100+step*4, 40+step*2, 180+step*4, 120+step*2)), abs=scale)
    visible = Detection(tuple(v*scale for v in (128, 54, 208, 134)), vector)
    label = tracker.update([visible], matcher, 1.8, render(shifted(subject, 28, 14)))[0]
    assert label.match.person_id == "a"
    assert not label.tracked


def test_weak_face_embedding_keeps_visual_identity(matcher, vector, subject):
    tracker = Tracker()
    confirm(tracker, matcher, vector, subject)
    unknown = np.roll(vector, 2)
    for step in range(1, 8):
        det = Detection((100+step*3, 40, 180+step*3, 120), unknown)
        label = tracker.update([det], matcher, .2+step*.2, shifted(subject, step*3))[0]
        assert label.match.person_id == "a"
        assert label.tracked


def test_unknown_faces_never_gain_identity_from_motion(matcher, vector, subject):
    tracker = Tracker()
    unknown = Detection((100, 40, 180, 120), np.roll(vector, 2))
    for clock in (0, .2, .4):
        label = tracker.update([unknown], matcher, clock, subject)[0]
        assert label.match.person_id is None
        assert not label.tracked
    assert tracker.update([], matcher, .6, subject) == []


def test_contradictory_identity_requires_new_confirmation(matcher, vector, subject):
    tracker = Tracker()
    confirm(tracker, matcher, vector, subject)
    other = Detection((100, 40, 180, 120), np.roll(vector, 1))
    assert tracker.update([other], matcher, .4, subject)[0].match.person_id is None
    assert tracker.update([other], matcher, .6, subject)[0].match.person_id == "b"


@pytest.mark.parametrize("face_detected", [False, True])
def test_occluded_identity_has_no_time_limit_while_tracking(matcher, vector, subject, face_detected):
    tracker = Tracker()
    confirm(tracker, matcher, vector, subject)
    covered = subject.copy()
    covered[40:120, 100:180] = 80
    detections = [Detection((100, 40, 180, 120), np.roll(vector, 2))] if face_detected else []
    for step in range(1, 62):
        labels = tracker.update(detections, matcher, .2+step, covered)
        assert len(labels) == 1
        assert labels[0].match.person_id == "a"
        assert labels[0].tracked
    # Removing the duration cap must still end retention when visual evidence ends.
    labels = tracker.update(detections, matcher, 62.2, np.zeros_like(subject))
    assert all(label.match.person_id is None for label in labels)


@pytest.mark.parametrize("change", ["blank", "cut", "resize", "gap", "backwards"])
def test_lost_or_discontinuous_image_drops_identity(matcher, vector, subject, change):
    tracker = Tracker()
    confirm(tracker, matcher, vector, subject)
    image, clock = subject, .4
    if change == "blank":
        image = np.zeros_like(subject)
    elif change == "cut":
        image = np.random.default_rng(7).integers(0, 256, subject.shape, dtype=np.uint8)
    elif change == "resize":
        image = cv2.resize(subject, (800, 600))
    elif change == "gap":
        clock = 3
    else:
        clock = .1
    assert tracker.update([], matcher, clock, image) == []


def test_missing_detection_without_images_never_creates_ghost(matcher, vector):
    tracker = Tracker()
    confirm(tracker, matcher, vector)
    assert tracker.update([], matcher, .4) == []


def test_ambiguous_crossing_does_not_inherit_names(matcher, vector):
    tracker = Tracker()
    left = Detection((0, 0, 100, 100), vector)
    right = Detection((60, 0, 160, 100), np.roll(vector, 1))
    tracker.update([left, right], matcher, 0)
    assert [l.match.person_id for l in tracker.update([right, left], matcher, .2)] == ["b", "a"]
    unknown = Detection((30, 0, 130, 100), np.roll(vector, 2))
    labels = tracker.update([unknown], matcher, .4)
    assert len(labels) == 1
    assert labels[0].match.person_id is None


def test_detector_order_cannot_steal_better_track(matcher, vector):
    tracker = Tracker()
    confirm(tracker, matcher, vector)
    weak = Detection((135, 40, 215, 120), np.roll(vector, 2))
    exact = Detection((100, 40, 180, 120), np.roll(vector, 2))
    labels = tracker.update([weak, exact], matcher, .4)
    assert labels[0].match.person_id is None
    assert labels[1].match.person_id == "a"


def test_clear_faces_skip_optical_flow(matcher, vector, subject, monkeypatch):
    tracker = Tracker()
    known = confirm(tracker, matcher, vector, subject)

    def unexpected_flow(*args, **kwargs):
        pytest.fail("Clear, matched faces should not run optical flow")

    monkeypatch.setattr(cv2, "calcOpticalFlowPyrLK", unexpected_flow)
    assert tracker.update([known], matcher, .4, subject)[0].match.person_id == "a"


@pytest.mark.parametrize("seed", [3, 7, 15])
def test_ten_covered_people_keep_separate_identities_at_1080p(seed):
    rng = np.random.default_rng(seed)
    image = np.zeros((1080, 1920, 3), np.uint8)
    rows, detections = [], []
    for i in range(10):
        x, y = 70+(i % 5)*360, 70+(i // 5)*480
        image[y:y+350, x:x+140] = rng.integers(20, 240, (350, 140, 3), dtype=np.uint8)
        vector = np.eye(1, 512, i, dtype=np.float32).ravel()
        rows.append(dict(person_id=str(i), name=str(i), embedding=vector))
        detections.append(Detection((x, y, x+140, y+140), vector))
    matcher, tracker = FaceMatcher(rows), Tracker()
    tracker.update(detections, matcher, 0, image)
    tracker.update(detections[::-1], matcher, .2, image)
    for det in detections:
        x1, y1, x2, y2 = det.bbox
        image[y1:y2, x1:x2] = 80
    for clock in (.4, .6, .8):
        labels = tracker.update([], matcher, clock, image)
        assert len(labels) == 10
        assert {l.match.person_id for l in labels} == {str(i) for i in range(10)}
        assert all(l.tracked for l in labels)

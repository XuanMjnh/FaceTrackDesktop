import json

import cv2
import numpy as np
import pytest

from app.config import Settings
from app.models.schemas import Detection
from app.services.face_matcher import FaceMatcher
from app.services.tracker import Tracker


@pytest.fixture
def matcher(vector):
    return FaceMatcher([
        {"person_id": "a", "name": "Ánh", "embedding": vector},
        {"person_id": "b", "name": "Bình", "embedding": np.roll(vector, 2)},
    ])


def face(vector, dx=0):
    return Detection((80+dx, 30, 130+dx, 80), vector)


def confirm(tracker, matcher, vector, scene=None):
    image = scene() if scene else None
    assert tracker.update([face(vector)], matcher, 0, image)[0].match.person_id is None
    label = tracker.update([face(vector)], matcher, .2, image)[0]
    assert label.match.person_id == "a"
    assert not label.tracked


def test_unknown_never_inherits_an_unconfirmed_identity(matcher, vector):
    tracker = Tracker()
    tracker.update([face(vector)], matcher, 0)
    label = tracker.update([face(np.roll(vector, 1))], matcher, .2)[0]
    assert label.match.person_id is None
    assert not label.tracked


def test_unrecognized_face_keeps_identity_without_time_limit(matcher, vector):
    tracker = Tracker()
    confirm(tracker, matcher, vector)
    for stamp in (.4, 15, 120, 3600):
        label = tracker.update([face(np.roll(vector, 1))], matcher, stamp)[0]
        assert label.match.person_id == "a"
        assert label.tracked


def test_conflicting_identity_replaces_old_name_only_after_confirmation(matcher, vector):
    tracker = Tracker()
    confirm(tracker, matcher, vector)
    other = face(np.roll(vector, 2))
    labels = tracker.update([other], matcher, .4)
    assert len(labels) == 1
    assert labels[0].match.person_id is None
    assert tracker.update([other], matcher, .6)[0].match.person_id == "b"


def test_cover_then_detector_loss_follows_moving_torso(matcher, vector, occlusion_scene):
    tracker = Tracker()
    confirm(tracker, matcher, vector, occlusion_scene)
    labels = tracker.update([face(np.roll(vector, 1), 4)], matcher, .4, occlusion_scene(4, True))
    assert labels[0].match.person_id == "a"
    assert labels[0].tracked
    for index in range(2, 12):
        labels = tracker.update([], matcher, .2+index*.2, occlusion_scene(index*4, True))
        assert len(labels) == 1
        assert labels[0].match.person_id == "a"
        assert labels[0].tracked
        assert labels[0].match.score == 0  # No stale similarity displayed as a new face match.
        assert labels[0].bbox[0] == pytest.approx(80+index*4, abs=2)
    label = tracker.update([face(vector, 44)], matcher, 2.6, occlusion_scene(44))[0]
    assert label.match.person_id == "a"
    assert not label.tracked


def test_visual_tracking_has_no_timeout_without_face_reconfirmation(matcher, vector, occlusion_scene):
    tracker = Tracker()
    confirm(tracker, matcher, vector, occlusion_scene)
    for index in range(1, 201):
        dx = (index//10) % 4
        labels = tracker.update([], matcher, .2+index*1.2, occlusion_scene(dx, True))
        assert len(labels) == 1
        assert labels[0].match.person_id == "a"
        assert labels[0].tracked
        assert labels[0].bbox[0] == pytest.approx(80+dx, abs=2)
    # After four minutes without a face, a real loss of visual evidence ends tracking.
    assert not tracker.update([], matcher, 241, occlusion_scene(present=False))


def test_head_can_leave_image_while_shoulders_remain_visible(matcher, vector, occlusion_scene):
    tracker = Tracker()
    confirm(tracker, matcher, vector, occlusion_scene)
    for index in range(1, 19):
        transform = np.float32([[1, 0, 0], [0, 1, -index*5]])
        image = cv2.warpAffine(occlusion_scene(covered=True), transform, (240, 200))
        labels = tracker.update([], matcher, .2+index*.2, image)
        assert len(labels) == 1
        assert labels[0].match.person_id == "a"
        assert labels[0].tracked
    assert labels[0].bbox[3] < 0


def test_departure_stops_presence_and_cannot_reuse_old_motion_points(matcher, vector, occlusion_scene):
    tracker = Tracker()
    confirm(tracker, matcher, vector, occlusion_scene)
    assert not tracker.update([], matcher, .4, occlusion_scene(present=False))
    assert not tracker.update([], matcher, .6, occlusion_scene(4, True))


def test_unknown_newcomer_cannot_reuse_identity_after_visual_departure(matcher, vector, occlusion_scene):
    tracker = Tracker()
    confirm(tracker, matcher, vector, occlusion_scene)
    assert not tracker.update([], matcher, .4, occlusion_scene(present=False))
    label = tracker.update([face(np.roll(vector, 1))], matcher, .6, occlusion_scene(covered=True))[0]
    assert label.match.person_id is None
    assert not label.tracked


def test_detector_loss_without_visual_evidence_does_not_report_presence(matcher, vector):
    tracker = Tracker()
    confirm(tracker, matcher, vector)
    assert not tracker.update([], matcher, .4)


def test_weak_spatial_overlap_does_not_inherit_name(matcher, vector):
    tracker = Tracker()
    confirm(tracker, matcher, vector)
    label = tracker.update([face(np.roll(vector, 1), 28)], matcher, .4)[0]
    assert label.match.person_id is None


@pytest.mark.parametrize("detected", [False, True])
def test_fast_side_to_side_motion_retains_identity(matcher, vector, occlusion_scene, detected):
    tracker = Tracker()
    confirm(tracker, matcher, vector, occlusion_scene)
    for index, dx in enumerate((60, -30, 70, 0), start=1):
        detections = [face(np.roll(vector, 1), dx)] if detected else []
        labels = tracker.update(detections, matcher, .2+index*.2, occlusion_scene(dx, True))
        assert len(labels) == 1
        assert labels[0].match.person_id == "a"
        assert labels[0].tracked
        assert labels[0].bbox[0] == pytest.approx(80+dx, abs=3)


def test_shaking_head_keeps_identity_when_shoulders_are_stationary(matcher, vector, occlusion_scene):
    tracker = Tracker()
    confirm(tracker, matcher, vector, occlusion_scene)
    original = occlusion_scene()
    for index, head_dx in enumerate((35, -35, 30, -30, 0), start=1):
        image = original.copy()
        image[30:80] = 0
        image[30:80, 80+head_dx:130+head_dx] = original[30:80, 80:130]
        image[30:80] = cv2.GaussianBlur(image[30:80], (9, 9), 0)
        labels = tracker.update([face(np.roll(vector, 1), head_dx)], matcher, .2+index*.2, image)
        assert len(labels) == 1
        assert labels[0].match.person_id == "a"
        assert labels[0].tracked
    assert tracker.update([], matcher, 1.4, occlusion_scene(covered=True))[0].match.person_id == "a"


def test_confirmed_face_reassociates_after_large_jump_without_overlap(matcher, vector):
    tracker = Tracker()
    confirm(tracker, matcher, vector)
    labels = tracker.update([face(vector, 100)], matcher, .4)
    assert len(labels) == 1
    assert labels[0].match.person_id == "a"
    assert not labels[0].tracked


def test_fast_motion_does_not_attach_unknown_with_different_torso(matcher, vector, occlusion_scene):
    tracker = Tracker()
    confirm(tracker, matcher, vector, occlusion_scene)
    stranger = occlusion_scene(60, True)
    stranger[80:160, 125:205] = np.random.default_rng(99).integers(30, 230, (80, 80, 3), dtype=np.uint8)
    labels = tracker.update([face(np.roll(vector, 1), 60)], matcher, .4, stranger)
    assert len(labels) == 1
    assert labels[0].match.person_id is None


def test_large_jump_with_motion_blur_can_recover_shoulder_appearance(matcher, vector, occlusion_scene):
    tracker = Tracker()
    confirm(tracker, matcher, vector, occlusion_scene)
    image = cv2.GaussianBlur(occlusion_scene(60, True), (7, 7), 0)
    labels = tracker.update([], matcher, .4, image)
    assert len(labels) == 1
    assert labels[0].match.person_id == "a"
    assert labels[0].bbox[0] == pytest.approx(140, abs=3)


def test_body_recovery_rejects_two_equally_matching_people(matcher, vector, occlusion_scene, monkeypatch):
    tracker = Tracker()
    confirm(tracker, matcher, vector, occlusion_scene)
    # Simulate optical-flow failure; appearance alone must not choose between
    # two people whose visible clothing is identical to the reference.
    monkeypatch.setattr("app.services.tracker.follow_points", lambda *args: None)
    image = occlusion_scene(present=False)
    left, right = occlusion_scene(-50, True), occlusion_scene(70, True)
    image[:, :110] = left[:, :110]
    image[:, 110:] = right[:, 110:]
    assert not tracker.update([], matcher, .4, image)


def test_two_nearby_unknown_heads_cannot_both_inherit_shoulder_track(matcher, vector, occlusion_scene):
    tracker = Tracker()
    confirm(tracker, matcher, vector, occlusion_scene)
    unknown = np.roll(vector, 1)
    detections = [face(unknown, 35), face(unknown, -35)]
    labels = tracker.update(detections, matcher, .4, occlusion_scene(covered=True))
    assert len(labels) == 2
    assert all(label.match.person_id is None for label in labels)


def test_crossing_faces_do_not_inherit_ambiguous_identities(matcher, vector):
    tracker = Tracker()
    known = [face(vector), face(np.roll(vector, 2), 40)]
    tracker.update(known, matcher, 0)
    assert [label.match.person_id for label in tracker.update(known, matcher, .2)] == ["a", "b"]
    unknown = np.roll(vector, 1)
    labels = tracker.update([face(unknown, 20), face(unknown, 21)], matcher, .4)
    assert len(labels) == 2
    assert all(label.match.person_id is None for label in labels)


@pytest.mark.parametrize("reverse", [False, True])
def test_one_track_cannot_label_two_faces(matcher, vector, reverse):
    tracker = Tracker()
    confirm(tracker, matcher, vector)
    unknown = np.roll(vector, 1)
    detections = [face(unknown), face(unknown, 28)]
    if reverse:
        detections.reverse()
    labels = tracker.update(detections, matcher, .4)
    assert sum(label.match.person_id == "a" for label in labels) == 1
    assert next(label for label in labels if label.match.person_id).bbox == face(unknown).bbox


def test_backward_time_requires_new_confirmation(matcher, vector):
    tracker = Tracker()
    confirm(tracker, matcher, vector)
    assert tracker.update([face(vector)], matcher, .1)[0].match.person_id is None
    assert tracker.update([face(vector)], matcher, .2)[0].match.person_id == "a"


def test_new_resolution_drops_visual_identity(matcher, vector, occlusion_scene):
    tracker = Tracker()
    confirm(tracker, matcher, vector, occlusion_scene)
    image = np.zeros((100, 120, 3), np.uint8)
    assert not tracker.update([], matcher, .4, image)


def test_tracking_text_setting_round_trip_ignores_obsolete_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv("FACETRACK_HOME", str(tmp_path))
    path = tmp_path/"settings.json"
    path.write_text(json.dumps({"tracking_hold_seconds": 0, "show_name": False}), encoding="utf-8")
    settings = Settings.load()
    assert settings.show_tracking_status
    assert not settings.show_name
    assert not hasattr(settings, "tracking_hold_seconds")
    settings.show_tracking_status = False
    settings.save()
    assert not Settings.load().show_tracking_status
    assert "tracking_hold_seconds" not in json.loads(path.read_text("utf-8"))

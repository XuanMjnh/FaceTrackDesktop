import numpy as np
import pytest
from app.services.face_matcher import FaceMatcher, normalize
from app.services.tracker import Tracker
from app.models.schemas import Detection


def test_known_and_unknown(vector):
    matcher = FaceMatcher([{"person_id":"a", "name":"Ánh", "embedding": vector}])
    assert matcher.match(vector*4).name == "Ánh"
    unknown = np.roll(vector, 1)
    assert matcher.match(unknown).person_id is None


def test_multiple_references_and_ambiguous_people(vector):
    rows = [{"person_id":"a", "name":"A", "embedding": vector},
            {"person_id":"a", "name":"A", "embedding": np.roll(vector, 1)}]
    assert FaceMatcher(rows).match(np.roll(vector, 1)).person_id == "a"
    rows.append({"person_id":"b", "name":"B", "embedding": vector})
    assert FaceMatcher(rows).match(vector).person_id is None


@pytest.mark.parametrize("bad", [np.zeros(512), np.ones(4), np.full(512, np.nan), np.full(512, np.inf)])
def test_invalid_embedding_rejected(bad):
    with pytest.raises(ValueError):
        normalize(bad)


def test_tracker_requires_confirmation_and_drops_low_confidence(vector):
    matcher = FaceMatcher([{"person_id":"a", "name":"A", "embedding":vector}])
    tracker = Tracker()
    known = Detection((0,0,100,100), vector)
    assert tracker.update([known], matcher, 0)[0].match.person_id is None
    assert tracker.update([known], matcher, .1)[0].match.person_id == "a"
    unknown = Detection((0,0,100,100), np.roll(vector, 1))
    assert tracker.update([unknown], matcher, .2)[0].match.person_id is None


def test_inactive_profiles_not_in_gallery(db, person, vector):
    db.add_reference(person, "ref.jpg", vector)
    db.edit_person(person, "Ánh", False)
    assert not db.gallery()

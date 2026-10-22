import numpy as np
import pytest
import cv2
from app.models.schemas import Detection
from app.services.enrollment import Enrollment


class FakeEngine:
    def __init__(self, faces):
        self.faces = faces

    def detect(self, image):
        return self.faces


def photo(tmp_path):
    path = tmp_path/"ảnh.png"
    ok, encoded = cv2.imencode(".png", np.full((150,150,3), 128, np.uint8))
    assert ok
    encoded.tofile(str(path))
    return path


def test_valid_registration_and_duplicate_warning(db, vector, tmp_path):
    service = Enrollment(db, FakeEngine([Detection((10,10,100,100), vector)]), tmp_path/"images")
    inspected = service.inspect(photo(tmp_path))
    pid = service.save("Ánh", inspected)
    assert len(db.references(pid)) == 1
    assert service.inspect(photo(tmp_path))[2].person_id == pid
    assert len(db.gallery()) == 1


@pytest.mark.parametrize("count", [0, 2])
def test_no_face_or_many_faces_rejected(db, vector, tmp_path, count):
    service = Enrollment(db, FakeEngine([Detection((0,0,100,100), vector)]*count), tmp_path/"images")
    with pytest.raises(ValueError):
        service.inspect(photo(tmp_path))
    assert not db.persons()


def test_reference_replacement(db, vector, tmp_path):
    service = Enrollment(db, FakeEngine([Detection((0,0,100,100), vector)]), tmp_path/"images")
    inspected = service.inspect(photo(tmp_path))
    pid = service.save("Ánh", inspected)
    old = db.references(pid)[0]
    service.save("Ánh", inspected, pid, old["id"])
    from pathlib import Path
    assert not Path(old["image_path"]).exists()
    assert len(db.references(pid)) == 1

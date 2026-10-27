import numpy as np
import pytest
from app.services.database import Database


@pytest.fixture
def db(tmp_path):
    service = Database(tmp_path/"test.sqlite3")
    yield service
    service.close()


@pytest.fixture
def vector():
    value = np.zeros(512, np.float32)
    value[0] = 1
    return value


@pytest.fixture
def person(db):
    return db.add_person("Nguyễn Thị Ánh")


@pytest.fixture
def occlusion_scene():
    """A moving textured torso remains visible when the face is covered."""
    rng = np.random.default_rng(12)
    torso = rng.integers(30, 230, (80, 80, 3), dtype=np.uint8)
    face = rng.integers(60, 200, (50, 50, 3), dtype=np.uint8)

    def render(dx=0, covered=False, present=True):
        image = np.zeros((200, 240, 3), np.uint8)
        if present:
            image[80:160, 65+dx:145+dx] = torso
            image[30:80, 80+dx:130+dx] = 150 if covered else face
        return image

    return render

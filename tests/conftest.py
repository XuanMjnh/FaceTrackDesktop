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

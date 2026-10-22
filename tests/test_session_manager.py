from app.services.session_manager import SessionManager


def test_fifteen_minutes_is_one_session(db, person):
    sessions = SessionManager(db, "camera", "camera:0", flush_seconds=0)
    for seconds in range(901):
        sessions.observe([(person, "Nguyễn Thị Ánh")], 1_700_000_000+seconds, seconds)
    sessions.close()
    rows = db.history()
    assert len(rows) == 1
    assert rows[0]["last_seen"]-rows[0]["first_seen"] == 900


def test_brief_occlusion_then_timeout_without_empty_frame(db, person):
    sessions = SessionManager(db, "camera", "cam", absence=30)
    sessions.observe([(person, "A")], 1000, 0)
    sessions.observe([(person, "A")], 1029, 29)
    sessions.observe([(person, "A")], 1060, 60)
    sessions.close()
    rows = sorted(db.history(), key=lambda r: r["first_seen"])
    assert len(rows) == 2
    assert rows[0]["last_seen"] == 1029
    assert rows[1]["first_seen"] == 1060


def test_checkout_is_last_observation_not_expiration(db, person):
    s = SessionManager(db, "camera", "cam")
    s.observe([(person, "A")], 1000, 0)
    s.observe([(person, "A")], 1010, 10)
    s.observe([], 1041, 41)
    assert db.history()[0]["last_seen"] == 1010
    assert db.history()[0]["status"] == "closed"


def test_many_people_and_safe_shutdown(db, person):
    second = db.add_person("Trần Bình")
    s = SessionManager(db, "camera", "cam")
    s.observe([(person, "A"), (second, "B"), (person, "A")], 100, 0)
    s.observe([(second, "B")], 105, 5)
    s.close()
    assert len(db.history()) == 2
    assert {r["status"] for r in db.history()} == {"closed"}


def test_monotonic_clock_independent_of_wall_clock(db, person):
    s = SessionManager(db, "camera", "cam")
    s.observe([(person, "A")], 1000, 0)
    s.observe([(person, "A")], 990, 10)
    s.close()
    assert len(db.history()) == 1
    assert db.history()[0]["last_seen"] >= db.history()[0]["first_seen"]


def test_delete_history_preserves_profiles_and_embeddings(db, person, vector):
    db.add_reference(person, "x.jpg", vector)
    s = SessionManager(db, "camera", "cam")
    s.observe([(person, "A")], 1, 0)
    s.close()
    db.delete_history()
    assert not db.history()
    assert db.persons()[0]["id"] == person
    assert len(db.gallery()) == 1


def test_delete_person_preserves_history_snapshot(db, person):
    s = SessionManager(db, "camera", "cam")
    s.observe([(person, "Tên lúc ghi")], 1, 0)
    s.close()
    db.delete_person(person)
    assert not db.persons()
    row = db.history()[0]
    assert row["person_id"] == person
    assert row["person_ref"] is None
    assert row["person_name"] == "Tên lúc ghi"


def test_recovery_closes_open_session(tmp_path):
    from app.services.database import Database
    path = tmp_path/"recover.sqlite3"
    db = Database(path)
    pid = db.add_person("A")
    s = SessionManager(db, "camera", "cam")
    s.observe([(pid, "A")], 100, 0)
    db.close()  # Simulated exit without session finalization.
    db = Database(path)
    try:
        assert db.history()[0]["status"] == "closed"
        assert len(db.persons()) == 1
    finally:
        db.close()

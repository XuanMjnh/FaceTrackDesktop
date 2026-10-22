import pytest
from app.services.session_manager import SessionManager
from app.services.video_service import frame_timestamp, video_source


def segment(db, pid, first, last, source="same"):
    s = SessionManager(db, "video", source)
    for stamp in range(first, last+1, 5):
        s.observe([(pid, "A")], stamp, stamp)
    s.close()


def test_backward_reanalysis_merges_intervals(db, person):
    segment(db, person, 100, 160)
    segment(db, person, 120, 180)
    segment(db, person, 50, 110)
    rows = db.history()
    assert len(rows) == 1
    assert rows[0]["first_seen_ms"] == 50000
    assert rows[0]["last_seen_ms"] == 180000


def test_disjoint_sessions_and_different_sources_remain_separate(db, person):
    segment(db, person, 0, 10)
    segment(db, person, 100, 110)
    segment(db, person, 0, 10, "another")
    assert len(db.history()) == 3


def test_transitive_interval_union(db, person):
    segment(db, person, 0, 10)
    segment(db, person, 70, 80)
    segment(db, person, 35, 55)
    assert len(db.history()) == 1
    assert db.history()[0]["last_seen"] == 80


def test_pause_does_not_advance_media_clock(db, person):
    s = SessionManager(db, "video", "clip")
    s.observe([(person, "A")], 10, 10)
    # Arbitrary wall-clock pause: only media time is supplied on resume.
    s.observe([(person, "A")], 10.04, 10.04)
    s.close()
    assert len(db.history()) == 1
    assert db.history()[0]["last_seen"] == 10.04


@pytest.mark.parametrize("pos,index,fps,expected", [(1000,25,25,1), (0,50,25,2), (0,1,25,.04), (float('nan'),50,25,2), (90000,25,25,1)])
def test_timestamps(pos, index, fps, expected):
    assert frame_timestamp(pos, index, fps) == expected


def test_invalid_fps():
    with pytest.raises(ValueError):
        frame_timestamp(1000, 25, 0)


def test_hash_identity_survives_rename_and_detects_changed_bytes(tmp_path):
    path = tmp_path/"a.mp4"
    path.write_bytes(b"video-content")
    first = video_source(path)
    second_path = tmp_path/"b.mp4"
    path.rename(second_path)
    assert video_source(second_path) == first
    second_path.write_bytes(b"other-video-content")
    assert video_source(second_path) != first


def test_source_and_timeline_filter(db, person):
    segment(db, person, 0, 10, "source-A")
    segment(db, person, 100, 110, "source-B")
    assert len(db.history(kind="video", source_query="source-A", media_start=2, media_end=8)) == 1
    assert not db.history(start=1_000_000)

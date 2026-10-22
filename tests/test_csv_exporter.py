import csv
from app.services.csv_exporter import HEADERS, export_csv, timeline


def test_vietnamese_bom_four_columns_and_source(tmp_path):
    path = tmp_path/"history.csv"
    row = {"person_id":"p", "person_name":"Nguyễn Thị Ánh", "source_type":"video", "source_id":"sha256:abc", "first_seen":1.25, "last_seen":20}
    assert export_csv(path, [row, row]) == 2
    assert path.read_bytes().startswith(b'\xef\xbb\xbf')
    with path.open(encoding="utf-8-sig", newline="") as f:
        result = list(csv.reader(f))
    assert result[0] == HEADERS
    assert len(result) == 3 and all(len(r) == 4 for r in result)
    assert result[1][1] == "Nguyễn Thị Ánh"
    assert result[1][2] == "Video [sha256:abc] 00:00:01.250"


def test_formula_neutralization_and_camera_timezone(tmp_path):
    path = tmp_path/"safe.csv"
    row = {"person_id":"p", "person_name":"=1+1", "source_type":"camera", "source_id":"cam", "first_seen":1700000000, "last_seen":1700000001}
    export_csv(path, [row])
    data = path.read_text("utf-8-sig")
    assert "'=1+1" in data
    assert "2023-" in data
    assert "Video" not in data


def test_long_timeline():
    assert timeline(90061.123) == "25:01:01.123"

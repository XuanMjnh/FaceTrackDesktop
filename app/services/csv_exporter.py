import csv
from datetime import datetime

HEADERS = ["Mã ID", "Họ tên", "Giờ xuất hiện đầu tiên - Check-in", "Giờ xuất hiện cuối cùng - Check-out"]


def timeline(seconds):
    millis = max(0, round(seconds * 1000))
    hours, rem = divmod(millis, 3600000)
    minutes, rem = divmod(rem, 60000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def display_time(row, field):
    if row["source_type"] == "video":
        return f"Video [{row['source_id']}] {timeline(row[field])}"
    return datetime.fromtimestamp(row[field]).astimezone().isoformat(timespec="milliseconds")


def safe_cell(value):
    text = str(value)
    # Prevent names/IDs being interpreted as spreadsheet formulas.
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def export_csv(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADERS)
        for row in rows:
            writer.writerow([safe_cell(row["person_id"]), safe_cell(row["person_name"]),
                             display_time(row, "first_seen"), display_time(row, "last_seen")])
    return len(rows)

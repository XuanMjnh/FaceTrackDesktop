"""A single SQLite owner thread. All public calls execute on that thread."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
import sqlite3
import threading
import uuid
import numpy as np
from app.services.face_matcher import normalize


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def owned(fn):
    @wraps(fn)
    def call(self, *args, **kwargs):
        if threading.get_ident() == self.owner:
            return fn(self, *args, **kwargs)
        return self.executor.submit(fn, self, *args, **kwargs).result()
    return call


class Database:
    def __init__(self, path):
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sqlite")
        self.owner = None
        self.executor.submit(self._open, path).result()

    def _open(self, path):
        self.owner = threading.get_ident()
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), timeout=15)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.executescript('''
        CREATE TABLE IF NOT EXISTS persons(
          id TEXT PRIMARY KEY,name TEXT NOT NULL,created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,is_active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS face_embeddings(
          id TEXT PRIMARY KEY,person_id TEXT NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
          image_path TEXT NOT NULL,embedding BLOB NOT NULL CHECK(length(embedding)=2048),
          created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS embedding_person ON face_embeddings(person_id);
        CREATE TABLE IF NOT EXISTS presence_sessions(
          id TEXT PRIMARY KEY,person_ref TEXT REFERENCES persons(id) ON DELETE SET NULL,
          person_id TEXT NOT NULL,person_name TEXT NOT NULL,source_type TEXT NOT NULL,
          source_id TEXT NOT NULL,first_seen REAL NOT NULL,last_seen REAL NOT NULL,
          first_seen_ms INTEGER,last_seen_ms INTEGER,status TEXT NOT NULL,created_at TEXT NOT NULL,
          CHECK(last_seen>=first_seen));
        CREATE INDEX IF NOT EXISTS session_merge ON presence_sessions(person_id,source_type,source_id,first_seen,last_seen);
        CREATE INDEX IF NOT EXISTS session_time ON presence_sessions(first_seen);
        PRAGMA user_version=1;
        ''')
        # Recover an interrupted run at its last durable successful recognition.
        with self.conn:
            self.conn.execute("UPDATE presence_sessions SET status='closed' WHERE status='open'")

    @owned
    def persons(self, query=""):
        rows = self.conn.execute('''SELECT p.*, (SELECT image_path FROM face_embeddings e
            WHERE e.person_id=p.id ORDER BY created_at LIMIT 1) AS avatar,
            (SELECT count(*) FROM face_embeddings e WHERE e.person_id=p.id) AS images
            FROM persons p ORDER BY p.name COLLATE NOCASE''').fetchall()
        q = query.casefold()
        return [dict(r) for r in rows if q in (r["name"] + " " + r["id"]).casefold()]

    @owned
    def add_person(self, name, person_id=None):
        name = name.strip()
        if not name or len(name) > 200:
            raise ValueError("Họ tên phải từ 1 đến 200 ký tự")
        pid = person_id or str(uuid.uuid4())
        with self.conn:
            self.conn.execute("INSERT INTO persons VALUES(?,?,?,?,1)", (pid, name, now(), now()))
        return pid

    @owned
    def edit_person(self, pid, name, active):
        if not name.strip() or len(name.strip()) > 200:
            raise ValueError("Họ tên phải từ 1 đến 200 ký tự")
        with self.conn:
            self.conn.execute("UPDATE persons SET name=?,is_active=?,updated_at=? WHERE id=?",
                              (name.strip(), int(active), now(), pid))

    @owned
    def references(self, pid):
        return [dict(r) for r in self.conn.execute(
            "SELECT id,image_path,created_at FROM face_embeddings WHERE person_id=? ORDER BY created_at", (pid,))]

    @owned
    def add_reference(self, pid, path, embedding, replace_id=None):
        blob = normalize(embedding).astype("<f4").tobytes()
        old = None
        with self.conn:
            if replace_id:
                row = self.conn.execute("SELECT image_path FROM face_embeddings WHERE id=? AND person_id=?", (replace_id, pid)).fetchone()
                if not row:
                    raise ValueError("Ảnh tham chiếu đã bị xóa")
                old = row[0]
                self.conn.execute("DELETE FROM face_embeddings WHERE id=?", (replace_id,))
            self.conn.execute("INSERT INTO face_embeddings VALUES(?,?,?,?,?)", (str(uuid.uuid4()), pid, str(path), blob, now()))
        return old

    @owned
    def delete_reference(self, rid):
        row = self.conn.execute("SELECT image_path FROM face_embeddings WHERE id=?", (rid,)).fetchone()
        with self.conn:
            self.conn.execute("DELETE FROM face_embeddings WHERE id=?", (rid,))
        return row[0] if row else None

    @owned
    def delete_person(self, pid):
        paths = [r[0] for r in self.conn.execute("SELECT image_path FROM face_embeddings WHERE person_id=?", (pid,))]
        with self.conn:
            self.conn.execute("DELETE FROM persons WHERE id=?", (pid,))
        return paths

    @owned
    def gallery(self):
        return [{"person_id": r[0], "name": r[1], "embedding": np.frombuffer(r[2], dtype="<f4").copy()}
                for r in self.conn.execute('''SELECT p.id,p.name,e.embedding FROM persons p
                JOIN face_embeddings e ON e.person_id=p.id WHERE p.is_active=1''')]

    @owned
    def save_session(self, sid, pid, name, kind, source, first, last, status, gap):
        """Merge video intervals transactionally, including transitive overlaps on replay."""
        first, last = sorted((float(first), float(last)))
        with self.conn:
            if kind == "video":
                # Expand until no further neighbor can join the interval.
                merged = set()
                while True:
                    rows = self.conn.execute('''SELECT id,first_seen,last_seen FROM presence_sessions
                        WHERE person_id=? AND source_type='video' AND source_id=?
                        AND first_seen<=? AND last_seen>=?''', (pid, source, last + gap, first - gap)).fetchall()
                    ids = {r[0] for r in rows}
                    if ids <= merged:
                        break
                    merged |= ids
                    first = min([first] + [r[1] for r in rows])
                    last = max([last] + [r[2] for r in rows])
                if merged:
                    sid = sorted(merged)[0]
                    self.conn.executemany("DELETE FROM presence_sessions WHERE id=?", [(i,) for i in merged])
            exists = self.conn.execute("SELECT 1 FROM persons WHERE id=?", (pid,)).fetchone()
            self.conn.execute('''INSERT INTO presence_sessions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen,
                last_seen_ms=excluded.last_seen_ms,status=excluded.status''',
                (sid, pid if exists else None, pid, name, kind, source, first, last,
                 round(first * 1000) if kind == "video" else None,
                 round(last * 1000) if kind == "video" else None, status, now()))
        return sid

    @owned
    def history(self, query="", start=None, end=None, kind="all", source_query="", media_start=None, media_end=None):
        sql = "SELECT * FROM presence_sessions WHERE 1=1"
        args = []
        if kind != "all":
            sql += " AND source_type=?"
            args.append(kind)
        # Calendar filters apply only to camera; videos have no invented recording date.
        for value, op in ((start, ">="), (end, "<=")):
            if value is not None:
                sql += f" AND source_type='camera' AND first_seen{op}?"
                args.append(value)
        for value, col, op in ((media_start, "last_seen", ">="), (media_end, "first_seen", "<=")):
            if value is not None:
                sql += f" AND source_type='video' AND {col}{op}?"
                args.append(value)
        rows = self.conn.execute(sql + " ORDER BY first_seen DESC", args).fetchall()
        return [dict(r) for r in rows if query.casefold() in (r["person_name"] + " " + r["person_id"]).casefold()
                and source_query.casefold() in r["source_id"].casefold()]

    @owned
    def delete_history(self, ids=None):
        with self.conn:
            if ids is None:
                self.conn.execute("DELETE FROM presence_sessions")
            else:
                self.conn.executemany("DELETE FROM presence_sessions WHERE id=?", [(i,) for i in ids])

    def close(self):
        self.executor.submit(self.conn.close).result()
        self.executor.shutdown(wait=True)

from dataclasses import dataclass
import time
import uuid


@dataclass
class Presence:
    sid: str
    pid: str
    name: str
    first: float
    last: float
    clock: float
    dirty: bool = True


class SessionManager:
    """One instance per analysis stream; called only under the epoch gate.

    Camera expiration uses monotonic time, video expiration uses media time.
    Pause produces no ticks. Seeking closes the current segment before a new one.
    """
    def __init__(self, db, kind, source, absence=30, flush_seconds=2):
        self.db, self.kind, self.source = db, kind, source
        self.absence = absence
        self.flush_seconds = flush_seconds
        self.active = {}
        self.flushed_at = time.monotonic()

    def _save(self, p, status):
        p.sid = self.db.save_session(p.sid, p.pid, p.name, self.kind, self.source,
                                     p.first, p.last, status, self.absence)
        p.dirty = False

    def observe(self, matches, timestamp, clock):
        # Expire BEFORE consuming observations; a return after timeout is a new session.
        for pid, p in list(self.active.items()):
            if clock - p.clock > self.absence:
                self._save(p, "closed")
                del self.active[pid]
        for pid, name in dict(matches).items():
            p = self.active.get(pid)
            if p is None:
                p = Presence(str(uuid.uuid4()), pid, name, timestamp, timestamp, clock)
                self.active[pid] = p
                self._save(p, "open")
            else:
                p.last = max(p.last, timestamp)
                p.clock = clock
                p.dirty = True
        if time.monotonic() - self.flushed_at >= self.flush_seconds:
            self.flush()

    def flush(self):
        for p in self.active.values():
            if p.dirty:
                self._save(p, "open")
        self.flushed_at = time.monotonic()

    def close(self):
        for p in self.active.values():
            self._save(p, "closed")
        self.active.clear()

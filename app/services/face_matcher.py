import numpy as np
from app.models.schemas import Match


def normalize(vector):
    v = np.asarray(vector, dtype=np.float32).reshape(-1)
    n = float(np.linalg.norm(v))
    if v.size != 512 or not np.isfinite(v).all() or not np.isfinite(n) or n < 1e-8:
        raise ValueError("Embedding phải là vector 512 chiều hữu hạn, khác 0")
    return v / n


class FaceMatcher:
    """Immutable gallery snapshot; maximum similarity across each person's references."""
    def __init__(self, rows=(), threshold=0.45, margin=0.04):
        self.threshold = threshold
        self.margin = margin
        self.people = [(r["person_id"], r["name"]) for r in rows]
        self.matrix = np.stack([normalize(r["embedding"]) for r in rows]) if rows else np.empty((0, 512), np.float32)

    def match(self, vector):
        if not self.people:
            return Match(None, "Không xác định", 0.0)
        scores = self.matrix @ normalize(vector)
        best_by_person = {}
        for (pid, name), score in zip(self.people, scores):
            if pid not in best_by_person or score > best_by_person[pid][1]:
                best_by_person[pid] = (name, float(score))
        ranked = sorted(best_by_person.items(), key=lambda r: r[1][1], reverse=True)
        pid, (name, score) = ranked[0]
        ambiguous = len(ranked) > 1 and score - ranked[1][1][1] < self.margin
        if score < self.threshold or ambiguous:
            return Match(None, "Không xác định", score)
        return Match(pid, name, score)

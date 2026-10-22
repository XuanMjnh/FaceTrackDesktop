"""Conservative IoU association plus consecutive embedding votes.

No identity is carried through a failed similarity threshold. This deliberately
prefers an unknown label over retaining a previous person's name on a crossing.
"""
from dataclasses import dataclass
from app.models.schemas import FaceLabel, Match


def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0, x2-x1) * max(0, y2-y1)
    area = max(0, a[2]-a[0])*max(0, a[3]-a[1]) + max(0, b[2]-b[0])*max(0, b[3]-b[1])
    return intersection / max(area-intersection, 1e-8)


@dataclass
class Track:
    box: tuple
    candidate: str | None
    votes: int
    seen: float


class Tracker:
    def __init__(self, confirmations=2):
        self.confirmations = confirmations
        self.tracks = []

    def update(self, detections, matcher, clock):
        previous = [t for t in self.tracks if 0 <= clock-t.seen <= 2]
        used, current, labels = set(), [], []
        for det in detections:
            match = matcher.match(det.embedding)
            choices = [(iou(det.bbox, t.box), i, t) for i, t in enumerate(previous) if i not in used]
            score, index, track = max(choices, default=(0, -1, None), key=lambda item: item[0])
            votes = 1
            if score >= 0.25:
                used.add(index)
                if match.person_id is not None and track.candidate == match.person_id:
                    votes = track.votes + 1
            current.append(Track(det.bbox, match.person_id, votes, clock))
            if votes < self.confirmations:
                match = Match(None, "Không xác định", match.score)
            labels.append(FaceLabel(det.bbox, match))
        self.tracks = current
        return labels

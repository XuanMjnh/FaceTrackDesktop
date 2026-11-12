"""Face confirmation with motion-supported identity retention."""
from dataclasses import dataclass
import numpy as np
from app.models.schemas import FaceLabel, Match
from app.services.visual_motion import VisualMotion


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
    confirmed: Match | None = None
    verified: float = 0.0
    points: np.ndarray | None = None


class Tracker:
    def __init__(self, confirmations=2, max_gap=2.0):
        self.confirmations = confirmations
        self.max_gap = max_gap
        self.tracks = []
        self.motion = VisualMotion()
        self.image_shape = None

    def update(self, detections, matcher, clock, image=None):
        previous = [t for t in self.tracks if 0 <= clock-t.seen <= self.max_gap]
        shape = image.shape[:2] if image is not None else None
        if shape != self.image_shape:
            previous = []
            self.motion.gray = None
            self.image_shape = shape
        matches = [matcher.match(det.embedding) for det in detections]
        gray = self.motion.prepare(image) if image is not None and (
            any(t.confirmed for t in previous) or any(m.person_id for m in matches)
        ) else None
        # A clear face near its last position already supplies stronger evidence.
        # Spend LK work only on tracks that need visual continuity or recovery.
        needed = {i for i, t in enumerate(previous) if t.confirmed and not any(
            m.person_id == t.confirmed.person_id and iou(det.bbox, t.box) >= 0.5
            for det, m in zip(detections, matches)
        )}
        predictions = self.motion.predict(previous, gray, needed)
        boxes = [predictions[i][0] if i in predictions else t.box for i, t in enumerate(previous)]

        # Associate globally, independent of detector ordering. Ambiguous overlaps
        # must earn a fresh face confirmation instead of inheriting a name.
        overlaps = [[iou(det.bbox, box) for box in boxes] for det in detections]
        pairs = sorted(((score, d, t) for d, row in enumerate(overlaps)
                        for t, score in enumerate(row) if score >= 0.25), reverse=True)
        assigned, used = {}, set()
        for score, d, t in pairs:
            if d in assigned or t in used:
                continue
            alternatives = [s for j, s in enumerate(overlaps[d]) if j != t and s >= 0.25]
            alternatives += [row[t] for j, row in enumerate(overlaps) if j != d and row[t] >= 0.25]
            if alternatives and score - max(alternatives) < 0.1:
                continue
            assigned[d] = t
            used.add(t)

        current, labels = [], []
        for d, (det, match) in enumerate(zip(detections, matches)):
            index = assigned.get(d)
            old = previous[index] if index is not None else None
            votes = old.votes + 1 if old and match.person_id and old.candidate == match.person_id else 1
            confirmed, verified = None, clock
            retained = False
            if match.person_id and (votes >= self.confirmations or (
                old and old.confirmed and old.confirmed.person_id == match.person_id
            )):
                confirmed = match
            elif old and old.confirmed and match.person_id is None:
                # Geometry covers a brief transition while a hand enters the face.
                # Longer retention requires valid image motion when frames exist.
                continuity = index in predictions or (
                    overlaps[d][index] >= 0.6 and (image is None or clock-old.verified <= 0.75)
                )
                if continuity:
                    confirmed, verified, retained = old.confirmed, old.verified, True
            track = Track(det.bbox, match.person_id, votes, clock, confirmed, verified)
            if confirmed and gray is not None:
                track.points = self.motion.seed(gray, det.bbox)
            current.append(track)
            displayed = confirmed or Match(None, "Không xác định", match.score)
            labels.append(FaceLabel(det.bbox, displayed, retained))

        # With no face detection, retain confirmed identities for as long as
        # optical flow supports continuous tracking.
        for i, old in enumerate(previous):
            if i in used or not old.confirmed or i not in predictions:
                continue
            box, points = predictions[i]
            if any(iou(box, det.bbox) >= 0.15 for det in detections):
                continue
            if any(i != j and iou(box, other) >= 0.25 for j, other in enumerate(boxes)):
                continue
            current.append(Track(box, None, 0, clock, old.confirmed, old.verified, points))
            labels.append(FaceLabel(box, old.confirmed, True))

        self.tracks = current
        self.motion.gray = gray
        return labels

"""Confirm face identities, then follow visual evidence through face occlusion."""
from collections import Counter
from dataclasses import dataclass

import cv2
import numpy as np

from app.models.schemas import FaceLabel, Match


def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0, x2-x1) * max(0, y2-y1)
    area = max(0, a[2]-a[0])*max(0, a[3]-a[1]) + max(0, b[2]-b[0])*max(0, b[3]-b[1])
    return intersection / max(area-intersection, 1e-8)


@dataclass
class BodyAnchor:
    template: np.ndarray
    box: tuple
    face_box: tuple  # Neutral head position relative to the tracked shoulders.


@dataclass
class Track:
    box: tuple
    candidate: str | None
    votes: int
    identity: Match | None = None
    points: np.ndarray | None = None
    body: BodyAnchor | None = None


def shifted(box, dx, dy):
    return tuple(float(value + (dx if index % 2 == 0 else dy)) for index, value in enumerate(box))


def move_body(body, dx, dy):
    if body is None:
        return None
    return BodyAnchor(body.template, shifted(body.box, dx, dy), shifted(body.face_box, dx, dy))


def shoulder_region(gray, box):
    x1, y1, x2, y2 = box
    width, height = x2-x1, y2-y1
    rows, cols = gray.shape
    return (max(0, int(x1-.25*width)), max(0, int(y2+.1*height)),
            min(cols, int(x2+.25*width)), min(rows, int(y2+1.5*height)))


def body_points(gray, box):
    """Anchor below the chin so head rotation does not move the shoulders."""
    left, top, right, bottom = shoulder_region(gray, box)
    if right <= left or bottom <= top:
        return None
    mask = np.zeros_like(gray)
    mask[top:bottom, left:right] = 255
    return cv2.goodFeaturesToTrack(gray, 60, .03, 5, mask=mask, blockSize=5)


def remember_body(gray, box):
    left, top, right, bottom = shoulder_region(gray, box)
    if right-left < 12 or bottom-top < 12:
        return None
    template = cv2.GaussianBlur(gray[top:bottom, left:right], (5, 5), 0)
    if template.std() < 5:
        return None
    return BodyAnchor(template, (left, top, right, bottom), box)


def recover_body(gray, track):
    """Recover large jumps from a distinctive shoulder patch, not elapsed time.

    Reject weak or competing peaks rather than attaching the identity to a
    similar nearby person. Only a face match refreshes the reference appearance.
    """
    body = track.body
    if body is None or gray is None:
        return None
    x1, y1, x2, y2 = body.box
    height, width = body.template.shape
    radius = max(width, height)*2
    left, top = max(0, int(x1-radius)), max(0, int(y1-radius))
    right, bottom = min(gray.shape[1], int(x2+radius)), min(gray.shape[0], int(y2+radius))
    if right-left < width or bottom-top < height:
        return None
    search = cv2.GaussianBlur(gray[top:bottom, left:right], (5, 5), 0)
    scores = cv2.matchTemplate(search, body.template, cv2.TM_CCOEFF_NORMED)
    _, best, _, position = cv2.minMaxLoc(scores)
    if not np.isfinite(best) or best < .78:
        return None
    px, py = position
    scores[max(0, py-height//3):py+height//3+1, max(0, px-width//3):px+width//3+1] = -1
    if best-float(scores.max()) < .08:
        return None
    dx, dy = left+px-x1, top+py-y1
    moved = move_body(body, dx, dy)
    points = body_points(gray, moved.face_box)
    return moved.face_box, points, moved


def follow_points(before, gray, track):
    """Forward/backward optical flow with a majority agreeing on translation.

    Never reseed on an occluded frame: that could start following the hand or
    background instead. A successful face match supplies fresh anchor points.
    """
    points = track.points
    if before is None or gray is None or points is None or len(points) < 6:
        return None
    # A shallower pyramid can preserve shoulder anchors close to an image edge
    # after the head leaves the image. Both attempts use the same evidence checks.
    return _follow_points(before, gray, track, 3) or _follow_points(before, gray, track, 1)


def _follow_points(before, gray, track, max_level):
    points = track.points
    moved, status, error = cv2.calcOpticalFlowPyrLK(before, gray, points, None, winSize=(21, 21), maxLevel=max_level)
    if moved is None or status is None:
        return None
    back, backward_status, _ = cv2.calcOpticalFlowPyrLK(gray, before, moved, None, winSize=(21, 21), maxLevel=max_level)
    if back is None or backward_status is None:
        return None
    old, new = points.reshape(-1, 2), moved.reshape(-1, 2)
    valid = ((status.ravel() == 1) & (backward_status.ravel() == 1)
             & (np.linalg.norm(back.reshape(-1, 2)-old, axis=1) < 1.5)
             & (error.ravel() < 25) & np.isfinite(new).all(axis=1))
    valid &= (new[:, 0] >= 0) & (new[:, 0] < gray.shape[1]) & (new[:, 1] >= 0) & (new[:, 1] < gray.shape[0])
    if valid.sum() < max(6, len(points)*.5):
        return None
    delta = new[valid]-old[valid]
    motion = np.median(delta, axis=0)
    inliers = np.linalg.norm(delta-motion, axis=1) < max(2.5, (track.box[2]-track.box[0])*.08)
    if inliers.sum() < max(6, len(points)*.5):
        return None
    dx, dy = np.median(delta[inliers], axis=0)
    x1, y1, x2, y2 = track.box
    if abs(dx) > x2-x1 or abs(dy) > y2-y1:
        return None
    body = move_body(track.body, dx, dy)
    box = body.face_box if body else shifted(track.box, dx, dy)
    # The head can be outside the image while shoulder anchors remain visible.
    # The in-frame point checks above decide whether the person is still tracked.
    return box, new[valid][inliers].reshape(-1, 1, 2), body


def head_near_shoulders(box, reference):
    """Allow head movement relative to the shoulders after a valid body update."""
    width, height = reference[2]-reference[0], reference[3]-reference[1]
    return (width > 0 and height > 0
            and abs((box[0]+box[2]-reference[0]-reference[2])/2) <= width*.9
            and abs((box[1]+box[3]-reference[1]-reference[3])/2) <= height*.6
            and .4 <= (box[2]-box[0])/width <= 1.8
            and .5 <= (box[3]-box[1])/height <= 1.8)


class Tracker:
    def __init__(self, confirmations=2):
        self.confirmations = confirmations
        self.tracks = []
        self.gray = None
        self.clock = None

    def update(self, detections, matcher, clock, image=None):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image is not None else None
        # Timeline resets normally arrive as a new pipeline epoch. Also protect
        # standalone callers and source resolution changes.
        if ((self.clock is not None and clock < self.clock)
                or (self.gray is not None and gray is not None and self.gray.shape != gray.shape)):
            self.tracks = []
            self.gray = None
        previous = self.tracks
        predictions = [follow_points(self.gray, gray, t) or recover_body(gray, t) for t in previous]
        boxes = [p[0] if p else t.box for t, p in zip(previous, predictions)]
        matches = [matcher.match(det.embedding) for det in detections]
        scores = [[iou(det.bbox, box) for box in boxes] for det in detections]
        known_detections = Counter(match.person_id for match in matches if match.person_id)
        known_tracks = Counter(t.identity.person_id for t in previous if t.identity)
        for d, (det, match) in enumerate(zip(detections, matches)):
            for t, track in enumerate(previous):
                if (track.identity and match.person_id == track.identity.person_id
                        and known_detections[match.person_id] == 1 and known_tracks[match.person_id] == 1):
                    # A fresh unambiguous face match can jump beyond the old box.
                    scores[d][t] = 2.0
                elif predictions[t] and track.identity and head_near_shoulders(det.bbox, boxes[t]):
                    scores[d][t] = max(scores[d][t], .55)
        # Global greedy association avoids detection-order-dependent track theft.
        pairs = sorted(((score, d, t) for d, row in enumerate(scores)
                        for t, score in enumerate(row) if score >= .25), reverse=True)
        assignments, used = {}, set()
        for score, d, t in pairs:
            if d not in assignments and t not in used:
                assignments[d] = (t, score)
                used.add(t)
        current, labels, blocked = [], [], set()
        for d, (det, match) in enumerate(zip(detections, matches)):
            index, overlap = assignments.get(d, (-1, 0))
            track = previous[index] if index >= 0 else None
            ambiguous = track is not None and (
                any(t != index and s >= .25 and s >= overlap-.1 for t, s in enumerate(scores[d]))
                or any(other != d and row[index] >= .25 and row[index] >= overlap-.1
                       for other, row in enumerate(scores)))
            votes = 1
            identity, points, body = None, None, None
            if track and not ambiguous:
                if match.person_id is not None and track.candidate == match.person_id:
                    votes = track.votes+1
                if track.identity and match.person_id == track.identity.person_id:
                    votes = max(votes, self.confirmations)
                if match.person_id is None and overlap >= .5 and track.identity:
                    identity = track.identity
                    points = predictions[index][1] if predictions[index] else None
                    body = predictions[index][2] if predictions[index] else None
            if match.person_id is not None and votes >= self.confirmations:
                identity = match
                if gray is not None:
                    points = body_points(gray, det.bbox)
                    body = remember_body(gray, det.bbox)
            # Suppress unassigned ghosts where detections overlap old tracks,
            # including crossings and replacement by a different identity.
            blocked.update(t for t, score in enumerate(scores[d]) if score >= .25)
            current.append(Track(det.bbox, match.person_id, votes, identity, points, body))
            output = identity or Match(None, "Không xác định", match.score)
            tracked = identity is not None and match.person_id is None
            if tracked:
                output = Match(identity.person_id, identity.name, 0.0)
            labels.append(FaceLabel(det.bbox, output, tracked=tracked))
        for index, track in enumerate(previous):
            if index in used or index in blocked:
                continue
            prediction = predictions[index]
            if not track.identity or not prediction:
                continue
            box, points, body = prediction
            # A face now occupying this position must be recognized afresh.
            if any(iou(box, det.bbox) >= .25 for det in detections):
                continue
            current.append(Track(box, None, 0, track.identity, points, body))
            match = Match(track.identity.person_id, track.identity.name, 0.0)
            labels.append(FaceLabel(box, match, tracked=True))
        # Without a detection or valid motion evidence, discard the old identity
        # so a newcomer at the same position cannot inherit it.
        self.tracks, self.gray, self.clock = current, gray, clock
        return labels

"""Small, CPU-only optical-flow helper; no additional inference or models."""
import cv2
import numpy as np


class VisualMotion:
    def __init__(self):
        self.gray = None
        self.scale = 1.0

    def prepare(self, image):
        height, width = image.shape[:2]
        self.scale = min(1.0, 480 / max(height, width))
        if self.scale < 1:
            image = cv2.resize(image, (round(width*self.scale), round(height*self.scale)), interpolation=cv2.INTER_AREA)
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def seed(self, gray, box):
        x1, y1, x2, y2 = (v*self.scale for v in box)
        width, height = x2-x1, y2-y1
        # Head and central upper torso: clothing can remain visible with a fully
        # covered face. Restrict width to avoid collecting nearby background.
        regions = [(x1, y1, x2, y2),
                   (x1+0.1*width, y2+0.35*height, x2-0.1*width, y2+1.5*height)]
        points = []
        for left, top, right, bottom in regions:
            left, top = max(0, round(left)), max(0, round(top))
            right, bottom = min(gray.shape[1], round(right)), min(gray.shape[0], round(bottom))
            if right-left < 8 or bottom-top < 8:
                continue
            found = cv2.goodFeaturesToTrack(gray[top:bottom, left:right], maxCorners=24,
                                           qualityLevel=0.03, minDistance=5, blockSize=5)
            if found is not None:
                found += np.array([left, top], np.float32)
                points.append(found)
        return np.concatenate(points) if points else None

    def predict(self, tracks, gray, needed):
        if gray is None or self.gray is None or gray.shape != self.gray.shape:
            return {}
        active = [(i, t) for i, t in enumerate(tracks)
                  if i in needed and t.points is not None and len(t.points) >= 6]
        if not active:
            return {}
        # All tracks share two LK calls, with at most 48 points per person.
        points = np.concatenate([t.points for _, t in active])
        params = dict(winSize=(21, 21), maxLevel=2,
                      criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 15, 0.03))
        forward, status, error = cv2.calcOpticalFlowPyrLK(self.gray, gray, points, None, **params)
        if forward is None:
            return {}
        backward, back_status, _ = cv2.calcOpticalFlowPyrLK(gray, self.gray, forward, None, **params)
        if backward is None:
            return {}
        valid = (status.ravel() == 1) & (back_status.ravel() == 1)
        valid &= np.isfinite(forward).all(axis=(1, 2)) & np.isfinite(backward).all(axis=(1, 2))
        valid &= np.linalg.norm((backward-points).reshape(-1, 2), axis=1) < 1.5
        valid &= error.ravel() < 25
        valid &= (forward[:, 0, 0] >= 0) & (forward[:, 0, 0] < gray.shape[1])
        valid &= (forward[:, 0, 1] >= 0) & (forward[:, 0, 1] < gray.shape[0])
        predictions, offset = {}, 0
        for index, track in active:
            end = offset + len(track.points)
            mask = valid[offset:end]
            moved = forward[offset:end][mask]
            origin = points[offset:end][mask]
            offset = end
            # Covering the face can remove over half the original features;
            # six consistent torso points still provide useful continuity.
            if len(moved) < max(6, len(track.points)*0.25):
                continue
            delta = (moved-origin).reshape(-1, 2)
            shift = np.median(delta, axis=0)
            inliers = np.linalg.norm(delta-shift, axis=1) <= 3
            if np.count_nonzero(inliers) < max(6, len(moved)*0.6):
                continue
            # Surviving points must cover an area, not a single edge or corner.
            spread = np.ptp(origin[inliers].reshape(-1, 2), axis=0)
            if min(spread) < 6:
                continue
            dx, dy = np.median(delta[inliers], axis=0) / self.scale
            x1, y1, x2, y2 = track.box
            box = (float(x1+dx), float(y1+dy), float(x2+dx), float(y2+dy))
            if x2+dx <= 0 or y2+dy <= 0 or x1+dx >= gray.shape[1]/self.scale or y1+dy >= gray.shape[0]/self.scale:
                continue
            predictions[index] = (box, moved[inliers].copy())
        return predictions

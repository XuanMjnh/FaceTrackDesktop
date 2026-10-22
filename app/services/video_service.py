import hashlib
from pathlib import Path
import math


def video_source(path, cancelled=lambda: False):
    """Full content hash keeps identity stable on replay, rename and copying."""
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while block := stream.read(4 * 1024 * 1024):
            if cancelled():
                raise InterruptedError("Đã hủy mở video")
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def frame_timestamp(position_ms, frame_index, fps):
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("Video không có FPS đáng tin cậy")
    fallback = max(0, frame_index) / fps
    if position_ms == 0 and frame_index > 0:
        return fallback
    if math.isfinite(position_ms) and position_ms >= 0:
        candidate = position_ms / 1000
        # Backends that return 0, NaN or a wildly inconsistent position use frame time.
        if abs(candidate-fallback) <= max(0.25, 2/fps):
            return candidate
    return fallback

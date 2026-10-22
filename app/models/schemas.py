from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class Detection:
    bbox: tuple[float, float, float, float]
    embedding: np.ndarray
    confidence: float = 1.0


@dataclass(frozen=True)
class Match:
    person_id: str | None
    name: str
    score: float


@dataclass(frozen=True)
class Frame:
    epoch: int
    image: np.ndarray
    source_type: str
    source_id: str
    timestamp: float  # Unix seconds for camera; media seconds for video.
    clock: float  # Monotonic clock for camera; media seconds for video.
    duration: float
    logging: bool


@dataclass(frozen=True)
class FaceLabel:
    bbox: tuple
    match: Match

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path


def home_dir():
    return Path(os.environ.get("FACETRACK_HOME", Path.home() / "FaceTrackDesktop"))


@dataclass
class Settings:
    camera: int = 0
    backend: str = "auto"
    detection_size: int = 640
    similarity: float = 0.45
    absence_seconds: float = 30.0
    recognition_hz: float = 5.0
    database_path: str = ""
    image_dir: str = ""
    model_root: str = ""
    show_name: bool = True
    show_id: bool = True
    show_score: bool = False

    def validate(self):
        if self.backend not in ("auto", "cpu", "cuda"):
            raise ValueError("Backend không hợp lệ")
        if not 0 < self.similarity <= 1 or not 0 < self.absence_seconds <= 3600:
            raise ValueError("Ngưỡng tương đồng/thời gian vắng mặt không hợp lệ")
        if not 0.2 <= self.recognition_hz <= 60 or self.detection_size not in (320, 480, 640, 960, 1280):
            raise ValueError("Tần suất/kích thước phát hiện không hợp lệ")
        if self.camera < 0:
            raise ValueError("Mã camera không hợp lệ")

    @classmethod
    def load(cls):
        root = home_dir()
        root.mkdir(parents=True, exist_ok=True)
        path = root / "settings.json"
        data = json.loads(path.read_text("utf-8")) if path.exists() else {}
        result = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        result.database_path = result.database_path or str(root / "facetrack.sqlite3")
        result.image_dir = result.image_dir or str(root / "images")
        result.model_root = result.model_root or str(root / "insightface")
        result.validate()
        return result

    def save(self):
        self.validate()
        path = home_dir() / "settings.json"
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), "utf-8")
        temp.replace(path)

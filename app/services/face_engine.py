"""InsightFace 0.7.3 API adapter. Model installation is an explicit offline step."""
from pathlib import Path
from threading import RLock
import numpy as np
from app.models.schemas import Detection
from app.services.face_matcher import normalize


class FaceEngine:
    def __init__(self, settings):
        self.settings = settings
        self.lock = RLock()
        self.analysis = None
        self.backend = "Chưa tải mô hình"
        self.warning = ""

    def _build(self, cuda):
        from insightface.app import FaceAnalysis
        root = Path(self.settings.model_root).expanduser()
        folder = root / "models" / "buffalo_l"
        required = ("det_10g.onnx", "w600k_r50.onnx")
        if any(not (folder / f).is_file() for f in required):
            raise RuntimeError(f"Thiếu mô hình buffalo_l tại {folder}.")
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if cuda else ["CPUExecutionProvider"]
        app = FaceAnalysis(name="buffalo_l", root=str(root),
                           allowed_modules=["detection", "recognition"], providers=providers)
        if "recognition" not in app.models:
            raise RuntimeError("Gói mô hình không có recognition")
        app.prepare(ctx_id=0 if cuda else -1, det_size=(self.settings.detection_size,) * 2)
        # Exercise both detection and recognition to catch DLL/kernel problems.
        app.get(np.zeros((self.settings.detection_size, self.settings.detection_size, 3), np.uint8))
        app.models["recognition"].get_feat(np.zeros((112, 112, 3), np.uint8))
        actual = {task: model.session.get_providers() for task, model in app.models.items()}
        if cuda and any(v[0] != "CUDAExecutionProvider" for v in actual.values()):
            raise RuntimeError(f"ONNX Runtime đã chuyển sang CPU: {actual}")
        self.backend = "CUDA + CPU fallback" if cuda else "CPU"
        return app

    def load(self):
        with self.lock:
            if self.analysis is not None:
                return
            import onnxruntime as ort
            available = ort.get_available_providers()
            cuda = self.settings.backend != "cpu" and "CUDAExecutionProvider" in available
            self.warning = ""
            if self.settings.backend == "cuda" and not cuda:
                self.warning = "CUDAExecutionProvider không khả dụng; đang dùng CPU."
            try:
                self.analysis = self._build(cuda)
            except Exception as exc:
                if not cuda:
                    raise
                self.warning = f"CUDA không khởi tạo được ({exc}); đã chuyển sang CPU."
                self.analysis = self._build(False)

    def detect(self, image):
        with self.lock:
            self.load()
            try:
                faces = self.analysis.get(image)
            except Exception as exc:
                if not self.backend.startswith("CUDA"):
                    raise
                self.warning = f"Lỗi CUDA khi nhận diện: {exc}. Đã chuyển sang CPU."
                self.analysis = self._build(False)
                faces = self.analysis.get(image)
            output = []
            for face in faces:
                if face.normed_embedding is None:
                    continue
                try:
                    vector = normalize(face.normed_embedding)
                except ValueError:
                    continue
                output.append(Detection(tuple(float(x) for x in face.bbox), vector, float(face.det_score)))
            return output

    def diagnostics(self):
        import onnxruntime as ort
        self.load()
        actual = {k: v.session.get_providers() for k, v in self.analysis.models.items()}
        return f"ONNX Runtime {ort.__version__}\nProviders có sẵn: {ort.get_available_providers()}\nBackend: {self.backend}\nSessions: {actual}\n{self.warning}"

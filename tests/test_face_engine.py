import sys
from types import SimpleNamespace
import numpy as np
from app.config import Settings
from app.services.face_engine import FaceEngine


def test_cuda_failure_falls_back_and_reports_actual_backend(monkeypatch):
    monkeypatch.setitem(sys.modules, "onnxruntime", SimpleNamespace(get_available_providers=lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"]))
    engine = FaceEngine(Settings(backend="cuda"))
    calls = []
    def build(cuda):
        calls.append(cuda)
        if cuda:
            raise RuntimeError("missing cudnn64_9.dll")
        engine.backend = "CPU"
        return object()
    monkeypatch.setattr(engine, "_build", build)
    engine.load()
    assert calls == [True, False]
    assert engine.backend == "CPU"
    assert "cudnn64_9.dll" in engine.warning
    engine.load()
    assert len(calls) == 2, "Loaded model must be reused"


def test_missing_model_is_rejected_before_faceanalysis_can_download(monkeypatch, tmp_path):
    constructed = []
    monkeypatch.setitem(sys.modules, "insightface.app", SimpleNamespace(FaceAnalysis=lambda **kw: constructed.append(kw)))
    import pytest
    engine = FaceEngine(Settings(model_root=str(tmp_path)))
    with pytest.raises(RuntimeError, match="Thiếu mô hình"):
        engine._build(False)
    assert not constructed


def test_cpu_selection_never_requests_cuda(monkeypatch):
    monkeypatch.setitem(sys.modules, "onnxruntime", SimpleNamespace(get_available_providers=lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"]))
    engine = FaceEngine(Settings(backend="cpu"))
    requested = []
    monkeypatch.setattr(engine, "_build", lambda cuda: requested.append(cuda) or object())
    engine.load()
    assert requested == [False]

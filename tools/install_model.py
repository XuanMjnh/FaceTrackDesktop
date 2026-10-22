"""Explicit local model installer. No download, package install or startup side effect."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import zipfile


def main():
    parser = argparse.ArgumentParser(description="Install buffalo_l from a locally downloaded ZIP")
    parser.add_argument("zip", type=Path)
    parser.add_argument("--root", type=Path, help="InsightFace root configured in Settings")
    parser.add_argument("--sha256", help="Optional checksum from a trusted independent source")
    args = parser.parse_args()
    if args.sha256:
        digest = hashlib.file_digest(args.zip.open("rb"), "sha256").hexdigest()
        if digest.lower() != args.sha256.lower():
            parser.error("SHA256 không khớp")
    root = args.root or Path(os.environ.get("FACETRACK_HOME", Path.home()/"FaceTrackDesktop"))/"insightface"
    models = root / "models"
    models.mkdir(parents=True, exist_ok=True)
    target = models / "buffalo_l"
    if target.exists():
        parser.error(f"Đã có {target}; đổi tên thư mục cũ trước khi cài lại")
    with tempfile.TemporaryDirectory(dir=models) as work:
        staging = Path(work)/"buffalo_l"
        staging.mkdir()
        with zipfile.ZipFile(args.zip) as archive:
            for required in ("det_10g.onnx", "w600k_r50.onnx"):
                candidates = [m for m in archive.infolist() if Path(m.filename).name == required]
                if len(candidates) != 1 or not 1000 < candidates[0].file_size < 500_000_000:
                    parser.error(f"Gói mô hình thiếu/trùng hoặc kích thước không hợp lệ: {required}")
                with archive.open(candidates[0]) as source, (staging/required).open("wb") as dest:
                    shutil.copyfileobj(source, dest)
        staging.replace(target)
    print(f"Model installed at {target}")


if __name__ == "__main__":
    main()

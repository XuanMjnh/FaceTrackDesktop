import argparse
import sys
from dataclasses import replace


def main():
    parser = argparse.ArgumentParser(description="FaceTrack Desktop")
    parser.add_argument("--backend", choices=("auto", "cpu", "cuda"))
    parser.add_argument("--diagnose", action="store_true", help="Load models and exercise both networks without GUI")
    args = parser.parse_args()
    from app.config import Settings
    from app.services.face_engine import FaceEngine
    settings = Settings.load()
    if args.backend:
        settings = replace(settings, backend=args.backend)
    if args.diagnose:
        try:
            print(FaceEngine(settings).diagnostics())
            return 0
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return 1
    from PySide6.QtCore import QLockFile
    from PySide6.QtWidgets import QApplication, QMessageBox
    from app.config import home_dir
    from app.services.database import Database
    from app.ui.main_window import MainWindow
    application = QApplication(sys.argv)
    application.setApplicationName("FaceTrack Desktop")
    # Single process per settings root prevents concurrent session writers.
    lock = QLockFile(str(home_dir() / "facetrack.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        QMessageBox.warning(None, "FaceTrack Desktop", "Ứng dụng đã chạy trong vùng dữ liệu này.")
        return 1
    try:
        db = Database(settings.database_path)
        window = MainWindow(settings, db)
    except Exception as exc:
        QMessageBox.critical(None, "Không thể khởi động", str(exc))
        return 1
    window.show()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())

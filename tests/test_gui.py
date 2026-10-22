import os
import time
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from app.config import Settings
from app.ui.main_window import MainWindow


def test_all_pages_and_async_clean_shutdown(db, tmp_path):
    # This test owns a separate DB because MainWindow closes its DB on exit.
    from app.services.database import Database
    owned_db = Database(tmp_path/"gui.sqlite3")
    application = QApplication.instance() or QApplication([])
    settings = Settings(database_path=str(tmp_path/"gui.sqlite3"), image_dir=str(tmp_path/"images"), model_root=str(tmp_path/"models"))
    window = MainWindow(settings, owned_db)
    window.show()
    for index in range(5):
        window.navigation.setCurrentRow(index)
        application.processEvents()
        assert window.pages.currentIndex() == index
    window.close()
    until = time.monotonic()+5
    while not window.safe_to_close and time.monotonic() < until:
        application.processEvents()
        time.sleep(.01)
    assert window.safe_to_close

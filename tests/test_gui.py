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


def test_presence_panel_distinguishes_tracked_identity():
    from app.models.schemas import FaceLabel, Match
    from app.ui.presence_panel import PresencePanel

    application = QApplication.instance() or QApplication([])
    settings = Settings()
    panel = PresencePanel(settings)
    identity = Match("a", "Ánh", .9)
    panel.update_people([FaceLabel((0, 0, 50, 50), identity)])
    assert "Đang theo dõi" not in panel.people.item(0).text()
    panel.update_people([FaceLabel((0, 0, 50, 50), identity, tracked=True)])
    assert "Đang theo dõi" in panel.people.item(0).text()
    assert panel.count.text() == "1 người"
    settings.show_tracking_status = False
    panel.update_people([FaceLabel((0, 0, 50, 50), identity, tracked=True)])
    assert "Đang theo dõi" not in panel.people.item(0).text()
    assert "Ánh" in panel.people.item(0).text()
    assert panel.count.text() == "1 người"
    panel.clear()
    assert panel.count.text() == "0 người"
    panel.close()


def test_hidden_tracking_status_hides_text_and_similarity_on_canvas():
    import numpy as np
    from app.models.schemas import FaceLabel, Match
    from app.ui.common import VideoCanvas

    application = QApplication.instance() or QApplication([])
    settings = Settings(show_name=False, show_id=False, show_score=True, show_tracking_status=False)
    canvas = VideoCanvas(settings)
    canvas.resize(320, 240)
    image = np.zeros((240, 320, 3), np.uint8)
    identity = Match("a", "Ánh", 0)
    tracked = FaceLabel((100, 100, 150, 150), identity, tracked=True)
    canvas.set_frame(image, [tracked])
    hidden = canvas.grab().toImage()
    settings.show_score = False
    canvas.set_frame(image, [FaceLabel(tracked.bbox, identity)])
    assert canvas.grab().toImage() == hidden
    settings.show_tracking_status = True
    canvas.set_frame(image, [tracked])
    assert canvas.grab().toImage() != hidden
    canvas.close()


def test_settings_save_tracking_text_option_applies_to_both_sources(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import numpy as np
    from PySide6.QtWidgets import QMessageBox
    from app.models.schemas import FaceLabel, Match
    from app.ui.common import VideoCanvas
    from app.ui.presence_panel import PresencePanel
    from app.ui.settings_page import SettingsPage

    application = QApplication.instance() or QApplication([])
    monkeypatch.setenv("FACETRACK_HOME", str(tmp_path))
    monkeypatch.setattr("app.ui.settings_page.camera_names", lambda: [])
    messages, errors = [], []
    monkeypatch.setattr(QMessageBox, "information", lambda *args: messages.append(args))
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: errors.append(args))
    settings = Settings.load()
    pages = [SimpleNamespace(canvas=VideoCanvas(settings), presence=PresencePanel(settings)) for _ in range(2)]
    tracked = FaceLabel((80, 30, 130, 80), Match("a", "Ánh", 0), tracked=True)
    for page in pages:
        page.canvas.set_frame(np.zeros((200, 240, 3), np.uint8), [tracked])
        page.presence.update_people([tracked])
        assert "Đang theo dõi" in page.presence.people.item(0).text()
    window = SimpleNamespace(settings=settings, camera_page=pages[0], video_page=pages[1])
    editor = SettingsPage(window)
    assert editor.tracking_status.isChecked()
    editor.tracking_status.setChecked(False)
    editor.save()
    assert messages and not errors
    assert not Settings.load().show_tracking_status
    for page in pages:
        assert not page.canvas.settings.show_tracking_status
        assert "Đang theo dõi" not in page.presence.people.item(0).text()
        assert page.presence.count.text() == "1 người"
    editor.tracking_status.setChecked(True)
    editor.save()
    assert Settings.load().show_tracking_status
    for page in pages:
        assert "Đang theo dõi" in page.presence.people.item(0).text()
        page.canvas.close()
        page.presence.close()
    editor.close()

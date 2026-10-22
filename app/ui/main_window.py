import threading
from PySide6.QtCore import QTimer, Signal, Qt, QSize
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
    QListWidgetItem, QStackedWidget, QMessageBox, QFrame, QApplication, QScrollArea)
from app.services.face_engine import FaceEngine
from app.services.enrollment import Enrollment
from app.workers.pipeline import Pipeline
from app.ui.common import Jobs
from app.ui.camera_page import CameraPage
from app.ui.video_page import VideoPage
from app.ui.persons_page import PersonsPage
from app.ui.history_page import HistoryPage
from app.ui.settings_page import SettingsPage
from app.config import home_dir
from app.services.notifications import NotificationService
from app.ui.notifications_page import NotificationsPage

from app.ui.theme import STYLE, apply_theme, line_icon, label



class MainWindow(QMainWindow):
    message = Signal(str)
    closed = Signal(bool)

    def __init__(self, settings, db, engine=None):
        super().__init__()
        self.settings, self.db = settings, db
        self.setWindowTitle("FaceTrack Desktop")
        apply_theme(self)
        available = QApplication.primaryScreen().availableGeometry()
        self.setMinimumSize(min(980, max(640, available.width()-24)),
                            min(640, max(440, available.height()-24)))
        self.resize(min(1380, max(self.minimumWidth(), available.width()-48)),
                    min(900, max(self.minimumHeight(), available.height()-48)))
        self.jobs = Jobs(self)
        self.engine = engine or FaceEngine(settings)
        self.enrollment = Enrollment(db, self.engine, settings.image_dir)
        self.notifications = NotificationService(home_dir(), self.message.emit)
        self.pipeline = Pipeline(db, self.engine, settings, self.message.emit,
                                 self.notifications.detection, self.notifications.cancel_pending)
        self.message.connect(self.show_message)
        self.closed.connect(self.finish_close)
        self.closing, self.safe_to_close = False, False
        self.last_frame = None
        self.last_engine_warning = ""
        root = QWidget()
        root.setObjectName("Workspace")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(224)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(16, 26, 16, 20)
        side.setSpacing(10)
        brand = QHBoxLayout()
        brand.setSpacing(10)
        mark = label("F", "BrandMark")
        mark.setFixedSize(34, 34)
        mark.setAlignment(Qt.AlignCenter)
        mark.setStyleSheet("background:#2867c7;color:white;border-radius:7px;font-size:22px;font-weight:600;")
        brand.addWidget(mark)
        brand.addWidget(label("FaceTrack", "Brand"))
        brand.addStretch()
        side.addLayout(brand)
        side.addSpacing(20)
        self.navigation = QListWidget()
        self.navigation.setObjectName("Navigation")
        self.navigation.setIconSize(QSize(19, 19))
        self.navigation.setSpacing(2)
        self.navigation.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.navigation.setFocusPolicy(Qt.NoFocus)
        self.navigation_icons = ["camera", "video", "people", "history", "mail", "settings"]
        for title, icon_name in zip(("Camera trực tiếp", "Video", "Hồ sơ người", "Lịch sử xuất hiện", "Thông báo", "Cài đặt"), self.navigation_icons):
            item = QListWidgetItem(line_icon(icon_name), title)
            item.setSizeHint(QSize(180, 46))
            self.navigation.addItem(item)
        side.addWidget(self.navigation, 1)
        divider = QFrame()
        divider.setObjectName("Hairline")
        divider.setFixedHeight(1)
        side.addWidget(divider)
        footer = QHBoxLayout()
        footer_icon = label("")
        footer_icon.setPixmap(line_icon("shield", "#74889f", 18).pixmap(18, 18))
        footer.addWidget(footer_icon, 0, Qt.AlignTop)
        footer.addWidget(label("Xử lý cục bộ", "Muted", True), 1)
        side.addSpacing(8)
        side.addLayout(footer)
        layout.addWidget(self.sidebar)
        self.pages = QStackedWidget()
        self.camera_page, self.video_page = CameraPage(self), VideoPage(self)
        self.persons_page, self.history_page = PersonsPage(self), HistoryPage(self)
        self.settings_page = SettingsPage(self)
        self.notifications_page = NotificationsPage(self)
        for page in (self.camera_page, self.video_page, self.persons_page, self.history_page, self.notifications_page, self.settings_page):
            if page is self.settings_page:
                self.pages.addWidget(page)
            else:
                # Keep controls reachable on short displays and at 125–150% DPI.
                host = QScrollArea()
                host.setWidgetResizable(True)
                host.setFrameShape(QFrame.NoFrame)
                host.setWidget(page)
                self.pages.addWidget(host)
        layout.addWidget(self.pages, 1)
        self.setCentralWidget(root)
        self.navigation.currentRowChanged.connect(self.change_page)
        self.navigation.setCurrentRow(0)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_frame)
        self.timer.start(33)
        self.backend_status = label("Chưa tải mô hình", "Muted")
        self.statusBar().addPermanentWidget(self.backend_status)
        self.statusBar().setContentsMargins(12, 0, 12, 0)
        self.model_loading = True
        self.model_error = ""
        self.backend_status.setText("Đang tải mô hình…")
        self.backend_status.setToolTip("Đang khởi tạo mô hình.")
        self.jobs.run(self.load_model, self.model_loaded)
        self.notifications_page.restore()

    def load_model(self):
        try:
            self.engine.load()
            return ""
        except Exception as exc:
            return str(exc)

    def model_loaded(self, error):
        self.model_loading = False
        self.model_error = error
        if error:
            self.show_message("Không thể tải mô hình: " + error)
            return
        if self.engine.warning and self.engine.warning != self.last_engine_warning:
            self.last_engine_warning = self.engine.warning
            self.show_message(self.engine.warning)

    def show_message(self, text):
        self.statusBar().showMessage(text, 15000)
        self.statusBar().setToolTip(text)

    def change_page(self, index):
        self.pages.setCurrentIndex(index)
        for row, name in enumerate(self.navigation_icons):
            self.navigation.item(row).setIcon(line_icon(name, "#2867c7" if row == index else "#65758b"))
        if index == 2:
            self.persons_page.refresh()
        elif index == 3:
            self.history_page.refresh()
        elif index == 4:
            self.notifications_page.refresh_logs()

    def start_media(self, kind, source, logging):
        self.camera_page.canvas.clear()
        self.video_page.canvas.clear()
        self.camera_page.presence.clear()
        self.video_page.presence.clear()
        self.last_frame = None
        self.pipeline.command("open_camera" if kind == "camera" else "open_video", source)
        self.pipeline.command("logging", logging)

    def stop_media(self):
        self.pipeline.command("stop")
        for page in (self.camera_page, self.video_page):
            page.canvas.clear()
            page.presence.clear()
        self.last_frame = None

    def set_logging(self, kind, enabled):
        if self.pipeline.snapshot()["kind"] == kind:
            self.pipeline.command("logging", enabled)

    def refresh_frame(self):
        state = self.pipeline.snapshot()
        self.video_page.update_position(state)
        if self.model_loading:
            self.backend_status.setText("Đang tải mô hình…")
            self.backend_status.setToolTip("Đang khởi tạo mô hình.")
        elif self.model_error:
            self.backend_status.setText("Lỗi tải mô hình")
            self.backend_status.setToolTip(self.model_error)
        else:
            self.backend_status.setText(self.engine.backend)
            self.backend_status.setToolTip(self.engine.warning or self.engine.backend)
        if self.engine.warning and self.engine.warning != self.last_engine_warning:
            self.last_engine_warning = self.engine.warning
            self.show_message(self.engine.warning)
        if state["kind"] != "video":
            logging = self.camera_page.logging.isChecked() and state["kind"] == "camera"
            status = "Đang ghi lịch sử" if logging and state["playing"] else "Lịch sử không ghi"
            activity = "Đang chạy" if state["playing"] else "Đã dừng"
            warning = " · Cảnh báo backend" if self.engine.warning else ""
            self.camera_page.status.setText(f"{activity}  ·  {state['fps']:.1f} FPS xử lý  ·  {self.engine.backend}  ·  {status}{warning}")
            self.camera_page.status.setToolTip(self.engine.warning)
        result = self.pipeline.results.peek()
        raw = self.pipeline.raw.peek()
        if getattr(self, "display_epoch", None) != self.pipeline.epoch:
            self.display_epoch = self.pipeline.epoch
            self.last_frame = None
            for page in (self.camera_page, self.video_page):
                page.canvas.clear()
                page.presence.clear()
        if result and result[0].epoch == self.pipeline.epoch:
            candidate, candidate_labels, _ = result
            target = self.camera_page if candidate.source_type == "camera" else self.video_page
            if raw is None or abs(raw.clock-candidate.clock) < max(0.4, 1/self.settings.recognition_hz):
                target.presence.update_people(candidate_labels)
            else:
                target.presence.clear()
        # Render results on their OWN frames: no boxes from an old timeline.
        # Capture remains paced; display falls back to raw preview if inference lags.
        labels = []
        frame = raw
        if result and result[0].epoch == self.pipeline.epoch:
            candidate, candidate_labels, rate = result
            if raw is None or abs(raw.clock-candidate.clock) < max(0.4, 1/self.settings.recognition_hz):
                frame, labels = candidate, candidate_labels
        if frame is not None and frame.epoch == self.pipeline.epoch:
            token = (frame.epoch, frame.timestamp, bool(labels))
            if token != self.last_frame:
                target = self.camera_page if frame.source_type == "camera" else self.video_page
                target.canvas.set_frame(frame.image, labels)
                self.last_frame = token

    def closeEvent(self, event):
        if self.safe_to_close:
            event.accept()
            return
        event.ignore()
        if self.closing:
            return
        self.closing = True
        self.jobs.accepting = False
        self.centralWidget().setEnabled(False)
        self.statusBar().showMessage("Đang đóng ứng dụng…")
        self.timer.stop()
        def close_resources():
            try:
                # Complete enrollment/history jobs before shutting down the DB.
                self.jobs.pool.shutdown(wait=True)
                ok = self.pipeline.shutdown()
                mail_ok = self.notifications.shutdown()
                ok = ok and mail_ok
                if ok:
                    self.db.close()
                self.closed.emit(ok)
            except Exception as exc:
                self.message.emit(str(exc))
                self.closed.emit(False)
        threading.Thread(target=close_resources, name="shutdown", daemon=True).start()

    def finish_close(self, ok):
        if ok:
            self.safe_to_close = True
            self.close()
        else:
            self.closing = False
            self.statusBar().showMessage("Tác vụ nền chưa dừng. Chờ tác vụ hoàn tất rồi thử đóng lại.")
            QMessageBox.warning(self, "Đang đóng ứng dụng", "Tác vụ nền chưa dừng. Chờ tác vụ hoàn tất rồi thử lại.")

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox, QFileDialog, QMessageBox
from app.services.camera_service import discover_cameras
from app.ui.common import button, VideoCanvas
from app.ui.theme import page_layout, page_header, panel, action, label, FlowLayout
from app.ui.theme import CheckBox as QCheckBox, ComboBox as QComboBox
from app.ui.presence_panel import PresencePanel

class CameraPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        layout = page_layout(self)
        page_header(layout, "Camera trực tiếp", "Nhận diện trực tiếp.")
        box, body = panel()
        controls = FlowLayout(spacing=8)
        device = QWidget()
        row = QHBoxLayout(device)
        row.setContentsMargins(0, 0, 6, 0)
        row.setSpacing(10)
        row.addWidget(label("Thiết bị", "FieldLabel"))
        self.camera = QComboBox()
        self.camera.setEditable(True)
        self.camera.setMinimumWidth(115)
        self.camera.addItem(str(window.settings.camera))
        row.addWidget(self.camera)
        controls.addWidget(device)
        controls.addWidget(action("Quét camera", self.scan))
        controls.addWidget(action("Bắt đầu camera", self.start, "primary", "camera"))
        controls.addWidget(action("Dừng", lambda: window.stop_media()))
        controls.addWidget(action("Chụp ảnh", self.snapshot))
        body.addLayout(controls)
        self.logging = QCheckBox("Ghi lịch sử xuất hiện")
        self.logging.setToolTip("Chỉ ghi lịch sử khi được phép.")
        self.logging.toggled.connect(lambda enabled: window.set_logging("camera", enabled))
        options = FlowLayout(spacing=20)
        options.addWidget(self.logging)
        self.alerts = QCheckBox("Thông báo khi phát hiện")
        self.alerts.setToolTip("Cấu hình email tại trang Thông báo.")
        self.alerts.toggled.connect(lambda enabled: window.notifications.set_enabled("camera", enabled))
        options.addWidget(self.alerts)
        body.addLayout(options)
        layout.addWidget(box)
        screen, screen_layout = panel()
        heading = QHBoxLayout()
        heading.addWidget(label("Hình ảnh trực tiếp", "SectionTitle"))
        heading.addStretch()
        heading.addWidget(label("Xử lý trên thiết bị", "Badge"))
        screen_layout.addLayout(heading)
        self.canvas = VideoCanvas(window.settings)
        self.canvas.empty_title = "Chưa kết nối camera"
        self.canvas.empty_hint = "Chọn thiết bị camera."
        screen_layout.addWidget(self.canvas, 1)
        self.status = label("Chưa mở camera · Lịch sử đang tắt", "Muted", True)
        self.status.setTextInteractionFlags(self.status.textInteractionFlags())
        screen_layout.addWidget(self.status)
        view = QHBoxLayout()
        view.addWidget(screen, 1)
        self.presence = PresencePanel()
        view.addWidget(self.presence)
        layout.addLayout(view, 1)


    def scan(self):
        self.window.jobs.run(discover_cameras, self.cameras_found)

    def cameras_found(self, cameras):
        self.camera.clear()
        self.camera.addItems([str(x) for x in cameras] or [str(self.window.settings.camera)])
        self.status.setText(f"Camera khả dụng: {len(cameras)}")

    def start(self):
        try:
            index = int(self.camera.currentText())
            if index < 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "Camera", "Mã thiết bị phải là số nguyên không âm.")
            return
        self.window.start_media("camera", index, self.logging.isChecked())

    def snapshot(self):
        frame = self.window.pipeline.raw.peek()
        if frame is None or frame.source_type != "camera":
            QMessageBox.information(self, "Chụp ảnh", "Chưa có khung hình.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Lưu ảnh", "camera.jpg", "JPEG (*.jpg)")
        if path:
            def save():
                import cv2
                ok, encoded = cv2.imencode(".jpg", frame.image)
                if not ok:
                    raise ValueError("Không mã hóa được ảnh")
                encoded.tofile(path)
            self.window.jobs.run(save, lambda _: self.status.setText("Đã lưu ảnh."))

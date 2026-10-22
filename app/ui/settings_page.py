from dataclasses import replace
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox,
    QDoubleSpinBox, QLineEdit, QCheckBox, QPushButton, QMessageBox, QPlainTextEdit, QScrollArea,
    QFileDialog, QSizePolicy)
from app.services.camera_service import camera_names
from app.ui.theme import page_layout, page_header, panel, action, label, field, FlowLayout, ResponsiveColumns
from app.ui.theme import CheckBox as QCheckBox, ComboBox as QComboBox, SpinBox as QSpinBox, DoubleSpinBox as QDoubleSpinBox


class SettingsPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        s = window.settings
        layout = page_layout(self)
        page_header(layout, "Cài đặt", "Thiết bị, nhận diện và lưu trữ.",
                    action("Lưu cài đặt", self.save, "primary"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 0, 8, 2)
        body.setSpacing(16)
        device, device_body = panel("Thiết bị & hiệu năng")
        self.camera = QComboBox()
        self.camera.setEditable(True)
        self.camera.setMinimumWidth(190)
        names = camera_names()
        for index, name in enumerate(names):
            self.camera.addItem(name.strip() or f"Camera {index}", index)
        if self.camera.findData(s.camera) < 0:
            self.camera.addItem(f"Camera {s.camera}", s.camera)
        self.camera.setCurrentIndex(self.camera.findData(s.camera))
        device_body.addWidget(field("Camera mặc định", self.camera))
        self.backend = QComboBox()
        self.backend.addItems(["auto", "cpu", "cuda"])
        self.backend.setCurrentText(s.backend)
        device_body.addWidget(field("Backend mong muốn", self.backend))
        self.size = QComboBox()
        self.size.addItems(["320", "480", "640", "960", "1280"])
        self.size.setCurrentText(str(s.detection_size))
        device_body.addWidget(field("Kích thước đầu vào mô hình", self.size))
        recognition, recognition_body = panel("Nhận diện & phiên xuất hiện")
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0.01, 1)
        self.threshold.setSingleStep(0.01)
        self.threshold.setValue(s.similarity)
        recognition_body.addWidget(field("Ngưỡng tương đồng cosine", self.threshold))
        self.absence = QDoubleSpinBox()
        self.absence.setRange(0.1, 3600)
        self.absence.setSuffix(" giây")
        self.absence.setValue(s.absence_seconds)
        recognition_body.addWidget(field("Thời gian vắng mặt để đóng phiên", self.absence))
        self.hz = QDoubleSpinBox()
        self.hz.setRange(0.2, 60)
        self.hz.setSuffix(" Hz")
        self.hz.setValue(s.recognition_hz)
        recognition_body.addWidget(field("Tần suất cập nhật nhận diện", self.hz))
        body.addWidget(ResponsiveColumns([device, recognition], breakpoint=750))
        storage, storage_body = panel("Lưu trữ dữ liệu")
        self.database = QLineEdit(s.database_path)
        self.images = QLineEdit(s.image_dir)
        self.models = QLineEdit(s.model_root)
        for caption, control, kind in (("Cơ sở dữ liệu SQLite", self.database, "db"),
                ("Thư mục ảnh tham chiếu", self.images, "folder"),
                ("Thư mục InsightFace — chứa models/buffalo_l", self.models, "folder")):
            row = QWidget()
            line = QHBoxLayout(row)
            line.setContentsMargins(0, 0, 0, 0)
            line.setSpacing(8)
            control.setMinimumWidth(120)
            control.setToolTip(control.text())
            control.textChanged.connect(control.setToolTip)
            line.addWidget(control, 1)
            line.addWidget(action("Chọn…", lambda checked=False, target=control, mode=kind: self.browse(target, mode)))
            storage_body.addWidget(field(caption, row))
        storage_body.addWidget(label("Đường dẫn mới có hiệu lực sau khi khởi động lại. Dữ liệu cũ không tự di chuyển.", "Muted", True))
        body.addWidget(storage)
        display, display_body = panel("Thông tin trên khung hình")
        checks = FlowLayout(spacing=24)
        self.name, self.id, self.score = QCheckBox("Họ tên"), QCheckBox("Mã ID"), QCheckBox("Điểm tương đồng")
        self.name.setChecked(s.show_name)
        self.id.setChecked(s.show_id)
        self.score.setChecked(s.show_score)
        for control in (self.name, self.id, self.score):
            checks.addWidget(control)
        display_body.addLayout(checks)
        body.addWidget(display)
        diagnostics, diagnostics_body = panel("Kiểm tra môi trường", "Backend CPU / NVIDIA CUDA.")
        test = action("Kiểm tra CPU / GPU", lambda: window.jobs.run(window.engine.diagnostics, self.report.setPlainText))
        diagnostics_body.addWidget(test, 0, Qt.AlignLeft)
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setPlaceholderText("Chưa có kết quả.")
        self.report.setMinimumHeight(140)
        self.report.setMaximumHeight(200)
        diagnostics_body.addWidget(self.report)
        body.addWidget(diagnostics)
        body.addWidget(label("Ảnh và embedding chưa được mã hóa.", "Muted", True))
        body.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

    def browse(self, target, kind):
        if kind == "db":
            path, _ = QFileDialog.getSaveFileName(self, "Chọn cơ sở dữ liệu SQLite", target.text(), "SQLite (*.sqlite3 *.db);;Tất cả (*)")
        else:
            path = QFileDialog.getExistingDirectory(self, "Chọn thư mục", target.text())
        if path:
            target.setText(path)

    def save(self):
        try:
            camera = self.camera.currentData()
            if camera is None:
                camera = int(self.camera.currentText())
            new = replace(self.window.settings, camera=int(camera), backend=self.backend.currentText(),
                          detection_size=int(self.size.currentText()), similarity=self.threshold.value(),
                          absence_seconds=self.absence.value(), recognition_hz=self.hz.value(),
                          database_path=self.database.text().strip(), image_dir=self.images.text().strip(),
                          model_root=self.models.text().strip(), show_name=self.name.isChecked(),
                          show_id=self.id.isChecked(), show_score=self.score.isChecked())
            if not all((new.database_path, new.image_dir, new.model_root)):
                raise ValueError("Các đường dẫn không được để trống")
            new.save()
            QMessageBox.information(self, "Đã lưu", "Khởi động lại để áp dụng. Dữ liệu không tự di chuyển khi đổi đường dẫn.")
        except Exception as exc:
            QMessageBox.warning(self, "Cài đặt", str(exc))

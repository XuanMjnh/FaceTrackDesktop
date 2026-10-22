from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox, QFileDialog, QSlider
from app.services.csv_exporter import timeline
from app.ui.common import button, VideoCanvas
from app.ui.theme import page_layout, page_header, panel, action, label, FlowLayout
from app.ui.theme import CheckBox as QCheckBox, ComboBox as QComboBox

class VideoPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window, self.path, self.duration = window, "", 0
        layout = page_layout(self)
        page_header(layout, "Video", "Xem và phân tích video theo thời gian trên bản ghi.")
        box, body = panel()
        controls = FlowLayout(spacing=8)
        controls.addWidget(action("Mở video", self.open, "primary", "folder"))
        controls.addWidget(action("Phát / Tạm dừng", self.toggle))
        controls.addWidget(action("Dừng về đầu", self.rewind))
        speed_field = QWidget()
        speed_row = QHBoxLayout(speed_field)
        speed_row.setContentsMargins(8, 0, 0, 0)
        speed_row.setSpacing(10)
        speed_row.addWidget(label("Tốc độ", "FieldLabel"))
        self.speed = QComboBox()
        self.speed.setMinimumWidth(90)
        self.speed.addItems(["0.25x", "0.5x", "1x", "1.5x", "2x"])
        self.speed.setCurrentIndex(2)
        self.speed.currentTextChanged.connect(lambda text: window.pipeline.command("speed", float(text[:-1])))
        speed_row.addWidget(self.speed)
        controls.addWidget(speed_field)
        body.addLayout(controls)
        self.filename = label("Chưa chọn tệp video", "Muted", True)
        self.filename.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.addWidget(self.filename)
        self.logging = QCheckBox("Phân tích và ghi lịch sử theo timeline")
        self.logging.setToolTip("Mặc định chỉ xem trước, không ghi lịch sử. Chỉ bật khi được phép ghi nhận.")
        self.logging.toggled.connect(lambda enabled: window.set_logging("video", enabled))
        body.addWidget(self.logging)
        layout.addWidget(box)
        screen, screen_layout = panel()
        heading = QHBoxLayout()
        heading.addWidget(label("Trình phát video", "SectionTitle"))
        heading.addStretch()
        heading.addWidget(label("Giữ nguyên tỷ lệ hình", "Badge"))
        screen_layout.addLayout(heading)
        self.canvas = VideoCanvas(window.settings)
        self.canvas.empty_icon = "video"
        self.canvas.empty_title = "Chưa có video"
        self.canvas.empty_hint = "Mở tệp MP4, AVI hoặc định dạng được hỗ trợ."
        screen_layout.addWidget(self.canvas, 1)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimumHeight(24)
        self.slider.setRange(0, 10000)
        self.slider.sliderReleased.connect(self.seek)
        screen_layout.addWidget(self.slider)
        self.status = label("00:00:00.000 / 00:00:00.000", "Muted", True)
        screen_layout.addWidget(self.status)
        layout.addWidget(screen, 1)


    def open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn video", "", "Video (*.mp4 *.avi *.mkv *.mov *.wmv);;Tất cả (*)")
        if path:
            self.path = path
            self.filename.setText(path)
            self.window.start_media("video", path, self.logging.isChecked())
            self.window.pipeline.command("speed", float(self.speed.currentText()[:-1]))

    def toggle(self):
        state = self.window.pipeline.snapshot()
        if state["kind"] != "video" or not self.path:
            return
        if state["position"] >= state["duration"] - 0.1:
            self.window.pipeline.command("seek", 0)
        self.window.pipeline.command("play", not state["playing"])

    def rewind(self):
        if self.window.pipeline.snapshot()["kind"] == "video":
            self.window.pipeline.command("play", False)
            self.window.pipeline.command("seek", 0)

    def seek(self):
        self.window.pipeline.command("seek", self.slider.value()/10000*self.duration)
        self.canvas.clear()

    def update_position(self, state):
        self.duration = state["duration"]
        if not self.slider.isSliderDown():
            self.slider.setValue(round(10000*state["position"]/max(self.duration, 0.001)))
        self.status.setText(f"{timeline(state['position'])} / {timeline(self.duration)} · Inference {state['fps']:.1f} FPS · {self.window.engine.backend}")

from PySide6.QtCore import Qt, QSignalBlocker
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QFileDialog, QSlider, QLineEdit,
                               QMessageBox, QStyle, QStyleOptionSlider)
from app.services.csv_exporter import timeline
from app.ui.common import VideoCanvas
from app.ui.presence_panel import PresencePanel
from app.ui.theme import page_layout, page_header, panel, action, label, FlowLayout
from app.ui.theme import CheckBox as QCheckBox, ComboBox as QComboBox


class SeekSlider(QSlider):
    """Click/drag anywhere on the bar; commit one seek when released."""
    def __init__(self):
        super().__init__(Qt.Horizontal)
        self.setRange(0, 10000)
        self.setMinimumHeight(28)
        self.setToolTip("Kéo để tua · ←/→ từng bước · Home/End đầu/cuối")
        self.setSingleStep(100)
        self.setPageStep(1000)

    def _position(self, event):
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        handle = self.style().subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle, self)
        span = max(1, self.width()-handle.width())
        self.setValue(QStyle.sliderValueFromPosition(self.minimum(), self.maximum(),
                      round(event.position().x()-handle.width()/2), span, option.upsideDown))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setFocus()
            self.setSliderDown(True)
            self._position(event)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.isSliderDown():
            self._position(event)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.isSliderDown():
            self._position(event)
            self.setSliderDown(False)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


def parse_time(text):
    parts = text.strip().split(":")
    if not 1 <= len(parts) <= 3:
        raise ValueError("Định dạng: giây, MM:SS hoặc HH:MM:SS.mmm.")
    try:
        values = [float(part) for part in parts]
        import math
        if any(not math.isfinite(value) or value < 0 for value in values):
            raise ValueError()
        if len(parts) > 1 and (any(not part.isdigit() for part in parts[:-1]) or any(value >= 60 for value in values[1:])):
            raise ValueError()
        result = 0.0
        for value in values:
            result = result*60 + value
        return result
    except ValueError:
        raise ValueError("Thời gian không hợp lệ.") from None


class VideoPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window, self.path, self.duration = window, "", 0
        layout = page_layout(self)
        page_header(layout, "Video", "Phát và nhận diện video.")
        box, body = panel()
        controls = FlowLayout(spacing=8)
        controls.addWidget(action("Mở video", self.open, "primary", "folder"))
        self.speed = QComboBox()
        self.speed.setMinimumWidth(90)
        self.speed.addItems(["0.25x", "0.5x", "1x", "1.5x", "2x"])
        self.speed.setCurrentIndex(2)
        self.speed.currentTextChanged.connect(lambda text: window.pipeline.command("speed", float(text[:-1])))
        body.addLayout(controls)
        self.filename = label("Chưa chọn tệp video", "Muted", True)
        self.filename.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.addWidget(self.filename)
        self.logging = QCheckBox("Phân tích và ghi lịch sử theo timeline")
        self.logging.setToolTip("Chỉ ghi lịch sử khi được phép.")
        self.logging.toggled.connect(lambda enabled: window.set_logging("video", enabled))
        options = FlowLayout(spacing=20)
        options.addWidget(self.logging)
        self.alerts = QCheckBox("Thông báo khi phát hiện")
        self.alerts.setToolTip("Cấu hình email tại trang Thông báo.")
        self.alerts.toggled.connect(lambda enabled: window.notifications.set_enabled("video", enabled))
        options.addWidget(self.alerts)
        body.addLayout(options)
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
        self.canvas.empty_hint = "Chọn video để phát."
        screen_layout.addWidget(self.canvas, 1)
        self.transport, transport = panel()
        self.slider = SeekSlider()
        self.slider.sliderReleased.connect(self.seek)
        self.slider.valueChanged.connect(self.slider_changed)
        transport.addWidget(self.slider)
        self.time_label = label("00:00:00.000 / 00:00:00.000", "FieldLabel")
        transport.addWidget(self.time_label)
        navigation = FlowLayout(spacing=8)
        navigation.addWidget(action("Về đầu", self.rewind))
        navigation.addWidget(action("−10 giây", lambda: self.skip(-10)))
        self.play_button = action("Phát", self.toggle, "primary")
        navigation.addWidget(self.play_button)
        navigation.addWidget(action("+10 giây", lambda: self.skip(10)))
        navigation.addWidget(self.speed)
        self.jump_time = QLineEdit()
        self.jump_time.setMaximumWidth(135)
        self.jump_time.setPlaceholderText("HH:MM:SS")
        self.jump_time.setToolTip("Giây · MM:SS · HH:MM:SS.mmm")
        self.jump_time.returnPressed.connect(self.jump)
        navigation.addWidget(self.jump_time)
        navigation.addWidget(action("Đi tới", self.jump))
        transport.addLayout(navigation)
        self.transport.setEnabled(False)
        screen_layout.addWidget(self.transport)
        self.status = label("Chưa mở video", "Muted", True)
        screen_layout.addWidget(self.status)
        view = QHBoxLayout()
        view.addWidget(screen, 1)
        self.presence = PresencePanel()
        view.addWidget(self.presence)
        layout.addLayout(view, 1)

    def open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn video", "", "Video (*.mp4 *.avi *.mkv *.mov *.wmv);;Tất cả (*)")
        if path:
            self.path = path
            self.filename.setText(path)
            self.duration = 0
            self.transport.setEnabled(False)
            self.window.start_media("video", path, self.logging.isChecked())
            self.window.pipeline.command("speed", float(self.speed.currentText()[:-1]))

    def toggle(self):
        state = self.window.pipeline.snapshot()
        if state["kind"] != "video" or not self.path:
            return
        # Last timestamp is duration - one frame; do not restart normal pauses near EOF.
        raw = self.window.pipeline.raw.peek()
        at_end = raw is not None and self.window.pipeline.ended_epoch == self.window.pipeline.epoch
        if at_end:
            self.window.pipeline.command("seek", 0)
        self.window.pipeline.command("play", not state["playing"])

    def rewind(self):
        if self.window.pipeline.snapshot()["kind"] == "video":
            self.window.pipeline.command("play", False)
            self.seek_to(0)

    def seek_to(self, seconds):
        if self.window.pipeline.snapshot()["kind"] != "video" or self.duration <= 0:
            return
        self.window.pipeline.command("seek", min(max(seconds, 0), self.duration))
        self.canvas.clear()
        self.presence.clear()

    def seek(self):
        self.seek_to(self.slider.value()/10000*self.duration)

    def slider_changed(self, value):
        self.time_label.setText(f"{timeline(value/10000*self.duration)} / {timeline(self.duration)}")
        if not self.slider.isSliderDown():
            self.seek()

    def skip(self, delta):
        state = self.window.pipeline.snapshot()
        self.seek_to(state["position"]+delta)

    def jump(self):
        try:
            seconds = parse_time(self.jump_time.text())
            if seconds > self.duration:
                raise ValueError("Thời gian vượt quá độ dài video.")
            self.seek_to(seconds)
        except ValueError as exc:
            QMessageBox.information(self, "Đi tới thời gian", str(exc))

    def update_position(self, state):
        active = state["kind"] == "video" and state["duration"] > 0
        self.duration = state["duration"] if active else 0
        self.transport.setEnabled(active)
        self.play_button.setText("Tạm dừng" if active and state["playing"] else "Phát")
        if not self.slider.isSliderDown():
            with QSignalBlocker(self.slider):
                self.slider.setValue(round(10000*state["position"]/max(self.duration, 0.001)) if active else 0)
            self.time_label.setText(f"{timeline(state['position'] if active else 0)} / {timeline(self.duration)}")
        self.status.setText(f"Nhận diện {state['fps']:.1f} FPS · {self.window.engine.backend}" if active else "Chưa mở video")

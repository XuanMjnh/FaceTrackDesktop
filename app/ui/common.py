from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import QObject, Signal, Qt, QRectF
from PySide6.QtGui import QImage, QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QWidget, QMessageBox, QPushButton, QTableWidgetItem, QAbstractItemView, QSizePolicy
from app.ui.theme import action, line_icon


class Jobs(QObject):
    done = Signal(object, object)
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ui-task")
        self.accepting = True
        self.done.connect(lambda callback, result: callback(result) if callback and self.accepting else None)
        self.error.connect(lambda text: QMessageBox.warning(parent, "Tìm Người", text) if self.accepting else None)

    def run(self, task, callback=None):
        if not self.accepting:
            return
        def execute():
            try:
                self.done.emit(callback, task())
            except Exception as exc:
                self.error.emit(str(exc))
        self.pool.submit(execute)


class TimeItem(QTableWidgetItem):
    def __init__(self, text, seconds):
        super().__init__(text)
        self.seconds = seconds
        self.setFlags(self.flags() & ~Qt.ItemIsEditable)

    def __lt__(self, other):
        if isinstance(other, TimeItem):
            return self.seconds < other.seconds
        return super().__lt__(other)


def button(text, callback, layout):
    control = action(text, callback)
    layout.addWidget(control)
    return control


def confirm(parent, text):
    return QMessageBox.question(parent, "Xác nhận", text, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes


def fill_table(table, rows):
    table.setSortingEnabled(False)
    table.setRowCount(len(rows))
    for i, values in enumerate(rows):
        for j, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item.setToolTip(str(value))
            table.setItem(i, j, item)
    table.setSortingEnabled(True)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.horizontalHeader().setStretchLastSection(False)


class VideoCanvas(QWidget):
    """Paint a source frame with a single uniform scale, including on HiDPI."""
    def __init__(self, settings):
        super().__init__()
        self.settings, self.image, self.labels = settings, None, []
        self.empty_title = "Chưa có hình ảnh"
        self.empty_hint = "Chọn nguồn dữ liệu để bắt đầu."
        self.empty_icon = "camera"
        self.setMinimumSize(240, 160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_frame(self, image, labels=()):
        if image is None or image.size == 0:
            self.clear()
            return
        rgb = image[:, :, ::-1].copy()
        self.image = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format_RGB888).copy()
        self.labels = labels
        self.update()

    def clear(self):
        self.image, self.labels = None, []
        self.update()

    def image_rect(self):
        if self.image is None:
            return QRectF()
        scale = min(self.width()/self.image.width(), self.height()/self.image.height())
        width, height = self.image.width()*scale, self.image.height()*scale
        return QRectF((self.width()-width)/2, (self.height()-height)/2, width, height)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if self.image is None:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#F0F2F4"))
            painter.drawRoundedRect(QRectF(self.rect()), 12, 12)
            center = self.rect().center()
            icon_rect = QRectF(center.x()-31, center.y()-66, 62, 62)
            painter.setPen(QPen(QColor("#DDE1E6"), 1))
            painter.setBrush(QColor("#ffffff"))
            painter.drawRoundedRect(icon_rect, 12, 12)
            line_icon(self.empty_icon, "#E57958", 28).paint(painter, int(center.x()-14), int(center.y()-49), 28, 28)
            font = self.font()
            font.setPointSize(12)
            font.setWeight(QFont.DemiBold)
            painter.setFont(font)
            painter.setPen(QColor("#252B34"))
            painter.drawText(QRectF(16, center.y()+9, self.width()-32, 26), Qt.AlignCenter, self.empty_title)
            font.setPointSize(10)
            font.setWeight(QFont.Normal)
            painter.setFont(font)
            painter.setPen(QColor("#66707C"))
            painter.drawText(QRectF(24, center.y()+40, self.width()-48, 50), Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, self.empty_hint)
            return
        painter.fillRect(self.rect(), QColor("#18212c"))
        target = self.image_rect()
        scale = target.width()/self.image.width()
        painter.drawImage(target, self.image)
        painter.setClipRect(self.rect())
        font = self.font()
        font.setPointSize(10)
        painter.setFont(font)
        for label in self.labels:
            x1, y1, x2, y2 = label.bbox
            rect = QRectF(target.left()+x1*scale, target.top()+y1*scale, max(0,(x2-x1)*scale), max(0,(y2-y1)*scale))
            match = label.match
            color = QColor("#48d7a3" if match.person_id else "#f0c36b")
            painter.setPen(QPen(color, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)
            parts = []
            if match.person_id:
                if self.settings.show_name:
                    parts.append(match.name)
                if self.settings.show_id:
                    parts.append("ID: " + match.person_id)
            else:
                parts.append("Không xác định")
            if self.settings.show_score:
                parts.append(f"Độ tương đồng: {match.score:.3f}")
            if not parts:
                continue
            text = "\n".join(parts)
            max_width = max(100, min(380, self.width()-24))
            bounds = painter.boundingRect(QRectF(0, 0, max_width-20, 300), Qt.TextWordWrap, text)
            width, height = min(max_width, bounds.width()+20), bounds.height()+14
            left = min(max(6, rect.left()), max(6, self.width()-width-6))
            top = rect.top()-height-5
            if top < 6:
                top = min(max(6, rect.top()+4), max(6, self.height()-height-6))
            box = QRectF(left, top, width, height)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(24, 33, 44, 230))
            painter.drawRoundedRect(box, 4, 4)
            painter.setPen(color)
            painter.drawText(box.adjusted(10, 7, -10, -7), Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, text)

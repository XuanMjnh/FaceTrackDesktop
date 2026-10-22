"""Geometric grayscale, charcoal and coral UI. Layout helpers stay compatible.

Bundled Be Vietnam Pro fonts are loaded once; all icons are drawn locally.
"""
from pathlib import Path
from functools import lru_cache
from PySide6.QtCore import Qt, QSize, QRect, QPoint, QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPalette, QLinearGradient
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QLayout,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget, QGridLayout, QHeaderView,
    QAbstractItemView)

# Keep the controls neutral so the geometric background stays subtle.
INK = "#20252D"
MUTED = "#66707C"
ACCENT = "#E57958"
FONT_FAMILY = "Be Vietnam Pro"

STYLE = """
QWidget { color: #20252D; font-family: "Be Vietnam Pro"; font-size: 13px; }
QMainWindow, QWidget#Workspace { background: transparent; }
QStackedWidget { background: transparent; }
QDialog, QMessageBox, QInputDialog { background: #F8F9FA; }
QLabel { background: transparent; }
QLabel#PageTitle { color: #1B2028; font-size: 25px; font-weight: 600; }
QLabel#Muted, QLabel#PageSubtitle { color: #66707C; }
QLabel#SectionTitle { color: #252B34; font-size: 14px; font-weight: 600; }
QLabel#FieldLabel { color: #59636F; font-size: 12px; }
QLabel#Brand { font-size: 22px; font-weight: 600; color: #1B2028; }
QLabel#BrandMark { background: #FFFFFF; color: #F28C28; border: 1px solid #DCE0E5; border-radius: 11px;
    font-size: 20px; font-weight: 600; }
QLabel#Eyebrow { font-size: 10px; font-weight: 600; color: #77808B; }
QLabel#Badge { background: #F0F2F4; color: #56606B; border: 1px solid #E0E3E7;
    border-radius: 11px; padding: 5px 9px; font-size: 11px; }
QFrame#Sidebar { background: rgba(250, 251, 252, 238); border-right: 1px solid rgba(199, 204, 211, 210); }
QFrame#Panel { background: transparent; border: none; }
QFrame#Hairline { background: #E0E3E7; border: 0; max-height: 1px; }
QListWidget#Navigation { background: transparent; border: none; outline: 0; }
QListWidget#Navigation::item { color: #59636F; padding: 0 10px;
    border-radius: 12px; margin: 2px 0; font-size: 12px; }
QListWidget#Navigation::item:hover { background: #F0F2F4; color: #20252D; }
QListWidget#Navigation::item:selected { background: #E8EBEF; color: #20252D; font-weight: 600; }
QPushButton { background: rgba(255, 255, 255, 244); color: #303740; border: 1px solid #D9DDE2;
    border-radius: 18px; padding: 8px 13px; min-height: 18px; font-size: 12px; }
QPushButton:hover { background: #F0F2F4; border-color: #BCC2CA; }
QPushButton:pressed { background: #E5E8EC; border-color: #ADB4BD; }
QPushButton[variant="primary"] { background: #252B34; border-color: #252B34;
    color: #FFFFFF; font-weight: 600; }
QPushButton[variant="primary"]:hover { background: #373E48; border-color: #373E48; }
QPushButton[variant="primary"]:pressed { background: #171B21; border-color: #171B21; }
QPushButton[variant="danger"] { color: #A44832; background: #FFF6F1; border-color: #EFD8CD; }
QPushButton[variant="danger"]:hover { background: #FBE7DD; border-color: #D99B81; }
QPushButton[variant="danger"]:pressed { background: #F4D5C6; }
QPushButton[variant="quiet"] { background: transparent; border-color: transparent; color: #66707C; }
QPushButton[variant="quiet"]:hover { background: #F0F2F4; border-color: #D9DDE2; }
QPushButton:focus, QPushButton[variant="primary"]:focus,
QPushButton[variant="danger"]:focus, QPushButton[variant="quiet"]:focus { border: 1px solid #D97855; }
QPushButton:disabled, QPushButton[variant="primary"]:disabled,
QPushButton[variant="danger"]:disabled, QPushButton[variant="quiet"]:disabled {
    color: #9098A2; background: #EFF1F3; border-color: #E1E4E8; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {
    background: rgba(255, 255, 255, 248); border: 1px solid #D9DDE2; border-radius: 10px;
    padding: 7px 10px; min-height: 20px; selection-background-color: #F8E5DA;
    selection-color: #20252D; }
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover { border-color: #BCC2CA; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus { border-color: #D97855; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled {
    background: #EFF1F3; color: #9098A2; border-color: #E1E4E8; }
QComboBox { padding-right: 28px; }
QComboBox::drop-down, QDateEdit::drop-down { width: 25px; border: none; }
QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border;
    subcontrol-position: top right; width: 20px; border: none; background: transparent; }
QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border;
    subcontrol-position: bottom right; width: 20px; border: none; background: transparent; }
QComboBox QAbstractItemView { background: #FFFFFF; color: #20252D;
    selection-background-color: #E8EBEF; selection-color: #20252D;
    border: 1px solid #D9DDE2; padding: 4px; outline: 0; }
QSpinBox, QDoubleSpinBox, QDateEdit { padding-right: 24px; }
QCheckBox { spacing: 9px; background: transparent; font-size: 12px; }
QCheckBox:disabled { color: #9098A2; }
QCheckBox::indicator { width: 17px; height: 17px; }
QTableWidget { background: rgba(255, 255, 255, 242); alternate-background-color: #F4F5F7; border: none;
    gridline-color: #E4E7EB; selection-background-color: #E8EBEF;
    selection-color: #20252D; outline: 0; }
QTableWidget::item { padding: 8px; border-bottom: 1px solid #E4E7EB; }
QTableWidget::item:selected { background: #E8EBEF; color: #20252D; }
QTableWidget::item:focus { border: 1px solid #C6CBD2; }
QHeaderView::section { background: #EEF0F3; color: #56606B; padding: 11px 8px;
    border: none; border-bottom: 1px solid #D9DDE2; font-size: 12px; font-weight: 600; }
QTableCornerButton::section { background: #EEF0F3; border: none; }
QListWidget#References { background: rgba(255, 255, 255, 238); border: 1px solid #DDE1E6; border-radius: 10px; padding: 4px; }
QListWidget#References::item { padding: 10px; border-radius: 8px; }
QListWidget#References::item:hover { background: #F0F2F4; }
QListWidget#References::item:selected { background: #E8EBEF; color: #20252D; }
QPlainTextEdit { background: #F2F4F6; color: #424A54; border: 1px solid #DDE1E6;
    border-radius: 10px; padding: 10px; selection-background-color: #F8E5DA; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #C8CDD4; min-height: 28px; border-radius: 3px; }
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: #AEB5BE; }
QScrollBar:horizontal { background: #ECEEF1; height: 11px; margin: 2px; }
QScrollBar::handle:horizontal { background: #C8CDD4; min-width: 28px; border-radius: 3px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QSlider::groove:horizontal { height: 4px; background: #DDE1E6; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #E57958; border-radius: 2px; }
QSlider::handle:horizontal { background: #252B34; border: 2px solid #FFFFFF;
    width: 12px; height: 12px; margin: -6px 0; border-radius: 8px; }
QSlider::handle:horizontal:hover { background: #E57958; }
QSlider::handle:horizontal:disabled { background: #BCC2CA; }
QSlider::sub-page:horizontal:disabled { background: #C8CDD4; }
QStatusBar { background: rgba(250, 251, 252, 238); color: #66707C; border-top: 1px solid #D9DDE2; font-size: 11px; }
QStatusBar::item { border: none; }
QToolTip { background: #252B34; color: #FFFFFF; border: 0; padding: 7px; border-radius: 6px; }
QCalendarWidget QWidget { background: #F8F9FA; color: #20252D; }
QCalendarWidget QToolButton { background: #EEF0F3; color: #20252D;
    border: none; border-radius: 6px; padding: 5px; }
QCalendarWidget QAbstractItemView { selection-background-color: #E8EBEF; selection-color: #20252D; }
"""


class GeometricBackground(QWidget):
    def __init__(self):
        super().__init__()
        image = Path(__file__).resolve().parent / "assets" / "white-geometrical-shapes-background-blurred.jpg"
        self._source = QPixmap(str(image))
        self._scaled = QPixmap()
        self.setAttribute(Qt.WA_OpaquePaintEvent)

    def paintEvent(self, event):
        painter = QPainter(self)
        if self._source.isNull():
            painter.fillRect(self.rect(), QColor("#F2F3F5"))
            return
        if self._scaled.size() != self.size():
            self._scaled = self._source.scaled(self.size(), Qt.KeepAspectRatioByExpanding,
                                               Qt.SmoothTransformation)
        x = (self.width() - self._scaled.width()) // 2
        y = (self.height() - self._scaled.height()) // 2
        painter.drawPixmap(x, y, self._scaled)
        painter.fillRect(self.rect(), QColor(218, 221, 226, 108))


def apply_theme(window):
    app = QApplication.instance()
    app.setStyle("Fusion")
    palette = QPalette()
    for role, color in ((QPalette.Window, "#F2F3F5"), (QPalette.WindowText, "#20252D"),
                        (QPalette.Base, "#FFFFFF"), (QPalette.AlternateBase, "#F4F5F7"),
                        (QPalette.Text, "#20252D"), (QPalette.Button, "#FAFBFC"),
                        (QPalette.ButtonText, "#303740"), (QPalette.Highlight, "#F8E5DA"),
                        (QPalette.HighlightedText, "#20252D"), (QPalette.ToolTipBase, "#252B34"),
                        (QPalette.ToolTipText, "#FFFFFF"), (QPalette.PlaceholderText, "#7D8590")):
        palette.setColor(role, QColor(color))
    for role in (QPalette.Text, QPalette.WindowText, QPalette.ButtonText):
        palette.setColor(QPalette.Disabled, role, QColor("#9098A2"))
    app.setPalette(palette)
    if not app.property("facetrack_fonts_loaded"):
        fonts = Path(__file__).resolve().parent / "assets" / "fonts"
        for filename in ("BeVietnamPro-Regular.ttf", "BeVietnamPro-SemiBold.ttf"):
            QFontDatabase.addApplicationFont(str(fonts / filename))
        app.setProperty("facetrack_fonts_loaded", True)
    app.setFont(QFont(FONT_FAMILY, 10))
    # Application scope also styles detached combo/calendar popups and dialogs.
    app.setStyleSheet(STYLE)
    window.setStyleSheet(STYLE)


@lru_cache(maxsize=256)

def line_icon(name, color=ACCENT, size=20):
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size/24, size/24)
    p.setPen(QPen(QColor(color), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    if name == "camera":
        p.drawRoundedRect(QRectF(3, 7, 18, 13), 2, 2)
        p.drawEllipse(QPoint(12, 13), 4, 4)
        p.drawLine(7, 7, 9, 4); p.drawLine(9, 4, 15, 4); p.drawLine(15, 4, 17, 7)
    elif name == "video":
        p.drawRoundedRect(QRectF(3, 4, 18, 16), 2, 2)
        p.drawLine(10, 8, 16, 12); p.drawLine(16, 12, 10, 16); p.drawLine(10, 16, 10, 8)
    elif name == "people":
        p.drawEllipse(QPoint(10, 8), 4, 4)
        p.drawArc(QRectF(3, 14, 14, 12), 0, 180*16)
        p.drawArc(QRectF(13, 5, 7, 7), -80*16, 160*16)
        p.drawArc(QRectF(15, 14, 7, 11), 0, 90*16)
    elif name == "history":
        p.drawEllipse(QPoint(12, 12), 9, 9)
        p.drawLine(12, 6, 12, 12); p.drawLine(12, 12, 16, 14)
    elif name == "mail":
        p.drawRoundedRect(QRectF(3, 5, 18, 14), 2, 2)
        p.drawLine(3, 6, 12, 13); p.drawLine(12, 13, 21, 6)
    elif name == "settings":
        for y, x in ((6, 9), (12, 16), (18, 7)):
            p.drawLine(3, y, x-3, y); p.drawLine(x+3, y, 21, y)
            p.drawEllipse(QPoint(x, y), 3, 3)
    elif name == "folder":
        p.drawPolyline([QPoint(3, 8), QPoint(3, 5), QPoint(10, 5), QPoint(12, 8), QPoint(21, 8), QPoint(21, 20), QPoint(3, 20), QPoint(3, 8)])
    elif name == "plus":
        p.drawLine(12, 5, 12, 19); p.drawLine(5, 12, 19, 12)
    elif name == "download":
        p.drawLine(12, 3, 12, 15); p.drawLine(7, 10, 12, 15); p.drawLine(12, 15, 17, 10)
        p.drawPolyline([QPoint(4, 16), QPoint(4, 21), QPoint(20, 21), QPoint(20, 16)])
    elif name == "shield":
        p.drawPolyline([QPoint(12, 3), QPoint(20, 6), QPoint(19, 15), QPoint(12, 21), QPoint(5, 15), QPoint(4, 6), QPoint(12, 3)])
        p.drawLine(8, 12, 11, 15); p.drawLine(11, 15, 16, 9)
    elif name == "search":
        p.drawEllipse(QPoint(10, 10), 6, 6)
        p.drawLine(15, 15, 21, 21)
    elif name == "refresh":
        p.drawArc(QRectF(4, 4, 16, 16), 35*16, 285*16)
        p.drawPolyline([QPoint(15, 4), QPoint(20, 4), QPoint(20, 9)])
    elif name == "stop":
        p.drawRoundedRect(QRectF(5, 5, 14, 14), 3, 3)
    elif name == "image":
        p.drawRoundedRect(QRectF(3, 3, 18, 18), 3, 3)
        p.drawEllipse(QPoint(8, 8), 2, 2)
        p.drawPolyline([QPoint(3, 17), QPoint(9, 12), QPoint(13, 16), QPoint(17, 11), QPoint(21, 16)])
    elif name == "eye":
        _paint_eye(p)
    elif name == "edit":
        p.drawPolyline([QPoint(4, 16), QPoint(15, 5), QPoint(19, 9), QPoint(8, 20), QPoint(4, 20), QPoint(4, 16)])
        p.drawLine(12, 8, 16, 12); p.drawLine(13, 21, 21, 21)
    elif name == "power":
        p.drawArc(QRectF(4, 4, 16, 16), 130*16, 280*16)
        p.drawLine(12, 2, 12, 11)
    elif name == "trash":
        p.drawLine(3, 6, 21, 6)
        p.drawPolyline([QPoint(8, 6), QPoint(8, 3), QPoint(16, 3), QPoint(16, 6)])
        p.drawPolyline([QPoint(5, 7), QPoint(6, 21), QPoint(18, 21), QPoint(19, 7)])
        p.drawLine(10, 10, 10, 17); p.drawLine(14, 10, 14, 17)
    elif name == "filter":
        p.drawPolyline([QPoint(3, 4), QPoint(21, 4), QPoint(14, 12), QPoint(14, 20),
                        QPoint(10, 18), QPoint(10, 12), QPoint(3, 4)])
    elif name == "save":
        p.drawPolyline([QPoint(4, 3), QPoint(17, 3), QPoint(21, 7), QPoint(21, 21),
                        QPoint(3, 21), QPoint(3, 3), QPoint(4, 3)])
        p.drawRect(QRectF(7, 3, 9, 6)); p.drawRect(QRectF(7, 14, 10, 7))
    elif name == "cpu":
        p.drawRoundedRect(QRectF(6, 6, 12, 12), 2, 2)
        p.drawRect(QRectF(9, 9, 6, 6))
        for n in (8, 12, 16):
            p.drawLine(n, 2, n, 6); p.drawLine(n, 18, n, 22)
            p.drawLine(2, n, 6, n); p.drawLine(18, n, 22, n)
    elif name in ("login", "logout"):
        p.drawPolyline([QPoint(14, 3), QPoint(20, 3), QPoint(20, 21), QPoint(14, 21)])
        p.drawLine(3, 12, 15, 12)
        x, dx = (15, -4) if name == "login" else (3, 4)
        p.drawPolyline([QPoint(x+dx, 8), QPoint(x, 12), QPoint(x+dx, 16)])
    elif name == "send":
        p.drawPolyline([QPoint(3, 10), QPoint(21, 3), QPoint(14, 21), QPoint(10, 14), QPoint(3, 10)])
        p.drawLine(10, 14, 21, 3)
    elif name == "play":
        p.drawPolyline([QPoint(8, 4), QPoint(20, 12), QPoint(8, 20), QPoint(8, 4)])
    elif name == "pause":
        p.drawRoundedRect(QRectF(6, 4, 4, 16), 1, 1)
        p.drawRoundedRect(QRectF(14, 4, 4, 16), 1, 1)
    elif name == "rewind":
        p.drawLine(5, 4, 5, 20)
        p.drawPolyline([QPoint(19, 5), QPoint(9, 12), QPoint(19, 19), QPoint(19, 5)])
    elif name in ("back", "forward"):
        direction = -1 if name == "back" else 1
        p.drawArc(QRectF(4, 4, 16, 16), (140 if direction < 0 else 40)*16,
                  (280 if direction < 0 else -280)*16)
        x = 4 if direction < 0 else 20
        p.drawPolyline([QPoint(x, 3), QPoint(x, 8), QPoint(x-direction*5, 8)])
        p.drawLine(12, 8, 12, 12); p.drawLine(12, 12, 15, 14)
    elif name == "arrow":
        p.drawLine(3, 12, 21, 12)
        p.drawPolyline([QPoint(15, 6), QPoint(21, 12), QPoint(15, 18)])
    elif name == "close":
        p.drawLine(6, 6, 18, 18); p.drawLine(18, 6, 6, 18)
    p.end()
    return QIcon(pixmap)


def label(text, role="Muted", wrap=False):
    item = QLabel(text)
    item.setObjectName(role)
    item.setWordWrap(wrap)
    item.setTextFormat(Qt.PlainText)
    return item


def _paint_eye(painter):
    eye = QPainterPath()
    eye.moveTo(2.5, 12)
    eye.cubicTo(5.1, 7.2, 8.2, 4.8, 12, 4.8)
    eye.cubicTo(15.8, 4.8, 18.9, 7.2, 21.5, 12)
    eye.cubicTo(18.9, 16.8, 15.8, 19.2, 12, 19.2)
    eye.cubicTo(8.2, 19.2, 5.1, 16.8, 2.5, 12)
    painter.drawPath(eye)
    painter.drawEllipse(QPointF(12, 12), 3.1, 3.1)
    painter.setBrush(painter.pen().color())
    painter.drawEllipse(QPointF(12, 12), 1.1, 1.1)
    painter.setBrush(Qt.NoBrush)


def brand_icon(size=48):
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.scale(size / 24, size / 24)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#FFFFFF"))
    painter.drawRoundedRect(QRectF(0, 0, 24, 24), 6, 6)
    painter.setPen(QPen(QColor("#F28C28"), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(Qt.NoBrush)
    _paint_eye(painter)
    painter.end()
    return QIcon(pixmap)


# Existing button() callers (including the reference-image dialog) retain icons.
_ACTION_ICONS = {
    "Quét camera": "refresh", "Bắt đầu camera": "camera", "Dừng": "stop",
    "Chụp ảnh": "camera", "Mở video": "folder", "Về đầu": "rewind",
    "−10 giây": "back", "+10 giây": "forward", "Phát": "play", "Tạm dừng": "pause",
    "Đi tới": "arrow", "Thêm người": "plus", "Tìm kiếm": "search",
    "Ảnh tham chiếu": "image", "Đổi tên": "edit", "Bật / Ngừng sử dụng": "power",
    "Xem lịch sử": "history", "Xóa hồ sơ": "trash", "Thêm ảnh": "plus",
    "Thay ảnh chọn": "refresh", "Xóa ảnh chọn": "trash", "Xuất CSV": "download",
    "Áp dụng bộ lọc": "filter", "Xóa phiên đã chọn": "trash", "Xóa toàn bộ lịch sử": "trash",
    "Lưu cài đặt": "save", "Chọn…": "folder", "Kiểm tra CPU / GPU": "cpu",
    "Đăng nhập": "login", "Đăng xuất": "logout", "Gửi thử": "send",
    "Thêm email": "plus", "Xóa đã chọn": "trash", "Làm mới": "refresh",
}


class ActionButton(QPushButton):
    """Keep accessible text and icon synchronized when playback changes state."""
    def __init__(self, text, variant="default", icon=None):
        super().__init__(text)
        self._variant = variant
        self._explicit_icon = icon
        self.setProperty("variant", variant)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.setIconSize(QSize(17, 17))
        self._sync_icon(text)

    def _sync_icon(self, text):
        name = self._explicit_icon or _ACTION_ICONS.get(text)
        if name:
            color = "#FFFFFF" if self._variant == "primary" else ("#B65A3E" if self._variant == "danger" else ACCENT)
            self.setIcon(line_icon(name, color, 18))
        else:
            self.setIcon(QIcon())
        self.setAccessibleName(text)
        self.setToolTip(text)

    def setText(self, text):
        if text != self.text():
            super().setText(text)
            self._sync_icon(text)


def action(text, callback, variant="default", icon=None):
    item = ActionButton(text, variant, icon)
    item.clicked.connect(callback)
    return item


def page_layout(widget):
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(24, 22, 24, 18)
    layout.setSpacing(16)
    return layout


def page_header(layout, title, subtitle, control=None):
    row = QHBoxLayout()
    row.setSpacing(16)
    titles = QVBoxLayout()
    titles.setSpacing(5)
    titles.addWidget(label(title, "PageTitle"))
    titles.addWidget(label(subtitle, "PageSubtitle", True))
    row.addLayout(titles, 1)
    if control:
        row.addWidget(control, 0, Qt.AlignTop)
    layout.addLayout(row)


class SoftPanel(QFrame):
    """Paint a small soft edge without a live QGraphicsEffect on video frames."""
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(2, 1, -2, -4)
        p.setPen(Qt.NoPen)
        for spread, alpha in ((3, 3), (2, 5), (1, 8)):
            p.setBrush(QColor(43, 49, 58, alpha))
            p.drawRoundedRect(rect.adjusted(-spread/2, 1, spread/2, spread), 16, 16)
        fill = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        fill.setColorAt(0, QColor(255, 255, 255, 244))
        fill.setColorAt(1, QColor(248, 249, 251, 236))
        p.setBrush(fill)
        p.setPen(QPen(QColor(204, 209, 216, 230), 1))
        p.drawRoundedRect(rect, 15, 15)


def panel(title=None, subtitle=None):
    frame = SoftPanel()
    frame.setObjectName("Panel")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(12)
    if title:
        layout.addWidget(label(title, "SectionTitle"))
    if subtitle:
        layout.addWidget(label(subtitle, "Muted", True))
    return frame, layout


def field(caption, widget, hint=None):
    container = QWidget()
    container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    layout.addWidget(label(caption, "FieldLabel", True))
    layout.addWidget(widget)
    if hint:
        layout.addWidget(label(hint, "Muted", True))
    return container


def setup_table(table):
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.setWordWrap(True)
    table.setTextElideMode(Qt.ElideNone)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.ExtendedSelection)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
    table.verticalHeader().hide()
    table.verticalHeader().setDefaultSectionSize(64)
    header = table.horizontalHeader()
    header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    header.setMinimumSectionSize(60)
    header.setStretchLastSection(False)
    header.setSectionResizeMode(QHeaderView.Interactive)
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


class FlowLayout(QLayout):
    """Natural-size controls wrap into rows instead of being squeezed."""
    def __init__(self, parent=None, spacing=8):
        super().__init__(parent)
        self.items = []
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(spacing)

    def addItem(self, item):
        self.items.append(item)

    def count(self):
        return len(self.items)

    def itemAt(self, index):
        return self.items[index] if 0 <= index < len(self.items) else None

    def takeAt(self, index):
        return self.items.pop(index) if 0 <= index < len(self.items) else None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._arrange(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._arrange(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        result = QSize()
        for item in self.items:
            result = result.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return result + QSize(margins.left()+margins.right(), margins.top()+margins.bottom())

    def _arrange(self, rect, measure):
        margins = self.contentsMargins()
        area = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x, y, height = area.x(), area.y(), 0
        for item in self.items:
            hint = item.sizeHint()
            width = min(hint.width(), area.width())
            if x > area.x() and x+width > area.right()+1:
                x, y, height = area.x(), y+height+self.spacing(), 0
            if not measure:
                item.setGeometry(QRect(QPoint(x, y), QSize(width, hint.height())))
            x += width+self.spacing()
            height = max(height, hint.height())
        return y+height-rect.y()+margins.bottom()


class ResponsiveColumns(QWidget):
    def __init__(self, widgets, breakpoint=780):
        super().__init__()
        self.widgets = widgets
        self.breakpoint = breakpoint
        self.columns = 0
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(16)
        self._relayout(2)

    def _relayout(self, columns):
        if columns == self.columns:
            return
        self.columns = columns
        for widget in self.widgets:
            self.grid.removeWidget(widget)
        for column in range(2):
            self.grid.setColumnStretch(column, 0)
        for i, widget in enumerate(self.widgets):
            self.grid.addWidget(widget, i//columns, i%columns, Qt.AlignTop)
        for column in range(columns):
            self.grid.setColumnStretch(column, 1)

    def resizeEvent(self, event):
        self._relayout(2 if self.width() >= self.breakpoint else 1)
        super().resizeEvent(event)

# Draw small indicators explicitly so their contrast is consistent on Windows,
# including systems whose application palette was previously dark.
from PySide6.QtGui import QPolygonF
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import (QCheckBox as _QCheckBox, QComboBox as _QComboBox,
    QSpinBox as _QSpinBox, QDoubleSpinBox as _QDoubleSpinBox, QDateEdit as _QDateEdit,
    QStyle, QStyleOptionButton)


def _triangle(painter, x, y, up=False, enabled=True):
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#66707C" if enabled else "#BCC2CA"))
    direction = -1 if up else 1
    painter.drawPolygon(QPolygonF([QPointF(x-3.5, y-2*direction),
        QPointF(x+3.5, y-2*direction), QPointF(x, y+2.5*direction)]))


class CheckBox(_QCheckBox):
    def paintEvent(self, event):
        super().paintEvent(event)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        rect = self.style().subElementRect(QStyle.SE_CheckBoxIndicator, option, self)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        box = QRectF(rect).adjusted(0.8, 0.8, -0.8, -0.8)
        p.setPen(QPen(QColor("#252B34" if self.isChecked() and self.isEnabled() else "#BCC2CA"), 1.2))
        p.setBrush(QColor(("#252B34" if self.isEnabled() else "#BCC2CA") if self.isChecked() else "#FFFFFF"))
        p.drawRoundedRect(box, 3, 3)
        if self.isChecked():
            p.setPen(QPen(QColor("#ffffff"), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPolyline(QPolygonF([QPointF(box.left()+3.3, box.center().y()),
                QPointF(box.left()+6.3, box.bottom()-3.4), QPointF(box.right()-3, box.top()+4)]))


class ComboBox(_QComboBox):
    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.width()-25, 4, 20, self.height()-8, QColor("#FFFFFF" if self.isEnabled() else "#EFF1F3"))
        _triangle(p, self.width()-15, self.height()/2, enabled=self.isEnabled())


class _SpinIndicators:
    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.width()-22, 2, 19, self.height()-4, QColor("#F3F4F6"))
        p.setPen(QPen(QColor("#E0E3E7"), 1))
        p.drawLine(self.width()-22, 3, self.width()-22, self.height()-3)
        _triangle(p, self.width()-13, self.height()/2-7, up=True, enabled=self.isEnabled())
        _triangle(p, self.width()-13, self.height()/2+7, enabled=self.isEnabled())


class SpinBox(_SpinIndicators, _QSpinBox):
    pass


class DoubleSpinBox(_SpinIndicators, _QDoubleSpinBox):
    pass


class DateEdit(_QDateEdit):
    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.width()-23, 2, 20, self.height()-4, QColor("#FFFFFF" if self.isEnabled() else "#EFF1F3"))
        _triangle(p, self.width()-13, self.height()/2, enabled=self.isEnabled())

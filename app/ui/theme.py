"""Light desktop theme and reusable layout helpers. No external assets required."""
from PySide6.QtCore import Qt, QSize, QRect, QPoint, QRectF
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPen, QPixmap, QPalette
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QLayout,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget, QGridLayout, QHeaderView,
    QAbstractItemView)

STYLE = """
QWidget { color: #243247; font-size: 13px; }
QMainWindow, QWidget#Workspace, QStackedWidget { background: #f5f7fa; }
QDialog { background: #ffffff; }
QLabel { background: transparent; }
QLabel#PageTitle { color: #17263c; font-size: 25px; font-weight: 600; }
QLabel#Muted, QLabel#PageSubtitle { color: #68768a; }
QLabel#SectionTitle { color: #253449; font-size: 14px; font-weight: 600; }
QLabel#FieldLabel { color: #526176; font-size: 12px; }
QLabel#Brand { font-size: 22px; font-weight: 650; color: #17263c; }
QLabel#Eyebrow { font-size: 10px; font-weight: 600; color: #8290a3; }
QLabel#Badge { background: #edf3fc; color: #35639b; border-radius: 4px; padding: 5px 9px; font-size: 11px; }
QFrame#Sidebar { background: #ffffff; border-right: 1px solid #e2e7ee; }
QFrame#Panel { background: #ffffff; border: 1px solid #e1e6ed; border-radius: 8px; }
QFrame#Hairline { background: #e8ecf1; border: 0; max-height: 1px; }
QListWidget#Navigation { background: transparent; border: none; outline: 0; }
QListWidget#Navigation::item { color: #526176; padding: 0 12px; border-radius: 6px; margin: 2px 0; }
QListWidget#Navigation::item:hover { background: #f3f6fa; }
QListWidget#Navigation::item:selected { background: #eaf1fc; color: #245fba; font-weight: 600; }
QPushButton { background: #ffffff; color: #33445c; border: 1px solid #d6dee8;
    border-radius: 5px; padding: 8px 13px; min-height: 18px; }
QPushButton:hover { background: #f5f8fc; border-color: #b5c6dc; }
QPushButton:pressed { background: #eaf0f7; }
QPushButton:disabled { color: #a3adbb; background: #f7f8fa; border-color: #e7ebf0; }
QPushButton[variant="primary"] { background: #2867c7; border-color: #2867c7; color: #ffffff; font-weight: 600; }
QPushButton[variant="primary"]:hover { background: #2059ae; border-color: #2059ae; }
QPushButton[variant="danger"] { color: #b43c3c; background: #ffffff; border-color: #e6cccc; }
QPushButton[variant="danger"]:hover { background: #fff3f3; border-color: #d69b9b; }
QPushButton[variant="quiet"] { background: transparent; border-color: transparent; color: #526176; }
QPushButton[variant="quiet"]:hover { background: #edf2f8; }
QPushButton:focus { border-color: #5189d8; }
QPushButton[variant="danger"]:disabled, QPushButton[variant="primary"]:disabled {
    color: #a3adbb; background: #f7f8fa; border-color: #e7ebf0; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {
    background: #ffffff; border: 1px solid #d6dee8; border-radius: 5px;
    padding: 7px 10px; min-height: 20px; selection-background-color: #dceafe;
    selection-color: #17263c; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus { border-color: #5189d8; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled { background: #f5f7fa; color: #98a2b0; }
QComboBox { padding-right: 28px; }
QComboBox::drop-down, QDateEdit::drop-down { width: 25px; border: none; }
QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right;
    width: 20px; border: none; background: transparent; }
QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right;
    width: 20px; border: none; background: transparent; }
QComboBox QAbstractItemView { background: #ffffff; color: #243247; selection-background-color: #eaf1fc;
    selection-color: #245fba; border: 1px solid #d6dee8; padding: 4px; outline: 0; }
QSpinBox, QDoubleSpinBox, QDateEdit { padding-right: 24px; }
QCheckBox { spacing: 9px; background: transparent; }
QCheckBox::indicator { width: 17px; height: 17px; }
QTableWidget { background: #ffffff; alternate-background-color: #fafbfd; border: none;
    gridline-color: #edf0f4; selection-background-color: #eaf2ff; selection-color: #203f6c; outline: 0; }
QTableWidget::item { padding: 8px; border-bottom: 1px solid #edf0f4; }
QTableWidget::item:selected { background: #eaf2ff; color: #203f6c; }
QHeaderView::section { background: #f7f9fc; color: #617086; padding: 11px 8px;
    border: none; border-bottom: 1px solid #e1e6ed; font-size: 12px; font-weight: 600; }
QTableCornerButton::section { background: #f7f9fc; border: none; }
QListWidget#References { background: #ffffff; border: 1px solid #e1e6ed; border-radius: 5px; padding: 4px; }
QListWidget#References::item { padding: 10px; border-radius: 4px; }
QListWidget#References::item:selected { background: #eaf2ff; color: #203f6c; }
QPlainTextEdit { background: #f8fafc; color: #41536a; border: 1px solid #e1e6ed;
    border-radius: 5px; padding: 10px; selection-background-color: #dceafe; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #cbd4df; min-height: 28px; border-radius: 3px; }
QScrollBar:horizontal { background: #f5f7fa; height: 11px; margin: 2px; }
QScrollBar::handle:horizontal { background: #cbd4df; min-width: 28px; border-radius: 3px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QSlider::groove:horizontal { height: 4px; background: #e1e7ef; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #5189d8; border-radius: 2px; }
QSlider::handle:horizontal { background: #2867c7; border: 2px solid #ffffff;
    width: 12px; height: 12px; margin: -6px 0; border-radius: 8px; }
QStatusBar { background: #ffffff; color: #6b7789; border-top: 1px solid #e2e7ee; font-size: 11px; }
QStatusBar::item { border: none; }
QToolTip { background: #253449; color: #ffffff; border: 0; padding: 7px; }
"""


def apply_theme(window):
    app = QApplication.instance()
    app.setStyle("Fusion")
    palette = QPalette()
    for role, color in ((QPalette.Window, "#f5f7fa"), (QPalette.WindowText, "#243247"),
                        (QPalette.Base, "#ffffff"), (QPalette.AlternateBase, "#fafbfd"),
                        (QPalette.Text, "#243247"), (QPalette.Button, "#ffffff"),
                        (QPalette.ButtonText, "#33445c"), (QPalette.Highlight, "#2867c7"),
                        (QPalette.HighlightedText, "#ffffff"), (QPalette.ToolTipBase, "#253449"),
                        (QPalette.ToolTipText, "#ffffff"), (QPalette.PlaceholderText, "#8c98a8")):
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    families = QFontDatabase.families()
    family = next((f for f in ("Segoe UI", "Noto Sans", "DejaVu Sans") if f in families), app.font().family())
    app.setFont(QFont(family, 10))
    window.setStyleSheet(STYLE)


def line_icon(name, color="#65758b", size=20):
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
    p.end()
    return QIcon(pixmap)


def label(text, role="Muted", wrap=False):
    item = QLabel(text)
    item.setObjectName(role)
    item.setWordWrap(wrap)
    item.setTextFormat(Qt.PlainText)
    return item


def action(text, callback, variant="default", icon=None):
    item = QPushButton(text)
    item.setProperty("variant", variant)
    item.setCursor(Qt.PointingHandCursor)
    item.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    if icon:
        item.setIcon(line_icon(icon, "#ffffff" if variant == "primary" else "#65758b"))
        item.setIconSize(QSize(17, 17))
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


def panel(title=None, subtitle=None):
    frame = QFrame()
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
    painter.setBrush(QColor("#64758a" if enabled else "#b7c0cd"))
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
        p.setPen(QPen(QColor("#2867c7" if self.isChecked() else "#b7c3d3"), 1.2))
        p.setBrush(QColor("#2867c7" if self.isChecked() else "#ffffff"))
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
        p.fillRect(self.width()-25, 4, 20, self.height()-8, QColor("#ffffff" if self.isEnabled() else "#f5f7fa"))
        _triangle(p, self.width()-15, self.height()/2, enabled=self.isEnabled())


class _SpinIndicators:
    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.width()-22, 2, 19, self.height()-4, QColor("#f7f9fc"))
        p.setPen(QPen(QColor("#e1e6ed"), 1))
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
        p.fillRect(self.width()-23, 2, 20, self.height()-4, QColor("#ffffff" if self.isEnabled() else "#f5f7fa"))
        _triangle(p, self.width()-13, self.height()/2, enabled=self.isEnabled())

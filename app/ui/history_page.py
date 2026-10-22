from datetime import datetime, time
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTableWidget,
    QComboBox, QCheckBox, QDateEdit, QFileDialog, QMessageBox, QDoubleSpinBox, QHeaderView)
from app.services.csv_exporter import display_time, export_csv, timeline
from app.ui.common import button, confirm, fill_table, TimeItem
from app.ui.theme import page_layout, page_header, panel, action, label, FlowLayout, setup_table, field, ResponsiveColumns
from app.ui.theme import CheckBox as QCheckBox, ComboBox as QComboBox, DateEdit as QDateEdit, DoubleSpinBox as QDoubleSpinBox


def history_stamp(row, field_name):
    if row["source_type"] == "video":
        return timeline(row[field_name]) + "\nTimeline video"
    stamp = datetime.fromtimestamp(row[field_name]).astimezone()
    offset = stamp.strftime("%z")
    return stamp.strftime("%d/%m/%Y\n%H:%M:%S") + " UTC" + offset[:3] + ":" + offset[3:]


def source_display(source):
    if source.startswith("sha256:"):
        digest = source[7:]
        return "sha256:\n" + "\n".join(digest[i:i+24] for i in range(0, len(digest), 24))
    return source


class HistoryPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window, self.rows = window, []
        layout = page_layout(self)
        page_header(layout, "Lịch sử xuất hiện", "Mỗi dòng là một phiên xuất hiện, từ lần nhận diện đầu tiên đến cuối cùng.",
                    action("Xuất CSV", self.export, "primary", "download"))
        box, body = panel()
        filters = FlowLayout(spacing=10)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Họ tên hoặc Mã ID…")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(230)
        self.search.returnPressed.connect(self.refresh)
        filters.addWidget(self.search)
        self.kind = QComboBox()
        self.kind.setMinimumWidth(145)
        self.kind.addItems(["Mọi nguồn", "Camera", "Video"])
        filters.addWidget(self.kind)
        self.source = QLineEdit()
        self.source.setMinimumWidth(240)
        self.source.setPlaceholderText("Định danh nguồn camera / video…")
        self.source.setClearButtonEnabled(True)
        filters.addWidget(self.source)
        filters.addWidget(action("Áp dụng bộ lọc", self.refresh))
        body.addLayout(filters)
        self.date_filter = QCheckBox("Lọc theo ngày camera")
        self.start = QDateEdit(QDate.currentDate())
        self.end = QDateEdit(QDate.currentDate())
        dates_widget = QWidget()
        dates = FlowLayout(dates_widget, spacing=8)
        dates.addWidget(self.date_filter)
        for control in (self.start, self.end):
            control.setCalendarPopup(True)
            control.setDisplayFormat("dd/MM/yyyy")
            control.setMinimumWidth(130)
            control.setEnabled(False)
            self.date_filter.toggled.connect(control.setEnabled)
        dates.addWidget(self.start)
        dates.addWidget(label("đến", "Muted"))
        dates.addWidget(self.end)
        body.addWidget(dates_widget)
        self.media_filter = QCheckBox("Lọc timeline video")
        self.media_start, self.media_end = QDoubleSpinBox(), QDoubleSpinBox()
        media_widget = QWidget()
        media = FlowLayout(media_widget, spacing=8)
        media.addWidget(self.media_filter)
        for control in (self.media_start, self.media_end):
            control.setRange(0, 360000)
            control.setDecimals(3)
            control.setSuffix(" s")
            control.setMinimumWidth(135)
            control.setEnabled(False)
            self.media_filter.toggled.connect(control.setEnabled)
        self.media_end.setValue(3600)
        media.addWidget(self.media_start)
        media.addWidget(label("đến", "Muted"))
        media.addWidget(self.media_end)
        body.addWidget(media_widget)
        self.date_filter.toggled.connect(lambda enabled: self.media_filter.setChecked(False) if enabled else None)
        self.media_filter.toggled.connect(lambda enabled: self.date_filter.setChecked(False) if enabled else None)
        layout.addWidget(box)
        actions = FlowLayout()
        actions.addWidget(action("Xóa phiên đã chọn", self.delete_selected, "danger"))
        actions.addWidget(action("Xóa toàn bộ lịch sử", self.delete_all, "quiet"))
        layout.addLayout(actions)
        table_box, table_body = panel()
        table_body.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Mã phiên", "Mã ID", "Họ tên", "Check-in", "Check-out", "Nguồn", "Trạng thái"])
        setup_table(self.table)
        self.table.hideColumn(0)
        self.configure_columns()
        self.table.sortItems(3, Qt.DescendingOrder)
        table_body.addWidget(self.table)
        layout.addWidget(table_box, 1)
        self.count = label("0 phiên · Áp dụng bộ lọc để cập nhật kết quả.", "Muted", True)
        layout.addWidget(self.count)

    def configure_columns(self):
        header = self.table.horizontalHeader()
        for column, width in ((1, 205), (2, 170), (3, 195), (4, 195), (5, 210), (6, 115)):
            header.setSectionResizeMode(column, QHeaderView.Interactive)
            self.table.setColumnWidth(column, width)
        header.setSectionResizeMode(2, QHeaderView.Stretch)


    def refresh(self):
        start = end = None
        if self.date_filter.isChecked():
            start = datetime.combine(self.start.date().toPython(), time.min).astimezone().timestamp()
            end = datetime.combine(self.end.date().toPython(), time.max).astimezone().timestamp()
            if start > end:
                QMessageBox.warning(self, "Bộ lọc", "Ngày bắt đầu phải trước ngày kết thúc")
                return
        if self.date_filter.isChecked() and self.media_filter.isChecked():
            QMessageBox.warning(self, "Bộ lọc", "Chọn lọc ngày camera hoặc timeline video mỗi lần")
            return
        low = self.media_start.value() if self.media_filter.isChecked() else None
        high = self.media_end.value() if self.media_filter.isChecked() else None
        if low is not None and low > high:
            QMessageBox.warning(self, "Bộ lọc", "Timeline bắt đầu phải trước kết thúc")
            return
        args = (self.search.text(), start, end, ["all", "camera", "video"][self.kind.currentIndex()], self.source.text(), low, high)
        self.window.jobs.run(lambda: self.window.db.history(*args), self.loaded)

    def loaded(self, rows):
        self.rows = rows
        fill_table(self.table, [[r["id"], r["person_id"], r["person_name"], history_stamp(r, "first_seen"),
                                history_stamp(r, "last_seen"), source_display(r["source_id"]), "Đang mở" if r["status"] == "open" else "Đã kết thúc"] for r in rows])
        self.table.setSortingEnabled(False)
        by_id = {r["id"]: r for r in rows}
        for index in range(self.table.rowCount()):
            row = by_id[self.table.item(index, 0).text()]
            for column, field in ((3, "first_seen"), (4, "last_seen")):
                self.table.setItem(index, column, TimeItem(history_stamp(row, field), row[field]))
        for index in range(self.table.rowCount()):
            row = by_id[self.table.item(index, 0).text()]
            self.table.item(index, 5).setToolTip(row["source_id"])
            for column in (1, 5):
                self.table.item(index, column).setFont(QFont("Consolas", 9))
            for column, field in ((3, "first_seen"), (4, "last_seen")):
                self.table.item(index, column).setToolTip(display_time(row, field))
            self.table.item(index, 6).setForeground(QColor("#237653" if row["status"] == "open" else "#68768a"))
        self.table.resizeRowsToContents()
        for index in range(self.table.rowCount()):
            self.table.setRowHeight(index, max(74, self.table.rowHeight(index)))
        self.table.setSortingEnabled(True)
        self.count.setText(f"{len(rows)} phiên · Video dùng timeline; camera dùng giờ thực kèm múi giờ. Cuộn ngang để xem đầy đủ các cột; kéo tiêu đề để đổi độ rộng.")

    def delete(self, ids):
        def remove():
            # Close active sessions before deletion; a later deliberate start can log again.
            self.window.pipeline.command("stop")
            self.window.db.delete_history(ids)
        self.window.jobs.run(remove, lambda _: self.refresh())

    def delete_selected(self):
        ids = [self.table.item(index.row(), 0).text() for index in self.table.selectionModel().selectedRows()]
        if ids and confirm(self, f"Dừng nguồn và xóa {len(ids)} phiên đã chọn? Hồ sơ người được giữ nguyên."):
            self.delete(ids)

    def delete_all(self):
        if confirm(self, "Dừng nguồn và xóa TOÀN BỘ lịch sử, kể cả ngoài bộ lọc? Hồ sơ và embedding được giữ nguyên."):
            self.delete(None)

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Xuất kết quả đang hiển thị", "lich_su.csv", "CSV (*.csv)")
        if path:
            rows = list(self.rows)
            self.window.jobs.run(lambda: export_csv(path, rows),
                                 lambda count: QMessageBox.information(self, "Xuất CSV", f"Đã xuất {count} phiên tới {path}"))

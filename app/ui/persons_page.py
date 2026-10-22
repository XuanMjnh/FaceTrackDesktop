from pathlib import Path
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon, QColor, QFont
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTableWidget,
    QFileDialog, QInputDialog, QMessageBox, QDialog, QListWidget, QListWidgetItem, QDialogButtonBox, QHeaderView)
from app.ui.common import button, confirm, fill_table
from app.ui.theme import page_layout, page_header, panel, action, label, FlowLayout, setup_table, line_icon

class PersonsPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window, self.rows, self.busy = window, {}, False
        layout = page_layout(self)
        page_header(layout, "Hồ sơ người", "Danh sách hồ sơ và ảnh tham chiếu.",
                    action("Thêm người", self.add, "primary", "plus"))
        box, body = panel()
        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Tìm họ tên hoặc Mã ID…")
        self.search.setClearButtonEnabled(True)
        self.search.setMaximumWidth(460)
        self.search.returnPressed.connect(self.refresh)
        search_row.addWidget(self.search, 1)
        search_row.addWidget(action("Tìm kiếm", self.refresh))
        search_row.addStretch()
        self.count = label("0 hồ sơ", "Muted")
        search_row.addWidget(self.count)
        body.addLayout(search_row)
        controls = FlowLayout()
        self.edit_actions = []
        for text, callback, variant in (("Ảnh tham chiếu", self.details, "default"),
                ("Đổi tên", self.rename, "default"), ("Bật / Ngừng sử dụng", self.active, "default"),
                ("Xem lịch sử", self.history, "default"), ("Xóa hồ sơ", self.delete, "danger")):
            control = action(text, callback, variant)
            control.setEnabled(False)
            self.edit_actions.append(control)
            controls.addWidget(control)
        body.addLayout(controls)
        layout.addWidget(box)
        table_box, table_body = panel()
        table_body.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Ảnh", "Mã ID", "Họ tên", "Trạng thái", "Số ảnh"])
        setup_table(self.table)
        self.table.setIconSize(QSize(40, 40))
        self.table.doubleClicked.connect(self.details)
        self.table.itemSelectionChanged.connect(self.update_actions)
        self.configure_columns()
        self.table.sortItems(2, Qt.AscendingOrder)
        table_body.addWidget(self.table)
        layout.addWidget(table_box, 1)

    def configure_columns(self):
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 68)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setColumnWidth(2, 200)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 80)

    def update_actions(self):
        enabled = self.table.currentRow() >= 0 and bool(self.table.selectionModel().selectedRows())
        for control in self.edit_actions:
            control.setEnabled(enabled)


    def refresh(self):
        query = self.search.text()
        self.window.jobs.run(lambda: self.window.db.persons(query), self.loaded)

    def loaded(self, rows):
        self.rows = {row["id"]: row for row in rows}
        fill_table(self.table, [["", r["id"], r["name"], "Hoạt động" if r["is_active"] else "Ngừng sử dụng", r["images"]] for r in rows])
        self.table.setSortingEnabled(False)
        for i in range(self.table.rowCount()):
            row = self.rows[self.table.item(i, 1).text()]
            if row["avatar"]:
                self.table.item(i, 0).setIcon(QIcon(row["avatar"]))
            self.table.setRowHeight(i, 64)
            self.table.item(i, 1).setFont(QFont(self.font().family(), 9))
            self.table.item(i, 4).setTextAlignment(Qt.AlignCenter)
            self.table.item(i, 3).setForeground(QColor("#3D7554" if row["is_active"] else "#75837A"))
        self.table.setSortingEnabled(True)
        self.configure_columns()
        self.count.setText(f"{len(rows)} hồ sơ")
        self.update_actions()

    def selected(self):
        row = self.table.currentRow()
        return self.rows.get(self.table.item(row, 1).text()) if row >= 0 else None

    def choose_image(self, name, pid=None, replace_id=None, after=None):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh tham chiếu", "", "Ảnh (*.jpg *.jpeg *.png *.bmp *.webp)")
        if not path:
            return
        def inspected(result):
            target = pid
            duplicate = result[2]
            if duplicate.person_id and duplicate.person_id != pid:
                choice = QMessageBox(self)
                choice.setWindowTitle("Ảnh tương đồng")
                choice.setText(f"Tương đồng {duplicate.score:.3f} · {duplicate.name} (ID: {duplicate.person_id})")
                existing = choice.addButton("Thêm vào hồ sơ hiện có", QMessageBox.AcceptRole)
                keep_label = "Dùng hồ sơ đã chọn" if pid else "Tạo hồ sơ mới"
                new = choice.addButton(keep_label, QMessageBox.ActionRole)
                choice.addButton("Hủy", QMessageBox.RejectRole)
                choice.exec()
                if choice.clickedButton() == existing:
                    target = duplicate.person_id
                elif choice.clickedButton() != new:
                    return
            effective_replace = replace_id if target == pid else None
            self.window.jobs.run(lambda: self.window.enrollment.save(name, result, target, effective_replace),
                                 lambda _: self.changed(after))
        self.window.jobs.run(lambda: self.window.enrollment.inspect(path), inspected)

    def changed(self, after=None):
        self.window.jobs.run(self.window.pipeline.reload_gallery, lambda _: self.refresh())
        if after:
            after()

    def add(self):
        name, ok = QInputDialog.getText(self, "Thêm người", "Họ tên:")
        if ok and name.strip():
            self.choose_image(name)

    def rename(self):
        row = self.selected()
        if row:
            name, ok = QInputDialog.getText(self, "Đổi tên", "Họ tên:", text=row["name"])
            if ok and name.strip():
                self.window.jobs.run(lambda: self.window.db.edit_person(row["id"], name, row["is_active"]), lambda _: self.changed())

    def active(self):
        row = self.selected()
        if row and confirm(self, "Đổi trạng thái sử dụng hồ sơ?"):
            self.window.jobs.run(lambda: self.window.db.edit_person(row["id"], row["name"], not row["is_active"]), lambda _: self.changed())

    def delete(self):
        row = self.selected()
        if row and confirm(self, "Xóa hồ sơ và ảnh tham chiếu? Lịch sử xuất hiện vẫn được giữ lại."):
            # Stop and flush first so an in-flight recognition cannot recreate a deleted profile.
            def remove():
                self.window.pipeline.command("stop")
                paths = self.window.db.delete_person(row["id"])
                for path in paths:
                    Path(path).unlink(missing_ok=True)
            self.window.jobs.run(remove, lambda _: self.changed())

    def history(self):
        row = self.selected()
        if row:
            self.window.history_page.search.setText(row["id"])
            self.window.history_page.refresh()
            self.window.navigation.setCurrentRow(3)

    def details(self):
        row = self.selected()
        if not row:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(row["name"] + " · " + row["id"])
        dialog.resize(720, 620)
        dialog.setMinimumSize(560, 480)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(14)
        layout.addWidget(label(row["name"], "SectionTitle"))
        layout.addWidget(label("Mã ID: " + row["id"], "Muted", True))
        preview = QLabel()
        preview.setMinimumHeight(180)
        preview.setAlignment(Qt.AlignCenter)
        layout.addWidget(preview)
        listing = QListWidget()
        listing.setObjectName("References")
        listing.setIconSize(QSize(40, 40))
        layout.addWidget(listing)
        def load():
            self.window.jobs.run(lambda: self.window.db.references(row["id"]), populate)
        def populate(refs):
            listing.clear()
            for ref in refs:
                item = QListWidgetItem(QIcon(ref["image_path"]), ref["created_at"] + " · " + Path(ref["image_path"]).name)
                item.setData(Qt.UserRole, ref)
                listing.addItem(item)
        def show_preview(item):
            if item:
                preview.setPixmap(QPixmap(item.data(Qt.UserRole)["image_path"]).scaled(500, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        listing.currentItemChanged.connect(lambda item, _: show_preview(item))
        controls = FlowLayout()
        button("Thêm ảnh", lambda: self.choose_image(row["name"], row["id"], after=load), controls)
        def replace():
            item = listing.currentItem()
            if item:
                self.choose_image(row["name"], row["id"], item.data(Qt.UserRole)["id"], load)
        button("Thay ảnh chọn", replace, controls)
        def delete_ref():
            item = listing.currentItem()
            if item and confirm(dialog, "Xóa ảnh tham chiếu đã chọn?"):
                rid = item.data(Qt.UserRole)["id"]
                def remove():
                    path = self.window.db.delete_reference(rid)
                    if path:
                        Path(path).unlink(missing_ok=True)
                self.window.jobs.run(remove, lambda _: self.changed(load))
        button("Xóa ảnh chọn", delete_ref, controls)
        layout.addLayout(controls)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Close).setIcon(line_icon("close"))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        load()
        dialog.exec()

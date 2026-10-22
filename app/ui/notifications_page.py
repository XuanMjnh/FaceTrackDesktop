import os
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLineEdit, QListWidget,
                               QTableWidget, QMessageBox)
from app.ui.common import fill_table
from app.ui.theme import (page_layout, page_header, panel, action, label, field,
                          FlowLayout, CheckBox, ComboBox, SpinBox, setup_table)


class NotificationsPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window, self.service = window, window.notifications
        self.busy = False
        layout = page_layout(self)
        page_header(layout, "Thông báo", "Email khi phát hiện.")
        account, body = panel("Tài khoản email gửi")
        self.status = label("Chưa đăng nhập", "Muted", True)
        body.addWidget(self.status)
        config = self.service.store.config()
        fields = QHBoxLayout()
        fields.setSpacing(12)
        self.email = QLineEdit(config.get("email", ""))
        self.email.setPlaceholderText("ten@gmail.com")
        self.email.setMinimumWidth(220)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("Mật khẩu ứng dụng")
        self.password.setMinimumWidth(220)
        fields.addWidget(field("Email gửi", self.email), 1)
        fields.addWidget(field("Mật khẩu ứng dụng", self.password), 1)
        body.addLayout(fields)
        transport = QHBoxLayout()
        transport.setSpacing(12)
        self.host = QLineEdit(config.get("host", "smtp.gmail.com"))
        self.port = SpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(config.get("port", 465))
        self.security = ComboBox()
        self.security.addItems(["SSL", "STARTTLS"])
        self.security.setCurrentText(config.get("security", "SSL"))
        transport.addWidget(field("Máy chủ SMTP", self.host), 2)
        transport.addWidget(field("Cổng", self.port), 1)
        transport.addWidget(field("Bảo mật", self.security), 1)
        body.addLayout(transport)
        self.remember = CheckBox("Ghi nhớ tài khoản")
        self.remember.setChecked(os.name == "nt")
        self.remember.setToolTip("Mật khẩu được mã hóa theo tài khoản Windows.")
        body.addWidget(self.remember)
        body.addWidget(label("Gmail: smtp.gmail.com · SSL · 465 · Mật khẩu ứng dụng.", "Muted", True))
        buttons = FlowLayout()
        self.login_button = action("Đăng nhập", self.login, "primary")
        self.logout_button = action("Đăng xuất", self.logout)
        self.test_button = action("Gửi thử", self.test_mail)
        for control in (self.login_button, self.logout_button, self.test_button):
            buttons.addWidget(control)
        body.addLayout(buttons)
        layout.addWidget(account)

        recipients, body = panel("Email nhận")
        row = QHBoxLayout()
        self.recipient = QLineEdit()
        self.recipient.setPlaceholderText("Địa chỉ email")
        self.recipient.returnPressed.connect(self.add_recipient)
        row.addWidget(self.recipient, 1)
        row.addWidget(action("Thêm email", self.add_recipient))
        row.addWidget(action("Xóa đã chọn", self.remove_recipient, "danger"))
        body.addLayout(row)
        self.recipients = QListWidget()
        self.recipients.setObjectName("References")
        self.recipients.setMinimumHeight(80)
        self.recipients.setMaximumHeight(120)
        body.addWidget(self.recipients)
        policy = QHBoxLayout()
        policy.setSpacing(12)
        self.cooldown = SpinBox()
        self.cooldown.setRange(10, 3600)
        self.cooldown.setValue(60)
        self.cooldown.setSuffix(" giây")
        self.cooldown.valueChanged.connect(self.update_policy)
        policy.addWidget(label("Khoảng nghỉ mỗi người / nguồn", "FieldLabel"))
        policy.addWidget(self.cooldown)
        self.unknown = CheckBox("Báo cả khuôn mặt không xác định")
        self.unknown.setChecked(False)
        self.unknown.toggled.connect(self.update_policy)
        policy.addWidget(self.unknown)
        policy.addStretch(1)
        body.addLayout(policy)
        layout.addWidget(recipients)

        logs, body = panel("Nhật ký email", "300 bản ghi gần nhất.")
        body.addWidget(action("Làm mới", self.refresh_logs), 0, Qt.AlignLeft)
        self.logs = QTableWidget(0, 7)
        self.logs.setHorizontalHeaderLabels(["Thời gian gửi", "Email gửi", "Email nhận", "Nguồn", "Tiêu đề", "Trạng thái", "Chi tiết"])
        setup_table(self.logs)
        self.logs.setMinimumHeight(240)
        self.logs.setColumnWidth(0, 205)
        self.logs.setColumnWidth(1, 190)
        self.logs.setColumnWidth(2, 190)
        self.logs.setColumnWidth(3, 150)
        self.logs.setColumnWidth(4, 250)
        self.logs.setColumnWidth(5, 100)
        self.logs.setColumnWidth(6, 380)
        self.logs.itemSelectionChanged.connect(self.show_log_detail)
        body.addWidget(self.logs, 1)
        self.log_detail = label("", "Muted", True)
        self.log_detail.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.addWidget(self.log_detail)
        layout.addWidget(logs, 1)
        self.refresh_recipients()
        self.refresh_logs()
        self.poll = QTimer(self)
        self.poll.timeout.connect(self.poll_logs)
        self.poll.start(3000)
        self.refresh_account()

    def refresh_account(self, message=None):
        email = self.service.snapshot()
        self.status.setText(message or (f"Đã đăng nhập: {email}" if email else "Chưa đăng nhập"))
        self.test_button.setEnabled(bool(email) and not self.busy)
        self.login_button.setEnabled(not self.busy)
        for control in (self.email, self.password, self.host, self.port, self.security, self.remember):
            control.setEnabled(not self.busy)

    def restore(self):
        self.busy = True
        self.refresh_account("Đang đăng nhập…")
        version = self.service.version
        self.window.jobs.run(lambda: self.service.restore(expected_version=version), self.login_finished)

    def login(self):
        values = (self.email.text(), self.password.text(), self.host.text(), self.port.value(),
                  self.security.currentText(), self.remember.isChecked())
        self.password.clear()
        self.busy = True
        self.refresh_account("Đang đăng nhập…")
        def task():
            try:
                return self.service.login(*values)
            except Exception as exc:
                return str(exc)
        self.window.jobs.run(task, self.login_finished)

    def login_finished(self, message):
        self.busy = False
        self.refresh_account(message)

    def logout(self):
        try:
            self.service.logout()
            self.password.clear()
            self.refresh_account("Đã đăng xuất. Email đang gửi có thể hoàn tất.")
        except Exception:
            self.refresh_account("Không thể xóa mật khẩu đã lưu. Kiểm tra quyền ghi rồi thử lại.")

    def test_mail(self):
        try:
            self.service.test_mail()
            self.window.show_message("Đang gửi email thử.")
        except ValueError as exc:
            QMessageBox.information(self, "Thông báo", str(exc))

    def refresh_recipients(self):
        self.recipients.clear()
        self.recipients.addItems(self.service.store.recipients())

    def add_recipient(self):
        try:
            self.service.store.add_recipient(self.recipient.text())
            self.recipient.clear()
            self.refresh_recipients()
        except Exception as exc:
            QMessageBox.warning(self, "Email nhận", str(exc))

    def remove_recipient(self):
        item = self.recipients.currentItem()
        if item:
            self.service.store.remove_recipient(item.text())
            self.refresh_recipients()

    def update_policy(self, *_):
        self.service.set_policy(self.cooldown.value(), self.unknown.isChecked())

    def poll_logs(self):
        if self.isVisible():
            self.refresh_logs()

    def refresh_logs(self):
        rows = self.service.store.logs()
        if rows != getattr(self, "_rows", None):
            self._rows = rows
            fill_table(self.logs, rows)

    def show_log_detail(self):
        row = self.logs.currentRow()
        item = self.logs.item(row, 6)
        self.log_detail.setText(item.text() if item else "")

"""Local notification state, Windows DPAPI credentials and bounded SMTP worker.

No third-party dependencies. Network operations never run on the Qt/capture thread.
"""
import base64
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
import json
import os
from pathlib import Path
import queue
import re
import smtplib
import socket
import sqlite3
import ssl
import threading
import time

from app.services.csv_exporter import timeline


def email_address(value):
    value = value.strip()
    if len(value) > 254 or not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}", value):
        raise ValueError("Địa chỉ email không hợp lệ.")
    return value


class WindowsSecret:
    """DPAPI CurrentUser; never fall back to a plaintext password file."""
    @staticmethod
    def _crypt(data, decrypt=False):
        if os.name != "nt":
            raise ValueError("Ghi nhớ mật khẩu chỉ hỗ trợ Windows.")
        class Blob(ctypes.Structure):
            _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]
        buffer = ctypes.create_string_buffer(data)
        source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
        target = Blob()
        crypt = ctypes.WinDLL("crypt32", use_last_error=True)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree.restype = ctypes.c_void_p
        function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
        function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                             ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        function.restype = wintypes.BOOL
        if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
            raise ValueError("Windows không thể mở hoặc lưu mật khẩu.")
        try:
            return ctypes.string_at(target.data, target.size)
        finally:
            kernel.LocalFree(ctypes.cast(target.data, ctypes.c_void_p))

    def protect(self, password):
        return base64.b64encode(self._crypt(password.encode("utf-8"))).decode("ascii")

    def unprotect(self, value):
        return self._crypt(base64.b64decode(value, validate=True), True).decode("utf-8")


class NotificationStore:
    def __init__(self, root):
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "notifications.sqlite3"
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS recipients (email TEXT PRIMARY KEY COLLATE NOCASE);
                CREATE TABLE IF NOT EXISTS mail_log (
                    id INTEGER PRIMARY KEY, sent_at TEXT NOT NULL, sender TEXT NOT NULL,
                    recipient TEXT NOT NULL, source TEXT NOT NULL, subject TEXT NOT NULL,
                    status TEXT NOT NULL, detail TEXT NOT NULL);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def config(self):
        with self.connect() as db:
            row = db.execute("SELECT value FROM config WHERE id=1").fetchone()
        return json.loads(row[0]) if row else {}

    def save_config(self, config):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO config VALUES (1, ?)", (json.dumps(config),))

    def recipients(self):
        with self.connect() as db:
            return [row[0] for row in db.execute("SELECT email FROM recipients ORDER BY email")]

    def add_recipient(self, value):
        value = email_address(value)
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO recipients VALUES (?)", (value,))

    def remove_recipient(self, value):
        with self.connect() as db:
            db.execute("DELETE FROM recipients WHERE email=?", (value,))

    def log(self, sender, recipient, source, subject, status, detail):
        with self.connect() as db:
            db.execute("INSERT INTO mail_log (sent_at,sender,recipient,source,subject,status,detail) VALUES (?,?,?,?,?,?,?)",
                       (datetime.now().astimezone().isoformat(timespec="seconds"), sender, recipient,
                        source, subject, status, detail))

    def logs(self, limit=300):
        with self.connect() as db:
            return db.execute("SELECT sent_at,sender,recipient,source,subject,status,detail FROM mail_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()


def smtp_error(exc):
    # Do not expose exception strings: SMTP replies may contain account/secret data.
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return "Đăng nhập bị từ chối. Kiểm tra email, mật khẩu ứng dụng và quyền SMTP."
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "Máy chủ từ chối địa chỉ người nhận."
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "Kết nối SMTP hết thời gian chờ."
    if isinstance(exc, ssl.SSLError):
        return "Không xác minh được kết nối TLS tới máy chủ SMTP."
    if isinstance(exc, OSError):
        return "Không kết nối được SMTP. Kiểm tra mạng, máy chủ và cổng."
    return "Thao tác email thất bại. Kiểm tra cấu hình SMTP và thử lại."


class NotificationService:
    def __init__(self, root, notify=lambda text: None, secret=None, smtp_factory=None):
        self.store = NotificationStore(root)
        self.secret = secret or WindowsSecret()
        self.notify = notify
        self.smtp_factory = smtp_factory
        self.lock = threading.RLock()
        self.account = None
        self.version = 0
        self.enabled = {"camera": False, "video": False}
        self.source_versions = {"camera": 0, "video": 0}
        self.cooldown = 60
        self.include_unknown = True
        self.last_sent = {}
        self.pending = queue.Queue(maxsize=32)
        self.stopping = threading.Event()
        self.worker = threading.Thread(target=self._work, name="mail-notifications", daemon=True)
        self.worker.start()

    def snapshot(self):
        with self.lock:
            return self.account["email"] if self.account else ""

    def _smtp(self, account):
        if self.smtp_factory:
            return self.smtp_factory(account)
        context = ssl.create_default_context()
        if account["security"] == "SSL":
            client = smtplib.SMTP_SSL(account["host"], account["port"], timeout=10, context=context)
        else:
            client = smtplib.SMTP(account["host"], account["port"], timeout=10)
            try:
                client.ehlo()
                client.starttls(context=context)
                client.ehlo()
            except Exception:
                client.close()
                raise
        return client

    def _authenticate(self, account):
        with self._smtp(account) as client:
            client.login(account["email"], account["password"])

    def login(self, email, password, host="smtp.gmail.com", port=465, security="SSL", remember=True, restoring=False, expected_version=None):
        email = email_address(email)
        host = host.strip()
        if not host or any(c.isspace() for c in host) or not 1 <= int(port) <= 65535 or security not in ("SSL", "STARTTLS"):
            raise ValueError("Máy chủ, cổng hoặc chế độ TLS không hợp lệ.")
        # Google displays app passwords in groups separated by spaces.
        password = password.replace(" ", "").strip()
        if not password:
            raise ValueError("Nhập mật khẩu ứng dụng của email gửi.")
        with self.lock:
            if self.stopping.is_set():
                return "Ứng dụng đang đóng."
            if expected_version is not None and expected_version != self.version:
                return "Đã hủy tự đăng nhập."
            self.version += 1
            version = self.version
            self.account = None
        config = dict(email=email, host=host, port=int(port), security=security)
        try:
            encrypted = self.secret.protect(password) if remember else None
            account = dict(config, password=password)
            self._authenticate(account)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(smtp_error(exc)) from None
        with self.lock:
            if version != self.version or self.stopping.is_set():
                return "Đã hủy đăng nhập."
            if not restoring:
                self.store.save_config(dict(config, protected_password=encrypted))
            self.account = account
            self.last_sent.clear()
        return "Đã đăng nhập: " + email

    def restore(self, expected_version=None):
        try:
            config = self.store.config()
            encrypted = config.pop("protected_password", None)
            if not encrypted:
                return "Chưa đăng nhập."
            password = self.secret.unprotect(encrypted)
            return self.login(password=password, remember=False, restoring=True, expected_version=expected_version, **config)
        except Exception:
            return "Tự đăng nhập thất bại. Đăng nhập lại tại trang Thông báo."

    def logout(self):
        with self.lock:
            self.version += 1
            self.account = None
            self.last_sent.clear()
            config = self.store.config()
            config.pop("protected_password", None)
            self.store.save_config(config)

    def set_enabled(self, kind, enabled):
        with self.lock:
            self.enabled[kind] = bool(enabled)
            self.source_versions[kind] += 1

    def cancel_pending(self):
        with self.lock:
            for kind in self.source_versions:
                self.source_versions[kind] += 1

    def set_policy(self, cooldown, include_unknown):
        with self.lock:
            self.cooldown = max(10, min(3600, int(cooldown)))
            self.include_unknown = bool(include_unknown)

    def detection(self, frame, labels):
        """Called under the pipeline epoch gate. Only RAM/put_nowait here."""
        with self.lock:
            if self.stopping.is_set() or not self.account or not self.enabled.get(frame.source_type):
                return
            people = {f.match.person_id: f.match.name for f in labels if f.match.person_id}
            unknown = sum(not f.match.person_id for f in labels)
            if unknown and self.include_unknown:
                people["__unknown__"] = f"Không xác định ({unknown} khuôn mặt)"
            now = time.monotonic()
            due = {key: name for key, name in people.items()
                   if now - self.last_sent.get((frame.source_id, key), -float("inf")) >= self.cooldown}
            if not due:
                return
            event = (self.version, self.source_versions[frame.source_type], frame.source_type,
                     frame.source_id, frame.timestamp, due, False)
            try:
                self.pending.put_nowait(event)
            except queue.Full:
                return
            self.last_sent = {key: stamp for key, stamp in self.last_sent.items() if now-stamp < self.cooldown}
            for key in due:
                self.last_sent[(frame.source_id, key)] = now

    def test_mail(self):
        with self.lock:
            if not self.account:
                raise ValueError("Đăng nhập email trước khi gửi thử.")
            if not self.store.recipients():
                raise ValueError("Thêm ít nhất một email nhận trước khi gửi thử.")
            try:
                self.pending.put_nowait((self.version, 0, "test", "Kiểm tra", 0, {}, True))
            except queue.Full:
                raise ValueError("Hàng đợi email đã đầy. Thử lại sau.") from None

    def _valid(self, event):
        version, source_version, kind, *_ = event
        return (not self.stopping.is_set() and self.account is not None and version == self.version
                and (kind == "test" or (self.enabled[kind] and source_version == self.source_versions[kind])))

    def _work(self):
        while not self.stopping.is_set():
            try:
                event = self.pending.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self._send(event)
            except Exception:
                self.notify("Không thể ghi nhật ký email.")
            finally:
                self.pending.task_done()

    def _send(self, event):
        with self.lock:
            if not self._valid(event):
                return
            account = dict(self.account)
        _, _, kind, source, stamp, people, test = event
        subject = "[FaceTrack] Kiểm tra email" if test else "[FaceTrack] Phát hiện người — " + ("Camera" if kind == "camera" else "Video")
        if test:
            content = "Đây là email kiểm tra từ FaceTrack Desktop."
        else:
            when = timeline(stamp) if kind == "video" else datetime.fromtimestamp(stamp).astimezone().isoformat(timespec="seconds")
            names = "\n".join(f"- {name}" + (f" | ID: {key}" if key != "__unknown__" else "") for key, name in people.items())
            content = f"Nguồn: {source}\nThời điểm {'trong video' if kind == 'video' else 'camera'}: {when}\n\n{names}\n\nKết quả nhận diện tự động cần được kiểm tra lại."
        for recipient in self.store.recipients():
            with self.lock:
                if not self._valid(event):
                    return
            message = EmailMessage()
            message["From"], message["To"], message["Subject"] = account["email"], recipient, subject
            message["Date"], message["Message-ID"] = formatdate(localtime=True), make_msgid()
            message.set_content(content)
            status, detail = "Đã gửi", "Máy chủ SMTP đã chấp nhận; không xác nhận đã vào hộp thư."
            try:
                with self._smtp(account) as client:
                    client.login(account["email"], account["password"])
                    with self.lock:
                        if not self._valid(event):
                            return
                    refused = client.send_message(message)
                    if refused:
                        raise smtplib.SMTPRecipientsRefused(refused)
            except Exception as exc:
                status, detail = "Thất bại", smtp_error(exc)
            self.store.log(account["email"], recipient, source, subject, status, detail + "\n\n" + content)
            self.notify(f"Email {recipient}: {status.lower()}")

    def shutdown(self):
        self.stopping.set()
        with self.lock:
            self.version += 1
            self.account = None
        self.worker.join(35)
        return not self.worker.is_alive()

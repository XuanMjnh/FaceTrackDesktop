from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QStackedWidget
from app.ui.theme import panel, label


class PresencePanel(QWidget):
    """People on the latest valid inference frame, never the history/gallery."""
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(210)
        self.setMaximumWidth(290)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        box, body = panel("Trong khung hình")
        self.count = label("0 người", "Badge")
        body.addWidget(self.count, 0, Qt.AlignLeft | Qt.AlignTop)
        self.content = QStackedWidget()
        self.empty = label("Không phát hiện.", "Muted", True)
        self.empty.setAlignment(Qt.AlignCenter)
        self.content.addWidget(self.empty)
        self.people = QListWidget()
        self.people.setObjectName("References")
        self.people.setMinimumHeight(180)
        self.people.setWordWrap(True)
        self.people.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content.addWidget(self.people)
        body.addWidget(self.content, 1)
        layout.addWidget(box, 1)
        self.signature = None

    def update_people(self, labels):
        known = {face.match.person_id: face.match.name for face in labels if face.match.person_id}
        unknown = sum(not face.match.person_id for face in labels)
        signature = (tuple(sorted(known.items())), unknown)
        if signature == self.signature:
            return
        self.signature = signature
        self.people.clear()
        for person_id, name in signature[0]:
            item = QListWidgetItem(f"{name}\nID: {person_id}")
            item.setToolTip(item.text())
            self.people.addItem(item)
        if unknown:
            self.people.addItem(f"Không xác định\n{unknown} khuôn mặt")
        self.count.setText(f"{len(known) + unknown} người")
        self.content.setCurrentWidget(self.people if labels else self.empty)

    def clear(self):
        self.signature = None
        self.update_people([])

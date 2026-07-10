from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class DebugWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("デバッグウィンドウ")
        self.resize(700, 420)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)

        self.command_edit = QLineEdit()
        self.send_engine_button = QPushButton("エンジンに送信")
        self.clear_button = QPushButton("ログ消去")

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.command_edit, stretch=1)
        bottom_layout.addWidget(self.send_engine_button)
        bottom_layout.addWidget(self.clear_button)

        root_layout = QVBoxLayout()
        root_layout.addWidget(self.log_edit)
        root_layout.addLayout(bottom_layout)
        self.setLayout(root_layout)

        self.clear_button.clicked.connect(self.clear)

    def append_log(self, text: str) -> None:
        self.log_edit.append(text)

    def clear(self) -> None:
        self.log_edit.clear()
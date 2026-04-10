from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SettingDialog(QDialog):
    """対局モードやエンジン設定などの各種設定画面を管理する。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("設定")
        self.resize(520, 320)

        self.game_mode_combo = QComboBox()
        self.game_mode_combo.addItems(["人 vs 人", "人 vs AI", "AI vs 人", "AI vs AI"])

        self.black_player_combo = QComboBox()
        self.black_player_combo.addItems(["人間", "AI"])

        self.white_player_combo = QComboBox()
        self.white_player_combo.addItems(["人間", "AI"])

        self.black_engine_edit = QLineEdit()
        self.black_engine_browse_button = QPushButton("参照")

        self.white_engine_edit = QLineEdit()
        self.white_engine_browse_button = QPushButton("参照")

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        self._setup_ui()
        self._connect_signals()
        self._sync_ui_from_mode()

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout()
        self.setLayout(root_layout)

        mode_group = QGroupBox("対局モード")
        mode_layout = QFormLayout()
        mode_group.setLayout(mode_layout)
        mode_layout.addRow("モード", self.game_mode_combo)

        player_group = QGroupBox("プレイヤー設定")
        player_layout = QFormLayout()
        player_group.setLayout(player_layout)
        player_layout.addRow("先手", self.black_player_combo)
        player_layout.addRow("後手", self.white_player_combo)

        engine_group = QGroupBox("エンジン設定")
        engine_layout = QGridLayout()
        engine_group.setLayout(engine_layout)

        engine_layout.addWidget(QLabel("先手エンジン"), 0, 0)
        engine_layout.addWidget(self.black_engine_edit, 0, 1)
        engine_layout.addWidget(self.black_engine_browse_button, 0, 2)

        engine_layout.addWidget(QLabel("後手エンジン"), 1, 0)
        engine_layout.addWidget(self.white_engine_edit, 1, 1)
        engine_layout.addWidget(self.white_engine_browse_button, 1, 2)

        root_layout.addWidget(mode_group)
        root_layout.addWidget(player_group)
        root_layout.addWidget(engine_group)
        root_layout.addStretch()
        root_layout.addWidget(self.button_box)

    def _connect_signals(self) -> None:
        self.game_mode_combo.currentIndexChanged.connect(self._sync_ui_from_mode)
        self.black_player_combo.currentIndexChanged.connect(self._sync_engine_inputs)
        self.white_player_combo.currentIndexChanged.connect(self._sync_engine_inputs)
        self.black_engine_browse_button.clicked.connect(self._browse_black_engine)
        self.white_engine_browse_button.clicked.connect(self._browse_white_engine)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def _sync_ui_from_mode(self) -> None:
        mode = self.game_mode_combo.currentText()

        if mode == "人 vs 人":
            self.black_player_combo.setCurrentText("人間")
            self.white_player_combo.setCurrentText("人間")
        elif mode == "人 vs AI":
            self.black_player_combo.setCurrentText("人間")
            self.white_player_combo.setCurrentText("AI")
        elif mode == "AI vs 人":
            self.black_player_combo.setCurrentText("AI")
            self.white_player_combo.setCurrentText("人間")
        elif mode == "AI vs AI":
            self.black_player_combo.setCurrentText("AI")
            self.white_player_combo.setCurrentText("AI")

        self._sync_engine_inputs()

    def _sync_engine_inputs(self) -> None:
        black_is_ai = self.black_player_combo.currentText() == "AI"
        white_is_ai = self.white_player_combo.currentText() == "AI"

        self.black_engine_edit.setEnabled(black_is_ai)
        self.black_engine_browse_button.setEnabled(black_is_ai)
        self.white_engine_edit.setEnabled(white_is_ai)
        self.white_engine_browse_button.setEnabled(white_is_ai)

    def _browse_black_engine(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "先手エンジンを選択",
            "",
            "Executable Files (*.exe);;All Files (*)",
        )
        if path:
            self.black_engine_edit.setText(path)

    def _browse_white_engine(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "後手エンジンを選択",
            "",
            "Executable Files (*.exe);;All Files (*)",
        )
        if path:
            self.white_engine_edit.setText(path)

    def get_settings(self) -> dict[str, str]:
        return {
            "game_mode": self.game_mode_combo.currentText(),
            "black_player": self.black_player_combo.currentText(),
            "white_player": self.white_player_combo.currentText(),
            "black_engine_path": self.black_engine_edit.text().strip(),
            "white_engine_path": self.white_engine_edit.text().strip(),
        }

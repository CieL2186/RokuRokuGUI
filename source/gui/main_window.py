from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from source.controller.game_controller import GameController
from source.core.position import Position
from source.gui.board_widget import BoardWidget
from source.gui.move_list_widget import MoveListWidget
from source.gui.setting_dialog import SettingDialog


class MainWindow(QMainWindow):
    """アプリ全体のメインウィンドウを管理する。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("66将棋GUI")
        self.resize(900, 600)

        self.board_widget = BoardWidget()
        self.clicked_square_label = QLabel("クリックしたマス: なし")
        self.status_label = QLabel("状態: 待機中")
        self.turn_label = QLabel("手番: 未設定")
        self.phase_label = QLabel("フェーズ: 未設定")
        self.move_list_widget = MoveListWidget()

        self.new_game_button = QPushButton("新規対局")
        self.settings_button = QPushButton("設定")

        self.controller = GameController(
            self.board_widget,
            self.move_list_widget,
            status_callback=self._set_status,
            turn_callback=self._set_turn,
            phase_callback=self._set_phase,
        )

        self._setup_ui()
        self._connect_signals()
        self.controller.new_game(Position())

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout()
        central_widget.setLayout(root_layout)

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.board_widget)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.clicked_square_label)
        right_layout.addWidget(self.status_label)
        right_layout.addWidget(self.turn_label)
        right_layout.addWidget(self.phase_label)
        right_layout.addWidget(self.new_game_button)
        right_layout.addWidget(self.settings_button)
        right_layout.addWidget(QLabel("棋譜"))
        right_layout.addWidget(self.move_list_widget)
        right_layout.addStretch()

        root_layout.addLayout(left_layout, stretch=3)
        root_layout.addLayout(right_layout, stretch=1)

    def _connect_signals(self) -> None:
        self.board_widget.square_clicked.connect(self._on_square_clicked)
        self.new_game_button.clicked.connect(self._on_new_game_clicked)
        self.settings_button.clicked.connect(self._on_settings_clicked)

    def _on_square_clicked(self, square: str) -> None:
        self.clicked_square_label.setText(f"クリックしたマス: {square}")

    def _on_new_game_clicked(self) -> None:
        self.controller.new_game(Position())
        self.clicked_square_label.setText("クリックしたマス: なし")

    def _on_settings_clicked(self) -> None:
        dialog = SettingDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self._set_status(f"設定を更新しました: {settings['game_mode']}")
        else:
            self._set_status("設定をキャンセルしました")

    def _set_status(self, text: str) -> None:
        self.status_label.setText(f"状態: {text}")

    def _set_turn(self, text: str) -> None:
        self.turn_label.setText(f"手番: {text}")

    def _set_phase(self, text: str) -> None:
        self.phase_label.setText(f"フェーズ: {text}")

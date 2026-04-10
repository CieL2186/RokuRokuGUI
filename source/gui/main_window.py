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
        self.status_label = QLabel("対局を開始してください")
        self.turn_label = QLabel("手番: 未設定")
        self.phase_label = QLabel("フェーズ: 未設定")
        self.move_list_widget = MoveListWidget()

        self.new_game_button = QPushButton("新規対局")
        self.settings_button = QPushButton("設定")
        self.undo_button = QPushButton("1手戻す")

        self.promotion_widget = QWidget()
        self.promote_button = QPushButton("成")
        self.no_promote_button = QPushButton("不成")

        self.setting_dialog = SettingDialog(self)

        self._setup_ui()
        self._hide_promotion_buttons()

        self.controller = GameController(
            board_widget=self.board_widget,
            move_list_widget=self.move_list_widget,
            status_callback=self.status_label.setText,
            turn_callback=self.turn_label.setText,
            phase_callback=self.phase_label.setText,
            promotion_request_callback=self._show_promotion_buttons,
            promotion_clear_callback=self._hide_promotion_buttons,
        )

        self._connect_signals()

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout()
        central_widget.setLayout(root_layout)

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.board_widget)

        promotion_layout = QHBoxLayout()
        promotion_layout.setContentsMargins(0, 0, 0, 0)
        promotion_layout.addWidget(self.promote_button)
        promotion_layout.addWidget(self.no_promote_button)
        self.promotion_widget.setLayout(promotion_layout)

        left_layout.addWidget(self.promotion_widget)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.status_label)
        right_layout.addWidget(self.turn_label)
        right_layout.addWidget(self.phase_label)
        right_layout.addWidget(self.new_game_button)
        right_layout.addWidget(self.settings_button)
        right_layout.addWidget(self.undo_button)
        right_layout.addWidget(QLabel("棋譜"))
        right_layout.addWidget(self.move_list_widget)
        right_layout.addStretch()

        root_layout.addLayout(left_layout, stretch=3)
        root_layout.addLayout(right_layout, stretch=1)

    def _connect_signals(self) -> None:
        self.new_game_button.clicked.connect(self._on_new_game_clicked)
        self.settings_button.clicked.connect(self._on_settings_clicked)
        self.undo_button.clicked.connect(self._on_undo_clicked)

        self.promote_button.clicked.connect(lambda: self.controller.handle_promotion_choice(True))
        self.no_promote_button.clicked.connect(lambda: self.controller.handle_promotion_choice(False))

    def _on_new_game_clicked(self) -> None:
        self.controller.new_game()

    def _on_settings_clicked(self) -> None:
        if self.setting_dialog.exec():
            settings = self.setting_dialog.get_settings()
            self.status_label.setText(
                f"設定を更新しました: {settings['game_mode']}"
            )

    def _on_undo_clicked(self) -> None:
        self.controller.undo_move()

    def _show_promotion_buttons(self, square: str) -> None:
        self.promotion_widget.show()

    def _hide_promotion_buttons(self) -> None:
        self.promotion_widget.hide()


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
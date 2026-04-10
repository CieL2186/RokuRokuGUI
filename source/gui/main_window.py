from __future__ import annotations

from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
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

        self.status_label = QLabel("状態: 対局を開始してください。")
        self.turn_label = QLabel("手番: 未設定")
        self.phase_label = QLabel("フェーズ: 未設定")

        self.move_list_widget = MoveListWidget()

        self.new_game_button = QPushButton("新規対局")
        self.settings_button = QPushButton("設定")
        self.undo_button = QPushButton("1手戻す")

        self.setting_dialog = SettingDialog(self)

        self._promotion_square: str | None = None

        self._setup_ui()
        self._setup_promotion_widget()

        self.controller = GameController(
            board_widget=self.board_widget,
            move_list_widget=self.move_list_widget,
            status_callback=self._set_status,
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

    def _setup_promotion_widget(self) -> None:
        self.promotion_widget = QFrame(self.board_widget)
        self.promotion_widget.setObjectName("promotionWidget")

        self.promote_button = QPushButton("成", self.promotion_widget)
        self.no_promote_button = QPushButton("不成", self.promotion_widget)

        layout = QHBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.addWidget(self.promote_button)
        layout.addWidget(self.no_promote_button)
        self.promotion_widget.setLayout(layout)

        self.promotion_widget.setStyleSheet(
            """
            QFrame#promotionWidget {
                background-color: rgba(255, 255, 255, 235);
                border: 1px solid #666666;
                border-radius: 4px;
            }
            QFrame#promotionWidget QPushButton {
                padding: 4px 10px;
                min-width: 44px;
            }
            """
        )

        self.promotion_widget.adjustSize()
        self.promotion_widget.hide()

    def _connect_signals(self) -> None:
        self.new_game_button.clicked.connect(self._on_new_game_clicked)
        self.settings_button.clicked.connect(self._on_settings_clicked)
        self.undo_button.clicked.connect(self._on_undo_clicked)

        self.promote_button.clicked.connect(
            lambda: self.controller.handle_promotion_choice(True)
        )
        self.no_promote_button.clicked.connect(
            lambda: self.controller.handle_promotion_choice(False)
        )

    def _on_new_game_clicked(self) -> None:
        self.controller.new_game()

    def _on_settings_clicked(self) -> None:
        if self.setting_dialog.exec():
            settings = self.setting_dialog.get_settings()
            self._set_status(f"設定を更新しました: {settings['game_mode']}")

    def _on_undo_clicked(self) -> None:
        self.controller.undo_move()

    def _set_status(self, text: str) -> None:
        self.status_label.setText(f"状態: {text}")

    def _show_promotion_buttons(self, square: str) -> None:
        self._promotion_square = square
        self._reposition_promotion_widget()
        self.promotion_widget.raise_()
        self.promotion_widget.show()

    def _hide_promotion_buttons(self) -> None:
        self._promotion_square = None
        self.promotion_widget.hide()

    def _reposition_promotion_widget(self) -> None:
        if self._promotion_square is None:
            return

        rect = self.board_widget.get_square_rect(self._promotion_square)
        if rect is None:
            return

        self.promotion_widget.adjustSize()

        widget_width = self.promotion_widget.width()
        widget_height = self.promotion_widget.height()

        x = rect.center().x() - widget_width // 2
        y = rect.top() - widget_height - 6

        if y < 0:
            y = rect.bottom() + 6

        max_x = max(0, self.board_widget.width() - widget_width)
        max_y = max(0, self.board_widget.height() - widget_height)

        x = max(0, min(x, max_x))
        y = max(0, min(y, max_y))

        self.promotion_widget.move(x, y)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)

        if self.promotion_widget.isVisible():
            self._reposition_promotion_widget()


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication([])

    window = MainWindow()
    window.show()

    app.exec()
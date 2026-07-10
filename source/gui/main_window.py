from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from source.controller.game_controller import GameController
from source.gui.board_widget import BoardWidget
from source.gui.hand_stand_widget import HandStandWidget
from source.gui.move_list_widget import MoveListWidget
from source.gui.match_setting_dialog import MatchSettingDialog
from source.gui.debug_window import DebugWindow


class MainWindow(QMainWindow):
    """アプリ全体のメインウィンドウを管理する。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("66将棋GUI")
        self.resize(1120, 720)

        self.board_widget = BoardWidget()

        self.white_hand_stand = HandStandWidget("white")
        self.black_hand_stand = HandStandWidget("black")

        self.white_hand_stand.setFixedSize(190, 320)
        self.black_hand_stand.setFixedSize(190, 320)

        self.status_label = QLabel("状態: 対局を開始してください。")
        self.turn_label = QLabel("手番: 未設定")
        self.phase_label = QLabel("フェーズ: 未設定")

        self.status_label.setWordWrap(True)
        self.status_label.setFixedWidth(220)
        self.status_label.setFixedHeight(60)
        self.status_label.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )

        self.turn_label.setFixedWidth(220)
        self.phase_label.setFixedWidth(220)

        self.move_list_widget = MoveListWidget()

        self.undo_button = QPushButton("1手戻す")

        button_width = 220
        self.undo_button.setFixedWidth(button_width)

        self.match_setting_dialog = MatchSettingDialog(self)

        self._promotion_square: str | None = None

        self._setup_ui()
        self._setup_promotion_widget()

        self.debug_window = DebugWindow()
        self._setup_menu()

        self.controller = GameController(
            board_widget=self.board_widget,
            move_list_widget=self.move_list_widget,
            status_callback=self._set_status,
            turn_callback=self._set_turn,
            phase_callback=self._set_phase,
            hands_callback=self._update_hands,
            hand_selection_callback=self._update_hand_selection,
            promotion_request_callback=self._show_promotion_buttons,
            promotion_clear_callback=self._hide_promotion_buttons,
            debug_log_callback=self.debug_window.append_log,
        )

        self._connect_signals()

    def _setup_menu(self) -> None:
        menu_bar = self.menuBar()

        self.match_action = menu_bar.addAction("対局(&G)")
        self.match_action.triggered.connect(self._on_match_clicked)

        view_menu = menu_bar.addMenu("表示(&V)")

        self.debug_action = view_menu.addAction("デバッグウィンドウ(&D)")
        self.debug_action.triggered.connect(self._show_debug_window)

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout()
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(10)
        central_widget.setLayout(root_layout)

        # 左: 後手駒台 + 棋譜
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)
        left_layout.addWidget(self.white_hand_stand)
        left_layout.addWidget(QLabel("棋譜"))
        left_layout.addWidget(self.move_list_widget, stretch=1)

        # 中央: 盤
        center_layout = QVBoxLayout()
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(
            self.board_widget,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )

        # 右: 情報欄 + 先手駒台
        right_panel = QWidget()
        right_panel.setFixedWidth(230)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)
        right_panel.setLayout(right_layout)

        right_layout.addWidget(self.status_label)
        right_layout.addWidget(self.turn_label)
        right_layout.addWidget(self.phase_label)
        right_layout.addWidget(self.undo_button)
        right_layout.addStretch()
        right_layout.addWidget(self.black_hand_stand)

        root_layout.addLayout(left_layout, stretch=0)
        root_layout.addLayout(center_layout, stretch=1)
        root_layout.addWidget(right_panel, stretch=0)

    def _setup_promotion_widget(self) -> None:
        self.promotion_widget = QFrame(self.board_widget)
        self.promotion_widget.setObjectName("promotionWidget")

        self.promote_button = QPushButton("成", self.promotion_widget)
        self.no_promote_button = QPushButton("不\n成", self.promotion_widget)

        layout = QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        layout.addWidget(self.promote_button)
        layout.addWidget(self.no_promote_button)
        self.promotion_widget.setLayout(layout)

        self.promotion_widget.setStyleSheet(
            """
            QFrame#promotionWidget {
                background-color: rgba(255, 255, 255, 210);
                border: 1px solid #666666;
                border-radius: 3px;
            }
            QFrame#promotionWidget QPushButton {
                padding: 0px;
                margin: 0px;
                font-weight: bold;
            }
            """
        )

        self.promotion_widget.hide()

    def _connect_signals(self) -> None:
        self.undo_button.clicked.connect(self._on_undo_clicked)

        self.promote_button.clicked.connect(
            lambda: self.controller.handle_promotion_choice(True)
        )
        self.no_promote_button.clicked.connect(
            lambda: self.controller.handle_promotion_choice(False)
        )

        self.black_hand_stand.hand_piece_clicked.connect(self.controller.select_hand_piece)
        self.white_hand_stand.hand_piece_clicked.connect(self.controller.select_hand_piece)

        self.black_hand_stand.hand_cancel_requested.connect(self.controller.cancel_hand_selection)
        self.white_hand_stand.hand_cancel_requested.connect(self.controller.cancel_hand_selection)

    def _on_undo_clicked(self) -> None:
        self.controller.undo_move()

    def _set_status(self, text: str) -> None:
        full_text = f"状態: {text}"
        self.status_label.setText(full_text)
        self.status_label.setToolTip(full_text)

    def _set_turn(self, text: str) -> None:
        self.turn_label.setText(text)
        self._refresh_hand_stands_state()

    def _set_phase(self, text: str) -> None:
        self.phase_label.setText(text)
        self._refresh_hand_stands_state()

    # =========================
    # 持ち駒表示
    # =========================

    def _update_hands(self, hands: dict[str, dict[str, int]]) -> None:
        self.black_hand_stand.set_hands(hands.get("black", {}))
        self.white_hand_stand.set_hands(hands.get("white", {}))
        self._refresh_hand_stands_state()

    def _update_hand_selection(
        self,
        side: str | None,
        piece: str | None,
    ) -> None:
        self.black_hand_stand.set_selected_piece(piece if side == "black" else None)
        self.white_hand_stand.set_selected_piece(piece if side == "white" else None)
        self._refresh_hand_stands_state()

    def _refresh_hand_stands_state(self) -> None:
        current_side = self._current_side_from_turn_label()
        self.black_hand_stand.set_active(current_side == "black")
        self.white_hand_stand.set_active(current_side == "white")

    def _current_side_from_turn_label(self) -> str | None:
        text = self.turn_label.text()
        if "先手" in text:
            return "black"
        if "後手" in text:
            return "white"
        return None

    # =========================
    # 成りUI
    # =========================

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

        self._update_promotion_widget_size(rect)

        x = rect.left() + 2
        y = rect.top() + 2

        max_x = max(0, self.board_widget.width() - self.promotion_widget.width())
        max_y = max(0, self.board_widget.height() - self.promotion_widget.height())

        x = max(0, min(x, max_x))
        y = max(0, min(y, max_y))

        self.promotion_widget.move(x, y)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)

        if self.promotion_widget.isVisible():
            self._reposition_promotion_widget()

    def _update_promotion_widget_size(self, rect) -> None:
        widget_width = max(36, rect.width() - 4)
        widget_height = max(36, rect.height() - 4)

        self.promotion_widget.setFixedSize(widget_width, widget_height)

        spacing = 2
        margins = 4
        button_area_width = widget_width - margins - spacing
        button_height = widget_height - 4

        promote_width = max(16, button_area_width // 2)
        no_promote_width = max(18, button_area_width - promote_width)

        self.promote_button.setFixedSize(promote_width, button_height)
        self.no_promote_button.setFixedSize(no_promote_width, button_height)

        font = QFont()
        font.setBold(True)
        font.setPointSize(max(12, rect.height() // 4))
        self.promote_button.setFont(font)
        self.no_promote_button.setFont(font)

    # =========================
    # 対局ウィンドウUI
    # =========================

    def _on_match_clicked(self) -> None:
        if self.match_setting_dialog.exec():
            settings = self.match_setting_dialog.get_settings()
            self.controller.new_game_from_settings(settings)
            self._set_status("対局を開始しました。")

    # =========================
    # デバッグウィンドウUI
    # =========================

    def _show_debug_window(self) -> None:
        self.debug_window.show()
        self.debug_window.raise_()
        self.debug_window.activateWindow()


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication([])

    window = MainWindow()
    window.show()

    app.exec()

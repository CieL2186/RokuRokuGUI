from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.board_widget import BoardWidget


class MainWindow(QMainWindow):
    """アプリ全体のメインウィンドウを管理する。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("66将棋GUI")
        self.resize(900, 600)

        self.board_widget = BoardWidget()
        self.status_label = QLabel("クリックしたマス: なし")
        self.turn_label = QLabel("手番: 未設定")
        self.phase_label = QLabel("フェーズ: 未設定")
        self.move_list_widget = QListWidget()

        self.new_game_button = QPushButton("新規対局")
        self.settings_button = QPushButton("設定")

        self._setup_ui()
        self._connect_signals()
        self._load_sample_board()

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout()
        central_widget.setLayout(root_layout)

        # 左側: 盤面
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.board_widget)

        # 右側: 情報表示
        right_layout = QVBoxLayout()
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
        self.status_label.setText(f"クリックしたマス: {square}")
        self.board_widget.set_selected_square(square)

    def _on_new_game_clicked(self) -> None:
        self.status_label.setText("クリックしたマス: なし")
        self.turn_label.setText("手番: 先手")
        self.phase_label.setText("フェーズ: 配置")
        self.move_list_widget.clear()
        self._load_sample_board()
        self.board_widget.clear_selection()

    def _on_settings_clicked(self) -> None:
        self.status_label.setText("設定画面は未実装です")

    def _load_sample_board(self) -> None:
        board = BoardWidget._create_empty_board()
        board.update(
            {
                "6a": "r",
                "5a": "b",
                "4a": "g",
                "3a": "s",
                "2a": "n",
                "1a": "k",
                "6b": "p",
                "5b": "p",
                "4b": "p",
                "3b": "p",
                "2b": "p",
                "1b": "p",
                "6e": "P",
                "5e": "P",
                "4e": "P",
                "3e": "P",
                "2e": "P",
                "1e": "P",
                "6f": "R",
                "5f": "B",
                "4f": "G",
                "3f": "S",
                "2f": "N",
                "1f": "K",
            }
        )

        self.board_widget.set_board(board)
        self.turn_label.setText("手番: 先手")
        self.phase_label.setText("フェーズ: 配置")
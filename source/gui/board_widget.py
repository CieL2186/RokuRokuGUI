from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget


class BoardWidget(QWidget):
    """
    66将棋の盤面表示用ウィジェット。

    責務:
    - 6x6盤を描画する
    - 座標ラベルを描画する
    - 駒を描画する
    - 選択マスをハイライトする
    - 合法手候補をハイライトする
    - クリックされたマスを座標文字列で返す

    非責務:
    - 合法手判定
    - 手番管理
    - 指し手適用
    - AI通信
    """

    square_clicked = Signal(str)

    BOARD_SIZE = 6
    LABEL_MARGIN_LEFT = 40
    LABEL_MARGIN_TOP = 30
    LABEL_MARGIN_RIGHT = 20
    LABEL_MARGIN_BOTTOM = 20
    DEFAULT_SQUARE_SIZE = 64

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._board: dict[str, str | None] = self._create_empty_board()
        self._selected_square: str | None = None
        self._highlight_squares: set[str] = set()

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMinimumSize(self.sizeHint())
        self.setMouseTracking(True)

    def sizeHint(self):
        board_px = self.BOARD_SIZE * self.DEFAULT_SQUARE_SIZE
        width = self.LABEL_MARGIN_LEFT + board_px + self.LABEL_MARGIN_RIGHT
        height = self.LABEL_MARGIN_TOP + board_px + self.LABEL_MARGIN_BOTTOM
        return super().sizeHint().expandedTo(self.minimumSizeHint()).grownBy(
            self.contentsMargins()
        )

    def minimumSizeHint(self):
        board_px = self.BOARD_SIZE * self.DEFAULT_SQUARE_SIZE
        from PySide6.QtCore import QSize
        return QSize(
            self.LABEL_MARGIN_LEFT + board_px + self.LABEL_MARGIN_RIGHT,
            self.LABEL_MARGIN_TOP + board_px + self.LABEL_MARGIN_BOTTOM,
        )

    def set_board(self, board: dict[str, str | None]) -> None:
        """盤面情報を更新する。キーは '5e' 形式。値は駒文字列または None。"""
        self._board = board.copy()
        self.update()

    def set_selected_square(self, square: str | None) -> None:
        """選択中のマスを更新する。"""
        self._selected_square = square
        self.update()

    def set_highlight_squares(self, squares: Iterable[str]) -> None:
        """合法手候補などのハイライト対象マスを更新する。"""
        self._highlight_squares = set(squares)
        self.update()

    def clear_selection(self) -> None:
        """選択状態とハイライトをクリアする。"""
        self._selected_square = None
        self._highlight_squares.clear()
        self.update()

    def get_square_at_position(self, x: int, y: int) -> str | None:
        """ウィジェット上の座標から盤上のマス ('5e' 形式) を返す。盤外なら None。"""
        board_rect = self._board_rect()
        if not board_rect.contains(x, y):
            return None

        square_size = self._square_size()
        col = int((x - board_rect.left()) // square_size)
        row = int((y - board_rect.top()) // square_size)

        if not (0 <= col < self.BOARD_SIZE and 0 <= row < self.BOARD_SIZE):
            return None

        return self._index_to_square(row, col)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        square = self.get_square_at_position(int(event.position().x()), int(event.position().y()))
        if square is not None:
            self.square_clicked.emit(square)

        super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        self._draw_background(painter)
        self._draw_board(painter)
        self._draw_labels(painter)
        self._draw_highlights(painter)
        self._draw_pieces(painter)

        painter.end()
        super().paintEvent(event)

    def _draw_background(self, painter: QPainter) -> None:
        painter.fillRect(self.rect(), QColor("#f7f7f7"))

    def _draw_board(self, painter: QPainter) -> None:
        board_rect = self._board_rect()
        square_size = self._square_size()

        painter.fillRect(board_rect, QColor("#e6c48c"))
        painter.setPen(QPen(QColor("#333333"), 2))

        for row in range(self.BOARD_SIZE):
            for col in range(self.BOARD_SIZE):
                rect = QRectF(
                    board_rect.left() + col * square_size,
                    board_rect.top() + row * square_size,
                    square_size,
                    square_size,
                )
                painter.drawRect(rect)

    def _draw_labels(self, painter: QPainter) -> None:
        board_rect = self._board_rect()
        square_size = self._square_size()

        font = QFont()
        font.setPointSize(11)
        painter.setFont(font)
        painter.setPen(QColor("#222222"))

        # 上部の列ラベル: 6 5 4 3 2 1
        for col in range(self.BOARD_SIZE):
            file_num = str(self.BOARD_SIZE - col)
            x = board_rect.left() + col * square_size
            rect = QRectF(x, 0, square_size, self.LABEL_MARGIN_TOP)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, file_num)

        # 左側の行ラベル: a b c d e f
        for row in range(self.BOARD_SIZE):
            rank_char = chr(ord("a") + row)
            y = board_rect.top() + row * square_size
            rect = QRectF(0, y, self.LABEL_MARGIN_LEFT, square_size)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, rank_char)

    def _draw_highlights(self, painter: QPainter) -> None:
        board_rect = self._board_rect()
        square_size = self._square_size()

        # 合法手候補
        for square in self._highlight_squares:
            pos = self._square_to_index(square)
            if pos is None:
                continue
            row, col = pos
            rect = QRectF(
                board_rect.left() + col * square_size,
                board_rect.top() + row * square_size,
                square_size,
                square_size,
            )
            painter.fillRect(rect, QColor(100, 180, 255, 90))

        # 選択中マス
        if self._selected_square is not None:
            pos = self._square_to_index(self._selected_square)
            if pos is not None:
                row, col = pos
                rect = QRectF(
                    board_rect.left() + col * square_size,
                    board_rect.top() + row * square_size,
                    square_size,
                    square_size,
                )
                painter.fillRect(rect, QColor(255, 220, 80, 120))
                painter.setPen(QPen(QColor("#d18f00"), 3))
                painter.drawRect(rect)

    def _draw_pieces(self, painter: QPainter) -> None:
        board_rect = self._board_rect()
        square_size = self._square_size()

        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        painter.setFont(font)

        for square, piece in self._board.items():
            if piece is None:
                continue

            pos = self._square_to_index(square)
            if pos is None:
                continue

            row, col = pos
            rect = QRectF(
                board_rect.left() + col * square_size,
                board_rect.top() + row * square_size,
                square_size,
                square_size,
            )

            painter.setPen(QColor("#111111"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, piece)

    def _board_rect(self) -> QRectF:
        square_size = self._square_size()
        board_px = self.BOARD_SIZE * square_size
        return QRectF(
            self.LABEL_MARGIN_LEFT,
            self.LABEL_MARGIN_TOP,
            board_px,
            board_px,
        )

    def _square_size(self) -> float:
        available_w = max(
            1,
            self.width() - self.LABEL_MARGIN_LEFT - self.LABEL_MARGIN_RIGHT,
        )
        available_h = max(
            1,
            self.height() - self.LABEL_MARGIN_TOP - self.LABEL_MARGIN_BOTTOM,
        )
        return min(available_w, available_h) / self.BOARD_SIZE

    @classmethod
    def _create_empty_board(cls) -> dict[str, str | None]:
        board: dict[str, str | None] = {}
        for row in range(cls.BOARD_SIZE):
            for col in range(cls.BOARD_SIZE):
                square = cls._index_to_square(row, col)
                board[square] = None
        return board

    @classmethod
    def _index_to_square(cls, row: int, col: int) -> str:
        file_num = str(cls.BOARD_SIZE - col)   # 左から 6,5,4,3,2,1
        rank_char = chr(ord("a") + row)        # 上から a,b,c,d,e,f
        return f"{file_num}{rank_char}"

    @classmethod
    def _square_to_index(cls, square: str) -> tuple[int, int] | None:
        if len(square) != 2:
            return None

        file_char, rank_char = square[0], square[1]
        if not file_char.isdigit():
            return None
        if rank_char < "a" or rank_char > "f":
            return None

        file_num = int(file_char)
        if not (1 <= file_num <= cls.BOARD_SIZE):
            return None

        row = ord(rank_char) - ord("a")
        col = cls.BOARD_SIZE - file_num
        return row, col


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication([])

    widget = BoardWidget()
    widget.resize(520, 520)

    sample_board = {
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

    full_board = BoardWidget._create_empty_board()
    full_board.update(sample_board)

    widget.set_board(full_board)
    widget.set_selected_square("5e")
    widget.set_highlight_squares(["5d", "4d", "6d"])

    def on_square_clicked(square: str) -> None:
        print(f"clicked: {square}")

    widget.square_clicked.connect(on_square_clicked)
    widget.show()

    app.exec()
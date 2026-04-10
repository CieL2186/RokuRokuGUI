from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget


class BoardWidget(QWidget):
    """66将棋の盤面表示用ウィジェット。"""

    square_clicked = Signal(str)

    BOARD_SIZE = 6
    LABEL_MARGIN_LEFT = 40
    LABEL_MARGIN_TOP = 30
    LABEL_MARGIN_RIGHT = 20
    LABEL_MARGIN_BOTTOM = 20
    DEFAULT_SQUARE_SIZE = 64

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._board: dict[str, str | None] = self.create_empty_board()
        self._selected_square: str | None = None
        self._highlight_squares: set[str] = set()

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(self.minimumSizeHint())
        self.setMouseTracking(True)

    def sizeHint(self) -> QSize:
        board_px = self.BOARD_SIZE * self.DEFAULT_SQUARE_SIZE
        return QSize(
            self.LABEL_MARGIN_LEFT + board_px + self.LABEL_MARGIN_RIGHT,
            self.LABEL_MARGIN_TOP + board_px + self.LABEL_MARGIN_BOTTOM,
        )

    def minimumSizeHint(self) -> QSize:
        board_px = self.BOARD_SIZE * self.DEFAULT_SQUARE_SIZE
        return QSize(
            self.LABEL_MARGIN_LEFT + board_px + self.LABEL_MARGIN_RIGHT,
            self.LABEL_MARGIN_TOP + board_px + self.LABEL_MARGIN_BOTTOM,
        )

    def set_board(self, board: dict[str, str | None]) -> None:
        self._board = board.copy()
        self.update()

    def set_selected_square(self, square: str | None) -> None:
        self._selected_square = square
        self.update()

    def set_highlight_squares(self, squares: Iterable[str]) -> None:
        self._highlight_squares = set(squares)
        self.update()

    def set_legal_target_squares(self, squares: Iterable[str]) -> None:
        self.set_highlight_squares(squares)

    def clear_selection(self) -> None:
        self._selected_square = None
        self._highlight_squares.clear()
        self.update()

    def get_square_at_position(self, x: int, y: int) -> str | None:
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

        for col in range(self.BOARD_SIZE):
            file_num = str(self.BOARD_SIZE - col)
            x = board_rect.left() + col * square_size
            rect = QRectF(x, 0, square_size, self.LABEL_MARGIN_TOP)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, file_num)

        for row in range(self.BOARD_SIZE):
            rank_char = chr(ord("a") + row)
            y = board_rect.top() + row * square_size
            rect = QRectF(0, y, self.LABEL_MARGIN_LEFT, square_size)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, rank_char)

    def _draw_highlights(self, painter: QPainter) -> None:
        board_rect = self._board_rect()
        square_size = self._square_size()

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

            painter.setPen(self._piece_color(piece))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._piece_display_text(piece))

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
        available_w = max(1, self.width() - self.LABEL_MARGIN_LEFT - self.LABEL_MARGIN_RIGHT)
        available_h = max(1, self.height() - self.LABEL_MARGIN_TOP - self.LABEL_MARGIN_BOTTOM)
        return min(available_w, available_h) / self.BOARD_SIZE

    @classmethod
    def create_empty_board(cls) -> dict[str, str | None]:
        board: dict[str, str | None] = {}
        for row in range(cls.BOARD_SIZE):
            for col in range(cls.BOARD_SIZE):
                square = cls._index_to_square(row, col)
                board[square] = None
        return board

    @classmethod
    def _index_to_square(cls, row: int, col: int) -> str:
        file_num = str(cls.BOARD_SIZE - col)
        rank_char = chr(ord("a") + row)
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

    @staticmethod
    def _piece_display_text(piece: str) -> str:
        if len(piece) >= 2 and piece[0] in {"b", "w"}:
            return piece[1:]
        return piece.upper()

    @staticmethod
    def _piece_color(piece: str) -> QColor:
        if piece.startswith("w") or piece.islower():
            return QColor("#7a1f1f")
        return QColor("#111111")

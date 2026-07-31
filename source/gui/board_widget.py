from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from PySide6.QtCore import QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
    QTransform,
)
from PySide6.QtWidgets import QSizePolicy, QWidget


class BoardWidget(QWidget):
    """66将棋の盤面表示用ウィジェット。"""

    square_clicked = Signal(str)

    BOARD_SIZE = 6
    LABEL_MARGIN_LEFT = 28
    LABEL_MARGIN_TOP = 30
    LABEL_MARGIN_RIGHT = 36
    LABEL_MARGIN_BOTTOM = 28
    DEFAULT_SQUARE_SIZE = 64
    CELL_HEIGHT_RATIO = 1.05

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._board: dict[str, str | None] = self.create_empty_board()
        self._selected_square: str | None = None
        self._highlight_squares: set[str] = set()
        self._flipped = False

        base_dir = Path(__file__).resolve().parents[1]
        self._assets_dir = base_dir / "assets"
        self._board_pixmap = QPixmap(str(self._assets_dir / "board" / "66board.png"))
        self._piece_pixmaps: dict[str, QPixmap] = {}

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(self.minimumSizeHint())
        self.setMouseTracking(True)

    def sizeHint(self) -> QSize:
        board_w = self.BOARD_SIZE * self.DEFAULT_SQUARE_SIZE
        board_h = int(board_w * self.CELL_HEIGHT_RATIO)

        return QSize(
            self.LABEL_MARGIN_LEFT + board_w + self.LABEL_MARGIN_RIGHT,
            self.LABEL_MARGIN_TOP + board_h + self.LABEL_MARGIN_BOTTOM,
        )

    def minimumSizeHint(self) -> QSize:
        board_w = self.BOARD_SIZE * self.DEFAULT_SQUARE_SIZE
        board_h = int(board_w * self.CELL_HEIGHT_RATIO)

        return QSize(
            self.LABEL_MARGIN_LEFT + board_w + self.LABEL_MARGIN_RIGHT,
            self.LABEL_MARGIN_TOP + board_h + self.LABEL_MARGIN_BOTTOM,
        )

    def set_board(self, board: dict[str, str | None]) -> None:
        self._board = board.copy()
        print("board pieces =", {k: v for k, v in self._board.items() if v is not None})
        self.update()

    def set_selected_square(self, square: str | None) -> None:
        self._selected_square = square
        self.update()

    def set_highlight_squares(self, squares: Iterable[str]) -> None:
        self._highlight_squares = set(squares)
        self.update()

    def set_legal_target_squares(self, squares: Iterable[str]) -> None:
        self.set_highlight_squares(squares)

    def set_flipped(self, flipped: bool) -> None:
        if self._flipped == flipped:
            return

        self._flipped = flipped
        self.update()

    def is_flipped(self) -> bool:
        return self._flipped

    def clear_selection(self) -> None:
        self._selected_square = None
        self._highlight_squares.clear()
        self.update()

    def get_square_at_position(self, x: int, y: int) -> str | None:
        board_rect = self._board_rect()
        if not board_rect.contains(x, y):
            return None

        square_w = self._square_width()
        square_h = self._square_height()

        view_col = int((x - board_rect.left()) // square_w)
        view_row = int((y - board_rect.top()) // square_h)

        if not (0 <= view_col < self.BOARD_SIZE and 0 <= view_row < self.BOARD_SIZE):
            return None

        row, col = self._view_to_board_index(view_row, view_col)
        return self._index_to_square(row, col)


    def get_square_rect(self, square: str) -> QRect | None:
        pos = self._square_to_index(square)
        if pos is None:
            return None

        row, col = pos
        view_row, view_col = self._board_to_view_index(row, col)

        board_rect = self._board_rect()
        square_w = self._square_width()
        square_h = self._square_height()

        rect = QRectF(
            board_rect.left() + view_col * square_w,
            board_rect.top() + view_row * square_h,
            square_w,
            square_h,
        )
        return rect.toRect()


    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        square = self.get_square_at_position(
            int(event.position().x()),
            int(event.position().y()),
        )
        if square is not None:
            self.square_clicked.emit(square)

        super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

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
        visual_rect = self._visual_rect()
        square_w = self._square_width()
        square_h = self._square_height()

        # 背景画像は、盤面だけでなく上下左右の余白込みで描画する
        if not self._board_pixmap.isNull():
            painter.drawPixmap(visual_rect.toRect(), self._board_pixmap)
        else:
            painter.fillRect(visual_rect, QColor("#e6c48c"))

        # 6x6の線はコードで描く
        painter.setPen(QPen(QColor(40, 30, 20, 170), 1))

        for row in range(self.BOARD_SIZE + 1):
            y = board_rect.top() + row * square_h
            painter.drawLine(
                int(board_rect.left()),
                int(y),
                int(board_rect.right()),
                int(y),
            )

        for col in range(self.BOARD_SIZE + 1):
            x = board_rect.left() + col * square_w
            painter.drawLine(
                int(x),
                int(board_rect.top()),
                int(x),
                int(board_rect.bottom()),
            )

    def _draw_labels(self, painter: QPainter) -> None:
        board_rect = self._board_rect()
        square_w = self._square_width()
        square_h = self._square_height()

        font = QFont()
        font.setPointSize(11)
        painter.setFont(font)
        painter.setPen(QColor("#222222"))

        label_top = board_rect.top() - self.LABEL_MARGIN_TOP
        label_right = board_rect.right()
        rank_labels = ["一", "二", "三", "四", "五", "六"]

        for view_col in range(self.BOARD_SIZE):
            _, board_col = self._view_to_board_index(0, view_col)
            file_num = str(self.BOARD_SIZE - board_col)

            x = board_rect.left() + view_col * square_w
            rect = QRectF(x, label_top, square_w, self.LABEL_MARGIN_TOP)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, file_num)

        for view_row in range(self.BOARD_SIZE):
            board_row, _ = self._view_to_board_index(view_row, 0)

            y = board_rect.top() + view_row * square_h
            rect = QRectF(label_right, y, self.LABEL_MARGIN_RIGHT, square_h)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, rank_labels[board_row])


    def _draw_highlights(self, painter: QPainter) -> None:
        board_rect = self._board_rect()
        square_w = self._square_width()
        square_h = self._square_height()

        for square in self._highlight_squares:
            pos = self._square_to_index(square)
            if pos is None:
                continue

            row, col = pos
            view_row, view_col = self._board_to_view_index(row, col)

            rect = QRectF(
                board_rect.left() + view_col * square_w,
                board_rect.top() + view_row * square_h,
                square_w,
                square_h,
            )
            painter.fillRect(rect, QColor(100, 180, 255, 90))

        if self._selected_square is not None:
            pos = self._square_to_index(self._selected_square)
            if pos is not None:
                row, col = pos
                view_row, view_col = self._board_to_view_index(row, col)

                rect = QRectF(
                    board_rect.left() + view_col * square_w,
                    board_rect.top() + view_row * square_h,
                    square_w,
                    square_h,
                )
                painter.fillRect(rect, QColor(255, 220, 80, 120))
                painter.setPen(QPen(QColor("#d18f00"), 3))
                painter.drawRect(rect)


    def _draw_pieces(self, painter: QPainter) -> None:
        board_rect = self._board_rect()
        square_w = self._square_width()
        square_h = self._square_height()

        for square, piece in self._board.items():
            if piece is None:
                continue

            pos = self._square_to_index(square)
            if pos is None:
                continue

            row, col = pos
            view_row, view_col = self._board_to_view_index(row, col)

            square_rect = QRectF(
                board_rect.left() + view_col * square_w,
                board_rect.top() + view_row * square_h,
                square_w,
                square_h,
            )

            padding = max(2, int(min(square_w, square_h) * 0.06))
            piece_rect = square_rect.adjusted(
                padding,
                padding,
                -padding,
                -padding,
            ).toRect()

            pixmap = self._get_piece_pixmap(piece)
            if not pixmap.isNull():
                if self._flipped:
                    pixmap = pixmap.transformed(QTransform().rotate(180))
                painter.drawPixmap(piece_rect, pixmap)
            else:
                self._draw_fallback_piece(painter, square_rect, piece)


    def _draw_fallback_piece(
        self,
        painter: QPainter,
        rect: QRectF,
        piece: str,
    ) -> None:
        font = QFont()
        font.setPointSize(max(12, int(rect.height() * 0.30)))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(self._piece_color(piece))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._piece_display_text(piece))

    def _board_to_view_index(self, row: int, col: int) -> tuple[int, int]:
        if not self._flipped:
            return row, col

        return self.BOARD_SIZE - 1 - row, self.BOARD_SIZE - 1 - col

    def _view_to_board_index(self, row: int, col: int) -> tuple[int, int]:
        if not self._flipped:
            return row, col

        return self.BOARD_SIZE - 1 - row, self.BOARD_SIZE - 1 - col

    def _board_rect(self) -> QRectF:
        square_w = self._square_width()
        square_h = self._square_height()

        board_w = self.BOARD_SIZE * square_w
        board_h = self.BOARD_SIZE * square_h

        total_w = self.LABEL_MARGIN_LEFT + board_w + self.LABEL_MARGIN_RIGHT
        total_h = self.LABEL_MARGIN_TOP + board_h + self.LABEL_MARGIN_BOTTOM

        origin_x = max(0.0, (self.width() - total_w) / 2.0)
        origin_y = max(0.0, (self.height() - total_h) / 2.0)

        return QRectF(
            origin_x + self.LABEL_MARGIN_LEFT,
            origin_y + self.LABEL_MARGIN_TOP,
            board_w,
            board_h,
        )
    
    def _visual_rect(self) -> QRectF:
        """盤面だけでなく、上下左右の余白も含めた木目背景領域。"""
        board_rect = self._board_rect()

        return QRectF(
            board_rect.left() - self.LABEL_MARGIN_LEFT,
            board_rect.top() - self.LABEL_MARGIN_TOP,
            board_rect.width() + self.LABEL_MARGIN_LEFT + self.LABEL_MARGIN_RIGHT,
            board_rect.height() + self.LABEL_MARGIN_TOP + self.LABEL_MARGIN_BOTTOM,
        )

    def _square_width(self) -> float:
        available_w = max(
            1,
            self.width() - self.LABEL_MARGIN_LEFT - self.LABEL_MARGIN_RIGHT,
        )
        available_h = max(
            1,
            self.height() - self.LABEL_MARGIN_TOP - self.LABEL_MARGIN_BOTTOM,
        )

        width_from_w = available_w / self.BOARD_SIZE
        width_from_h = available_h / (self.BOARD_SIZE * self.CELL_HEIGHT_RATIO)

        return min(width_from_w, width_from_h)


    def _square_height(self) -> float:
        return self._square_width() * self.CELL_HEIGHT_RATIO


    def _get_piece_pixmap(self, piece: str) -> QPixmap:
        filename = self._piece_to_filename(piece)
        if filename in self._piece_pixmaps:
            return self._piece_pixmaps[filename]

        pixmap = QPixmap(str(self._assets_dir / "pieces" / filename))
        self._piece_pixmaps[filename] = pixmap
        return pixmap

    def _piece_to_filename(self, piece: str) -> str:
        side, base_piece, promoted = self._split_piece(piece)
        prefix = "black" if side == "black" else "white"

        if base_piece == "K":
            name = "king2" if side == "black" else "king"
        elif promoted and base_piece == "P":
            name = "prom_pawn"
        elif promoted and base_piece == "L":
            name = "prom_lance"
        elif promoted and base_piece == "N":
            name = "prom_knight"
        elif promoted and base_piece == "S":
            name = "prom_silver"
        elif promoted and base_piece == "R":
            name = "dragon"
        elif promoted and base_piece == "B":
            name = "horse"
        else:
            name_map = {
                "K": "king",
                "G": "gold",
                "S": "silver",
                "N": "knight",
                "L": "lance",
                "R": "rook",
                "B": "bishop",
                "P": "pawn",
            }
            name = name_map.get(base_piece, "pawn")

        return f"{prefix}_{name}.png"

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
    def _split_piece(piece: str) -> tuple[str, str, bool]:
        """pieceを side/base/promoted に分解する。

        現在の実装の "P"/"p" 形式に加えて、"bP"/"wP" 形式や
        "+P"/"+p" 形式も扱えるようにしている。
        """
        text = piece.strip()
        promoted = False

        if text.startswith("+"):
            promoted = True
            text = text[1:]

        if len(text) >= 2 and text[0] in {"b", "w"}:
            side = "black" if text[0] == "b" else "white"
            body = text[1:]
            if body.startswith("+"):
                promoted = True
                body = body[1:]
        else:
            body = text
            side = "black" if body.isupper() else "white"

        base_piece = body.upper()
        return side, base_piece, promoted

    @classmethod
    def _piece_display_text(cls, piece: str) -> str:
        _, base_piece, promoted = cls._split_piece(piece)
        return f"+{base_piece}" if promoted else base_piece

    @classmethod
    def _piece_color(cls, piece: str) -> QColor:
        side, _, _ = cls._split_piece(piece)
        if side == "white":
            return QColor("#7a1f1f")
        return QColor("#111111")
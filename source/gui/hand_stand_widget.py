from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QRect, Signal, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap, QTransform
from PySide6.QtWidgets import QWidget


class HandStandWidget(QWidget):
    """木箱画像の上に持ち駒を固定位置で表示するWidget。

    - 駒種ごとに置き場所を固定
    - 同じ駒は少しずつずらして重ねて表示
    """

    hand_piece_clicked = Signal(str, str)   # side, piece
    hand_cancel_requested = Signal(str)     # side

    # 表示順
    PIECE_ORDER = ["P", "L", "N", "S", "G", "B", "R", "K"]

    # 駒ごとの固定位置（左上座標の比率）
    # x, y は widget サイズに対する比率
    # 必要ならあとで微調整しやすいようにまとめてある
    SLOT_POSITIONS = {
        "P": (0.08, 0.10),

        "B": (0.12, 0.38),
        "R": (0.42, 0.38),
        "K": (0.70, 0.38),

        "L": (0.10, 0.66),
        "N": (0.32, 0.66),
        "S": (0.54, 0.66),
        "G": (0.76, 0.66),
    }

    def __init__(self, side: str, parent=None) -> None:
        super().__init__(parent)

        self.side = side  # "black" or "white"
        self.hands: dict[str, int] = {}
        self.selected_piece: str | None = None
        self.active = False
        self._flipped = False

        base_dir = Path(__file__).resolve().parents[1]
        self.assets_dir = base_dir / "assets"

        self.stand_pixmap = self._load_stand_pixmap()
        self.piece_pixmaps: dict[str, QPixmap] = {}

        # クリック判定用
        self.piece_hit_rects: dict[str, QRect] = {}

        self.setMinimumSize(190, 320)
        self.setMouseTracking(True)

    def sizeHint(self) -> QSize:
        return QSize(190, 320)

    def set_hands(self, hands: dict[str, int] | None) -> None:
        self.hands = self._normalize_hands(hands or {})
        self.update()

    def set_selected_piece(self, piece: str | None) -> None:
        self.selected_piece = piece
        self.update()

    def set_active(self, active: bool) -> None:
        self.active = active
        self.update()

    def set_flipped(self, flipped: bool) -> None:
        self._flipped = flipped
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        self._draw_stand(painter)
        self._draw_pieces(painter)

        if not self.active:
            painter.fillRect(self.rect(), QColor(255, 255, 255, 45))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self.hand_cancel_requested.emit(self.side)
            return

        if event.button() != Qt.MouseButton.LeftButton:
            return

        if not self.active:
            return

        pos = event.position().toPoint()

        # 前面に見えているものを優先しやすいように逆順でチェック
        for piece in reversed(self.PIECE_ORDER):
            rect = self.piece_hit_rects.get(piece)
            if rect is not None and rect.contains(pos):
                self.hand_piece_clicked.emit(self.side, piece)
                return

        # 空白部分クリックでキャンセル
        self.hand_cancel_requested.emit(self.side)

    def _load_stand_pixmap(self) -> QPixmap:
        stand_dir = self.assets_dir / "stands"

        if self.side == "black":
            candidates = [
                stand_dir / "black_stands.png",
                stand_dir / "brack_stands.png",  # typo対策
            ]
        else:
            candidates = [
                stand_dir / "white_stands.png",
            ]

        for path in candidates:
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                return pixmap

        return QPixmap()

    def _draw_stand(self, painter: QPainter) -> None:
        if not self.stand_pixmap.isNull():
            painter.drawPixmap(self.rect(), self.stand_pixmap)
        else:
            painter.fillRect(self.rect(), QColor(118, 72, 36))

    def _draw_pieces(self, painter: QPainter) -> None:
        self.piece_hit_rects.clear()

        # 駒サイズを大きくする
        piece_w = min(50, max(40, int(self.width() * 0.24)))
        piece_h = int(piece_w * 1.18)

        for piece in self.PIECE_ORDER:
            count = self.hands.get(piece, 0)
            if count <= 0:
                continue

            if piece not in self.SLOT_POSITIONS:
                continue

            base_x_ratio, base_y_ratio = self.SLOT_POSITIONS[piece]
            base_x = int(self.width() * base_x_ratio)
            base_y = int(self.height() * base_y_ratio)

            rects: list[QRect] = []

            if piece == "P":
                # 歩は最大12枚を想定して、6枚×2段で少し広めに重ねる
                max_cols = 6
                dx = max(22, int(piece_w * 0.55))
                dy = max(20, int(piece_h * 0.42))

                for i in range(count):
                    col = i % max_cols
                    row = i // max_cols

                    x = base_x + col * dx
                    y = base_y + row * dy

                    rect = QRect(x, y, piece_w, piece_h)
                    rects.append(rect)

                    pixmap = self._get_piece_pixmap(piece)
                    if not pixmap.isNull():
                        painter.drawPixmap(rect, pixmap)
                    else:
                        self._draw_fallback_piece(painter, rect, piece)

            else:
                # 歩以外は最大2枚程度なので、少しだけ横にずらして重ねる
                dx = max(18, int(piece_w * 0.42))
                dy = -2

                for i in range(count):
                    x = base_x + i * dx
                    y = base_y + i * dy

                    rect = QRect(x, y, piece_w, piece_h)
                    rects.append(rect)

                    pixmap = self._get_piece_pixmap(piece)
                    if not pixmap.isNull():
                        self._draw_piece_pixmap(painter, rect, pixmap)
                    else:
                        self._draw_fallback_piece(painter, rect, piece)

            if not rects:
                continue

            union_rect = rects[0]
            for r in rects[1:]:
                union_rect = union_rect.united(r)

            self.piece_hit_rects[piece] = union_rect

            if self.selected_piece == piece:
                self._draw_selected_frame(painter, union_rect)

    def _draw_piece_pixmap(
        self,
        painter: QPainter,
        rect: QRect,
        pixmap: QPixmap,
    ) -> None:
        if pixmap.isNull():
            return

        if not self._flipped:
            painter.drawPixmap(rect, pixmap)
            return

        transform = QTransform()
        transform.rotate(180)

        flipped_pixmap = pixmap.transformed(
            transform,
            Qt.TransformationMode.SmoothTransformation,
        )

        painter.drawPixmap(rect, flipped_pixmap)

    def _draw_fallback_piece(self, painter: QPainter, rect: QRect, piece: str) -> None:
        painter.save()

        if self._flipped:
            painter.translate(rect.center())
            painter.rotate(180)
            painter.translate(-rect.center())

        painter.setBrush(QColor(245, 220, 150))
        painter.setPen(QPen(QColor(90, 55, 20), 1))
        painter.drawRoundedRect(rect, 4, 4)
        painter.setFont(QFont("Yu Gothic", 10, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, piece)

        painter.restore()

    def _draw_selected_frame(self, painter: QPainter, rect: QRect) -> None:
        painter.save()
        painter.setPen(QPen(QColor(255, 190, 40), 3))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 5, 5)
        painter.restore()

    def _get_piece_pixmap(self, piece: str) -> QPixmap:
        key = f"{self.side}:{piece}"
        if key in self.piece_pixmaps:
            return self.piece_pixmaps[key]

        path = self.assets_dir / "pieces" / self._piece_to_filename(piece)
        pixmap = QPixmap(str(path))
        self.piece_pixmaps[key] = pixmap
        return pixmap

    def _piece_to_filename(self, piece: str) -> str:
        prefix = "black" if self.side == "black" else "white"

        name_map = {
            "K": "king",
            "G": "gold",
            "S": "silver",
            "N": "knight",
            "L": "lance",
            "R": "rook",
            "B": "bishop",
            "P": "pawn",
            "+S": "prom_silver",
            "+N": "prom_knight",
            "+L": "prom_lance",
            "+P": "prom_pawn",
            "+R": "dragon",
            "+B": "horse",
        }

        name = name_map.get(piece, "pawn")

        if piece == "K" and self.side == "black":
            name = "king2"

        return f"{prefix}_{name}.png"

    def _normalize_hands(self, hands: dict[str, int]) -> dict[str, int]:
        normalized: dict[str, int] = {}

        for piece, count in hands.items():
            if count is None:
                continue

            try:
                count_int = int(count)
            except (TypeError, ValueError):
                continue

            if count_int <= 0:
                continue

            normalized[self._normalize_piece_name(str(piece))] = count_int

        return normalized

    def _normalize_piece_name(self, piece: str) -> str:
        piece = piece.strip()

        if piece in {
            "K", "G", "S", "N", "L", "R", "B", "P",
            "+S", "+N", "+L", "+P", "+R", "+B",
        }:
            return piece

        jp_map = {
            "玉": "K",
            "王": "K",
            "金": "G",
            "銀": "S",
            "桂": "N",
            "桂馬": "N",
            "香": "L",
            "香車": "L",
            "飛": "R",
            "飛車": "R",
            "角": "B",
            "角行": "B",
            "歩": "P",
            "歩兵": "P",
            "と": "+P",
            "成銀": "+S",
            "成桂": "+N",
            "成香": "+L",
            "龍": "+R",
            "竜": "+R",
            "馬": "+B",
        }
        return jp_map.get(piece, piece)
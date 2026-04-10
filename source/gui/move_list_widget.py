from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget


class MoveListWidget(QListWidget):
    """棋譜や指し手の一覧を表示するウィジェット。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setAlternatingRowColors(True)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

    def set_moves(self, moves: Iterable[tuple[str, str]]) -> None:
        """棋譜一覧をまとめて設定する。要素は (side, move) のタプル。"""
        self.clear()

        for index, (side, move) in enumerate(moves, start=1):
            self._add_move_item(index, side, move)

        self.select_last_move()

    def add_move(self, side: str, move: str) -> None:
        """指し手を末尾に1件追加する。side は 'black' または 'white'。"""
        move_number = self.count() + 1
        self._add_move_item(move_number, side, move)
        self.select_last_move()

    def clear_moves(self) -> None:
        """棋譜一覧をクリアする。"""
        self.clear()

    def select_last_move(self) -> None:
        """最後の指し手を選択状態にする。"""
        if self.count() == 0:
            return

        last_row = self.count() - 1
        self.setCurrentRow(last_row)
        item = self.item(last_row)
        if item is not None:
            self.scrollToItem(item)

    def _add_move_item(self, move_number: int, side: str, move: str) -> None:
        """一覧に表示する1件分のアイテムを追加する。"""
        prefix = "▲" if side == "black" else "△"
        text = f"{move_number}. {prefix} {move}"

        item = QListWidgetItem(text)

        if side == "black":
            item.setForeground(QColor("#222222"))
        else:
            item.setForeground(QColor("#c62828"))

        self.addItem(item)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication([])

    widget = MoveListWidget()
    widget.set_moves(
        [
            ("black", "2c2d"),
            ("white", "5e5d"),
            ("black", "3c3d"),
            ("white", "4e4d"),
        ]
    )
    widget.add_move("black", "2d2e")
    widget.resize(240, 320)
    widget.show()

    app.exec()
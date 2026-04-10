from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget


class MoveListWidget(QListWidget):
    """棋譜や指し手の一覧を表示するウィジェット。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setAlternatingRowColors(True)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

    def set_moves(self, moves: Iterable[str]) -> None:
        self.clear()

        for index, move in enumerate(moves, start=1):
            self._add_move_item(index, move)

        self.select_last_move()

    def add_move(self, move: str) -> None:
        move_number = self.count() + 1
        self._add_move_item(move_number, move)
        self.select_last_move()

    def clear_moves(self) -> None:
        self.clear()

    def select_last_move(self) -> None:
        if self.count() == 0:
            return

        last_row = self.count() - 1
        self.setCurrentRow(last_row)
        item = self.item(last_row)
        if item is not None:
            self.scrollToItem(item)

    def _add_move_item(self, move_number: int, move: str) -> None:
        text = f"{move_number}. {move}"
        item = QListWidgetItem(text)
        self.addItem(item)

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, Signal

from source.core.move import Move
from source.core.position import Position
from source.core import rules


class GameController(QObject):
    move_made = Signal(str)
    selection_changed = Signal(str)
    status_changed = Signal(str)
    board_refreshed = Signal()

    def __init__(
        self,
        board_widget,
        move_list_widget=None,
        *,
        status_callback: Callable[[str], None] | None = None,
        turn_callback: Callable[[str], None] | None = None,
        phase_callback: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__()
        self.board_widget = board_widget
        self.move_list_widget = move_list_widget
        self.status_callback = status_callback
        self.turn_callback = turn_callback
        self.phase_callback = phase_callback

        self.position: Position | None = None
        self.selected_square: str | None = None
        self.legal_moves_from_selected: list[Move] = []
        self.last_clicked_square: str | None = None

        self.board_widget.square_clicked.connect(self.on_square_clicked)

    def new_game(self, position: Position | None = None) -> None:
        self.position = position if position is not None else Position()
        self.selected_square = None
        self.legal_moves_from_selected = []
        self.last_clicked_square = None

        if self.move_list_widget is not None and hasattr(self.move_list_widget, "clear_moves"):
            self.move_list_widget.clear_moves()
        elif self.move_list_widget is not None and hasattr(self.move_list_widget, "clear"):
            self.move_list_widget.clear()

        self.refresh_view()
        self._emit_status("新規対局を開始しました")

    def set_position(self, position: Position) -> None:
        self.position = position
        self.selected_square = None
        self.legal_moves_from_selected = []
        self.refresh_view()

    def on_square_clicked(self, square: str) -> None:
        self.last_clicked_square = square
        self.selection_changed.emit(square)

        if self.position is None:
            self._emit_status("先に new_game() を呼んでください")
            return

        if self.selected_square is None:
            self._select_square(square)
            return

        if square == self.selected_square:
            self._clear_selection()
            self._emit_status(f"選択解除: {square}")
            return

        move = self._find_move_to(square)
        if move is not None:
            self._apply_move(move)
            return

        if self._is_selectable_square(square):
            self._select_square(square)
            return

        self._emit_status(f"{square} へは移動できません")

    def undo(self) -> bool:
        if self.position is None:
            return False

        if not self.position.undo_move():
            self._emit_status("これ以上戻せません")
            return False

        if self.move_list_widget is not None and hasattr(self.move_list_widget, "set_moves"):
            self.move_list_widget.set_moves(self._get_move_history_usi())

        self._clear_selection(refresh=False)
        self.refresh_view()
        self._emit_status("1手戻しました")
        return True

    def refresh_view(self) -> None:
        self._update_board_widget()
        self._update_highlight()
        self._update_side_to_move()
        self._update_phase()
        self.board_refreshed.emit()

    def _select_square(self, square: str) -> None:
        legal_moves = self._get_legal_moves_from(square)
        if not legal_moves:
            self._clear_selection(refresh=False)
            self.refresh_view()
            self._emit_status(f"{square} は選択できません")
            return

        self.selected_square = square
        self.legal_moves_from_selected = legal_moves
        self.refresh_view()
        self._emit_status(f"{square} を選択しました")

    def _clear_selection(self, refresh: bool = True) -> None:
        self.selected_square = None
        self.legal_moves_from_selected = []
        if refresh:
            self.refresh_view()

    def _apply_move(self, move: Move) -> None:
        if self.position is None:
            return

        if not self.position.do_move(move):
            self._emit_status(f"指し手を適用できませんでした: {move}")
            return

        move_text = move.to_usi()
        if self.move_list_widget is not None and hasattr(self.move_list_widget, "add_move"):
            self.move_list_widget.add_move(move_text)

        self._clear_selection(refresh=False)
        self.refresh_view()
        self.move_made.emit(move_text)

        if self.position.is_game_over():
            self._emit_status(self._get_game_result_text())
        else:
            self._emit_status(f"着手: {move_text}")

    def _find_move_to(self, destination: str) -> Move | None:
        for move in self.legal_moves_from_selected:
            if move.to_square == destination:
                return move
        return None

    def _is_selectable_square(self, square: str) -> bool:
        return len(self._get_legal_moves_from(square)) > 0

    def _get_legal_moves_from(self, square: str) -> list[Move]:
        if self.position is None:
            return []
        return list(self.position.get_legal_moves_from(square))

    def _get_game_result_text(self) -> str:
        if self.position is None:
            return "対局終了"
        return f"対局終了: {self.position.get_game_result()}"

    def _get_move_history_usi(self) -> list[str]:
        if self.position is None:
            return []
        return [move.to_usi() for move in self.position.get_move_history()]

    def _update_board_widget(self) -> None:
        if self.position is None:
            return
        self.board_widget.set_board(self.position.get_board())

    def _update_highlight(self) -> None:
        legal_targets = [move.to_square for move in self.legal_moves_from_selected if move.to_square is not None]
        self.board_widget.set_selected_square(self.selected_square)

        if hasattr(self.board_widget, "set_legal_target_squares"):
            self.board_widget.set_legal_target_squares(legal_targets)
        elif hasattr(self.board_widget, "set_highlight_squares"):
            self.board_widget.set_highlight_squares(legal_targets)
        else:
            self.board_widget.update()

    def _update_side_to_move(self) -> None:
        if self.turn_callback is None or self.position is None:
            return

        side = self.position.get_side_to_move()
        text = "先手" if side == rules.BLACK else "後手"
        self.turn_callback(text)

    def _update_phase(self) -> None:
        if self.phase_callback is None or self.position is None:
            return
        self.phase_callback(str(self.position.get_phase()))

    def _emit_status(self, text: str) -> None:
        self.status_changed.emit(text)
        if self.status_callback is not None:
            self.status_callback(text)

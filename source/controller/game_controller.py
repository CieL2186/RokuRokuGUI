from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal

from core.move import Move

try:
    from core.position import Position
except Exception:  # pragma: no cover
    Position = object  # type: ignore[misc,assignment]

try:
    from core import rules
except Exception:  # pragma: no cover
    rules = None


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
        status_callback: Optional[Callable[[str], None]] = None,
        turn_callback: Optional[Callable[[str], None]] = None,
        phase_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__()
        self.board_widget = board_widget
        self.move_list_widget = move_list_widget
        self.status_callback = status_callback
        self.turn_callback = turn_callback
        self.phase_callback = phase_callback

        self.position = None
        self.selected_square: Optional[str] = None
        self.legal_moves_from_selected: list[Move] = []
        self.last_clicked_square: Optional[str] = None

        if hasattr(self.board_widget, "square_clicked"):
            self.board_widget.square_clicked.connect(self.on_square_clicked)

    def new_game(self, position: Optional[Position] = None) -> None:
        if position is not None:
            self.position = position
        else:
            position_cls = self._resolve_position_class()
            if position_cls is None:
                raise RuntimeError(
                    "Position を生成できません。core.position.Position を実装するか、"
                    "new_game(position=...) で局面オブジェクトを渡してください。"
                )
            self.position = position_cls()
            if hasattr(self.position, "new_game"):
                self.position.new_game()
            elif hasattr(self.position, "reset"):
                self.position.reset()

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

        if hasattr(self.position, "undo_move"):
            ok = bool(self.position.undo_move())
        else:
            ok = False

        if not ok:
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

        ok = self._do_move(move)
        if not ok:
            self._emit_status(f"指し手を適用できませんでした: {move}")
            return

        move_text = self._move_to_text(move)
        if self.move_list_widget is not None:
            if hasattr(self.move_list_widget, "add_move"):
                self.move_list_widget.add_move(move_text)
            elif hasattr(self.move_list_widget, "append_move"):
                self.move_list_widget.append_move(move_text)

        self._clear_selection(refresh=False)
        self.refresh_view()
        self.move_made.emit(move_text)

        if self._is_game_over():
            self._emit_status(self._get_game_result_text())
        else:
            self._emit_status(f"着手: {move_text}")

    def _find_move_to(self, destination: str) -> Optional[Move]:
        for move in self.legal_moves_from_selected:
            if getattr(move, "to_square", None) == destination:
                return move
        return None

    def _is_selectable_square(self, square: str) -> bool:
        return len(self._get_legal_moves_from(square)) > 0

    def _get_legal_moves_from(self, square: str) -> list[Move]:
        if self.position is None:
            return []

        if hasattr(self.position, "get_legal_moves_from"):
            moves = self.position.get_legal_moves_from(square)
            return list(moves)

        if rules is not None:
            if hasattr(rules, "get_legal_moves_from"):
                return list(rules.get_legal_moves_from(self.position, square))
            if hasattr(rules, "generate_legal_moves_from"):
                return list(rules.generate_legal_moves_from(self.position, square))
            if hasattr(rules, "get_all_legal_moves"):
                all_moves = list(rules.get_all_legal_moves(self.position))
                return [m for m in all_moves if getattr(m, "from_square", None) == square]

        return []

    def _do_move(self, move: Move) -> bool:
        if self.position is None:
            return False

        if hasattr(self.position, "do_move"):
            return bool(self.position.do_move(move))

        if rules is not None and hasattr(rules, "do_move"):
            return bool(rules.do_move(self.position, move))

        return False

    def _is_game_over(self) -> bool:
        if self.position is None:
            return False
        if hasattr(self.position, "is_game_over"):
            return bool(self.position.is_game_over())
        if rules is not None and hasattr(rules, "is_game_over"):
            return bool(rules.is_game_over(self.position))
        return False

    def _get_game_result_text(self) -> str:
        if self.position is None:
            return "対局終了"

        if hasattr(self.position, "get_game_result"):
            result = self.position.get_game_result()
            return f"対局終了: {result}"

        if rules is not None and hasattr(rules, "get_game_result"):
            result = rules.get_game_result(self.position)
            return f"対局終了: {result}"

        return "対局終了"

    def _get_move_history_usi(self) -> list[str]:
        if self.position is None:
            return []

        if hasattr(self.position, "get_move_history"):
            history = self.position.get_move_history()
        elif hasattr(self.position, "move_history"):
            history = self.position.move_history
        else:
            history = []

        result: list[str] = []
        for move in history:
            if hasattr(move, "to_usi"):
                result.append(move.to_usi())
            else:
                result.append(str(move))
        return result

    def _update_board_widget(self) -> None:
        if self.position is None:
            return

        board = None
        if hasattr(self.position, "get_board"):
            board = self.position.get_board()
        elif hasattr(self.position, "board"):
            board = self.position.board

        if hasattr(self.board_widget, "set_board"):
            self.board_widget.set_board(board)
        elif hasattr(self.board_widget, "load_position"):
            self.board_widget.load_position(board)
        elif hasattr(self.board_widget, "board"):
            self.board_widget.board = board
            if hasattr(self.board_widget, "update"):
                self.board_widget.update()

    def _update_highlight(self) -> None:
        legal_targets = [getattr(move, "to_square", None) for move in self.legal_moves_from_selected]
        legal_targets = [sq for sq in legal_targets if sq is not None]

        if hasattr(self.board_widget, "set_selected_square"):
            self.board_widget.set_selected_square(self.selected_square)
        elif hasattr(self.board_widget, "selected_square"):
            self.board_widget.selected_square = self.selected_square

        if hasattr(self.board_widget, "set_legal_target_squares"):
            self.board_widget.set_legal_target_squares(legal_targets)
        elif hasattr(self.board_widget, "set_legal_moves"):
            self.board_widget.set_legal_moves(legal_targets)
        elif hasattr(self.board_widget, "legal_target_squares"):
            self.board_widget.legal_target_squares = legal_targets

        if hasattr(self.board_widget, "update"):
            self.board_widget.update()

    def _update_side_to_move(self) -> None:
        if self.turn_callback is None or self.position is None:
            return

        side = None
        if hasattr(self.position, "get_side_to_move"):
            side = self.position.get_side_to_move()
        elif hasattr(self.position, "side_to_move"):
            side = self.position.side_to_move

        if side is None:
            return

        if isinstance(side, int):
            text = "先手" if side == 0 else "後手"
        else:
            text = str(side)
        self.turn_callback(text)

    def _update_phase(self) -> None:
        if self.phase_callback is None or self.position is None:
            return

        phase = None
        if hasattr(self.position, "get_phase"):
            phase = self.position.get_phase()
        elif hasattr(self.position, "phase"):
            phase = self.position.phase

        if phase is not None:
            self.phase_callback(str(phase))

    def _emit_status(self, text: str) -> None:
        self.status_changed.emit(text)
        if self.status_callback is not None:
            self.status_callback(text)

    def _move_to_text(self, move: Move) -> str:
        if hasattr(move, "to_usi"):
            return move.to_usi()
        return str(move)

    @staticmethod
    def _resolve_position_class():
        return Position if Position is not object else None

from __future__ import annotations

from collections.abc import Callable

from source.core.move import Move
from source.core.position import Position


class GameController:
    """GUI と局面処理をつなぐ最小コントローラ。"""

    def __init__(
        self,
        board_widget,
        move_list_widget=None,
        status_callback: Callable[[str], None] | None = None,
        turn_callback: Callable[[str], None] | None = None,
        phase_callback: Callable[[str], None] | None = None,
        promotion_request_callback: Callable[[str], None] | None = None,
        promotion_clear_callback: Callable[[], None] | None = None,
    ) -> None:
        self._board_widget = board_widget
        self._move_list_widget = move_list_widget
        self._status_callback = status_callback
        self._turn_callback = turn_callback
        self._phase_callback = phase_callback
        self._promotion_request_callback = promotion_request_callback
        self._promotion_clear_callback = promotion_clear_callback

        self._position = Position()
        self._selected_square: str | None = None
        self._pending_promotion_moves: dict[bool, Move] | None = None
        self._pending_promotion_square: str | None = None

        self._connect_board_signal()
        self._refresh_view()
        self._set_status("対局を開始しました。")

    def new_game(self, position: Position | None = None) -> None:
        self._position = position if position is not None else Position()
        self._selected_square = None
        self._clear_pending_promotion()

        if self._move_list_widget is not None and hasattr(self._move_list_widget, "clear_moves"):
            self._move_list_widget.clear_moves()

        self._clear_board_selection()
        self._refresh_view()
        self._set_status("新規対局を開始しました。")

    def handle_square_clicked(self, square: str) -> None:
        if self._pending_promotion_moves is not None:
            self._set_status("成るか不成かを選んでください。")
            return

        piece = self._position.get_piece_at(square)
        current_side = self._position.get_side_to_move()

        if self._selected_square is None:
            if piece is None:
                self._set_status("駒のあるマスを選んでください。")
                return

            if not self._is_own_piece(piece, current_side):
                self._set_status("自分の駒を選んでください。")
                return

            self._select_square(square)
            return

        if square == self._selected_square:
            self._clear_selection_only()
            self._set_status("選択を解除しました。")
            return

        if piece is not None and self._is_own_piece(piece, current_side):
            self._select_square(square)
            return

        result = self._resolve_move_choice(self._selected_square, square)
        if result is None:
            self._set_status("そのマスには移動できません。")
            return

        if isinstance(result, Move):
            self._execute_move(result)
            return

        normal_move, promote_move = result
        self._pending_promotion_moves = {
            False: normal_move,
            True: promote_move,
        }
        self._pending_promotion_square = square

        if self._promotion_request_callback is not None:
            self._promotion_request_callback(square)

        self._set_status(f"{square} で成るか不成かを選んでください。")

    def handle_promotion_choice(self, promote: bool) -> None:
        if self._pending_promotion_moves is None:
            self._set_status("選択中の成り候補はありません。")
            return

        move = self._pending_promotion_moves[promote]
        self._clear_pending_promotion()
        self._execute_move(move)

    def cancel_promotion_choice(self) -> None:
        if self._pending_promotion_moves is None:
            return

        self._clear_pending_promotion()
        self._set_status("成り選択をキャンセルしました。")

    def undo_move(self) -> None:
        self._clear_pending_promotion()

        if not self._position.undo_move():
            self._set_status("これ以上戻せません。")
            return

        self._selected_square = None
        self._clear_board_selection()

        if self._move_list_widget is not None and hasattr(self._move_list_widget, "set_moves"):
            history_items: list[tuple[str, str]] = []
            side = "black"
            for move in self._position.get_move_history():
                history_items.append((side, move.to_usi()))
                side = "white" if side == "black" else "black"
            self._move_list_widget.set_moves(history_items)

        self._refresh_view()

        current_side = self._position.get_side_to_move()
        turn_text = "先手" if current_side == "black" else "後手"

        if self._position.is_checkmate(current_side):
            self._set_status(f"{turn_text}は詰みです。")
        elif self._position.is_in_check(current_side):
            self._set_status(f"{turn_text}は王手されています。")
        else:
            self._set_status("1手戻しました。")

    def _resolve_move_choice(
        self,
        from_square: str,
        to_square: str,
    ) -> Move | tuple[Move, Move] | None:
        legal_moves = self._position.get_legal_moves_from(from_square)
        candidates = [move for move in legal_moves if move.to_square == to_square]

        if not candidates:
            return None

        promoted = next((move for move in candidates if move.promote), None)
        normal = next((move for move in candidates if not move.promote), None)

        if promoted is not None and normal is not None:
            return normal, promoted

        if promoted is not None:
            return promoted

        if normal is not None:
            return normal

        return None

    def _execute_move(self, move: Move) -> None:
        moving_side = self._position.get_side_to_move()

        if not self._position.do_move(move):
            self._set_status("着手に失敗しました。")
            return

        if self._move_list_widget is not None and hasattr(self._move_list_widget, "add_move"):
            self._move_list_widget.add_move(moving_side, move.to_usi())

        self._selected_square = None
        self._clear_board_selection()
        self._refresh_view()

        next_side = self._position.get_side_to_move()
        next_side_text = "先手" if next_side == "black" else "後手"

        move_text = f"{move.to_usi()} で成りました。" if move.promote else f"{move.to_usi()} を指しました。"

        if self._position.is_checkmate(next_side):
            winner = "先手" if moving_side == "black" else "後手"
            self._set_status(f"{move_text} {next_side_text}は詰みです。{winner}の勝ちです。")
            return

        if self._position.is_in_check(next_side):
            self._set_status(f"{move_text} {next_side_text}に王手です。")
            return

        self._set_status(move_text)

    def _select_square(self, square: str) -> None:
        self._selected_square = square

        legal_moves = self._position.get_legal_moves_from(square)
        target_squares = []
        seen: set[str] = set()

        for move in legal_moves:
            if move.to_square in seen:
                continue
            seen.add(move.to_square)
            target_squares.append(move.to_square)

        if hasattr(self._board_widget, "set_selected_square"):
            self._board_widget.set_selected_square(square)

        if hasattr(self._board_widget, "set_legal_target_squares"):
            self._board_widget.set_legal_target_squares(target_squares)
        elif hasattr(self._board_widget, "set_highlight_squares"):
            self._board_widget.set_highlight_squares(target_squares)

        piece = self._position.get_piece_at(square)
        if piece is None:
            self._set_status(f"{square} を選択しました。")
        else:
            self._set_status(f"{square} の {piece} を選択しました。")

    def _clear_selection_only(self) -> None:
        self._selected_square = None
        self._clear_board_selection()

    def _clear_board_selection(self) -> None:
        if hasattr(self._board_widget, "clear_selection"):
            self._board_widget.clear_selection()
            return

        if hasattr(self._board_widget, "set_selected_square"):
            self._board_widget.set_selected_square(None)

        if hasattr(self._board_widget, "set_legal_target_squares"):
            self._board_widget.set_legal_target_squares([])
        elif hasattr(self._board_widget, "set_highlight_squares"):
            self._board_widget.set_highlight_squares([])

    def _refresh_view(self) -> None:
        if hasattr(self._board_widget, "set_board"):
            self._board_widget.set_board(self._position.get_board())

        if self._turn_callback is not None:
            turn_text = "先手" if self._position.get_side_to_move() == "black" else "後手"
            self._turn_callback(f"手番: {turn_text}")

        if self._phase_callback is not None:
            self._phase_callback(f"フェーズ: {self._position.get_phase()}")

    def _set_status(self, text: str) -> None:
        if self._status_callback is not None:
            self._status_callback(text)

    def _clear_pending_promotion(self) -> None:
        self._pending_promotion_moves = None
        self._pending_promotion_square = None

        if self._promotion_clear_callback is not None:
            self._promotion_clear_callback()

    def _is_own_piece(self, piece: str, side: str) -> bool:
        if side == "black":
            return piece.startswith("b") or (not piece.startswith("w") and piece.lstrip("+").isupper())
        return piece.startswith("w") or (not piece.startswith("b") and piece.lstrip("+").islower())

    def _connect_board_signal(self) -> None:
        if hasattr(self._board_widget, "square_clicked"):
            self._board_widget.square_clicked.connect(self.handle_square_clicked)

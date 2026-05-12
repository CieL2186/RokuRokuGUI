from __future__ import annotations

from collections.abc import Callable

from source.core import rules
from source.core.move import Move
from source.core.position import Position


class GameController:
    """GUI と局面処理をつなぐコントローラ。"""

    def __init__(
        self,
        board_widget,
        move_list_widget=None,
        status_callback: Callable[[str], None] | None = None,
        turn_callback: Callable[[str], None] | None = None,
        phase_callback: Callable[[str], None] | None = None,
        hands_callback: Callable[[dict[str, dict[str, int]]], None] | None = None,
        hand_selection_callback: Callable[[str | None, str | None], None] | None = None,
        promotion_request_callback: Callable[[str], None] | None = None,
        promotion_clear_callback: Callable[[], None] | None = None,
    ) -> None:
        self._board_widget = board_widget
        self._move_list_widget = move_list_widget
        self._status_callback = status_callback
        self._turn_callback = turn_callback
        self._phase_callback = phase_callback
        self._hands_callback = hands_callback
        self._hand_selection_callback = hand_selection_callback
        self._promotion_request_callback = promotion_request_callback
        self._promotion_clear_callback = promotion_clear_callback

        self._position = Position()

        self._selected_square: str | None = None
        self._selected_hand_side: str | None = None
        self._selected_hand_piece: str | None = None

        self._pending_promotion_moves: dict[bool, Move] | None = None
        self._pending_promotion_square: str | None = None

        self._connect_board_signal()
        self._refresh_view()
        self._set_status("対局を開始しました。")

    def new_game(self, position: Position | None = None) -> None:
        self._position = position if position is not None else Position()
        self._selected_square = None
        self._selected_hand_side = None
        self._selected_hand_piece = None
        self._clear_pending_promotion()

        if self._move_list_widget is not None and hasattr(self._move_list_widget, "clear_moves"):
            self._move_list_widget.clear_moves()

        self._clear_board_selection()
        self._notify_hand_selection()
        self._refresh_view()
        self._set_status("新規対局を開始しました。")

    # =========================
    # 持ち駒選択
    # =========================

    def select_hand_piece(self, side_or_piece: str, piece: str | None = None) -> None:
        """
        駒台Widgetからは select_hand_piece(side, piece) で呼ばれる。
        古いボタン式から select_hand_piece(piece) で呼ばれても動くようにしている。
        """

        if self._pending_promotion_moves is not None:
            self._clear_pending_promotion()

        if piece is None:
            side = self._position.get_side_to_move()
            piece = side_or_piece
        else:
            side = side_or_piece

        current_side = self._position.get_side_to_move()

        if side != current_side:
            self._set_status(f"現在は{self._side_text(current_side)}の手番です。")
            return

        if self._get_hand_count(side, piece) <= 0:
            self._set_status(f"{piece} はもう持っていません。")
            return

        if self._selected_hand_side == side and self._selected_hand_piece == piece:
            self.cancel_hand_selection(side)
            return

        self._selected_hand_side = side
        self._selected_hand_piece = piece
        self._selected_square = None

        self._clear_board_selection()
        self._notify_hand_selection()
        self._set_drop_highlights(side, piece)

        if self._position.get_phase() == "配置":
            self._set_status(f"{piece} を選択しました。配置先をクリックしてください。")
        else:
            self._set_status(f"{piece} を選択しました。打ち先をクリックしてください。")

    def cancel_hand_selection(self, side: str | None = None) -> None:
        if self._pending_promotion_moves is not None:
            self._clear_pending_promotion()
            self._clear_selection_only()
            self._set_status("選択を解除しました。")
            return

        if self._selected_hand_piece is None:
            return

        if side is not None and self._selected_hand_side is not None and side != self._selected_hand_side:
            return

        piece = self._selected_hand_piece
        self._selected_hand_side = None
        self._selected_hand_piece = None
        self._clear_board_selection()
        self._notify_hand_selection()
        self._set_status(f"{piece} の選択を解除しました。")

    # =========================
    # 盤クリック
    # =========================

    def handle_square_clicked(self, square: str) -> None:
        if self._pending_promotion_moves is not None:
            self._handle_square_clicked_during_promotion(square)
            return

        # 持ち駒選択中なら、配置フェーズ/対局フェーズ共通で打ち/配置を試す
        if self._selected_hand_piece is not None:
            self._handle_drop_click(square)
            return

        if self._position.get_phase() == "配置":
            self._set_status("まず持ち駒を選んでください。")
            return

        self._handle_battle_click(square)

    def _handle_square_clicked_during_promotion(self, square: str) -> None:
        """成り/不成ボタン表示中に、盤上の別マスがクリックされたときの処理。"""

        if self._selected_square is None:
            self._clear_pending_promotion()
            self._clear_selection_only()
            self._set_status("選択を解除しました。")
            return

        current_side = self._position.get_side_to_move()
        clicked_piece = self._position.get_piece_at(square)

        # もとの選択駒をもう一度クリックしたらキャンセル
        if square == self._selected_square:
            self._clear_pending_promotion()
            self._clear_selection_only()
            self._set_status("選択を解除しました。")
            return

        # 自分の別の駒をクリックしたら、成り選択を消してその駒を選択
        if clicked_piece is not None and self._is_own_piece(clicked_piece, current_side):
            self._clear_pending_promotion()
            self._select_board_square(square)
            return

        # 選択中の駒から、クリック先への手を再判定
        result = self._resolve_move_choice(self._selected_square, square)

        # 移動できないマス、または何もないところをクリックしたら全部解除
        if result is None:
            self._clear_pending_promotion()
            self._clear_selection_only()
            self._set_status("選択を解除しました。")
            return

        # 成り選択が不要な手なら、成りボタンを消してその手を実行
        if isinstance(result, Move):
            self._clear_pending_promotion()
            self._execute_battle_move(result)
            return

        # 別の成り可能マスなら、成りボタンをそのマスへ移動
        normal_move, promote_move = result
        self._start_promotion_choice(square, normal_move, promote_move)

    def handle_promotion_choice(self, promote: bool) -> None:
        if self._pending_promotion_moves is None:
            self._set_status("選択中の成り候補はありません。")
            return

        move = self._pending_promotion_moves[promote]
        self._clear_pending_promotion()
        self._execute_battle_move(move)

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
        self._selected_hand_side = None
        self._selected_hand_piece = None
        self._clear_board_selection()
        self._notify_hand_selection()

        if self._move_list_widget is not None and hasattr(self._move_list_widget, "set_moves"):
            history_items: list[tuple[str, str]] = []
            side = "black"
            for move in self._position.get_move_history():
                history_items.append((side, move.to_usi()))
                side = "white" if side == "black" else "black"
            self._move_list_widget.set_moves(history_items)

        self._refresh_view()

        current_side = self._position.get_side_to_move()
        turn_text = self._side_text(current_side)

        if self._position.is_checkmate(current_side):
            self._set_status(f"{turn_text}は詰みです。")
        elif self._position.is_in_check(current_side):
            self._set_status(f"{turn_text}は王手されています。")
        else:
            self._set_status("1手戻しました。")

    # =========================
    # 打ち駒 / 配置
    # =========================

    def _handle_drop_click(self, square: str) -> None:
        if self._selected_hand_piece is None:
            self._set_status("持ち駒を選んでください。")
            return

        side_before_move = self._position.get_side_to_move()
        phase_before_move = self._position.get_phase()
        dropped_piece = self._selected_hand_piece
        move = self._make_drop_move(dropped_piece, square)

        error_message = None
        if hasattr(rules, "get_drop_error_message"):
            error_message = rules.get_drop_error_message(
                self._position,
                move,
                side_before_move,
            )
        elif hasattr(rules, "get_legal_drop_squares"):
            legal_squares = rules.get_legal_drop_squares(
                self._position,
                dropped_piece,
                side_before_move,
            )
            if square not in legal_squares:
                error_message = "そのマスには打てません。"
        else:
            legal_squares = self._fallback_legal_drop_squares(side_before_move, dropped_piece)
            if square not in legal_squares:
                error_message = "そのマスには打てません。"

        if error_message is not None:
            self._set_status(error_message)
            return

        if not self._position.do_move(move):
            self._set_status("着手に失敗しました。")
            return

        if self._move_list_widget is not None and hasattr(self._move_list_widget, "add_move"):
            self._move_list_widget.add_move(side_before_move, move.to_usi())

        self._selected_hand_side = None
        self._selected_hand_piece = None
        self._notify_hand_selection()
        self._clear_board_selection()
        self._refresh_view()

        if phase_before_move == "配置":
            if self._position.get_phase() == "対局":
                self._set_status(
                    f"{dropped_piece} を {square} に配置しました。配置フェーズが終了し、対局フェーズに移行しました。"
                )
            else:
                self._set_status(f"{dropped_piece} を {square} に配置しました。")
            return

        next_side = self._position.get_side_to_move()
        next_side_text = self._side_text(next_side)

        if self._position.is_checkmate(next_side):
            winner = self._side_text(side_before_move)
            self._set_status(f"{move.to_usi()} を打ちました。{next_side_text}は詰みです。{winner}の勝ちです。")
            return

        if self._position.is_in_check(next_side):
            self._set_status(f"{move.to_usi()} を打ちました。{next_side_text}に王手です。")
            return

        self._set_status(f"{move.to_usi()} を打ちました。")

    def _make_drop_move(self, piece: str, square: str) -> Move:
        if hasattr(Move, "make_drop"):
            return Move.make_drop(piece, square)

        # プロジェクト内のMove実装差分にある程度耐えるため複数パターンを試す
        try:
            return Move(drop_piece=piece, to_square=square)
        except TypeError:
            pass

        try:
            return Move(from_square=None, to_square=square, drop_piece=piece)
        except TypeError:
            pass

        try:
            return Move(None, square, False, piece)
        except TypeError:
            pass

        # ここまで来た場合はMoveの定義に合わせて調整が必要
        raise TypeError("Move の drop 生成方法が分かりません。Move クラスを確認してください。")

    def _fallback_legal_drop_squares(self, side: str, piece: str) -> list[str]:
        board = self._position.get_board()
        empty_squares = [square for square, value in board.items() if value is None]

        if self._position.get_phase() != "配置":
            return empty_squares

        own_rank = "f" if side == "black" else "a"
        return [square for square in empty_squares if square.endswith(own_rank)]

    # =========================
    # 対局フェーズ（盤上の駒移動）
    # =========================

    def _handle_battle_click(self, square: str) -> None:
        piece = self._position.get_piece_at(square)
        current_side = self._position.get_side_to_move()

        if self._selected_square is None:
            if piece is None:
                self._set_status("駒のあるマスを選んでください。")
                return

            if not self._is_own_piece(piece, current_side):
                self._set_status("自分の駒を選んでください。")
                return

            self._select_board_square(square)
            return

        if square == self._selected_square:
            self._clear_selection_only()
            self._set_status("選択を解除しました。")
            return

        if piece is not None and self._is_own_piece(piece, current_side):
            self._select_board_square(square)
            return

        result = self._resolve_move_choice(self._selected_square, square)
        if result is None:
            self._set_status("そのマスには移動できません。")
            return

        if isinstance(result, Move):
            self._execute_battle_move(result)
            return

        normal_move, promote_move = result
        self._pending_promotion_moves = {
            False: normal_move,
            True: promote_move,
        }
        self._pending_promotion_square = square

        if isinstance(result, Move):
            self._execute_battle_move(result)
            return

        normal_move, promote_move = result
        self._start_promotion_choice(square, normal_move, promote_move)


    def _start_promotion_choice(
        self,
        square: str,
        normal_move: Move,
        promote_move: Move,
    ) -> None:
        self._pending_promotion_moves = {
            False: normal_move,
            True: promote_move,
        }
        self._pending_promotion_square = square

        if self._promotion_request_callback is not None:
            self._promotion_request_callback(square)

        self._set_status(f"{square} で成るか不成かを選んでください。")

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

    def _execute_battle_move(self, move: Move) -> None:
        moving_side = self._position.get_side_to_move()

        if not self._position.do_move(move):
            self._set_status("着手に失敗しました。")
            return

        if self._move_list_widget is not None and hasattr(self._move_list_widget, "add_move"):
            self._move_list_widget.add_move(moving_side, move.to_usi())

        self._selected_square = None
        self._selected_hand_side = None
        self._selected_hand_piece = None
        self._notify_hand_selection()
        self._clear_board_selection()
        self._refresh_view()

        next_side = self._position.get_side_to_move()
        next_side_text = self._side_text(next_side)

        move_text = f"{move.to_usi()} で成りました。" if move.promote else f"{move.to_usi()} を指しました。"

        if self._position.is_checkmate(next_side):
            winner = self._side_text(moving_side)
            self._set_status(f"{move_text} {next_side_text}は詰みです。{winner}の勝ちです。")
            return

        if self._position.is_in_check(next_side):
            self._set_status(f"{move_text} {next_side_text}に王手です。")
            return

        self._set_status(move_text)

    # =========================
    # 選択・表示
    # =========================

    def _select_board_square(self, square: str) -> None:
        self._selected_square = square
        self._selected_hand_side = None
        self._selected_hand_piece = None
        self._notify_hand_selection()

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

    def _set_drop_highlights(self, side: str, piece: str) -> None:
        if hasattr(rules, "get_legal_drop_squares"):
            legal_squares = rules.get_legal_drop_squares(self._position, piece, side)
        else:
            legal_squares = self._fallback_legal_drop_squares(side, piece)

        if hasattr(self._board_widget, "set_selected_square"):
            self._board_widget.set_selected_square(None)

        if hasattr(self._board_widget, "set_legal_target_squares"):
            self._board_widget.set_legal_target_squares(legal_squares)
        elif hasattr(self._board_widget, "set_highlight_squares"):
            self._board_widget.set_highlight_squares(legal_squares)

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
            turn_text = self._side_text(self._position.get_side_to_move())
            self._turn_callback(f"手番: {turn_text}")

        if self._phase_callback is not None:
            self._phase_callback(f"フェーズ: {self._position.get_phase()}")

        self._notify_hands()

    # =========================
    # 持ち駒データ取得
    # =========================

    def _notify_hands(self) -> None:
        if self._hands_callback is None:
            return

        self._hands_callback(self._get_all_hands())

    def _get_all_hands(self) -> dict[str, dict[str, int]]:
        """Position 側の実装差分に耐えるため、複数の持ち駒データ名を試す。"""

        if hasattr(self._position, "get_hands"):
            hands = self._position.get_hands()
            return self._normalize_all_hands(hands)

        # 例: position.hands = {"black": {...}, "white": {...}}
        for attr_name in ("hands", "_hands"):
            if hasattr(self._position, attr_name):
                hands = getattr(self._position, attr_name)
                return self._normalize_all_hands(hands)

        # 例: position.black_hands / position.white_hands
        black = None
        white = None

        for attr_name in ("black_hands", "black_hand", "_black_hands", "_black_hand"):
            if hasattr(self._position, attr_name):
                black = getattr(self._position, attr_name)
                break

        for attr_name in ("white_hands", "white_hand", "_white_hands", "_white_hand"):
            if hasattr(self._position, attr_name):
                white = getattr(self._position, attr_name)
                break

        return {
            "black": self._normalize_one_hand(black or {}),
            "white": self._normalize_one_hand(white or {}),
        }

    def _get_hand_count(self, side: str, piece: str) -> int:
        if hasattr(self._position, "get_hand_count"):
            return int(self._position.get_hand_count(side, piece))

        return self._get_all_hands().get(side, {}).get(piece, 0)

    def _normalize_all_hands(self, hands) -> dict[str, dict[str, int]]:
        if not isinstance(hands, dict):
            return {"black": {}, "white": {}}

        # {"black": {...}, "white": {...}} 形式
        if "black" in hands or "white" in hands:
            return {
                "black": self._normalize_one_hand(hands.get("black", {})),
                "white": self._normalize_one_hand(hands.get("white", {})),
            }

        # 念のため {"b": {...}, "w": {...}} 形式
        if "b" in hands or "w" in hands:
            return {
                "black": self._normalize_one_hand(hands.get("b", {})),
                "white": self._normalize_one_hand(hands.get("w", {})),
            }

        return {"black": {}, "white": {}}

    def _normalize_one_hand(self, hand) -> dict[str, int]:
        if not isinstance(hand, dict):
            return {}

        result: dict[str, int] = {}

        for piece, count in hand.items():
            try:
                count_int = int(count)
            except (TypeError, ValueError):
                continue

            if count_int <= 0:
                continue

            result[self._normalize_piece_name(str(piece))] = count_int

        return result

    @staticmethod
    def _normalize_piece_name(piece: str) -> str:
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

    def _notify_hand_selection(self) -> None:
        if self._hand_selection_callback is not None:
            self._hand_selection_callback(self._selected_hand_side, self._selected_hand_piece)

    def _set_status(self, text: str) -> None:
        if self._status_callback is not None:
            self._status_callback(text)

    def _clear_pending_promotion(self) -> None:
        self._pending_promotion_moves = None
        self._pending_promotion_square = None

        if self._promotion_clear_callback is not None:
            self._promotion_clear_callback()

    def _is_own_piece(self, piece: str, side: str) -> bool:
        if hasattr(rules, "get_piece_side"):
            return rules.get_piece_side(piece) == side

        if len(piece) >= 2 and piece[0] in {"b", "w"}:
            piece_side = "black" if piece[0] == "b" else "white"
            return piece_side == side

        body = piece[1:] if piece.startswith("+") else piece
        piece_side = "black" if body.isupper() else "white"
        return piece_side == side

    def _connect_board_signal(self) -> None:
        if hasattr(self._board_widget, "square_clicked"):
            self._board_widget.square_clicked.connect(self.handle_square_clicked)

    @staticmethod
    def _side_text(side: str) -> str:
        return "先手" if side == "black" else "後手"

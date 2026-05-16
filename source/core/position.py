from __future__ import annotations

from copy import deepcopy

from source.core import rules
from source.core.move import Move


class Position:
    """局面データと基本操作を管理する。"""

    def __init__(self) -> None:
        self.board: dict[str, str | None] = self.create_empty_board()
        self.side_to_move: str = "black"
        self.phase: str = "配置"
        self.move_history: list[Move] = []
        self.hands: dict[str, dict[str, int]] = {
            "black": {},
            "white": {},
        }
        self._undo_stack: list[
            tuple[
                dict[str, str | None],
                str,
                str,
                list[Move],
                dict[str, dict[str, int]],
            ]
        ] = []

        self.new_game()

    @staticmethod
    def create_empty_board() -> dict[str, str | None]:
        board: dict[str, str | None] = {}
        for file_num in "654321":
            for rank_char in "abcdef":
                board[f"{file_num}{rank_char}"] = None
        return board

    def new_game(self) -> None:
        """新規対局を配置フェーズから開始する。

        初期盤面は歩兵のみ配置済み。
        玉・金・銀・桂・香・飛・角は持ち駒として駒台に表示する。
        飛車/角は配置フェーズ中だけ排他扱いにする。
        """
        self.board = self.create_empty_board()

        self.board.update(
            {
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
            }
        )

        self.hands = {
            "black": {
                "K": 1,
                "G": 1,
                "S": 1,
                "N": 1,
                "L": 1,
                "R": 1,
                "B": 1,
            },
            "white": {
                "K": 1,
                "G": 1,
                "S": 1,
                "N": 1,
                "L": 1,
                "R": 1,
                "B": 1,
            },
        }

        self.side_to_move = "black"
        self.phase = "配置"
        self.move_history.clear()
        self._undo_stack.clear()

    def get_piece_at(self, square: str) -> str | None:
        return self.board.get(square)

    def set_piece_at(self, square: str, piece: str | None) -> None:
        self.board[square] = piece

    def get_board(self) -> dict[str, str | None]:
        return self.board.copy()

    def get_hands(self) -> dict[str, dict[str, int]]:
        return {
            "black": self.hands["black"].copy(),
            "white": self.hands["white"].copy(),
        }

    def get_hand_count(self, side: str, piece: str) -> int:
        base_piece = self._piece_to_hand_piece(piece)
        return self.hands.get(side, {}).get(base_piece, 0)

    def get_side_to_move(self) -> str:
        return self.side_to_move

    def get_phase(self) -> str:
        return self.phase

    def get_move_history(self) -> list[Move]:
        return self.move_history.copy()

    def get_legal_moves_from(self, square: str) -> list[Move]:
        if self.phase == "配置":
            return []
        return rules.generate_legal_moves_from(self, square)

    def get_all_legal_moves(self, side: str | None = None) -> list[Move]:
        if self.phase == "配置":
            return []
        return rules.get_all_legal_moves(self, side)

    def is_legal_move(self, move: Move) -> bool:
        if self._is_drop_move(move):
            return self._is_legal_drop_move(move)

        from_square = getattr(move, "from_square", None)
        if from_square is None:
            return False

        if self.phase == "配置":
            return False

        legal_moves = self.get_legal_moves_from(from_square)
        return move in legal_moves

    def do_move(self, move: Move) -> bool:
        if not self.is_legal_move(move):
            return False

        self._push_undo_state()

        if self._is_drop_move(move):
            return self._do_drop_move(move)

        return self._do_board_move(move)

    def undo_move(self) -> bool:
        if not self._undo_stack:
            return False

        board, side_to_move, phase, move_history, hands = self._undo_stack.pop()
        self.board = board
        self.side_to_move = side_to_move
        self.phase = phase
        self.move_history = move_history
        self.hands = hands
        return True

    def is_in_check(self, side: str | None = None) -> bool:
        if self.phase == "配置":
            return False

        target_side = self.side_to_move if side is None else side
        return rules.is_in_check(self, target_side)

    def is_checkmate(self, side: str | None = None) -> bool:
        if self.phase == "配置":
            return False

        target_side = self.side_to_move if side is None else side
        return rules.is_checkmate(self, target_side)

    def has_any_legal_moves(self, side: str | None = None) -> bool:
        return len(self.get_all_legal_moves(side)) > 0

    def is_game_over(self) -> bool:
        return self.is_checkmate(self.side_to_move)

    def get_game_result(self) -> str | None:
        if self.is_checkmate("black"):
            return "white"
        if self.is_checkmate("white"):
            return "black"

        if self.phase != "配置":
            # 将来的に持将棋や千日手等を扱うならここを拡張
            if not self.has_any_legal_moves("black") or not self.has_any_legal_moves("white"):
                return "draw"

        return None

    # =========================
    # 内部処理: 通常の指し手
    # =========================

    def _do_board_move(self, move: Move) -> bool:
        from_square = getattr(move, "from_square", None)
        to_square = getattr(move, "to_square", None)

        if from_square is None or to_square is None:
            return False

        piece = self.get_piece_at(from_square)
        if piece is None:
            return False

        captured_piece = self.get_piece_at(to_square)

        self.set_piece_at(from_square, None)

        promote = bool(getattr(move, "promote", False))
        moved_piece = rules.promote_piece(piece) if promote else piece
        self.set_piece_at(to_square, moved_piece)

        if captured_piece is not None:
            captured_hand_piece = self._piece_to_hand_piece(captured_piece)
            self._add_hand_piece(self.side_to_move, captured_hand_piece)

        self.move_history.append(move)
        self._change_turn()
        return True

    # =========================
    # 内部処理: 持ち駒の配置/打ち駒
    # =========================

    def _do_drop_move(self, move: Move) -> bool:
        side = self.side_to_move
        phase_before_move = self.phase
        to_square = getattr(move, "to_square", None)
        drop_piece = self._get_drop_piece(move)

        if to_square is None or drop_piece is None:
            return False

        hand_piece = self._piece_to_hand_piece(drop_piece)

        if not self._remove_hand_piece(side, hand_piece):
            return False

        board_piece = self._hand_piece_to_board_piece(hand_piece, side)
        self.set_piece_at(to_square, board_piece)

        if phase_before_move == "配置":
            self._apply_initial_big_piece_exclusion(side, hand_piece)

        self.move_history.append(move)
        self._change_turn()

        if phase_before_move == "配置" and self._is_placement_finished():
            self.phase = "対局"

        return True

    def _is_legal_drop_move(self, move: Move) -> bool:
        side = self.side_to_move
        to_square = getattr(move, "to_square", None)
        drop_piece = self._get_drop_piece(move)

        if to_square is None or drop_piece is None:
            return False

        if to_square not in self.board:
            return False

        if self.get_piece_at(to_square) is not None:
            return False

        hand_piece = self._piece_to_hand_piece(drop_piece)
        if self.get_hand_count(side, hand_piece) <= 0:
            return False

        if self.phase == "配置":
            return self._is_legal_placement_square(side, to_square)

        # rules.py側に詳細な打ち駒判定がある場合はそれを使う
        if hasattr(rules, "get_drop_error_message"):
            return rules.get_drop_error_message(self, move, side) is None

        if hasattr(rules, "get_legal_drop_squares"):
            return to_square in rules.get_legal_drop_squares(self, hand_piece, side)

        return True

    def _is_legal_placement_square(self, side: str, square: str) -> bool:
        if self.get_piece_at(square) is not None:
            return False

        own_rank = "f" if side == "black" else "a"
        return square.endswith(own_rank)

    def _apply_initial_big_piece_exclusion(self, side: str, placed_piece: str) -> None:
        """配置フェーズ中だけ飛車/角の排他ルールを適用する。"""
        if placed_piece == "R":
            self.hands[side].pop("B", None)
        elif placed_piece == "B":
            self.hands[side].pop("R", None)

    def _is_placement_finished(self) -> bool:
        return (
            not self._has_any_hand_piece("black")
            and not self._has_any_hand_piece("white")
        )

    def _has_any_hand_piece(self, side: str) -> bool:
        return any(count > 0 for count in self.hands.get(side, {}).values())

    # =========================
    # 持ち駒操作
    # =========================

    def _add_hand_piece(self, side: str, piece: str) -> None:
        hand_piece = self._piece_to_hand_piece(piece)
        self.hands.setdefault(side, {})
        self.hands[side][hand_piece] = self.hands[side].get(hand_piece, 0) + 1

    def _remove_hand_piece(self, side: str, piece: str) -> bool:
        hand_piece = self._piece_to_hand_piece(piece)
        current_count = self.hands.get(side, {}).get(hand_piece, 0)

        if current_count <= 0:
            return False

        if current_count == 1:
            self.hands[side].pop(hand_piece, None)
        else:
            self.hands[side][hand_piece] = current_count - 1

        return True

    # =========================
    # 表現変換
    # =========================

    @staticmethod
    def _is_drop_move(move: Move) -> bool:
        return bool(getattr(move, "is_drop", False)) or getattr(move, "drop_piece", None) is not None

    @staticmethod
    def _get_drop_piece(move: Move) -> str | None:
        drop_piece = getattr(move, "drop_piece", None)
        if drop_piece is not None:
            return str(drop_piece)

        # Move実装によっては piece_type / piece などの名前かもしれないので一応見る
        for attr_name in ("piece_type", "piece"):
            value = getattr(move, attr_name, None)
            if value is not None and getattr(move, "from_square", None) is None:
                return str(value)

        return None

    @classmethod
    def _piece_to_hand_piece(cls, piece: str) -> str:
        """盤上/持ち駒の表現から、持ち駒用の基本駒へ変換する。

        捕獲時は成りを解除し、先後情報を落とす。
        """
        _, base_piece, _ = cls._split_piece(piece)
        return base_piece

    @classmethod
    def _hand_piece_to_board_piece(cls, piece: str, side: str) -> str:
        base_piece = cls._piece_to_hand_piece(piece)

        if side == "black":
            return base_piece
        return base_piece.lower()

    @staticmethod
    def _split_piece(piece: str) -> tuple[str, str, bool]:
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

    def _change_turn(self) -> None:
        self.side_to_move = "white" if self.side_to_move == "black" else "black"

    def _push_undo_state(self) -> None:
        self._undo_stack.append(
            (
                deepcopy(self.board),
                self.side_to_move,
                self.phase,
                self.move_history.copy(),
                deepcopy(self.hands),
            )
        )

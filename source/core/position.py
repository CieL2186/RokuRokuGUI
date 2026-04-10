from __future__ import annotations

from copy import deepcopy

from source.core import rules
from source.core.move import Move


class Position:
    """局面データと基本操作を管理する。"""

    def __init__(self) -> None:
        self.board: dict[str, str | None] = self.create_empty_board()
        self.side_to_move: str = "black"
        self.phase: str = "対局"
        self.move_history: list[Move] = []
        self._undo_stack: list[tuple[dict[str, str | None], str, str, list[Move]]] = []

        self.new_game()

    @staticmethod
    def create_empty_board() -> dict[str, str | None]:
        board: dict[str, str | None] = {}
        for file_num in "654321":
            for rank_char in "abcdef":
                board[f"{file_num}{rank_char}"] = None
        return board

    def new_game(self) -> None:
        self.board = self.create_empty_board()

        self.board.update(
            {
                "6a": "r",
                "5a": "b",
                "4a": "g",
                "3a": "s",
                "2a": "n",
                "1a": "k",
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
                "6f": "R",
                "5f": "B",
                "4f": "G",
                "3f": "S",
                "2f": "N",
                "1f": "K",
            }
        )

        self.side_to_move = "black"
        self.phase = "対局"
        self.move_history.clear()
        self._undo_stack.clear()

    def get_piece_at(self, square: str) -> str | None:
        return self.board.get(square)

    def set_piece_at(self, square: str, piece: str | None) -> None:
        self.board[square] = piece

    def get_board(self) -> dict[str, str | None]:
        return self.board.copy()

    def get_side_to_move(self) -> str:
        return self.side_to_move

    def get_phase(self) -> str:
        return self.phase

    def get_move_history(self) -> list[Move]:
        return self.move_history.copy()

    def get_legal_moves_from(self, square: str) -> list[Move]:
        return rules.generate_legal_moves_from(self, square)

    def get_all_legal_moves(self) -> list[Move]:
        return rules.get_all_legal_moves(self)

    def is_legal_move(self, move: Move) -> bool:
        if move.is_drop:
            return False
        if move.from_square is None:
            return False

        legal_moves = self.get_legal_moves_from(move.from_square)
        return move in legal_moves

    def do_move(self, move: Move) -> bool:
        if not self.is_legal_move(move):
            return False

        if move.from_square is None:
            return False

        self._push_undo_state()

        piece = self.get_piece_at(move.from_square)
        if piece is None:
            return False

        self.set_piece_at(move.from_square, None)

        moved_piece = rules.promote_piece(piece) if move.promote else piece
        self.set_piece_at(move.to_square, moved_piece)

        self.move_history.append(move)
        self.side_to_move = "white" if self.side_to_move == "black" else "black"
        return True

    def undo_move(self) -> bool:
        if not self._undo_stack:
            return False

        board, side_to_move, phase, move_history = self._undo_stack.pop()
        self.board = board
        self.side_to_move = side_to_move
        self.phase = phase
        self.move_history = move_history
        return True

    def is_game_over(self) -> bool:
        black_king_exists = any(piece == "K" or piece == "bK" for piece in self.board.values())
        white_king_exists = any(piece == "k" or piece == "wK" for piece in self.board.values())
        return not black_king_exists or not white_king_exists

    def get_game_result(self) -> str | None:
        black_king_exists = any(piece == "K" or piece == "bK" for piece in self.board.values())
        white_king_exists = any(piece == "k" or piece == "wK" for piece in self.board.values())

        if black_king_exists and white_king_exists:
            return None
        if black_king_exists:
            return "black"
        if white_king_exists:
            return "white"
        return "draw"

    def _push_undo_state(self) -> None:
        self._undo_stack.append(
            (
                deepcopy(self.board),
                self.side_to_move,
                self.phase,
                self.move_history.copy(),
            )
        )

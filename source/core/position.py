from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from source.core.move import Move
from source.core import rules


@dataclass(slots=True)
class _Snapshot:
    board: dict[str, str | None]
    side_to_move: int
    phase: str
    move_history: list[Move]


class Position:
    """66将棋GUI の controller 動作確認用の最小 Position。"""

    def __init__(self) -> None:
        self.board: dict[str, str | None] = {}
        self.side_to_move: int = rules.BLACK
        self.phase: str = "対局"
        self.move_history: list[Move] = []
        self._snapshots: list[_Snapshot] = []
        self.new_game()

    def new_game(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.board = self._create_demo_battle_board()
        self.side_to_move = rules.BLACK
        self.phase = "対局"
        self.move_history = []
        self._snapshots = []

    def get_board(self) -> dict[str, str | None]:
        return dict(self.board)

    def get_side_to_move(self) -> int:
        return self.side_to_move

    def get_phase(self) -> str:
        return self.phase

    def get_piece_at(self, square: str) -> str | None:
        return self.board.get(square)

    def get_legal_moves_from(self, square: str) -> list[Move]:
        return list(rules.get_legal_moves_from(self, square))

    def get_all_legal_moves(self) -> list[Move]:
        return list(rules.get_all_legal_moves(self))

    def do_move(self, move: Move) -> bool:
        if not rules.is_legal_move(self, move):
            return False

        self._snapshots.append(
            _Snapshot(
                board=deepcopy(self.board),
                side_to_move=self.side_to_move,
                phase=self.phase,
                move_history=list(self.move_history),
            )
        )
        return rules.do_move(self, move)

    def undo_move(self) -> bool:
        if not self._snapshots:
            return False

        snap = self._snapshots.pop()
        self.board = snap.board
        self.side_to_move = snap.side_to_move
        self.phase = snap.phase
        self.move_history = snap.move_history
        return True

    def get_move_history(self) -> list[Move]:
        return list(self.move_history)

    def is_game_over(self) -> bool:
        return rules.is_game_over(self)

    def get_game_result(self) -> str:
        return rules.get_game_result(self)

    def set_board(
        self,
        board: dict[str, str | None],
        *,
        side_to_move: int = rules.BLACK,
        phase: str = "対局",
    ) -> None:
        self.board = dict(board)
        self.side_to_move = side_to_move
        self.phase = phase
        self.move_history = []
        self._snapshots = []

    @staticmethod
    def _create_demo_battle_board() -> dict[str, str | None]:
        board = {f"{file_}{rank}": None for file_ in "654321" for rank in "abcdef"}
        board.update(
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
        return board

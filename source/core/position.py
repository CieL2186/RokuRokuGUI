from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Optional

from core.move import Move

try:
    from core import rules
except Exception:  # pragma: no cover
    rules = None


@dataclass(slots=True)
class _Snapshot:
    board: dict[str, str]
    side_to_move: int
    phase: str
    move_history: list[Move]


class Position:
    """66将棋GUI の controller 動作確認用の最小 Position。

    これは GUI / controller / core の配線を先に進めるための仮実装で、
    66将棋の完全ルールはまだ含みません。
    当面は「対局フェーズだけを簡易に試す」用途を想定しています。
    """

    def __init__(self) -> None:
        self.board: dict[str, str] = {}
        self.side_to_move: int = 0
        self.phase: str = "対局"
        self.move_history: list[Move] = []
        self._snapshots: list[_Snapshot] = []
        self.new_game()

    def new_game(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.board = self._create_demo_battle_board()
        self.side_to_move = 0
        self.phase = "対局"
        self.move_history = []
        self._snapshots = []

    def get_board(self) -> dict[str, str]:
        return self.board

    def get_side_to_move(self) -> int:
        return self.side_to_move

    def get_phase(self) -> str:
        return self.phase

    def get_piece_at(self, square: str) -> Optional[str]:
        return self.board.get(square)

    def get_legal_moves_from(self, square: str) -> list[Move]:
        if rules is None:
            return []
        return list(rules.get_legal_moves_from(self, square))

    def get_all_legal_moves(self) -> list[Move]:
        if rules is None:
            return []
        return list(rules.get_all_legal_moves(self))

    def do_move(self, move: Move) -> bool:
        if rules is None:
            return False

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
        return bool(rules.do_move(self, move))

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
        if rules is None:
            return False
        return bool(rules.is_game_over(self))

    def get_game_result(self) -> str:
        if rules is None:
            return "未判定"
        return str(rules.get_game_result(self))

    def set_board(
        self,
        board: dict[str, str],
        *,
        side_to_move: int = 0,
        phase: str = "対局",
    ) -> None:
        self.board = dict(board)
        self.side_to_move = side_to_move
        self.phase = phase
        self.move_history = []
        self._snapshots = []

    @staticmethod
    def _create_demo_battle_board() -> dict[str, str]:
        # 実際の66将棋の初期配置ではなく、GUI/controller 動作確認用の仮盤面。
        return {
            "6f": "bK",
            "5f": "bG",
            "4f": "bS",
            "3f": "bB",
            "2f": "bR",
            "1f": "bP",
            "6e": "bP",
            "5e": "bN",
            "1a": "wK",
            "2a": "wG",
            "3a": "wS",
            "4a": "wB",
            "5a": "wR",
            "6a": "wP",
            "1b": "wP",
            "2b": "wN",
        }

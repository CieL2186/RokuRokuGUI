from __future__ import annotations

from enum import Enum
from collections.abc import Callable

from source.core.move import Move
from source.core.position import Position


class GameState(Enum):
    READY = "ready"
    WAIT_HUMAN = "wait_human"
    WAIT_AI = "wait_ai"
    ENDED = "ended"


class MatchController:
    def __init__(
        self,
        on_position_changed: Callable[[Position], None] | None = None,
        on_move_played: Callable[[str, Move], None] | None = None,
        on_status_changed: Callable[[str], None] | None = None,
        on_game_over: Callable[[str | None], None] | None = None,
    ) -> None:
        self.position = Position()
        self.state = GameState.READY

        self.black_player = None
        self.white_player = None

        self.on_position_changed = on_position_changed
        self.on_move_played = on_move_played
        self.on_status_changed = on_status_changed
        self.on_game_over = on_game_over

    def setup_players(self, black_player, white_player) -> None:
        self.black_player = black_player
        self.white_player = white_player

        self.black_player.set_match_controller(self)
        self.white_player.set_match_controller(self)

    def new_game(self, position: Position | None = None) -> None:
        self.position = position if position is not None else Position()
        self.state = GameState.READY
        self._notify_position()
        self._set_status("新規対局を開始しました。")
        self.start_current_turn()

    def current_side(self) -> str:
        return self.position.get_side_to_move()

    def current_player(self):
        return self.black_player if self.current_side() == "black" else self.white_player

    def start_current_turn(self) -> None:
        if self.position.is_game_over():
            self._finish_game()
            return

        player = self.current_player()
        if player is None:
            self._set_status("プレイヤーが設定されていません。")
            return

        if player.is_human:
            self.state = GameState.WAIT_HUMAN
            player.start_turn(self.position)
        else:
            self.state = GameState.WAIT_AI
            player.start_turn(self.position)

    def submit_move(self, move: Move) -> bool:
        if self.state == GameState.ENDED:
            return False

        moving_side = self.current_side()

        if not self.position.do_move(move):
            self._set_status("不正な手です。")
            return False

        if self.on_move_played is not None:
            self.on_move_played(moving_side, move)

        self._notify_position()

        next_side = self.current_side()

        if self.position.is_checkmate(next_side):
            self._finish_game()
            return True

        self.start_current_turn()
        return True

    def undo_move(self) -> bool:
        if self.state == GameState.WAIT_AI:
            self._set_status("AI思考中は待ったできません。")
            return False

        if not self.position.undo_move():
            self._set_status("これ以上戻せません。")
            return False

        self._notify_position()
        self._set_status("1手戻しました。")
        self.start_current_turn()
        return True

    def get_position_command(self) -> str:
        history = self.position.get_move_history()
        if not history:
            return "position startpos"

        moves = " ".join(move.to_usi() for move in history)
        return f"position startpos moves {moves}"

    def set_status(self, text: str) -> None:
        self._set_status(text)

    def _finish_game(self) -> None:
        self.state = GameState.ENDED
        result = self.position.get_game_result()

        if result == "black":
            message = "先手の勝ちです。"
        elif result == "white":
            message = "後手の勝ちです。"
        elif result == "draw":
            message = "引き分けです。"
        else:
            message = "対局終了です。"

        self._set_status(message)

        if self.on_game_over is not None:
            self.on_game_over(result)

    def _notify_position(self) -> None:
        if self.on_position_changed is not None:
            self.on_position_changed(self.position)

    def _set_status(self, text: str) -> None:
        if self.on_status_changed is not None:
            self.on_status_changed(text)
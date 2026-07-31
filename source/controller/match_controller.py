from __future__ import annotations

from enum import Enum
from collections.abc import Callable

from source.core.move import Move
from source.core.position import Position
from source.controller.match_clock import MatchClock


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
        self.match_clock: MatchClock | None = None
        self.game_state = "waiting"

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
        self.game_state = "playing"

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

        side = self.position.get_side_to_move()

        if self.match_clock is not None:
            self.match_clock.start_turn(side)

        if player.is_human:
            self.state = GameState.WAIT_HUMAN
        else:
            self.state = GameState.WAIT_AI

        player.start_turn(self.position)

    def submit_move(self, move: Move) -> bool:
        if self.game_state == "ended":
            return

        if self.position is None:
            return

        if self.check_timeout():
            return

        moving_side = self.current_side()

        if not self.position.do_move(move):
            self._set_status("不正な手です。")
            return False

        if self.match_clock is not None:
            clock_result = self.match_clock.finish_turn(moving_side)

            if clock_result.timed_out:
                winner = "white" if moving_side == "black" else "black"

                if self.on_move_played is not None:
                    self.on_move_played(moving_side, move)

                self._notify_position()

                self.state = GameState.ENDED
                self._set_status(
                    f"{self._side_label(moving_side)} 時間切れ。"
                    f"{self._side_label(winner)} の勝ちです。"
                )
                return True

        if self.on_move_played is not None:
            self.on_move_played(moving_side, move)

        self._notify_position()

        next_side = self.current_side()

        if self.position.is_checkmate(next_side):
            self._finish_game()
            return True

        self.start_current_turn()
        return True
    
    def _side_label(self, side: str) -> str:
        return "先手" if side == "black" else "後手"
        
    def undo_move(self) -> bool:
        return self.undo_moves(1) > 0


    def undo_moves(self, count: int) -> int:
        if self.state == GameState.WAIT_AI:
            self._set_status("AI思考中は待ったできません。")
            return 0

        if count <= 0:
            return 0

        if self.match_clock is not None:
            self.match_clock.stop_current_turn()

        undone_count = 0

        for _ in range(count):
            if not self.position.undo_move():
                break

            undone_count += 1

        if undone_count <= 0:
            self._set_status("これ以上戻せません。")
            return 0

        self.game_state = "playing"
        self.state = GameState.READY

        self._notify_position()

        if undone_count == 1:
            self._set_status("1手戻しました。")
        else:
            self._set_status(f"{undone_count}手戻しました。")

        self.start_current_turn()
        return undone_count

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

    def set_match_clock(self, match_clock: MatchClock | None) -> None:
        self.match_clock = match_clock

    def is_ended(self) -> bool:
        return self.game_state == "ended"

    def check_timeout(self) -> bool:
        if self.position is None:
            return False

        if self.game_state == "ended":
            return False

        if self.match_clock is None:
            return False

        if not self.match_clock.is_current_turn_timeout():
            return False

        loser = self.match_clock.current_side or self.position.side_to_move
        winner = "white" if loser == "black" else "black"

        self.match_clock.stop_current_turn()
        self.game_state = "ended"

        self.set_status(
            f"{self._side_label(loser)} 時間切れ。"
            f"{self._side_label(winner)} の勝ちです。"
        )

        return True

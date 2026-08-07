from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Signal

from source.core import rules
from source.core.move import Move
from source.core.position import Position
from source.controller.match_controller import MatchController
from source.controller.match_clock import MatchClock
from source.engine.usi_process import USIProcess
from source.engine.usi_parser import USIParser
from source.core.kif_write import KifuWriter


class GameController:
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
        debug_log_callback: Callable[[str], None] | None = None,
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
        self._debug_log_callback = debug_log_callback
        self._match_settings: dict[str, object] = {}
        self.match_clock: MatchClock | None = None
        self.kifu_writer = KifuWriter()

        self.match_controller = MatchController(
            on_position_changed=self._refresh_view,
            on_move_played=self._add_move_to_list,
            on_status_changed=self._set_status,
            on_game_over=self._on_game_over,
        )

        self.black_player = HumanPlayer("black", self)
        self.white_player = HumanPlayer("white", self)

        self.match_controller.setup_players(
            self.black_player,
            self.white_player,
        )

        self._connect_board_signal()
        self.new_game()

    @property
    def position(self) -> Position:
        return self.match_controller.position

    def new_game(self, position: Position | None = None) -> None:
        self.clear_human_selection()

        if self._move_list_widget is not None and hasattr(self._move_list_widget, "clear_moves"):
            self._move_list_widget.clear_moves()

        self.match_controller.new_game(position)

    def new_game_from_settings(self, settings: dict[str, object]) -> None:
        self._match_settings = settings
        self.match_clock = MatchClock(settings)
        self.match_controller.set_match_clock(self.match_clock)

        #self._debug_log(f"[settings] {settings}")
        #self._debug_log(f"[go option built] {self._go_option}")

        self.black_player = self._create_player(
            side="black",
            player_type=str(settings["black_player"]),
            engine_path=str(settings.get("black_engine_path", "")),
        )

        self.white_player = self._create_player(
            side="white",
            player_type=str(settings["white_player"]),
            engine_path=str(settings.get("white_engine_path", "")),
        )

        self.match_controller.setup_players(
            self.black_player,
            self.white_player,
        )
        self.new_game()

    def _on_game_over(self, result: str | None) -> None:
            try:
                path = self.kifu_writer.save_txt(
                    position=self.position,
                    result=result,
                    settings=self._match_settings,
                )
                self._set_status(f"対局終了。棋譜を保存しました: {path}")
            except Exception as exc:
                self._set_status(f"対局終了。棋譜保存に失敗しました: {exc}")

    def _create_player(self, side: str, player_type: str, engine_path: str):
        if player_type == "AI":
            return AIPlayer(
                side=side,
                engine_path=engine_path,
                debug_log_callback=self._debug_log,
                go_option_provider=self._get_go_option,
            )

        return HumanPlayer(side, self)

    def handle_square_clicked(self, square: str) -> None:
        if self.match_controller.is_ended():
            return
        
        player = self.match_controller.current_player()

        if player is None or not player.is_human:
            return

        player.handle_square_clicked(square)

    def select_hand_piece(self, side_or_piece: str, piece: str | None = None) -> None:
        player = self.match_controller.current_player()

        if player is None or not player.is_human:
            return

        player.select_hand_piece(side_or_piece, piece)

    def handle_promotion_choice(self, promote: bool) -> None:
        player = self.match_controller.current_player()

        if player is None or not player.is_human:
            self._clear_promotion_ui()
            return

        player.handle_promotion_choice(promote)

    def cancel_promotion_choice(self) -> None:
        player = self.match_controller.current_player()

        if player is None or not player.is_human:
            return

        player.cancel_promotion_choice()

    def undo_move(self) -> None:
        self.clear_human_selection()

        undo_count = 2 if self._is_human_vs_ai() else 1

        history = self.position.get_move_history()

        if self._is_human_vs_ai() and len(history) < 2:
            self._set_status("戻せる自分の手がまだありません。")
            return

        undone_count = self.match_controller.undo_moves(undo_count)

        if undone_count <= 0:
            return

        self._rebuild_move_list()

    def submit_human_move(self, move: Move) -> bool:
        return self.match_controller.submit_move(move)

    def clear_human_selection(self) -> None:
        for player in (self.black_player, self.white_player):
            if hasattr(player, "clear_selection"):
                player.clear_selection()

        self._clear_board_selection()
        self._notify_hand_selection(None, None)
        self._clear_promotion_ui()

    def _refresh_view(self, position: Position) -> None:
        if hasattr(self._board_widget, "set_board"):
            self._board_widget.set_board(position.get_board())

        if self._turn_callback is not None:
            self._turn_callback(f"手番: {self._side_text(position.get_side_to_move())}")

        if self._phase_callback is not None:
            self._phase_callback(f"フェーズ: {position.get_phase()}")

        if self._hands_callback is not None:
            self._hands_callback(position.get_hands())

    def _add_move_to_list(self, side: str, move: Move) -> None:
        if self._move_list_widget is not None and hasattr(self._move_list_widget, "add_move"):
            self._move_list_widget.add_move(side, move.to_usi())

    def _set_status(self, text: str) -> None:
        if self._status_callback is not None:
            self._status_callback(text)

    def _debug_log(self, text: str) -> None:
        if self._debug_log_callback is not None:
            self._debug_log_callback(text)
        else:
            print(text)

    def _build_go_option(self, settings: dict[str, object]) -> str:
        time_mode = str(settings.get("time_mode", "none"))

        if time_mode == "main_time":
            hour = int(settings.get("main_time_hour", 0))
            minute = int(settings.get("main_time_min", 10))
            byoyomi_sec = int(settings.get("byoyomi_sec", 10))

            main_ms = (hour * 60 + minute) * 60 * 1000
            byoyomi_ms = max(byoyomi_sec * 1000, 0)

            # 持ち時間0分・秒読み0秒だと危ないので最低1秒は渡す
            if main_ms <= 0 and byoyomi_ms <= 0:
                byoyomi_ms = 1000

            return f"btime {main_ms} wtime {main_ms} byoyomi {byoyomi_ms}"

        if time_mode == "byoyomi":
            byoyomi_sec = int(settings.get("byoyomi_sec", 1))
            byoyomi_ms = max(byoyomi_sec * 1000, 1000)

            return f"btime 0 wtime 0 byoyomi {byoyomi_ms}"

        if time_mode == "increment":
            increment_sec = int(settings.get("increment_sec", 1))
            increment_ms = max(increment_sec * 1000, 1000)

            return f"btime 0 wtime 0 binc {increment_ms} winc {increment_ms}"

        # 秒読みも加算もなし
        # 今はAIが無限に考え続けるのを避けるため、仮で1秒思考にする
        return "btime 0 wtime 0 byoyomi 1000"
    
    def _get_go_option(self) -> str:
        if self.match_clock is None:
            return "btime 1000 wtime 1000 byoyomi 1000"

        return self.match_clock.make_go_option()

    def _notify_hand_selection(self, side: str | None, piece: str | None) -> None:
        if self._hand_selection_callback is not None:
            self._hand_selection_callback(side, piece)

    def _request_promotion(self, square: str) -> None:
        if self._promotion_request_callback is not None:
            self._promotion_request_callback(square)

    def _clear_promotion_ui(self) -> None:
        if self._promotion_clear_callback is not None:
            self._promotion_clear_callback()

    def _clear_board_selection(self) -> None:
        if hasattr(self._board_widget, "clear_selection"):
            self._board_widget.clear_selection()

    def _set_board_selection(self, square: str | None, targets: list[str]) -> None:
        if hasattr(self._board_widget, "set_selected_square"):
            self._board_widget.set_selected_square(square)

        if hasattr(self._board_widget, "set_legal_target_squares"):
            self._board_widget.set_legal_target_squares(targets)
        elif hasattr(self._board_widget, "set_highlight_squares"):
            self._board_widget.set_highlight_squares(targets)

    def _connect_board_signal(self) -> None:
        if hasattr(self._board_widget, "square_clicked"):
            self._board_widget.square_clicked.connect(self.handle_square_clicked)

    def get_clock_display_text(self) -> str:
        if self.match_clock is None:
            return "先手: --:-- / 後手: --:--"

        return self.match_clock.display_text()
    
    def is_ended(self) -> bool:
        return self.game_state == "ended"
    
    def check_timeout(self) -> bool:
        timed_out = self.match_controller.check_timeout()

        if timed_out:
            self._clear_board_selection()

        return timed_out
    
    def _is_human_vs_ai(self) -> bool:
        black_is_human = getattr(self.black_player, "is_human", False)
        white_is_human = getattr(self.white_player, "is_human", False)

        return black_is_human != white_is_human

    def _rebuild_move_list(self) -> None:
        if self._move_list_widget is None:
            return

        if not hasattr(self._move_list_widget, "clear_moves"):
            return

        if not hasattr(self._move_list_widget, "add_move"):
            return

        self._move_list_widget.clear_moves()

        side = "black"

        for move in self.position.get_move_history():
            self._move_list_widget.add_move(side, move.to_usi())
            side = "white" if side == "black" else "black"

    @staticmethod
    def _side_text(side: str) -> str:
        return "先手" if side == "black" else "後手"
    
    def cancel_hand_selection(self, side: str | None = None) -> None:
        player = self.match_controller.current_player()
        if player is None or not player.is_human:
            return
        if hasattr(player, "cancel_hand_selection"):
            player.cancel_hand_selection(side)
        
class HumanPlayer:
    def __init__(self, side: str, game_controller: GameController) -> None:
        self.side = side
        self.game_controller = game_controller
        self.match_controller: MatchController | None = None

        self._selected_square: str | None = None
        self._selected_hand_side: str | None = None
        self._selected_hand_piece: str | None = None
        self._pending_promotion_moves: dict[bool, Move] | None = None
        self._pending_promotion_square: str | None = None

    @property
    def is_human(self) -> bool:
        return True

    @property
    def position(self) -> Position:
        return self.match_controller.position

    def set_match_controller(self, controller: MatchController) -> None:
        self.match_controller = controller

    def start_turn(self, position: Position) -> None:
        self.clear_selection()
        self.game_controller._set_status(
            f"{self.game_controller._side_text(self.side)}の手番です。"
        )

    def select_hand_piece(self, side_or_piece: str, piece: str | None = None) -> None:
        if piece is None:
            side = self.position.get_side_to_move()
            piece = side_or_piece
        else:
            side = side_or_piece

        if side != self.position.get_side_to_move():
            self.game_controller._set_status("現在の手番の持ち駒を選んでください。")
            return

        if self.position.get_hand_count(side, piece) <= 0:
            self.game_controller._set_status(f"{piece} は持っていません。")
            return

        self._selected_square = None
        self._selected_hand_side = side
        self._selected_hand_piece = piece

        legal_squares = self._get_legal_drop_squares(side, piece)

        self.game_controller._set_board_selection(None, legal_squares)
        self.game_controller._notify_hand_selection(side, piece)
        self.game_controller._set_status(f"{piece} を選択しました。")

    def handle_square_clicked(self, square: str) -> None:
        if self.match_controller.is_ended():
            return
        
        if self._pending_promotion_moves is not None:
            self._handle_square_clicked_during_promotion(square)
            return

        if self._selected_hand_piece is not None:
            self._handle_drop_click(square)
            return

        if self.position.get_phase() == "配置":
            self.game_controller._set_status("まず持ち駒を選んでください。")
            return

        self._handle_battle_click(square)

    def handle_promotion_choice(self, promote: bool) -> None:
        if self._pending_promotion_moves is None:
            self.game_controller._clear_promotion_ui()
            return

        move = self._pending_promotion_moves[promote]

        self.clear_selection()
        self.game_controller._clear_promotion_ui()
        self.game_controller._clear_board_selection()
        self.game_controller._notify_hand_selection(None, None)

        success = self.game_controller.submit_human_move(move)
        if not success:
            self.game_controller._set_status("成りの手を指せませんでした。")

    def cancel_promotion_choice(self) -> None:
        self._pending_promotion_moves = None
        self._pending_promotion_square = None
        self.game_controller._clear_promotion_ui()

    def clear_selection(self) -> None:
        self._selected_square = None
        self._selected_hand_side = None
        self._selected_hand_piece = None
        self._pending_promotion_moves = None
        self._pending_promotion_square = None

    def _handle_drop_click(self, square: str) -> None:
        if self.match_controller.is_ended():
            return
        
        piece = self._selected_hand_piece
        if piece is None:
            return

        move = Move(
            from_square=None,
            to_square=square,
            promote=False,
            drop_piece=piece,
        )

        if not self.position.is_legal_move(move):
            if hasattr(rules, "get_drop_error_message"):
                side = self.position.get_side_to_move()
                message = rules.get_drop_error_message(self.position, move, side)
                self.game_controller._set_status(message or "そのマスには打てません。")
            else:
                self.game_controller._set_status("そのマスには打てません。")
            return

        self.clear_selection()
        self.game_controller._clear_board_selection()
        self.game_controller._notify_hand_selection(None, None)
        self.game_controller.submit_human_move(move)

    def _handle_battle_click(self, square: str) -> None:
        if self.match_controller.is_ended():
            return
        
        piece = self.position.get_piece_at(square)
        current_side = self.position.get_side_to_move()

        if self._selected_square is None:
            if piece is None:
                self.game_controller._set_status("駒のあるマスを選んでください。")
                return

            if not self._is_own_piece(piece, current_side):
                self.game_controller._set_status("自分の駒を選んでください。")
                return

            self._select_board_square(square)
            return

        if square == self._selected_square:
            self.clear_selection()
            self.game_controller._clear_board_selection()
            return

        if piece is not None and self._is_own_piece(piece, current_side):
            self._select_board_square(square)
            return

        result = self._resolve_move_choice(self._selected_square, square)

        if result is None:
            self.game_controller._set_status("そのマスには移動できません。")
            return

        if isinstance(result, Move):
            self.clear_selection()
            self.game_controller._clear_board_selection()
            self.game_controller.submit_human_move(result)
            return

        normal_move, promote_move = result
        self._pending_promotion_moves = {
            False: normal_move,
            True: promote_move,
        }
        self._pending_promotion_square = square
        self.game_controller._request_promotion(square)

    def _handle_square_clicked_during_promotion(self, square: str) -> None:
        if self.match_controller.is_ended():
            return
        
        self.cancel_promotion_choice()
        self.handle_square_clicked(square)

    def _select_board_square(self, square: str) -> None:
        self._selected_square = square
        self._selected_hand_side = None
        self._selected_hand_piece = None

        legal_moves = self.position.get_legal_moves_from(square)
        targets = []

        for move in legal_moves:
            if move.to_square not in targets:
                targets.append(move.to_square)

        self.game_controller._notify_hand_selection(None, None)
        self.game_controller._set_board_selection(square, targets)

    def _resolve_move_choice(self, from_square: str, to_square: str) -> Move | tuple[Move, Move] | None:
        legal_moves = self.position.get_legal_moves_from(from_square)
        candidates = [move for move in legal_moves if move.to_square == to_square]

        if not candidates:
            return None

        promoted = next((move for move in candidates if move.promote), None)
        normal = next((move for move in candidates if not move.promote), None)

        if promoted is not None and normal is not None:
            return normal, promoted

        return promoted or normal

    def _get_legal_drop_squares(self, side: str, piece: str) -> list[str]:
        board = self.position.get_board()
        empty_squares = [square for square, value in board.items() if value is None]

        if self.position.get_phase() == "配置":
            own_rank = "f" if side == "black" else "a"
            return [square for square in empty_squares if square.endswith(own_rank)]

        return [
            square
            for square in empty_squares
            if self.position.is_legal_move(
                Move(from_square=None, to_square=square, drop_piece=piece)
            )
        ]

    def _is_own_piece(self, piece: str, side: str) -> bool:
        if hasattr(rules, "get_piece_side"):
            return rules.get_piece_side(piece) == side

        body = piece[1:] if piece.startswith("+") else piece
        piece_side = "black" if body.isupper() else "white"
        return piece_side == side
    def cancel_hand_selection(self, side: str | None = None) -> None:
        if side is not None and self._selected_hand_side is not None:
            if side != self._selected_hand_side:
                return

        self._selected_hand_side = None
        self._selected_hand_piece = None

        self.game_controller._clear_board_selection()
        self.game_controller._notify_hand_selection(None, None)
        self.game_controller._set_status("持ち駒の選択を解除しました。")

class AIWorker(QObject):
    move_ready = Signal(object)
    error = Signal(str)
    debug_log = Signal(str)

    def __init__(
        self,
        side: str,
        engine_path: str,
        position_command: str,
        go_option: str,
    ) -> None:
        super().__init__()
        self.side = side
        self.engine_path = engine_path
        self.position_command = position_command
        self.go_option = go_option

    def run(self) -> None:
        process = USIProcess(
            self.engine_path,
            engine_name=self.side,
            log_callback=self.debug_log.emit,
        )

        try:
            process.start()

            parser = USIParser(process)
            parser.initialize()
            parser.send(self.position_command)

            move = parser.go(self.go_option)
            self.move_ready.emit(move)

        except Exception as exc:
            self.debug_log.emit(f"[{self.side}] エラー: {exc}")
            self.error.emit(str(exc))

        finally:
            process.stop()
class AIPlayer(QObject):
    def __init__(
        self,
        side: str,
        engine_path: str,
        debug_log_callback: Callable[[str], None] | None = None,
        go_option_provider: Callable[[], str] | None = None,
    ) -> None:
        super().__init__()
        self.side = side
        self.engine_path = engine_path
        self.debug_log_callback = debug_log_callback
        self.go_option_provider = go_option_provider
        self.match_controller: MatchController | None = None

        self._thread: QThread | None = None
        self._worker: AIWorker | None = None

    @property
    def is_human(self) -> bool:
        return False

    def set_match_controller(self, controller: MatchController) -> None:
        self.match_controller = controller

    def start_turn(self, position: Position) -> None:
        if self.match_controller is None:
            return

        if self._thread is not None:
            self._on_debug_log(f"[{self.side}] すでにAI思考中です。")
            return

        if not self.engine_path:
            self._on_error("AIエンジンのパスが設定されていません。")
            return

        position_command = self.match_controller.get_position_command()

        go_option = (
            self.go_option_provider()
            if self.go_option_provider is not None
            else "btime 1000 wtime 1000 byoyomi 1000"
        )

        self._on_debug_log(f"[{self.side}] go option: {go_option}")

        self._thread = QThread()
        self._worker = AIWorker(
            side=self.side,
            engine_path=self.engine_path,
            position_command=position_command,
            go_option=go_option,
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)

        self._worker.debug_log.connect(self._on_debug_log)
        self._worker.move_ready.connect(self._on_move_ready)
        self._worker.error.connect(self._on_error)

        self._worker.move_ready.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)

        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_worker_refs)

        self._thread.start()

    def _clear_worker_refs(self) -> None:
        self._worker = None
        self._thread = None

    def _on_debug_log(self, text: str) -> None:
        if self.debug_log_callback is not None:
            self.debug_log_callback(text)
        else:
            print(text)

    def _on_move_ready(self, move: Move) -> None:
        if self.match_controller is not None:
            self.match_controller.submit_move(move)

    def _on_error(self, message: str) -> None:
        self._on_debug_log(f"[{self.side}] AIエラー: {message}")

        if self.match_controller is not None:
            self.match_controller.set_status(f"AIエラー: {message}")
    
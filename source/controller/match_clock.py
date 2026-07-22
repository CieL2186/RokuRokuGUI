from __future__ import annotations

import time
from dataclasses import dataclass


Side = str


@dataclass
class ClockResult:
    timed_out: bool
    elapsed_ms: int


class MatchClock:
    def __init__(self, settings: dict[str, object]) -> None:
        self.time_mode = str(settings.get("time_mode", "none"))

        # =========================
        # 持ち時間：先手・後手別
        # =========================
        black_hour = int(settings.get("black_main_time_hour", settings.get("main_time_hour", 0)))
        black_min = int(settings.get("black_main_time_min", settings.get("main_time_min", 0)))

        white_hour = int(settings.get("white_main_time_hour", settings.get("main_time_hour", 0)))
        white_min = int(settings.get("white_main_time_min", settings.get("main_time_min", 0)))

        black_main_ms = (black_hour * 60 + black_min) * 60 * 1000
        white_main_ms = (white_hour * 60 + white_min) * 60 * 1000

        # =========================
        # 秒読み：先手・後手別
        # =========================
        black_byoyomi_sec = int(settings.get("black_byoyomi_sec", settings.get("byoyomi_sec", 0)))
        white_byoyomi_sec = int(settings.get("white_byoyomi_sec", settings.get("byoyomi_sec", 0)))

        self.byoyomi_ms: dict[Side, int] = {
            "black": max(black_byoyomi_sec * 1000, 0),
            "white": max(white_byoyomi_sec * 1000, 0),
        }

        # =========================
        # 1手ごとの加算：先手・後手別
        # =========================
        black_increment_sec = int(settings.get("black_increment_sec", settings.get("increment_sec", 0)))
        white_increment_sec = int(settings.get("white_increment_sec", settings.get("increment_sec", 0)))

        self.increment_ms: dict[Side, int] = {
            "black": max(black_increment_sec * 1000, 0),
            "white": max(white_increment_sec * 1000, 0),
        }

        self.lose_on_time = bool(settings.get("lose_on_time", False))

        # =========================
        # 残り時間
        # =========================
        if self.time_mode == "main_time":
            self.remaining_ms: dict[Side, int] = {
                "black": black_main_ms,
                "white": white_main_ms,
            }

        elif self.time_mode == "byoyomi":
            self.remaining_ms = {
                "black": 0,
                "white": 0,
            }

            # 秒読み0秒だと即時間切れになるので最低1秒にする
            if self.byoyomi_ms["black"] <= 0:
                self.byoyomi_ms["black"] = 1000
            if self.byoyomi_ms["white"] <= 0:
                self.byoyomi_ms["white"] = 1000

        elif self.time_mode == "increment":
            self.remaining_ms = {
                "black": black_main_ms,
                "white": white_main_ms,
            }

            # 加算0秒だと実用上扱いにくいので最低1秒にする
            if self.increment_ms["black"] <= 0:
                self.increment_ms["black"] = 1000
            if self.increment_ms["white"] <= 0:
                self.increment_ms["white"] = 1000

        else:
            self.remaining_ms = {
                "black": 0,
                "white": 0,
            }

        self.current_side: Side | None = None
        self.turn_started_at: float | None = None

    def start_turn(self, side: Side) -> None:
        self.current_side = side
        self.turn_started_at = time.monotonic()

    def elapsed_ms(self) -> int:
        if self.turn_started_at is None:
            return 0

        return int((time.monotonic() - self.turn_started_at) * 1000)

    def finish_turn(self, side: Side) -> ClockResult:
        elapsed = self.elapsed_ms()

        if self.time_mode == "none":
            self.current_side = None
            self.turn_started_at = None
            return ClockResult(timed_out=False, elapsed_ms=elapsed)

        timed_out = self._is_timeout(side, elapsed)

        if self.time_mode == "main_time":
            self.remaining_ms[side] = max(0, self.remaining_ms[side] - elapsed)

        elif self.time_mode == "byoyomi":
            self.remaining_ms[side] = 0

        elif self.time_mode == "increment":
            self.remaining_ms[side] = max(0, self.remaining_ms[side] - elapsed)
            if not timed_out:
                self.remaining_ms[side] += self.increment_ms[side]

        self.current_side = None
        self.turn_started_at = None

        return ClockResult(timed_out=timed_out, elapsed_ms=elapsed)

    def _is_timeout(self, side: Side, elapsed_ms: int) -> bool:
        if not self.lose_on_time:
            return False

        if self.time_mode == "main_time":
            return elapsed_ms > self.remaining_ms[side]

        if self.time_mode == "byoyomi":
            return elapsed_ms > self.byoyomi_ms[side]

        if self.time_mode == "increment":
            return elapsed_ms > self.remaining_ms[side]

        return False

    def make_go_option(self) -> str:
        side = self.current_side or "black"

        if self.time_mode == "main_time":
            return (
                f"btime {self.remaining_ms['black']} "
                f"wtime {self.remaining_ms['white']}"
            )

        if self.time_mode == "byoyomi":
            byoyomi_ms = max(self.byoyomi_ms[side], 1000)
            return f"btime 0 wtime 0 byoyomi {byoyomi_ms}"

        if self.time_mode == "increment":
            return (
                f"btime {self.remaining_ms['black']} "
                f"wtime {self.remaining_ms['white']} "
                f"binc {self.increment_ms['black']} "
                f"winc {self.increment_ms['white']}"
            )

        return "movetime 1000"

    def display_text(self) -> str:
        black_text = self._side_display_text("black")
        white_text = self._side_display_text("white")
        return f"先手: {black_text} / 後手: {white_text}"

    def _side_display_text(self, side: Side) -> str:
        if self.time_mode == "none":
            return "無制限"

        ms = self.visible_remaining_ms(side)

        if ms is None:
            return "無制限"

        total_sec = max(0, ms // 1000)
        minute = total_sec // 60
        second = total_sec % 60

        return f"{minute:02d}:{second:02d}"
    
    def visible_remaining_ms(self, side: Side) -> int | None:
        if self.time_mode == "none":
            return None

        base = self.remaining_ms[side]

        if side != self.current_side or self.turn_started_at is None:
            if self.time_mode == "byoyomi":
                return self.byoyomi_ms[side]
            return base

        elapsed = self.elapsed_ms()

        if self.time_mode == "main_time":
            return max(0, base - elapsed)

        if self.time_mode == "byoyomi":
            return max(0, self.byoyomi_ms[side] - elapsed)

        if self.time_mode == "increment":
            return max(0, base - elapsed)

        return None
    
    def is_current_turn_timeout(self) -> bool:
        if not self.lose_on_time:
            return False

        if self.current_side is None:
            return False

        return self._is_timeout(self.current_side, self.elapsed_ms())
    
    def stop_current_turn(self) -> None:
        self.current_side = None
        self.turn_started_at = None
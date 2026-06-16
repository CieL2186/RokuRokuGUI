from __future__ import annotations

from source.core.move import Move
from source.engine.usi_process import USIProcess


class USIParser:
    def __init__(self, process: USIProcess) -> None:
        self.process = process

    def initialize(self) -> None:
        self.send("usi")
        self.wait_until("usiok")

        self.send("isready")
        self.wait_until("readyok")

    def send(self, command: str) -> None:
        self.process.send_line(command)

    def wait_until(self, expected: str) -> None:
        while True:
            line = self.process.read_line()
            if line == expected:
                return

    def position_startpos(self, moves: list[Move]) -> None:
        if not moves:
            self.send("position startpos")
            return

        move_text = " ".join(move.to_usi() for move in moves)
        self.send(f"position startpos moves {move_text}")

    def go(self, option: str = "btime 1000 wtime 1000 byoyomi 1000") -> Move:
        self.send(f"go {option}")

        while True:
            line = self.process.read_line()

            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) < 2:
                    raise RuntimeError("Invalid bestmove response.")

                return move_from_usi(parts[1])


def move_from_usi(text: str) -> Move:
    if text == "resign":
        raise RuntimeError("Engine resigned.")

    if "*" in text:
        piece, to_square = text.split("*", 1)
        return Move(
            from_square=None,
            to_square=to_square,
            drop_piece=piece,
        )

    promote = text.endswith("+")
    raw = text[:-1] if promote else text

    return Move(
        from_square=raw[:2],
        to_square=raw[2:4],
        promote=promote,
    )
from __future__ import annotations

import subprocess


class USIProcess:
    def __init__(self, engine_path: str) -> None:
        self.engine_path = engine_path
        self.proc: subprocess.Popen[str] | None = None

    def start(self) -> None:
        self.proc = subprocess.Popen(
            [self.engine_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    def send_line(self, line: str) -> None:
        if self.proc is None or self.proc.stdin is None:
            raise RuntimeError("Engine process is not running.")

        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

    def read_line(self) -> str:
        if self.proc is None or self.proc.stdout is None:
            raise RuntimeError("Engine process is not running.")

        return self.proc.stdout.readline().strip()

    def stop(self) -> None:
        if self.proc is None:
            return

        try:
            self.send_line("quit")
        except Exception:
            pass

        self.proc.terminate()
        self.proc = None
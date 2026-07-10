from __future__ import annotations

import subprocess
import threading
from collections.abc import Callable
from pathlib import Path


class USIProcess:
    def __init__(
        self,
        engine_path: str,
        engine_name: str = "engine",
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.engine_path = engine_path
        self.engine_name = engine_name
        self.log_callback = log_callback

        self.proc: subprocess.Popen[str] | None = None
        self._stderr_thread: threading.Thread | None = None
        self._eof_logged = False

    def _log(self, text: str) -> None:
        message = f"[{self.engine_name}] {text}"

        if self.log_callback is not None:
            self.log_callback(message)
        else:
            print(message)

    def start(self) -> None:
        engine_file = Path(self.engine_path)

        if not engine_file.exists():
            raise FileNotFoundError(f"エンジンが見つかりません: {self.engine_path}")

        # 重要:
        # nn.bin などを相対パスで読むエンジンが多いので、
        # 作業ディレクトリをエンジンexeのあるフォルダにする。
        work_dir = engine_file.parent

        self._log(f"start: {engine_file}")
        self._log(f"cwd: {work_dir}")

        try:
            self.proc = subprocess.Popen(
                [str(engine_file)],
                cwd=str(work_dir),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except Exception as exc:
            self._log(f"起動失敗: {exc}")
            raise

        self._start_stderr_reader()

    def send_line(self, line: str) -> None:
        if self.proc is None or self.proc.stdin is None:
            raise RuntimeError("Engine process is not running.")

        if self.proc.poll() is not None:
            raise RuntimeError(
                f"Engine process already exited. exit_code={self.proc.returncode}"
            )

        self._log(f"> {line}")

        try:
            self.proc.stdin.write(line + "\n")
            self.proc.stdin.flush()
        except Exception as exc:
            self._log(f"送信失敗: {exc}")
            raise

    def read_line(self) -> str:
        if self.proc is None or self.proc.stdout is None:
            raise RuntimeError("Engine process is not running.")

        try:
            line = self.proc.stdout.readline()
        except Exception as exc:
            self._log(f"受信失敗: {exc}")
            raise

        # エンジンが終了すると stdout.readline() は "" を返す。
        # ここで "" を返してしまうと USIParser 側の while True が回り続けて
        # EOFログが無限に出るので、必ず例外で止める。
        if line == "":
            exit_code = self.proc.poll()

            if not self._eof_logged:
                self._eof_logged = True
                self._log(f"EOF: engine process ended. exit_code={exit_code}")

            raise RuntimeError(
                f"Engine process ended unexpectedly. exit_code={exit_code}"
            )

        line = line.rstrip("\r\n")
        self._log(f"< {line}")
        return line

    def stop(self) -> None:
        if self.proc is None:
            return

        proc = self.proc

        if proc.poll() is not None:
            self._log(f"stop: process already ended. exit_code={proc.returncode}")
            self.proc = None
            return

        self._log("stop")

        try:
            self.send_line("quit")
        except Exception:
            pass

        try:
            proc.terminate()
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._log("terminate timeout. kill process.")
            proc.kill()
        except Exception as exc:
            self._log(f"stop error: {exc}")

        self.proc = None

    def _start_stderr_reader(self) -> None:
        if self.proc is None or self.proc.stderr is None:
            return

        proc = self.proc
        stderr = self.proc.stderr

        def read_stderr() -> None:
            while True:
                try:
                    line = stderr.readline()
                except Exception:
                    break

                if line == "":
                    break

                self._log(f"! {line.rstrip()}")

        self._stderr_thread = threading.Thread(
            target=read_stderr,
            daemon=True,
        )
        self._stderr_thread.start()
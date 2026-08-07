from __future__ import annotations

from datetime import datetime
from pathlib import Path

from source.core.position import Position


class KifuWriter:
    def __init__(self, save_dir: str | Path = "kif") -> None:
        self.save_dir = Path(save_dir)

    def save_txt(
        self,
        position: Position,
        result: str | None = None,
        settings: dict[str, object] | None = None,
    ) -> Path:
        self.save_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        path = self.save_dir / f"rokuroku_{now:%Y%m%d_%H%M%S}.txt"

        lines: list[str] = []
        lines.append("# RokuRokuGUI Kif")
        lines.append(f"date: {now:%Y-%m-%d %H:%M:%S}")

        if settings is not None:
            lines.append(f"black_player: {settings.get('black_player', '')}")
            lines.append(f"white_player: {settings.get('white_player', '')}")

        lines.append(f"result: {result or 'unknown'}")
        lines.append("")
        lines.append("moves:")

        side = "black"
        for index, move in enumerate(position.get_move_history(), start=1):
            side_text = "black" if side == "black" else "white"
            lines.append(f"{index}. {side_text} {move.to_usi()}")
            side = "white" if side == "black" else "black"

        path.write_text("\n".join(lines), encoding="utf-8")
        return path
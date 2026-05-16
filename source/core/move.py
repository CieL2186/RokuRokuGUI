from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Move:
    """66将棋GUIで扱う指し手表現。"""

    from_square: str | None
    to_square: str
    promote: bool = False
    drop_piece: str | None = None

    @property
    def is_drop(self) -> bool:
        return self.drop_piece is not None

    def to_usi(self) -> str:
        if self.is_drop:
            return f"{self.drop_piece}*{self.to_square}"

        if self.from_square is None:
            raise ValueError("通常手なのに from_square がありません。")

        suffix = "+" if self.promote else ""
        return f"{self.from_square}{self.to_square}{suffix}"

    def __str__(self) -> str:
        return self.to_usi()
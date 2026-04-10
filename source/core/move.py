from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class Move:
    from_square: Optional[str] = None
    to_square: Optional[str] = None
    drop_piece: Optional[str] = None
    promote: bool = False

    @property
    def is_drop(self) -> bool:
        return self.drop_piece is not None

    def to_usi(self) -> str:
        if self.is_drop:
            if self.drop_piece is None or self.to_square is None:
                raise ValueError("Drop move requires drop_piece and to_square.")
            return f"{self.drop_piece}*{self.to_square}"

        if self.from_square is None or self.to_square is None:
            raise ValueError("Normal move requires from_square and to_square.")

        return f"{self.from_square}{self.to_square}{'+' if self.promote else ''}"

    def __str__(self) -> str:
        return self.to_usi()

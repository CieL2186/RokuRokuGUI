from __future__ import annotations

from typing import Iterable, Optional

from core.move import Move

FILES = "654321"
RANKS = "abcdef"
BOARD_WIDTH = 6
BOARD_HEIGHT = 6
BLACK = 0
WHITE = 1


STEP_VECTORS_BLACK: dict[str, tuple[tuple[int, int], ...]] = {
    "K": ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)),
    "G": ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (0, 1)),
    "S": ((-1, -1), (0, -1), (1, -1), (-1, 1), (1, 1)),
    "N": ((-1, -2), (1, -2)),
    "P": ((0, -1),),
}

SLIDING_DIRECTIONS_BLACK: dict[str, tuple[tuple[int, int], ...]] = {
    "R": ((0, -1), (0, 1), (-1, 0), (1, 0)),
    "B": ((-1, -1), (1, -1), (-1, 1), (1, 1)),
}


def get_legal_moves_from(position, square: str) -> list[Move]:
    piece = position.board.get(square)
    if piece is None:
        return []
    if piece_side(piece) != position.side_to_move:
        return []

    moves: list[Move] = []
    kind = piece_kind(piece)
    side = piece_side(piece)

    if kind in STEP_VECTORS_BLACK:
        for dx, dy in oriented_vectors(STEP_VECTORS_BLACK[kind], side):
            to_sq = offset_square(square, dx, dy)
            if to_sq is None:
                continue
            target = position.board.get(to_sq)
            if target is not None and piece_side(target) == side:
                continue
            moves.append(Move(from_square=square, to_square=to_sq))
        return moves

    if kind in SLIDING_DIRECTIONS_BLACK:
        for dx, dy in oriented_vectors(SLIDING_DIRECTIONS_BLACK[kind], side):
            for to_sq in ray_squares(square, dx, dy):
                target = position.board.get(to_sq)
                if target is None:
                    moves.append(Move(from_square=square, to_square=to_sq))
                    continue
                if piece_side(target) != side:
                    moves.append(Move(from_square=square, to_square=to_sq))
                break
        return moves

    return []


def get_all_legal_moves(position) -> list[Move]:
    moves: list[Move] = []
    for square, piece in position.board.items():
        if piece_side(piece) != position.side_to_move:
            continue
        moves.extend(get_legal_moves_from(position, square))
    return moves


def is_legal_move(position, move: Move) -> bool:
    if move.from_square is None or move.to_square is None:
        return False
    return move.to_usi() in {m.to_usi() for m in get_legal_moves_from(position, move.from_square)}


def do_move(position, move: Move) -> bool:
    if move.from_square is None or move.to_square is None:
        return False
    piece = position.board.get(move.from_square)
    if piece is None:
        return False
    if piece_side(piece) != position.side_to_move:
        return False

    position.board.pop(move.from_square, None)
    position.board[move.to_square] = piece
    position.move_history.append(move)
    position.side_to_move = WHITE if position.side_to_move == BLACK else BLACK
    return True


def is_game_over(position) -> bool:
    has_black_king = any(piece == "bK" for piece in position.board.values())
    has_white_king = any(piece == "wK" for piece in position.board.values())
    return not has_black_king or not has_white_king


def get_game_result(position) -> str:
    has_black_king = any(piece == "bK" for piece in position.board.values())
    has_white_king = any(piece == "wK" for piece in position.board.values())

    if has_black_king and has_white_king:
        return "未決着"
    if has_black_king:
        return "先手勝ち"
    if has_white_king:
        return "後手勝ち"
    return "両王不在"


def piece_side(piece: str) -> int:
    return BLACK if piece.startswith("b") else WHITE


def piece_kind(piece: str) -> str:
    return piece[1:]


def oriented_vectors(vectors: Iterable[tuple[int, int]], side: int) -> list[tuple[int, int]]:
    if side == BLACK:
        return list(vectors)
    return [(-dx, -dy) for dx, dy in vectors]


def ray_squares(start_square: str, dx: int, dy: int) -> list[str]:
    x, y = square_to_xy(start_square)
    result: list[str] = []
    while True:
        x += dx
        y += dy
        if not inside_board(x, y):
            return result
        result.append(xy_to_square(x, y))


def offset_square(square: str, dx: int, dy: int) -> Optional[str]:
    x, y = square_to_xy(square)
    x += dx
    y += dy
    if not inside_board(x, y):
        return None
    return xy_to_square(x, y)


def square_to_xy(square: str) -> tuple[int, int]:
    file_char = square[0]
    rank_char = square[1]
    x = FILES.index(file_char)
    y = RANKS.index(rank_char)
    return x, y


def xy_to_square(x: int, y: int) -> str:
    return f"{FILES[x]}{RANKS[y]}"


def inside_board(x: int, y: int) -> bool:
    return 0 <= x < BOARD_WIDTH and 0 <= y < BOARD_HEIGHT

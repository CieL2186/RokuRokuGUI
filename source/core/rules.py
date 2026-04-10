from __future__ import annotations

from typing import TYPE_CHECKING

from source.core.move import Move

if TYPE_CHECKING:
    from source.core.position import Position


BOARD_SIZE = 6
PROMOTION_ZONE_RANKS = 2


def generate_legal_moves_from(position: Position, square: str) -> list[Move]:
    piece = position.get_piece_at(square)
    if piece is None:
        return []

    side = get_piece_side(piece)
    if side != position.side_to_move:
        return []

    base_piece = get_base_piece(piece)
    promoted = is_promoted(piece)

    row_col = square_to_index(square)
    if row_col is None:
        return []

    row, col = row_col
    moves: list[Move] = []

    if promoted and base_piece in {"P", "S", "N", "L"}:
        destinations = _step_destinations(position, row, col, _gold_directions(side))
        moves.extend(_moves_with_promotion(position, square, piece, destinations))
        return _dedupe_moves(moves)

    if promoted and base_piece == "R":
        rook_dests = _slide_destinations(
            position,
            row,
            col,
            [(-1, 0), (1, 0), (0, -1), (0, 1)],
        )
        king_diag_dests = _step_destinations(
            position,
            row,
            col,
            [(-1, -1), (-1, 1), (1, -1), (1, 1)],
        )
        moves.extend(_moves_with_promotion(position, square, piece, rook_dests))
        moves.extend(_moves_with_promotion(position, square, piece, king_diag_dests))
        return _dedupe_moves(moves)

    if promoted and base_piece == "B":
        bishop_dests = _slide_destinations(
            position,
            row,
            col,
            [(-1, -1), (-1, 1), (1, -1), (1, 1)],
        )
        king_orth_dests = _step_destinations(
            position,
            row,
            col,
            [(-1, 0), (1, 0), (0, -1), (0, 1)],
        )
        moves.extend(_moves_with_promotion(position, square, piece, bishop_dests))
        moves.extend(_moves_with_promotion(position, square, piece, king_orth_dests))
        return _dedupe_moves(moves)

    if base_piece == "K":
        destinations = _step_destinations(
            position,
            row,
            col,
            [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)],
        )
        moves.extend(_moves_with_promotion(position, square, piece, destinations))
        return _dedupe_moves(moves)

    if base_piece == "G":
        destinations = _step_destinations(position, row, col, _gold_directions(side))
        moves.extend(_moves_with_promotion(position, square, piece, destinations))
        return _dedupe_moves(moves)

    if base_piece == "S":
        directions = _forward_relative_dirs(
            side,
            [(-1, -1), (-1, 0), (-1, 1), (1, -1), (1, 1)],
        )
        destinations = _step_destinations(position, row, col, directions)
        moves.extend(_moves_with_promotion(position, square, piece, destinations))
        return _dedupe_moves(moves)

    if base_piece == "N":
        directions = _forward_relative_dirs(side, [(-2, -1), (-2, 1)])
        destinations = _step_destinations(position, row, col, directions)
        moves.extend(_moves_with_promotion(position, square, piece, destinations))
        return _dedupe_moves(moves)

    if base_piece == "L":
        directions = _forward_relative_dirs(side, [(-1, 0)])
        destinations = _slide_destinations(position, row, col, directions)
        moves.extend(_moves_with_promotion(position, square, piece, destinations))
        return _dedupe_moves(moves)

    if base_piece == "P":
        directions = _forward_relative_dirs(side, [(-1, 0)])
        destinations = _step_destinations(position, row, col, directions)
        moves.extend(_moves_with_promotion(position, square, piece, destinations))
        return _dedupe_moves(moves)

    if base_piece == "R":
        destinations = _slide_destinations(
            position,
            row,
            col,
            [(-1, 0), (1, 0), (0, -1), (0, 1)],
        )
        moves.extend(_moves_with_promotion(position, square, piece, destinations))
        return _dedupe_moves(moves)

    if base_piece == "B":
        destinations = _slide_destinations(
            position,
            row,
            col,
            [(-1, -1), (-1, 1), (1, -1), (1, 1)],
        )
        moves.extend(_moves_with_promotion(position, square, piece, destinations))
        return _dedupe_moves(moves)

    return []


def get_all_legal_moves(position: Position, side: str | None = None) -> list[Move]:
    target_side = position.side_to_move if side is None else side
    moves: list[Move] = []

    for square, piece in position.board.items():
        if piece is None:
            continue
        if get_piece_side(piece) != target_side:
            continue
        moves.extend(generate_legal_moves_from(position, square))

    return _dedupe_moves(moves)


def can_promote_move(position: Position, move: Move) -> bool:
    if move.is_drop or move.from_square is None:
        return False

    piece = position.get_piece_at(move.from_square)
    if piece is None:
        return False

    return can_promote_piece(piece, move.from_square, move.to_square)


def can_promote_piece(piece: str, from_square: str, to_square: str) -> bool:
    if is_promoted(piece):
        return False

    base_piece = get_base_piece(piece)
    if base_piece not in {"R", "B", "S", "N", "L", "P"}:
        return False

    side = get_piece_side(piece)
    return is_promotion_zone(side, from_square) or is_promotion_zone(side, to_square)


def must_promote(piece: str, to_square: str) -> bool:
    base_piece = get_base_piece(piece)
    side = get_piece_side(piece)

    row_col = square_to_index(to_square)
    if row_col is None:
        return False

    row, _ = row_col

    if base_piece in {"P", "L"}:
        return (side == "black" and row == 0) or (side == "white" and row == BOARD_SIZE - 1)

    if base_piece == "N":
        return (side == "black" and row <= 1) or (side == "white" and row >= BOARD_SIZE - 2)

    return False


def is_promotion_zone(side: str, square: str) -> bool:
    row_col = square_to_index(square)
    if row_col is None:
        return False

    row, _ = row_col

    if side == "black":
        return row < PROMOTION_ZONE_RANKS
    return row >= BOARD_SIZE - PROMOTION_ZONE_RANKS


def promote_piece(piece: str) -> str:
    if is_promoted(piece):
        return piece

    if piece.startswith("b") or piece.startswith("w"):
        prefix = piece[0]
        body = piece[1:]
        return f"{prefix}+{body.upper()}"

    if piece.startswith("+"):
        return piece

    if piece.isupper():
        return f"+{piece.upper()}"
    return f"+{piece.lower()}"


def unpromote_piece(piece: str) -> str:
    if piece.startswith("b+") or piece.startswith("w+"):
        return piece[0] + piece[2:]

    if piece.startswith("+"):
        return piece[1:]

    return piece


def get_piece_side(piece: str) -> str:
    if piece.startswith("b"):
        return "black"
    if piece.startswith("w"):
        return "white"

    stripped = piece[1:] if piece.startswith("+") else piece
    if stripped.isupper():
        return "black"
    return "white"


def get_base_piece(piece: str) -> str:
    body = piece
    if body.startswith("b") or body.startswith("w"):
        body = body[1:]
    if body.startswith("+"):
        body = body[1:]
    return body.upper()


def is_promoted(piece: str) -> bool:
    if piece.startswith("b+") or piece.startswith("w+"):
        return True
    return piece.startswith("+")


def square_to_index(square: str) -> tuple[int, int] | None:
    if len(square) != 2:
        return None

    file_char, rank_char = square[0], square[1]
    if not file_char.isdigit():
        return None
    if rank_char < "a" or rank_char > "f":
        return None

    file_num = int(file_char)
    if not (1 <= file_num <= BOARD_SIZE):
        return None

    row = ord(rank_char) - ord("a")
    col = BOARD_SIZE - file_num
    return row, col


def index_to_square(row: int, col: int) -> str:
    file_num = str(BOARD_SIZE - col)
    rank_char = chr(ord("a") + row)
    return f"{file_num}{rank_char}"


def _moves_with_promotion(
    position: Position,
    from_square: str,
    piece: str,
    destinations: list[str],
) -> list[Move]:
    moves: list[Move] = []

    for to_square in destinations:
        if can_promote_piece(piece, from_square, to_square):
            if not must_promote(piece, to_square):
                moves.append(Move(from_square=from_square, to_square=to_square, promote=False))
            moves.append(Move(from_square=from_square, to_square=to_square, promote=True))
        else:
            moves.append(Move(from_square=from_square, to_square=to_square, promote=False))

    return moves


def _step_destinations(
    position: Position,
    row: int,
    col: int,
    directions: list[tuple[int, int]],
) -> list[str]:
    result: list[str] = []
    from_square = index_to_square(row, col)
    piece = position.get_piece_at(from_square)
    if piece is None:
        return result

    side = get_piece_side(piece)

    for dr, dc in directions:
        nr = row + dr
        nc = col + dc
        if not _inside_board(nr, nc):
            continue

        to_square = index_to_square(nr, nc)
        target = position.get_piece_at(to_square)
        if target is not None and get_piece_side(target) == side:
            continue

        result.append(to_square)

    return result


def _slide_destinations(
    position: Position,
    row: int,
    col: int,
    directions: list[tuple[int, int]],
) -> list[str]:
    result: list[str] = []
    from_square = index_to_square(row, col)
    piece = position.get_piece_at(from_square)
    if piece is None:
        return result

    side = get_piece_side(piece)

    for dr, dc in directions:
        nr = row + dr
        nc = col + dc

        while _inside_board(nr, nc):
            to_square = index_to_square(nr, nc)
            target = position.get_piece_at(to_square)

            if target is None:
                result.append(to_square)
            else:
                if get_piece_side(target) != side:
                    result.append(to_square)
                break

            nr += dr
            nc += dc

    return result


def _forward_relative_dirs(side: str, dirs: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if side == "black":
        return dirs
    return [(-dr, dc) for dr, dc in dirs]


def _gold_directions(side: str) -> list[tuple[int, int]]:
    return _forward_relative_dirs(
        side,
        [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, 0)],
    )


def _inside_board(row: int, col: int) -> bool:
    return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE


def _dedupe_moves(moves: list[Move]) -> list[Move]:
    seen: set[tuple[str | None, str, bool, str | None]] = set()
    result: list[Move] = []

    for move in moves:
        key = (move.from_square, move.to_square, move.promote, move.drop_piece)
        if key in seen:
            continue
        seen.add(key)
        result.append(move)

    return result
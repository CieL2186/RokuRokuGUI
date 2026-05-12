from __future__ import annotations

from typing import TYPE_CHECKING

from source.core.move import Move

if TYPE_CHECKING:
    from source.core.position import Position


BOARD_SIZE = 6
PROMOTION_ZONE_RANKS = 2


def generate_legal_moves_from(
    position: Position,
    square: str,
    side_override: str | None = None,
) -> list[Move]:
    piece = position.get_piece_at(square)
    if piece is None:
        return []

    moving_side = get_piece_side(piece)
    target_side = position.side_to_move if side_override is None else side_override

    if moving_side != target_side:
        return []

    pseudo_moves = generate_pseudo_legal_moves_from(
        position=position,
        square=square,
        side_override=target_side,
    )

    legal_moves: list[Move] = []
    for move in pseudo_moves:
        if _is_legal_after_move(position, move, moving_side):
            legal_moves.append(move)

    return _dedupe_moves(legal_moves)


def generate_pseudo_legal_moves_from(
    position: Position,
    square: str,
    side_override: str | None = None,
) -> list[Move]:
    piece = position.get_piece_at(square)
    if piece is None:
        return []

    side = get_piece_side(piece)
    target_side = position.side_to_move if side_override is None else side_override

    if side != target_side:
        return []

    row_col = square_to_index(square)
    if row_col is None:
        return []

    row, col = row_col
    destinations = _destinations_for_piece(position, row, col, piece)
    return _moves_with_promotion(position, square, piece, destinations)


def get_all_legal_moves(position: Position, side: str | None = None) -> list[Move]:
    target_side = position.side_to_move if side is None else side
    moves: list[Move] = []

    for square, piece in position.board.items():
        if piece is None:
            continue
        if get_piece_side(piece) != target_side:
            continue
        moves.extend(generate_legal_moves_from(position, square, side_override=target_side))

    return _dedupe_moves(moves)


def find_king_square(position: Position, side: str) -> str | None:
    for square, piece in position.board.items():
        if piece is None:
            continue
        if get_piece_side(piece) != side:
            continue
        if get_base_piece(piece) == "K":
            return square
    return None


def is_in_check(position: Position, side: str) -> bool:
    king_square = find_king_square(position, side)
    if king_square is None:
        return True

    opponent = "white" if side == "black" else "black"

    for square, piece in position.board.items():
        if piece is None:
            continue
        if get_piece_side(piece) != opponent:
            continue

        attacks = get_attack_squares_from(position, square)
        if king_square in attacks:
            return True

    return False


def is_checkmate(position: Position, side: str) -> bool:
    if not is_in_check(position, side):
        return False

    return len(get_all_legal_moves(position, side)) == 0


def get_attack_squares_from(position: Position, square: str) -> list[str]:
    piece = position.get_piece_at(square)
    if piece is None:
        return []

    row_col = square_to_index(square)
    if row_col is None:
        return []

    row, col = row_col
    return _destinations_for_piece(position, row, col, piece)


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

    text = piece.strip()

    # bP / wP 形式だけ接頭辞として扱う
    # 1文字の "b" は後手角なので、ここに入れてはいけない
    if len(text) >= 2 and text[0] in {"b", "w"}:
        prefix = text[0]
        body = text[1:]
        return f"{prefix}+{body.upper()}"

    if text.startswith("+"):
        return text

    if text.isupper():
        return f"+{text.upper()}"

    return f"+{text.lower()}"


def unpromote_piece(piece: str) -> str:
    text = piece.strip()

    # b+P / w+P 形式
    if len(text) >= 3 and text[0] in {"b", "w"} and text[1] == "+":
        return text[0] + text[2:]

    # +P / +p / +b 形式
    if text.startswith("+"):
        return text[1:]

    return text


def get_piece_side(piece: str) -> str:
    text = piece.strip()

    # bP / wP / b+P / w+P 形式だけ接頭辞として扱う
    # 重要: 1文字の "b" は後手角なので black prefix として扱わない
    if len(text) >= 2 and text[0] in {"b", "w"}:
        return "black" if text[0] == "b" else "white"

    # +P / +p / +b などの成り記号を外す
    if text.startswith("+"):
        text = text[1:]

    return "black" if text.isupper() else "white"


def get_base_piece(piece: str) -> str:
    text = piece.strip()

    # bP / wP / b+P / w+P 形式
    if len(text) >= 2 and text[0] in {"b", "w"}:
        text = text[1:]
        if text.startswith("+"):
            text = text[1:]
        return text.upper()

    # +P / +p / +b 形式
    if text.startswith("+"):
        text = text[1:]

    return text.upper()


def is_promoted(piece: str) -> bool:
    text = piece.strip()

    # b+P / w+P 形式
    if len(text) >= 3 and text[0] in {"b", "w"} and text[1] == "+":
        return True

    # +P / +p / +b 形式
    return text.startswith("+")


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


def _destinations_for_piece(
    position: Position,
    row: int,
    col: int,
    piece: str,
) -> list[str]:
    side = get_piece_side(piece)
    base_piece = get_base_piece(piece)
    promoted = is_promoted(piece)

    if promoted and base_piece in {"P", "S", "N", "L"}:
        return _step_destinations(position, row, col, piece, _gold_directions(side))

    if promoted and base_piece == "R":
        rook_dests = _slide_destinations(
            position,
            row,
            col,
            piece,
            [(-1, 0), (1, 0), (0, -1), (0, 1)],
        )
        king_diag_dests = _step_destinations(
            position,
            row,
            col,
            piece,
            [(-1, -1), (-1, 1), (1, -1), (1, 1)],
        )
        return rook_dests + king_diag_dests

    if promoted and base_piece == "B":
        bishop_dests = _slide_destinations(
            position,
            row,
            col,
            piece,
            [(-1, -1), (-1, 1), (1, -1), (1, 1)],
        )
        king_orth_dests = _step_destinations(
            position,
            row,
            col,
            piece,
            [(-1, 0), (1, 0), (0, -1), (0, 1)],
        )
        return bishop_dests + king_orth_dests

    if base_piece == "K":
        return _step_destinations(
            position,
            row,
            col,
            piece,
            [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)],
        )

    if base_piece == "G":
        return _step_destinations(position, row, col, piece, _gold_directions(side))

    if base_piece == "S":
        directions = _forward_relative_dirs(
            side,
            [(-1, -1), (-1, 0), (-1, 1), (1, -1), (1, 1)],
        )
        return _step_destinations(position, row, col, piece, directions)

    if base_piece == "N":
        directions = _forward_relative_dirs(side, [(-2, -1), (-2, 1)])
        return _step_destinations(position, row, col, piece, directions)

    if base_piece == "L":
        directions = _forward_relative_dirs(side, [(-1, 0)])
        return _slide_destinations(position, row, col, piece, directions)

    if base_piece == "P":
        directions = _forward_relative_dirs(side, [(-1, 0)])
        return _step_destinations(position, row, col, piece, directions)

    if base_piece == "R":
        return _slide_destinations(
            position,
            row,
            col,
            piece,
            [(-1, 0), (1, 0), (0, -1), (0, 1)],
        )

    if base_piece == "B":
        return _slide_destinations(
            position,
            row,
            col,
            piece,
            [(-1, -1), (-1, 1), (1, -1), (1, 1)],
        )

    return []


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

    return _dedupe_moves(moves)


def _step_destinations(
    position: Position,
    row: int,
    col: int,
    piece: str,
    directions: list[tuple[int, int]],
) -> list[str]:
    result: list[str] = []
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
    piece: str,
    directions: list[tuple[int, int]],
) -> list[str]:
    result: list[str] = []
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


def _is_legal_after_move(position: Position, move: Move, moving_side: str) -> bool:
    if move.is_drop:
        return False
    if move.from_square is None:
        return False

    from_square = move.from_square
    to_square = move.to_square

    moving_piece = position.get_piece_at(from_square)
    captured_piece = position.get_piece_at(to_square)

    if moving_piece is None:
        return False

    moved_piece = promote_piece(moving_piece) if move.promote else moving_piece

    position.set_piece_at(from_square, None)
    position.set_piece_at(to_square, moved_piece)

    safe = not is_in_check(position, moving_side)

    position.set_piece_at(from_square, moving_piece)
    position.set_piece_at(to_square, captured_piece)

    return safe


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

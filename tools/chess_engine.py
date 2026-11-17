"""Small chess engine used by the profile: material + piece-square evaluation, alpha-beta search with quiescence.

Levels: Easy (1 ply, loose), Medium (3 plies), Hard (iterative deepening on a time budget).
"""
import random
import time

import chess

# ------------------------------------------------------------------ evaluation (material + piece-square tables)
VALUE = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330, chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0}
# Tables are written from White's point of view, rank 8 first (a8..h8, a7..h7, ...).
PST = {
    chess.PAWN: [0, 0, 0, 0, 0, 0, 0, 0, 50, 50, 50, 50, 50, 50, 50, 50, 10, 10, 20, 30, 30, 20, 10, 10,
                 5, 5, 10, 25, 25, 10, 5, 5, 0, 0, 0, 20, 20, 0, 0, 0, 5, -5, -10, 0, 0, -10, -5, 5,
                 5, 10, 10, -20, -20, 10, 10, 5, 0, 0, 0, 0, 0, 0, 0, 0],
    chess.KNIGHT: [-50, -40, -30, -30, -30, -30, -40, -50, -40, -20, 0, 0, 0, 0, -20, -40, -30, 0, 10, 15, 15, 10, 0, -30,
                   -30, 5, 15, 20, 20, 15, 5, -30, -30, 0, 15, 20, 20, 15, 0, -30, -30, 5, 10, 15, 15, 10, 5, -30,
                   -40, -20, 0, 5, 5, 0, -20, -40, -50, -40, -30, -30, -30, -30, -40, -50],
    chess.BISHOP: [-20, -10, -10, -10, -10, -10, -10, -20, -10, 0, 0, 0, 0, 0, 0, -10, -10, 0, 5, 10, 10, 5, 0, -10,
                   -10, 5, 5, 10, 10, 5, 5, -10, -10, 0, 10, 10, 10, 10, 0, -10, -10, 10, 10, 10, 10, 10, 10, -10,
                   -10, 5, 0, 0, 0, 0, 5, -10, -20, -10, -10, -10, -10, -10, -10, -20],
    chess.ROOK: [0, 0, 0, 0, 0, 0, 0, 0, 5, 10, 10, 10, 10, 10, 10, 5, -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5,
                 -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5, 0, 0, 0, 5, 5, 0, 0, 0],
    chess.QUEEN: [-20, -10, -10, -5, -5, -10, -10, -20, -10, 0, 0, 0, 0, 0, 0, -10, -10, 0, 5, 5, 5, 5, 0, -10,
                  -5, 0, 5, 5, 5, 5, 0, -5, 0, 0, 5, 5, 5, 5, 0, -5, -10, 5, 5, 5, 5, 5, 0, -10,
                  -10, 0, 5, 0, 0, 0, 0, -10, -20, -10, -10, -5, -5, -10, -10, -20],
    chess.KING: [-30, -40, -40, -50, -50, -40, -40, -30, -30, -40, -40, -50, -50, -40, -40, -30,
                 -30, -40, -40, -50, -50, -40, -40, -30, -30, -40, -40, -50, -50, -40, -40, -30,
                 -20, -30, -30, -40, -40, -30, -30, -20, -10, -20, -20, -20, -20, -20, -20, -10,
                 20, 20, 0, 0, 0, 0, 20, 20, 20, 30, 10, 0, 0, 10, 30, 20],
}
MATE = 100_000


def evaluate(board):
    """Score from the side to move's point of view."""
    score = 0
    for sq, piece in board.piece_map().items():
        idx = chess.square_mirror(sq) if piece.color == chess.WHITE else sq
        v = VALUE[piece.piece_type] + PST[piece.piece_type][idx]
        score += v if piece.color == chess.WHITE else -v
    return score if board.turn == chess.WHITE else -score


def ordered(board, moves):
    def key(m):
        victim = board.piece_at(m.to_square)
        attacker = board.piece_at(m.from_square)
        cap = (VALUE[victim.piece_type] * 10 - VALUE[attacker.piece_type]) if victim else 0
        return -(cap + (800 if m.promotion else 0) + (50 if board.gives_check(m) else 0))
    return sorted(moves, key=key)


class OutOfTime(Exception):
    pass


_deadline = None  # set while a timed (Hard) search runs
_nodes = 0


def tick():
    global _nodes
    _nodes += 1
    if _deadline is not None and _nodes % 1024 == 0 and time.monotonic() > _deadline:
        raise OutOfTime


def quiesce(board, alpha, beta, depth=4):
    tick()
    stand = evaluate(board)
    if stand >= beta or depth == 0:
        return stand
    alpha = max(alpha, stand)
    for m in ordered(board, [m for m in board.legal_moves if board.is_capture(m)]):
        board.push(m)
        score = -quiesce(board, -beta, -alpha, depth - 1)
        board.pop()
        if score >= beta:
            return score
        alpha = max(alpha, score)
    return alpha


def negamax(board, depth, alpha, beta):
    tick()
    if board.is_checkmate():
        return -MATE - depth
    if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
        return 0
    if depth == 0:
        return quiesce(board, alpha, beta)
    best = -MATE * 2
    for m in ordered(board, list(board.legal_moves)):
        board.push(m)
        score = -negamax(board, depth - 1, -beta, -alpha)
        board.pop()
        best = max(best, score)
        alpha = max(alpha, score)
        if alpha >= beta:
            break
    return best


LEVELS = {
    # depth: plies searched; slack: how many centipawns worse than the best move the bot may still pick
    "easy": {"label": "Easy", "depth": 1, "slack": 200, "about": "beginner, often picks weaker moves"},
    "medium": {"label": "Medium", "depth": 3, "slack": 12, "about": "casual, looks three moves ahead"},
    "hard": {"label": "Hard", "depth": 6, "slack": 0, "seconds": 10, "about": "thinks as deep as it can in about 10 seconds"},
}
DEFAULT_LEVEL = "medium"


def root_scores(board, moves, depth, narrow):
    """Score each root move. narrow=True uses an alpha-beta window: faster, but only the best score is exact."""
    scored, alpha = [], -MATE * 2
    for m in moves:
        board.push(m)
        s = -negamax(board, depth - 1, -MATE * 2, -alpha if narrow else MATE * 2)
        board.pop()
        scored.append((s, m))
        if narrow:
            alpha = max(alpha, s)
    return scored


def bot_move(board, level=DEFAULT_LEVEL, seconds=None):
    """Pick a move for the side to move. seconds overrides the think time of timed levels (Hard)."""
    global _deadline
    cfg = dict(LEVELS.get(level, LEVELS[DEFAULT_LEVEL]))
    if seconds is not None and "seconds" in cfg:
        cfg["seconds"] = seconds
    moves = ordered(board, list(board.legal_moves))
    if "seconds" not in cfg:
        scored = root_scores(board.copy(), moves, cfg["depth"], narrow=False)
        best = max(s for s, _ in scored)
        return random.choice([m for s, m in scored if s >= best - cfg["slack"]])

    # Hard: iterative deepening until the time budget runs out; keep the last fully searched depth.
    _deadline = time.monotonic() + cfg["seconds"]
    best_move = moves[0]
    try:
        for depth in range(1, cfg["depth"] + 1):
            scored = root_scores(board.copy(), moves, depth, narrow=True)  # a copy, so an abort leaves board intact
            top = max(s for s, _ in scored)
            best_move = next(m for s, m in scored if s == top)
            moves = [best_move] + [m for m in moves if m != best_move]  # search the best line first next time
            if abs(top) >= MATE:
                break
    except OutOfTime:
        pass
    finally:
        _deadline = None
    return best_move

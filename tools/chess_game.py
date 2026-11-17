"""Apply one visitor move from an issue title, let the bot answer as Black, and update data/chess.json.

Usage: python chess_game.py "<issue title>" <github login> <reply.md>

Issue titles look like  chess|move|e2e4|<game>.<ply>  (written by the links in README.md).
The title  chess|newgame  starts a fresh board, but only when the issue was opened by the profile owner.
Writes `changed=true|false` and `summary=...` to $GITHUB_OUTPUT when that variable is set.
"""
import json
import os
import random
import sys
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "data" / "chess.json"
OWNER = os.environ.get("GITHUB_REPOSITORY_OWNER", "wildanpanjii")
BOARD_LINK = f"https://github.com/{OWNER}#readme"

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


def quiesce(board, alpha, beta, depth=4):
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


def bot_move(board, depth=3):
    scored = []
    for m in ordered(board, list(board.legal_moves)):
        board.push(m)
        scored.append((-negamax(board, depth - 1, -MATE * 2, MATE * 2), m))
        board.pop()
    best = max(s for s, _ in scored)
    return random.choice([m for s, m in scored if s >= best - 12])  # small variety between equal moves


# ------------------------------------------------------------------ game flow
def load():
    state = {"game": 1, "moves": [], "players": [], "score": {"visitors": 0, "bot": 0, "draws": 0}, "last_result": ""}
    if STATE_FILE.exists():
        state.update(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    return state


def result_text(board, outcome):
    if outcome.winner is None:
        reason = outcome.termination.name.replace("_", " ").lower()
        return f"draw by {reason}"
    return ("White (visitors)" if outcome.winner else "Black (bot)") + " won by checkmate"


def finish(state, board):
    """If the game is over, record it and start a fresh one. Returns a sentence for the reply, or ''."""
    outcome = board.outcome(claim_draw=True)
    if outcome is None:
        return ""
    if outcome.winner is None:
        state["score"]["draws"] += 1
    elif outcome.winner:
        state["score"]["visitors"] += 1
    else:
        state["score"]["bot"] += 1
    text = result_text(board, outcome)
    state.update(game=state["game"] + 1, moves=[], players=[], last_result=f"game {state['game']}: {text}")
    return f"\n\n**Game over: {text}.** A new game has started, so the next White move is yours to make."


def save(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8", newline="\n")


def new_game(player):
    """Owner-only reset: abandon the current game (not counted in the score) and start a fresh board."""
    if player.lower() != OWNER.lower():
        return False, (f"Only @{OWNER} can start a new game. You can still "
                       f"[play a move on the current board]({BOARD_LINK})."), ""
    state = load()
    if not state["moves"]:
        return False, f"The board is already at the starting position. [Make the first move]({BOARD_LINK}).", ""
    old = state["game"]
    state.update(game=old + 1, moves=[], players=[], last_result=f"game {old} was reset by @{OWNER}")
    save(state)
    return True, (f"Game {old} was reset and is not counted in the score. Game {old + 1} starts from the beginning. "
                  f"[Make the first move]({BOARD_LINK})."), f"Chess: start game {old + 1}"


def play(title, player):
    """Returns (changed, reply_markdown, summary)."""
    if title.strip() == "chess|newgame":
        return new_game(player)
    parts = title.strip().split("|")
    if len(parts) != 4 or parts[0] != "chess" or parts[1] != "move":
        return False, "This issue title is not a chess move, so nothing was played.", ""
    uci, stamp = parts[2].strip(), parts[3].strip()
    state = load()
    board = chess.Board()
    for m in state["moves"]:
        board.push_uci(m)
    current = f"{state['game']}.{len(state['moves'])}"
    if stamp != current:
        why = ("This link was for an earlier game." if stamp.split(".")[0] != str(state["game"])
               else "Someone moved before you, so this link was for an older position.")
        return False, f"{why} [Pick a move on the current board]({BOARD_LINK}).", ""
    try:
        move = chess.Move.from_uci(uci)
    except ValueError:
        move = None
    if move is None or move not in board.legal_moves:
        return False, f"`{uci}` is not a legal move in this position. [Back to the board]({BOARD_LINK}).", ""

    you = board.san(move)
    board.push(move)
    state["moves"].append(move.uci())
    state["players"].append(player)
    reply = f"You played **{you}**."
    summary = f"Chess: @{player} plays {you}"

    ended = finish(state, board)
    if not ended:
        reply_move = bot_move(board)
        bot = board.san(reply_move)
        board.push(reply_move)
        state["moves"].append(reply_move.uci())
        reply += f" The bot answered **{bot}**."
        summary += f", bot replies {bot}"
        ended = finish(state, board)
    reply += ended + f"\n\nThanks for playing! [See the board]({BOARD_LINK})."
    save(state)
    return True, reply, summary


if __name__ == "__main__":
    title, player, reply_path = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    changed, reply, summary = play(title, player)
    reply_path.write_text(reply + "\n", encoding="utf-8")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
            fh.write(f"changed={'true' if changed else 'false'}\nsummary={summary.replace(chr(10), ' ')}\n")
    print(("CHANGED " if changed else "UNCHANGED ") + summary)
    print(reply)

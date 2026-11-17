"""Play a Hard bot vs Hard bot game and render it as a looping, animated SVG replay.

Usage: python chess_replay.py <art_dir>

Writes <art_dir>/chess-replay.svg and <art_dir>/cache/replay.json (game number, moves, result).
Each game starts from a randomly picked opening, so every day's game is different. Long games that one side is
clearly winning are adjudicated, so the replay stays watchable.
Environment: REPLAY_SECONDS (think time per move, default 3), REPLAY_MAX_PLIES (default 160).
"""
import datetime as dt
import json
import os
import random
import sys
from pathlib import Path

import chess

from chess_engine import bot_move, evaluate

# A side that stays this far ahead (centipawns, roughly a rook) for this many plies after move 50 is declared the winner;
# at the move limit, a lead of ADJUDICATE_LIMIT_CP or more also decides the game.
ADJUDICATE_CP, ADJUDICATE_PLIES, ADJUDICATE_AFTER, ADJUDICATE_LIMIT_CP = 500, 8, 100, 250

OPENINGS = [
    ("Italian Game", "e2e4 e7e5 g1f3 b8c6 f1c4"),
    ("Ruy Lopez", "e2e4 e7e5 g1f3 b8c6 f1b5"),
    ("Sicilian Defence", "e2e4 c7c5"),
    ("French Defence", "e2e4 e7e6"),
    ("Caro-Kann Defence", "e2e4 c7c6"),
    ("Scandinavian Defence", "e2e4 d7d5"),
    ("Queen's Gambit", "d2d4 d7d5 c2c4"),
    ("King's Indian Defence", "d2d4 g8f6 c2c4 g7g6"),
    ("Nimzo-Indian Defence", "d2d4 g8f6 c2c4 e7e6 b1c3 f8b4"),
    ("London System", "d2d4 d7d5 c1f4"),
    ("English Opening", "c2c4 e7e5"),
    ("Reti Opening", "g1f3 d7d5 c2c4"),
    ("Pirc Defence", "e2e4 d7d6 d2d4 g8f6"),
    ("Scotch Game", "e2e4 e7e5 g1f3 b8c6 d2d4"),
]

FIRST_DAY = dt.date(2026, 11, 17)

# timing of the animation, in seconds
INTRO, STEP, MOVE, OUTRO, FADE = 1.6, 1.1, 0.55, 5.0, 0.8

# look (same avatar-blue palette as the rest of the profile)
GOLD, CREAM, MUTED = "#56b6ea", "#e6edf3", "#8d96a0"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
SANS = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
SQ, BX, BY = 56, 56, 92
W, H = BX * 2 + SQ * 8, 700
PIECES = {
    "p": '<rect x="24" y="80" width="52" height="11" rx="4"/><path d="M33 80 C40 66 43 58 43 48 L57 48 C57 58 60 66 67 80 Z"/>'
         '<rect x="35" y="43" width="30" height="7" rx="3.5"/><circle cx="50" cy="30" r="14"/>',
    "r": '<rect x="24" y="80" width="52" height="11" rx="4"/><path d="M33 80 L36 40 L64 40 L67 80 Z"/>'
         '<path d="M27 16 h11 v7 h7 v-7 h10 v7 h7 v-7 h11 v20 q0 4 -4 4 h-38 q-4 0 -4 -4 Z"/>',
    "b": '<rect x="24" y="80" width="52" height="11" rx="4"/><path d="M34 80 C40 68 44 60 44 52 L56 52 C56 60 60 68 66 80 Z"/>'
         '<rect x="35" y="46" width="30" height="7" rx="3.5"/><circle cx="50" cy="10" r="4.5"/>'
         '<path d="M50 13 C61 23 65 33 60 46 L40 46 C35 33 39 23 50 13 Z"/><path d="M56 24 L48 35" fill="none" stroke-width="4" stroke-linecap="round"/>',
    "n": '<rect x="24" y="80" width="52" height="11" rx="4"/>'
         '<path d="M34 80 C34 64 40 56 47 48 L38 52 L28 46 L30 38 L44 22 L46 11 L55 20 C69 26 75 46 70 80 Z"/>'
         '<circle cx="44" cy="31" r="1.6"/><path d="M58 27 C65 37 67 52 65 70" fill="none"/>',
    "q": '<rect x="24" y="80" width="52" height="11" rx="4"/><path d="M30 80 L33 66 L67 66 L70 80 Z"/>'
         '<path d="M31 66 L21 32 L34 50 L37 26 L45 48 L50 22 L55 48 L63 26 L66 50 L79 32 L69 66 Z"/>'
         '<circle cx="21" cy="29" r="4.5"/><circle cx="37" cy="22" r="4.5"/><circle cx="50" cy="18" r="4.5"/><circle cx="63" cy="22" r="4.5"/><circle cx="79" cy="29" r="4.5"/>',
    "k": '<rect x="24" y="80" width="52" height="11" rx="4"/><path d="M46 6 h8 v8 h8 v8 h-8 v14 h-8 v-14 h-8 v-8 h8 Z"/>'
         '<path d="M33 80 C35 68 28 58 28 48 C28 36 42 32 50 42 C58 32 72 36 72 48 C72 58 65 68 67 80 Z"/>',
}
STYLE = {True: ('#f0f6fc', '#0d1117'), False: ('#0d1117', GOLD)}  # fill, stroke per colour


# ------------------------------------------------------------------ the game
def white_eval(board):
    return evaluate(board) if board.turn == chess.WHITE else -evaluate(board)


def play_game(rnd, seconds, max_plies):
    """Play until the game ends; a long, clearly won game is adjudicated so the replay doesn't drag on."""
    name, line = rnd.choice(OPENINGS)
    board = chess.Board()
    for uci in line.split():
        board.push_uci(uci)
    streak, adjudicated = 0, None
    while not board.is_game_over(claim_draw=True) and len(board.move_stack) < max_plies:
        board.push(bot_move(board, "hard", seconds=seconds))
        ev = white_eval(board)
        streak = streak + 1 if abs(ev) >= ADJUDICATE_CP else 0
        if len(board.move_stack) >= ADJUDICATE_AFTER and streak >= ADJUDICATE_PLIES:
            adjudicated = ev > 0
            break
    if adjudicated is None and not board.is_game_over(claim_draw=True) and abs(white_eval(board)) >= ADJUDICATE_LIMIT_CP:
        adjudicated = white_eval(board) > 0
    outcome = board.outcome(claim_draw=True)
    if adjudicated is not None:
        score = "1–0" if adjudicated else "0–1"
        text = ("White" if adjudicated else "Black") + " wins on adjudication"
    elif outcome is None:
        score, text = "½–½", "Draw by move limit"
    elif outcome.winner is None:
        score, text = "½–½", "Draw by " + outcome.termination.name.replace("_", " ").lower()
    else:
        score = "1–0" if outcome.winner else "0–1"
        text = ("White" if outcome.winner else "Black") + " wins by checkmate"
    return {"opening": name, "moves": [m.uci() for m in board.move_stack], "score": score, "result": text}


# ------------------------------------------------------------------ animation helpers
def xy(square):
    return BX + chess.square_file(square) * SQ, BY + (7 - chess.square_rank(square)) * SQ


def pct(t, total):
    return f"{100 * t / total:.3f}%"


def keyframes(name, frames):
    """frames: list of (percent_string, css_declarations); duplicates collapse to the last one."""
    seen = {}
    for p, css in frames:
        seen[p] = css
    body = " ".join(f"{p}{{{css}}}" for p, css in sorted(seen.items(), key=lambda kv: float(kv[0][:-1])))
    return f"@keyframes {name}{{{body}}}"


def tr(x, y):
    return f"transform:translate({x}px,{y}px)"


def render(game, number, day):
    board = chess.Board()
    pieces = []           # each: type, colour, start, moves[(t, from, to)], out, inn
    at = {}
    for sq, pc in board.piece_map().items():
        at[sq] = len(pieces)
        pieces.append({"type": pc.symbol().lower(), "white": pc.color, "start": sq, "moves": [], "out": None, "in": None})

    ticks, marks, checks = [], [], []
    for k, uci in enumerate(game["moves"]):
        move = chess.Move.from_uci(uci)
        t = INTRO + k * STEP
        san = board.san(move)
        ticks.append((t, f"{board.fullmove_number}{'.' if board.turn else '…'} {san}"))
        marks.append((t, move.from_square, move.to_square))
        mover = at.pop(move.from_square)
        if board.is_en_passant(move):
            cap = move.to_square + (-8 if board.turn else 8)
        elif board.is_capture(move):
            cap = move.to_square
        else:
            cap = None
        if cap is not None:
            pieces[at.pop(cap)]["out"] = t + MOVE * 0.45
        pieces[mover]["moves"].append((t, move.from_square, move.to_square))
        at[move.to_square] = mover
        if board.is_castling(move):
            rank = chess.square_rank(move.from_square)
            kingside = chess.square_file(move.to_square) == 6
            rf, rt = chess.square(7 if kingside else 0, rank), chess.square(5 if kingside else 3, rank)
            rook = at.pop(rf)
            pieces[rook]["moves"].append((t, rf, rt))
            at[rt] = rook
        if move.promotion:
            pieces[mover]["out"] = t + MOVE
            at[move.to_square] = len(pieces)
            pieces.append({"type": chess.piece_symbol(move.promotion), "white": board.turn, "start": move.to_square,
                           "moves": [], "out": None, "in": t + MOVE})
        board.push(move)
        checks.append((t + MOVE, board.king(board.turn) if board.is_check() else None))

    end = INTRO + len(game["moves"]) * STEP
    total = end + OUTRO
    css, body = [], []

    # pieces: movers drawn last so they slide over the others
    order = sorted(range(len(pieces)), key=lambda i: len(pieces[i]["moves"]))
    for i in order:
        p = pieces[i]
        x0, y0 = xy(p["start"])
        anims = []
        if p["moves"]:
            frames = [("0%", tr(x0 + 3, y0 + 3))]
            for t, f, to in p["moves"]:
                fx, fy = xy(f)
                tx, ty = xy(to)
                frames.append((pct(t, total), tr(fx + 3, fy + 3) + ";animation-timing-function:cubic-bezier(.45,0,.2,1)"))
                frames.append((pct(t + MOVE, total), tr(tx + 3, ty + 3)))
            lx, ly = xy(p["moves"][-1][2])
            frames.append(("100%", tr(lx + 3, ly + 3)))
            css.append(keyframes(f"m{i}", frames))
            anims.append(f"m{i}")
        if p["out"] is not None:
            css.append(keyframes(f"o{i}", [("0%", "opacity:1"), (pct(p["out"], total), "opacity:1"),
                                           (pct(p["out"] + 0.25, total), "opacity:0"), ("100%", "opacity:0")]))
            anims.append(f"o{i}")
        if p["in"] is not None:
            css.append(keyframes(f"o{i}", [("0%", "opacity:0"), (pct(p["in"], total), "opacity:0"),
                                           (pct(p["in"] + 0.25, total), "opacity:1"), ("100%", "opacity:1")]))
            anims.append(f"o{i}")
        fill, stroke = STYLE[p["white"]]
        style = f' style="animation-name:{",".join(anims)}"' if anims else ""
        opacity = ' opacity="0"' if p["in"] is not None else ""
        body.append(f'<g class="a" transform="translate({x0 + 3} {y0 + 3})"{style}{opacity}>'
                    f'<use href="#pc-{p["type"]}" transform="scale(0.5)" fill="{fill}" stroke="{stroke}" '
                    f'stroke-width="3" stroke-linejoin="round"/></g>')

    # last-move and check highlights jump at the start of each move (steps timing)
    off = tr(-200, -200)
    for name, idx in (("hf", 1), ("ht", 2)):
        frames = [("0%", off)] + [(pct(t, total), tr(*xy(m[idx]))) for m in marks for t in [m[0]]]
        css.append(keyframes(name, frames + [("100%", tr(*xy(marks[-1][idx])) if marks else off)]))
    frames = [("0%", off)] + [(pct(t, total), tr(*xy(k)) if k is not None else off) for t, k in checks]
    css.append(keyframes("ck", frames + [("100%", frames[-1][1])]))

    # move ticker
    ticker = []
    for k, (t, text) in enumerate(ticks):
        t_next = ticks[k + 1][0] if k + 1 < len(ticks) else end
        css.append(keyframes(f"t{k}", [("0%", "opacity:0"), (pct(t, total), "opacity:1"),
                                       (pct(t_next, total), "opacity:0"), ("100%", "opacity:0")]))
        ticker.append(f'<text class="s" x="{W / 2}" y="{BY + SQ * 8 + 62}" text-anchor="middle" opacity="0" '
                      f'style="animation-name:t{k}" font-family="{MONO}" font-size="20" font-weight="700" fill="{CREAM}">'
                      f'{text}</text>')

    css.append(keyframes("res", [("0%", "opacity:0"), (pct(end + 0.4, total), "opacity:0"),
                                 (pct(end + 1.0, total), "opacity:1"), ("100%", "opacity:1")]))
    css.append(keyframes("cov", [("0%", "opacity:1"), (pct(FADE, total), "opacity:0"),
                                 (pct(total - FADE, total), "opacity:0"), ("100%", "opacity:1")]))
    css.append(keyframes("bar", [("0%", "transform:scaleX(0)"), (pct(INTRO, total), "transform:scaleX(0)"),
                                 (pct(end, total), "transform:scaleX(1)"), ("100%", "transform:scaleX(1)")]))

    squares = []
    for rank in range(8):
        for file in range(8):
            x, y = BX + file * SQ, BY + (7 - rank) * SQ
            squares.append(f'<rect x="{x}" y="{y}" width="{SQ}" height="{SQ}" fill="{"#9cc3e0" if (rank + file) % 2 else "#2b4f6e"}"/>')
    coords = "".join(f'<text x="{BX + i * SQ + SQ / 2}" y="{BY + SQ * 8 + 22}" text-anchor="middle">{c}</text>' for i, c in enumerate("abcdefgh"))
    coords += "".join(f'<text x="{BX - 20}" y="{BY + (7 - i) * SQ + SQ / 2 + 4}" text-anchor="middle">{i + 1}</text>' for i in range(8))
    defs = "".join(f'<g id="pc-{k}">{v}</g>' for k, v in PIECES.items())
    n_moves = (len(game["moves"]) + 1) // 2
    T = f"{total:.2f}s"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Hard bot vs Hard bot, game {number}: {game["opening"]}, {game["score"]} ({game["result"]}) after {n_moves} moves">
<style>
.a,.s,.h{{animation-duration:{T};animation-iteration-count:infinite;animation-timing-function:linear;animation-fill-mode:both}}
.s,.h{{animation-timing-function:steps(1,end)}}
#hf{{animation-name:hf}} #ht{{animation-name:ht}} #ck{{animation-name:ck}}
#res{{animation:res {T} linear infinite both}} #cov{{animation:cov {T} linear infinite both}}
#bar{{transform-box:fill-box;transform-origin:left center;animation:bar {T} linear infinite both}}
{chr(10).join(css)}
</style>
<defs>{defs}
  <linearGradient id="felt" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#17293d"/><stop offset="1" stop-color="#0d1117"/></linearGradient>
  <radialGradient id="glint" cx="85%" cy="92%" r="55%"><stop offset="0" stop-color="{GOLD}" stop-opacity="0.28"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>
</defs>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="30" fill="url(#felt)"/>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="30" fill="url(#glint)" stroke="{GOLD}" stroke-opacity="0.55" stroke-width="1.5"/>
<text x="{W / 2}" y="38" text-anchor="middle" font-family="{MONO}" font-size="11" letter-spacing="4" fill="{GOLD}">GAME #{number} · {day:%d %b %Y}</text>
<text x="{W / 2}" y="60" text-anchor="middle" font-family="{SANS}" font-size="14" fill="{MUTED}">{game["opening"]}</text>
<g transform="translate({BX} 24) scale(0.3)" fill="#f0f6fc" stroke="#0d1117" stroke-width="5"><use href="#pc-k"/></g>
<g transform="translate({W - BX - 30} 24) scale(0.3)" fill="#0d1117" stroke="{GOLD}" stroke-width="5"><use href="#pc-k"/></g>
<rect x="{BX - 6}" y="{BY - 6}" width="{SQ * 8 + 12}" height="{SQ * 8 + 12}" rx="8" fill="#161b22" stroke="{GOLD}" stroke-opacity="0.6"/>
{"".join(squares)}
<rect id="hf" class="h" width="{SQ}" height="{SQ}" fill="#a5dcf7" fill-opacity="0.35" style="transform:translate(-200px,-200px)"/>
<rect id="ht" class="h" width="{SQ}" height="{SQ}" fill="#a5dcf7" fill-opacity="0.5" style="transform:translate(-200px,-200px)"/>
<rect id="ck" class="h" width="{SQ}" height="{SQ}" fill="#ff5a3c" fill-opacity="0.55" style="transform:translate(-200px,-200px)"/>
{chr(10).join(body)}
<g font-family="{MONO}" font-size="12" font-weight="700" fill="{GOLD}">{coords}</g>
{chr(10).join(ticker)}
<rect x="{BX}" y="{BY + SQ * 8 + 84}" width="{SQ * 8}" height="3" rx="1.5" fill="{GOLD}" fill-opacity="0.18"/>
<rect id="bar" x="{BX}" y="{BY + SQ * 8 + 84}" width="{SQ * 8}" height="3" rx="1.5" fill="{GOLD}"/>
<text x="{W / 2}" y="{H - 22}" text-anchor="middle" font-family="{MONO}" font-size="11" fill="{MUTED}">{n_moves} moves · a new game every day</text>
<g id="res" opacity="0">
  <rect x="{BX + 44}" y="{BY + SQ * 3}" width="{SQ * 8 - 88}" height="{SQ * 2}" rx="16" fill="#0d1117" fill-opacity="0.92" stroke="{GOLD}" stroke-opacity="0.7"/>
  <text x="{W / 2}" y="{BY + SQ * 4 - 4}" text-anchor="middle" font-family="{SANS}" font-size="34" font-weight="800" fill="{GOLD}">{game["score"]}</text>
  <text x="{W / 2}" y="{BY + SQ * 4 + 28}" text-anchor="middle" font-family="{SANS}" font-size="16" fill="{CREAM}">{game["result"]}</text>
</g>
<rect id="cov" x="{BX - 6}" y="{BY - 6}" width="{SQ * 8 + 12}" height="{SQ * 8 + 100}" rx="8" fill="#0d1117" opacity="0"/>
</svg>'''


if __name__ == "__main__":
    art = Path(sys.argv[1])
    day = dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).date()
    number = (day - FIRST_DAY).days + 1  # one game per day, numbered from the first replay
    rnd = random.Random()
    game = play_game(rnd, float(os.environ.get("REPLAY_SECONDS", "3")), int(os.environ.get("REPLAY_MAX_PLIES", "160")))
    (art / "cache").mkdir(parents=True, exist_ok=True)
    (art / "chess-replay.svg").write_text(render(game, number, day), encoding="utf-8", newline="\n")
    (art / "cache" / "replay.json").write_text(json.dumps({"game": number, "date": day.isoformat(), **game}, indent=2) + "\n",
                                               encoding="utf-8", newline="\n")
    print(f"game {number}: {game['opening']}, {len(game['moves'])} plies, {game['score']} ({game['result']})")

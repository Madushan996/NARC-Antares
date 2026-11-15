"""Makes tools/openings.txt: random 8-ply openings that an engine judges level.

  python tools/make_openings.py ENGINE.exe [count]

Plays 8 random legal moves from the start, then keeps the position if a short
search scores it within 60 centipawns of equal.
"""
import random
import sys
from pathlib import Path

import chess
import chess.engine

HERE = Path(__file__).resolve().parent


def main():
    exe = sys.argv[1]
    want = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    rng = random.Random(2026)
    eng = chess.engine.SimpleEngine.popen_uci(exe)
    found, seen = [], set()
    tries = 0
    while len(found) < want and tries < want * 20:
        tries += 1
        board = chess.Board()
        for _ in range(8):
            moves = list(board.legal_moves)
            if not moves:
                break
            board.push(rng.choice(moves))
        if board.is_game_over() or len(board.move_stack) < 8:
            continue
        key = " ".join(m.uci() for m in board.move_stack)
        if key in seen:
            continue
        seen.add(key)
        info = eng.analyse(board, chess.engine.Limit(depth=8))
        cp = info["score"].white().score(mate_score=100000)
        if cp is not None and abs(cp) <= 60:
            found.append(key)
    eng.quit()
    lines = ["# Openings for tools/match.py: 8 random plies from the start position that",
             "# a depth-8 search scores within 60 centipawns of equal (tools/make_openings.py)."] + found
    (HERE / "openings.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(found)} openings from {tries} tries")


if __name__ == "__main__":
    main()

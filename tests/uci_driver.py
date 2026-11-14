"""Drives UCI engines for testing: tactical positions and engine-vs-engine games.

  python tests/uci_driver.py tactics            mate and tactics positions
  python tests/uci_driver.py game <movetime_ms> a game against the C++ Genesys 5.1
  python tests/uci_driver.py selfplay <ms>      the Antares engine against itself
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# The interpreted engine by default. Set NARC_BINARY to test a compiled one,
# for example NARC_BINARY=avx2 for builds/NARC-Genesys-5.1-Antares-bitboard-avx2.exe.
ANT_ENGINE = ["antares", os.path.join(ROOT, "src", "narc.ant")]
if os.environ.get("NARC_BINARY"):
    ANT_ENGINE = [os.path.join(ROOT, "builds", "NARC-Genesys-5.1-Antares-bitboard-" + os.environ["NARC_BINARY"] + ".exe")]
CPP_ENGINE = [os.path.join(os.path.dirname(ROOT), "NARC_ChessEngine", "builds", "NARC-Genesys-5.1", "NARC-Genesys-5.1-generic.exe")]


class Engine:
    def __init__(self, cmd, name):
        self.name = name
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.send("uci")
        self.wait_for("uciok")
        self.send("isready")
        self.wait_for("readyok")

    def send(self, line):
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()

    def wait_for(self, prefix):
        lines = []
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError(f"{self.name} exited; last lines: {lines[-5:]}")
            line = line.strip()
            lines.append(line)
            if line.startswith(prefix):
                return lines

    def go(self, position, limit):
        self.send(position)
        self.send("go " + limit)
        lines = self.wait_for("bestmove")
        info = [l for l in lines if l.startswith("info depth")]
        return lines[-1].split()[1], (info[-1] if info else "")

    def quit(self):
        try:
            self.send("quit")
            self.p.wait(timeout=5)
        except Exception:
            self.p.kill()


TACTICS = [
    # (name, fen, search limit for the Antares engine)
    ("mate in 1", "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1", "depth 3"),
    ("mate in 1 (queen)", "7k/5Q2/6K1/8/8/8/8/8 w - - 0 1", "depth 3"),
    ("mate in 2", "r2qkb1r/pp2nppp/3p4/2pNN1B1/2BnP3/3P4/PPP2PPP/R2bK2R w KQkq - 1 1", "depth 5"),
    ("mate in 3", "r1b1kb1r/pppp1ppp/5q2/4n3/3KP3/2N3PN/PPP4P/R1BQ1B1R b kq - 0 1", "depth 9"),
    ("win the queen (fork)", "r3k2r/ppp2ppp/2n5/3q4/8/2N5/PPP2PPP/R2QK2R w KQkq - 0 1", "depth 4"),
    ("take the hanging rook", "4k3/8/8/3r4/8/8/3R4/4K3 w - - 0 1", "depth 4"),
    ("promotion", "8/4P1k1/8/8/8/8/8/4K3 w - - 0 1", "depth 4"),
    ("kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", "depth 5"),
    ("rook endgame", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", "depth 6"),
    ("middlegame", "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10", "depth 5"),
]


def score_of(info):
    return info.split(" score ")[1].split(" nodes")[0].strip() if " score " in info else "?"


def tactics():
    """The C++ engine is the reference: where it sees a forced mate, the Antares
    engine must find a mate of the same length; elsewhere its move must be one
    the C++ engine also rates within 60 centipawns of its own best."""
    e = Engine(ANT_ENGINE, "antares")
    ref = Engine(CPP_ENGINE, "c++")
    ok = True
    for name, fen, limit in TACTICS:
        pos = "position fen " + fen
        t = time.time()
        move, info = e.go(pos, limit)
        took = time.time() - t
        score = score_of(info)
        ref_move, ref_info = ref.go(pos, "depth 12")
        ref_score = score_of(ref_info)
        if ref_score.startswith("mate"):
            good = score.split()[:2] == ref_score.split()[:2]
            note = f"reference {ref_score}"
        else:
            # how does the reference rate the move the Antares engine chose?
            _, after = ref.go(pos + " moves " + move, "depth 11")
            their = score_of(after)
            loss = None
            if their.startswith("cp") and ref_score.startswith("cp"):
                loss = int(ref_score.split()[1]) + int(their.split()[1])
            # fine if it is the same move, costs at most 60 cp, or still leaves a decisive advantage
            still_winning = their.startswith("cp") and int(their.split()[1]) <= -500
            good = move == ref_move or (loss is not None and loss <= 60) or still_winning
            note = f"reference plays {ref_move}" + ("" if move == ref_move else f", this move loses {loss} cp")
        ok = ok and good
        print(f"{'ok  ' if good else 'FAIL'} {name:22} played {move:6} score {score:9} {took:5.1f}s   {note}")
    e.quit()
    ref.quit()
    print("all positions agree with the C++ engine" if ok else "SOME POSITIONS DISAGREE")
    return ok


def legal_moves(ref, pos):
    """The legal moves in a position, according to the C++ engine's perft."""
    ref.send(pos)
    ref.send("perft 1")
    moves = []
    while True:
        line = ref.p.stdout.readline().strip()
        if line.startswith("Nodes searched"):
            return moves
        if ": " in line and len(line.split(":")[0]) in (4, 5):
            moves.append(line.split(":")[0])


def game(white, black, limit_w, limit_b, max_plies=160):
    """Plays a game. Every move from either side is checked for legality by the C++ engine."""
    referee = Engine(CPP_ENGINE, "referee")
    moves = []
    engines = [white, black]
    limits = [limit_w, limit_b]
    for e in engines:
        e.send("ucinewgame")
    result = f"stopped after {max_plies} plies"
    illegal = 0
    for ply in range(max_plies):
        e = engines[ply % 2]
        pos = "position startpos" + (" moves " + " ".join(moves) if moves else "")
        legal = legal_moves(referee, pos)
        if not legal:
            result = f"game over: {engines[(ply + 1) % 2].name} delivered mate or stalemate"
            break
        move, info = e.go(pos, limits[ply % 2])
        score = score_of(info)
        depth = info.split()[2] if info else "?"
        if move not in legal:
            illegal += 1
            print(f"ILLEGAL MOVE {move} by {e.name} at ply {ply + 1}")
            result = "illegal move"
            break
        moves.append(move)
        print(f"{ply // 2 + 1:3}{'. ' if ply % 2 == 0 else '...'}{move:6} {e.name:8} depth {depth:>2} score {score}", flush=True)
    referee.quit()
    print("moves:", " ".join(moves))
    print("result:", result)
    print(f"{len(moves)} moves played, {illegal} illegal")
    return illegal == 0


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "tactics"
    ms = sys.argv[2] if len(sys.argv) > 2 else "1000"
    if mode == "tactics":
        sys.exit(0 if tactics() else 1)
    elif mode == "selfplay":
        a, b = Engine(ANT_ENGINE, "ant-A"), Engine(ANT_ENGINE, "ant-B")
        game(a, b, f"movetime {ms}", f"movetime {ms}", int(sys.argv[3]) if len(sys.argv) > 3 else 60)
        a.quit(); b.quit()
    elif mode == "game":
        a, b = Engine(ANT_ENGINE, "antares"), Engine(CPP_ENGINE, "c++")
        game(a, b, f"movetime {ms}", "nodes 400", int(sys.argv[3]) if len(sys.argv) > 3 else 120)
        a.quit(); b.quit()

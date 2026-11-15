"""Plays two UCI engines against each other and says which is stronger.

  python tools/match.py NEW.exe OLD.exe [--games 200] [--tc 8+0.08] [--concurrency 2]
                        [--openings tools/openings.txt] [--pgn out.pgn]

Each opening is played twice, once with each engine as White. Clocks are real
(time used is measured here; running out of time loses). Games that are
clearly decided are stopped early: both engines agreeing on a big advantage
for 4 moves in a row, or on a near-zero score for 8 moves after move 40.
At the end it prints wins, draws and losses for NEW, and an Elo difference
with its 95% error margin.
"""
import argparse
import math
import os
import random
import sys
import threading
import time
from pathlib import Path

import chess
import chess.engine
import chess.pgn

HERE = Path(__file__).resolve().parent


def elo(score):
    score = min(max(score, 1e-6), 1 - 1e-6)
    return -400 * math.log10(1 / score - 1)


def summary(w, d, l):
    n = w + d + l
    if n == 0:
        return "no games"
    s = (w + d / 2) / n
    # 95% margin from the spread of game results
    var = (w * (1 - s) ** 2 + d * (0.5 - s) ** 2 + l * (0 - s) ** 2) / n
    se = math.sqrt(var / n) if n > 1 else 0.5
    lo, hi = elo(s - 1.96 * se), elo(s + 1.96 * se)
    los = 0.5 * (1 + math.erf((w - l) / math.sqrt(2 * (w + l)))) if w + l else 0.5
    return f"{w}-{d}-{l} ({n} games), score {s:.1%}, Elo {elo(s):+.0f} [{lo:+.0f}, {hi:+.0f}], LOS {los:.1%}"


def load_openings(path):
    lines = [l.strip() for l in Path(path).read_text(encoding="utf-8").splitlines()]
    return [l for l in lines if l and not l.startswith("#")]


class Match:
    def __init__(self, args):
        self.args = args
        base, inc = args.tc.split("+")
        self.base, self.inc = float(base), float(inc)
        self.openings = load_openings(args.openings)
        random.Random(args.seed).shuffle(self.openings)
        self.lock = threading.Lock()
        self.next_game = 0
        self.results = {"w": 0, "d": 0, "l": 0}
        self.games = []
        self.timeouts = {"new": 0, "old": 0}
        self.errors = 0

    def take(self):
        with self.lock:
            if self.next_game >= self.args.games:
                return None
            g = self.next_game
            self.next_game += 1
            return g

    def worker(self):
        engines = {}
        try:
            engines["new"] = chess.engine.SimpleEngine.popen_uci(self.args.new)
            engines["old"] = chess.engine.SimpleEngine.popen_uci(self.args.old)
            for e in engines.values():
                if self.args.option:
                    e.configure(dict(o.split("=", 1) for o in self.args.option))
            while True:
                g = self.take()
                if g is None:
                    break
                opening = self.openings[(g // 2) % len(self.openings)]
                new_white = g % 2 == 0
                try:
                    result, game = self.play(engines, opening, new_white, g)
                except chess.engine.EngineTerminatedError as e:
                    with self.lock:
                        self.errors += 1
                    print(f"game {g + 1}: an engine stopped ({e}); restarting", flush=True)
                    for k in engines:
                        try:
                            engines[k].quit()
                        except Exception:
                            pass
                    engines["new"] = chess.engine.SimpleEngine.popen_uci(self.args.new)
                    engines["old"] = chess.engine.SimpleEngine.popen_uci(self.args.old)
                    continue
                self.record(g, result, new_white, game)
        finally:
            for e in engines.values():
                try:
                    e.quit()
                except Exception:
                    pass

    def play(self, engines, opening, new_white, g):
        board = chess.Board()
        for uci in opening.split():
            board.push_uci(uci)
        white, black = ("new", "old") if new_white else ("old", "new")
        clocks = {chess.WHITE: self.base, chess.BLACK: self.base}
        for e in engines.values():
            e.protocol.send_line("ucinewgame")
            e.ping()
        big = {chess.WHITE: 0, chess.BLACK: 0}
        quiet = 0
        result = None
        reason = ""
        while result is None:
            if board.is_game_over(claim_draw=True):
                result = board.result(claim_draw=True)
                reason = "rules"
                break
            mover = board.turn
            who = white if mover == chess.WHITE else black
            limit = chess.engine.Limit(white_clock=clocks[chess.WHITE], black_clock=clocks[chess.BLACK],
                                       white_inc=self.inc, black_inc=self.inc)
            t0 = time.perf_counter()
            res = engines[who].play(board, limit, info=chess.engine.INFO_SCORE)
            used = time.perf_counter() - t0
            clocks[mover] -= used
            # a small margin for the time it takes to pass messages to and from the engine
            if clocks[mover] < -self.args.margin / 1000:
                result = "0-1" if mover == chess.WHITE else "1-0"
                reason = f"{who} lost on time"
                with self.lock:
                    self.timeouts[who] += 1
                break
            clocks[mover] += self.inc
            if res.move is None or res.move not in board.legal_moves:
                result = "0-1" if mover == chess.WHITE else "1-0"
                reason = f"{who} played an illegal move {res.move}"
                break
            score = res.info.get("score")
            board.push(res.move)
            # adjudication from both engines' scores (from White's side)
            if score is not None:
                cp = score.white().score(mate_score=100000)
                if cp is not None:
                    big[mover] = big[mover] + 1 if abs(cp) >= 1000 else 0
                    if big[chess.WHITE] >= 4 and big[chess.BLACK] >= 4:
                        result = "1-0" if cp > 0 else "0-1"
                        reason = "adjudicated: decisive"
                    if board.fullmove_number > 40 and abs(cp) <= 10:
                        quiet += 1
                    else:
                        quiet = 0
                    if quiet >= 16:
                        result = "1/2-1/2"
                        reason = "adjudicated: drawn"
        game = chess.pgn.Game.from_board(board)  # all the moves, from the start position
        game.headers.update({"Event": "match", "Round": str(g + 1), "White": white, "Black": black,
                             "Result": result, "Termination": reason, "TimeControl": self.args.tc})
        return result, game

    def record(self, g, result, new_white, game):
        if result == "1/2-1/2":
            k = "d"
        elif (result == "1-0") == new_white:
            k = "w"
        else:
            k = "l"
        with self.lock:
            self.results[k] += 1
            self.games.append(game)
            done = sum(self.results.values())
            if done % self.args.report == 0 or done == self.args.games:
                r = self.results
                print(f"[{done}/{self.args.games}] NEW vs OLD: {summary(r['w'], r['d'], r['l'])}", flush=True)

    def run(self):
        threads = [threading.Thread(target=self.worker) for _ in range(self.args.concurrency)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        r = self.results
        print(f"\nFinal: NEW {Path(self.args.new).name} vs OLD {Path(self.args.old).name}, {self.args.tc}")
        print(summary(r["w"], r["d"], r["l"]))
        print(f"time losses: new {self.timeouts['new']}, old {self.timeouts['old']}; engine restarts: {self.errors}")
        if self.args.pgn:
            with open(self.args.pgn, "w", encoding="utf-8") as f:
                for game in self.games:
                    print(game, file=f, end="\n\n")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("new")
    p.add_argument("old")
    p.add_argument("--games", type=int, default=200)
    p.add_argument("--tc", default="8+0.08")
    p.add_argument("--concurrency", type=int, default=2)
    p.add_argument("--openings", default=str(HERE / "openings.txt"))
    p.add_argument("--pgn")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--report", type=int, default=20)
    p.add_argument("--margin", type=float, default=100, help="ms an engine may go over its clock")
    p.add_argument("--option", action="append", help="NAME=VALUE for both engines")
    Match(p.parse_args()).run()
    # python-chess can leave engine threads waiting on Windows; everything is saved, so leave now
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()

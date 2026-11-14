# NARC Antares: an experiment

![NARC Antares](builds/logo/narc-genesys-antares-banner.png)

> **This is an experiment, not an update to NARC Genesys.** It is the NARC
> Genesys engine's code base re-written in
> [Antares](https://github.com/Madushan996/Antares-Programming-Language), my
> own programming language, to see how a real program does in it. It is not a
> new version and does not need any testing or rating. It is slower and weaker
> than the original, so to play against NARC or test it, use the C++
> NARC Genesys.

The NARC Genesys chess engine (C++, by Madushan Dissanayake) re-written in the
Antares language. It is a working UCI engine that searches the same way as the
original and uses a NARC Genesys network: `networks/narc-antares.nnue`, the
mixed249m twin-lane network from the Genesys development engine (16 king
buckets, 1024 hidden units of which 768 share their weights across king
buckets). Its evaluations are exactly the C++ development engine's with the
same network.

## Binaries (to try it out)

Ready-to-run engines are attached to the
[GitHub releases](https://github.com/Madushan996/NARC-Antares/releases)
(`python build.py` puts them in `builds/`):

| Files | What they are |
|---|---|
| `NARC-Antares-*.exe` | The current engine, about 460,000 to 475,000 positions per second |
| `NARC-Genesys-5.1-Antares-*.exe` | The earlier array-board engine (kept in `archive/array-board/`; it looks for the Genesys 5.1 network, which is no longer in `networks/`) |

Earlier builds of the bitboard engine, with the Genesys 5.1 network, are kept
in `archive/`: `bitboard-antares-1.0/` (Antares 0.2.0, the v1.0 release) and
`bitboard-antares-0.1/` (Antares 0.1.0).

Each comes in four variants:

| Ending | For |
|---|---|
| `-avx2.exe` | Processors with AVX2 (2013 and later). Use this one if it runs. |
| `-sse42.exe` | Processors with SSE4.2 (2009 and later) |
| `-generic.exe` | Any 64-bit PC |
| `-native.exe` | Built for exactly the machine that compiled it |

Add one to a chess GUI as a UCI engine, or run it and type UCI commands
(`uci`, `isready`, `position startpos moves e2e4`, `go depth 10`,
`go movetime 2000`, `go wtime 60000 btime 60000`, `stop`, `quit`) or the
extras `d` (show the board), `eval` and `perft 4`. It announces itself as
"NARC Antares".

Each binary has the network embedded (about 8.6 MB in all), so it is a single
self-contained file: copy it anywhere and it runs. The UCI option `EvalFile`
loads a different network file instead; both the twin-lane format (DRNNUE04)
and the earlier single-lane one (DRNNUE03, like the Genesys 5.1 network) work.

The `.bmp` next to each binary is its logo for Arena (100 x 50); the banner,
icon and `.ico` are in `builds/logo/`.

To rebuild the binaries (needs the `antares` command and Rust):

```bash
python build.py
```

The current binaries need Antares 0.3.0 or later: they use compact matrices
changed by row, which compiled programs do in place.

## Speed compared with the C++ engine

Same position (after 1. e4 e5), search to depth 13, best of six runs on the
development laptop, measured in the same session, both engines with the same
network:

| Engine | Positions searched | Positions per second |
|---|---|---|
| NARC Antares, avx2 | 214,964 | 462,000 |
| NARC Antares, native | 214,964 | 474,000 |
| C++ NARC Genesys development build | 170,730 | 1,004,000 |

With the Genesys 5.1 network (single lane) the same Antares code reached about
548,000 positions per second, against 433,000 for the C++ generic build and
1,027,000 for the C++ avx2 build. A twin-lane network needs two row updates and
two output sums per evaluation, so it costs the Antares engine more. Timings
on this laptop vary by tens of percent from run to run, and more when a chess
GUI is running engines at the same time.

What still separates it from the original:

- **The network.** About a third of the time goes to the network: the updates
  of the accumulators (the arithmetic is the same as the C++ engine's) and the
  calls around them.
- **Search values.** Scores, history and depths are ordinary Antares numbers
  (64-bit decimals) where the C++ engine uses integers.
- **Move generation.** Moves are generated without regard to pins and checked
  by playing them; the C++ engine generates only legal moves.
- **Checks the C++ does not make.** Array accesses are checked to be in range
  (against a constant for the fixed tables), and most functions report
  problems through a result value.

`antares build tests/profile.ant` and `tests/profile_eval.ant` time each
building block.

## Layout

| Path | What it holds |
|---|---|
| `src/board.ant` | Bitboards and attack tables, the position, making and taking back moves, move generation, exchange evaluation (SEE), FEN, perft. Ports `position.cpp`, `movegen.cpp`, `bitboard.cpp`, `perft.cpp` |
| `src/nnue.ant` | Loading the network; incremental accumulators; evaluation. Ports `nnue.cpp` |
| `src/search.ant` | The search and everything it learns while searching. Ports `search.cpp`, `movepick.cpp`, `tt.cpp`, `history.h` |
| `src/narc.ant` | The UCI front end and time management. Ports `uci.cpp`, `main.cpp` |
| `src/config.ant` | Finds the network: the embedded copy in a binary, otherwise the file |
| `networks/narc-antares.nnue` | The network (the mixed249m twin-lane network of the Genesys development engine); embedded into the binaries by `build.py`, read directly when running interpreted |
| `builds/` | The binaries |
| `archive/array-board/` | The earlier array-board version: its binaries and its `nnue.ant`, `search.ant`, `narc.ant` (its `board.ant` was not kept) |
| `build.py` | Builds the binaries |
| `tests/` | Tests and the timing breakdown |

To run the engine without compiling:

```bash
antares src/narc.ant
```

## Tests

| Command | What it checks |
|---|---|
| `antares tests/test_perft.ant` | Move generation: 11 perft counts on 6 standard positions |
| `antares tests/test_eval.ant` | Evaluation equals the C++ engine's `eval` output on 6 positions, and the incremental update equals a from-scratch evaluation after every move of three games (castling, en passant, promotions, king walks) |
| `python tests/uci_driver.py tactics` | With the C++ engine as reference: forced mates in 1, 2 and 3 found with the same length; other moves are the reference's choice or rated as good |
| `python tests/uci_driver.py selfplay 150 140` | A 140-move game against itself, every move checked for legality by the C++ engine |

Set `NARC_BINARY=avx2` (or `generic`, `sse42`, `native`) to run the two Python
tests against a binary instead of the interpreted engine. They expect the
original C++ build at
`Documents/NARC_ChessEngine/builds/NARC-Genesys-5.1/NARC-Genesys-5.1-generic.exe`.

All of these pass, interpreted and on the bitboard binaries. The interpreted
engine and every binary search exactly the same positions (237,721 at depth 13
above; 8,131 at depth 8). A 93-move game against the C++ engine, refereed by
it, had no illegal moves.

## What it shares with the C++ engine

The search features that are on by default in 5.1, with the 5.1 constants:
iterative deepening with aspiration windows, principal variation search,
quiescence search, transposition table, mate-distance pruning, reverse
futility pruning, razoring, null-move pruning, internal iterative reduction,
late-move, futility, history and SEE pruning, late-move reductions, check and
singular extensions with multi-cut, killers, counter moves, threat-split quiet
history, continuation history, capture history, the four correction histories,
the time manager with its stability / score-trend / node-share scaling, and
the 5.1 repetition rule. The evaluation is the same network with the same
arithmetic, updated incrementally and lazily as in the original.

## How it differs from the C++ engine

- **Move generation:** bitboards as in the original, but moves are generated
  without regard to pins and checked for legality by playing them, and
  sliding attacks come from ray tables and bit scans, not magic bitboards.
- **Evaluation:** a king move rebuilds that side's accumulator; there is no
  king-bucket cache.
- **Move ordering:** staged as in the original (hash move, captures, then
  quiet moves only if still needed), but killers and the counter move are
  ordered among the quiet moves by score instead of having their own stages.
- **Transposition table:** one entry per slot (262,144 slots), always
  replaced, instead of three-entry buckets with ageing. No `Hash` option.
- **One thread only.** No `Threads` option.
- **Not ported:** the features that are off by default in 5.1 (ProbCut, TT-PV,
  fifty-move damping, quiescence evasion pruning, the double-extension cap,
  doubt, root watch, four-ply continuation history), and the tools
  (`bench`, `datagen`, `relabel`, `nnuecheck`, `legalcheck`, tuning options).
- **Stopping:** the clock and the GUI are checked every 128 positions, so
  `Move Overhead` defaults to 80 ms instead of 10.

## Licence

GPL v3, the same as the original engine (see `LICENSE`).

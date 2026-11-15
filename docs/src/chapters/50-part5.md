# The Complete Engine {#part-complete .part}

The last pieces: how the engine talks to chess programs, how an Antares program becomes a fast native engine, and how to measure whether a change makes it stronger. The part ends with ideas for taking the engine further yourself.

# Talking UCI {#uci}

The interface file, `antares_chess.ant`, is the engine's front door. It reads commands from the GUI, sets up positions, starts searches and sends back the moves. This chapter reads it from the top.

## Finding the network

Before it can evaluate anything, the engine needs its network file. `config.ant` finds it:

@listing config.ant find_network

The built engine carries the network inside itself (Chapter 27), which Antares reads under the name `embedded:antares-chess.nnue`. When run from source, the engine looks next to the program and in a `networks` folder beside or above it. `program_folder()` is the folder holding the program being run.

The interface loads the network only when it's first needed, so that `uci` is answered instantly:

@listing antares_chess.ant ensure_network

## The main loop

The engine's last lines are its main loop. It reads one line at a time and hands it to `handle`:

@listing antares_chess.ant lines from "show \"{ENGINE_NAME} by"

Two details matter. A command that arrived *during* a search was saved by `should_stop` in `pending_line`, so it's handled first. And every command is handled inside `try`: if anything goes wrong, such as a malformed FEN from a GUI, the engine reports it in an `info string` line and carries on, instead of crashing in the middle of a game.

> **Antares.** `input()` reads one line, and gives `nothing` when there is no more input, which happens when the GUI closes the engine's input. That's why `line == nothing` ends the loop.

## Handling commands

@listing antares_chess.ant handle

Each command is a `when` branch. `split(line)` breaks the line into words, and the first word chooses the branch. Note `ucinewgame`: it clears the transposition table and all the history tables, so nothing learned in one game carries over to the next.

## Setting up a position

`position` comes in two forms: `position startpos moves e2e4 e7e5 ...` and `position fen <six FEN fields> moves ...`:

@listing antares_chess.ant set_position

The FEN fields are put back together into one text and passed to `set_fen`. Then each move is played with `play_text_move`, which finds the legal move with that name:

@listing board.ant find_move

@listing board.ant play_text_move

Moves from the GUI are played at ply `MAX_PLY + 2`, a slice of the move rows the search never uses for its own moves.

## Options

GUIs show an engine's options as settings the user can change, and send them with `setoption name <name> value <value>`:

@listing antares_chess.ant set_option

Option names may contain spaces, like `Move Overhead`, so the function collects the words between `name` and `value`, and those after `value`.

## go and bestmove

`go` (shown in Chapter 25) works out the time limits, calls `think`, and finally sends `bestmove`. One subtle rule of UCI: after `go infinite` the engine must not send `bestmove` until the GUI sends `stop`, even if it has finished searching. That's what the loop after `think()` waits for.

## Try it yourself

1. Add a command `side` that prints `white` or `black` for the side to move. Where in `handle` does it go?
2. What happens if you send `position startpos moves e2e5`? Try it.

## Summary

- `config.ant` finds the network, preferring the copy embedded in the built engine.
- The main loop reads lines and handles each inside `try`, so bad input never crashes the engine.
- `handle` chooses a branch by the first word; `set_position` reads FEN and moves; `set_option` reads options.

# Making It Fast {#fast}

Run from source, the engine searches a few thousand positions a second. Built with `antares build`, it searches over half a million. This chapter explains what building does, and the habits that let the compiler make the engine fast.

## Interpreted and compiled

When you run `antares src/antares_chess.ant`, Antares **interprets** the program: it translates each function into compact instructions for its own virtual machine and carries them out one by one. That's quick to start and great for experiments, but every operation pays for being general: is this value a number or text? Is this position inside the row?

`antares build` **compiles** the program instead. It works out the type of every variable, writes the whole program as Rust code, and has the Rust compiler turn that into native machine code. The result is a normal `.exe` that runs on its own, without Antares installed.

Measured on the same laptop, searching to depth 9 after 1. e4 e5:

| | Positions per second | perft 4 (728,887 positions) |
|---|---:|---:|
| Interpreted | 2,400 | 40 seconds |
| Compiled (avx2) | 314,000 | 0.055 seconds |

The compiled engine searches about 130 times faster, and generates moves over 700 times faster. In a longer search it reaches about 535,000 positions a second, close to half the speed of its C++ ancestor (1,138,000).

## Building the engine

@listing ../build.py lines from "# variant name"

`build.py` calls `antares build` once for each processor level:

- `--cpu x86-64` runs on any 64-bit PC;
- `--cpu x86-64-v2` uses SSE4.2 and the `popcnt` instruction (2009 and later);
- `--cpu x86-64-v3` uses AVX2 and BMI2 (2013 and later), whose wider vector instructions speed up the network's row additions;
- `--cpu native` uses everything the building computer has.

`--embed` packs the 25 MB network file into the `.exe`, and `--icon` gives it the star icon.

## Writing code the compiler loves

The compiler can only make code fast when it can be sure what kind of value each variable holds. The engine follows a few habits that make that easy.

**Fixed tables.** Every big table is made once at the top level with `ints(n)` or `zeros(n)` and afterwards only read and changed by position, like `board[sq] = p`. The compiler turns these into plain machine arrays.

**One kind of value per variable.** A variable that always holds an integer becomes a raw 64-bit machine integer. That's why the engine writes `int(0)` where it means an integer: `best_move = int(0)` makes it clear from the start that `best_move` is an integer, never a fraction.

**Constants.** A top-level variable given a value once and never changed, like `MAX_PLY = 120` or `MOVES_PER_PLY = 256`, is treated as a constant and built into the code.

**Ranges.** This is the biggest one. Each time a compiled program reads `board[sq]`, it must make sure `sq` is between 0 and 63, or a bug could read memory outside the row. These checks are small, but in move generation they run billions of times. With `within`, the engine tells the compiler the range of each square variable and of the position's state:

@listing board.ant lines from "board = ints(64) within 0 to EMPTY" to "halfmove = int(0)"

Antares checks a range once, when a value is *given* to the variable or passed to the function. After that, every use is known to be safe and the compiler leaves the check out. For example, in `rook_att(sq within 0 to 63, occ)`, the compiler knows `sq * 4 + 3` is at most 255, inside `rook_info`, so the table reads need no checks. Adding ranges made move generation 35 to 54% faster.

**Compact matrices for the network.** The network's weights and accumulators are compact 16-bit matrices, changed a row at a time with `update_rows` and read with `screlu_dot`. The compiler does these with vector instructions, adding 16 numbers at once on an AVX2 processor, and changes accumulator rows in place without copying.

> **Tip.** To see where the compiler couldn't make a variable fast, build with the setting `ANTARES_EXPLAIN=1`. It explains every variable it had to treat as a general value, and why.

## The engine's history, in speed

| Version | What changed | Built with |
|---|---|---|
| NARC Genesys 5.1 Antares Edition 1.0 | The first port of the C++ engine to Antares | Antares 0.2 |
| NARC Antares 2.0 | Twin-lane network, compact accumulators, magic bitboards, king-bucket cache | Antares 0.3 |
| NARC Antares 2.1 | Ranges: move generation 35 to 54% faster | Antares 0.4 |
| Antares Chess 1.0 | New name, bucketed transposition table with a `Hash` option | Antares 0.5 |

Each version of the engine pushed the language to get faster, and each version of the language made the engine faster.

## Try it yourself

1. Build the engine with `python build.py native` and compare its `perft 5` time with the interpreted engine's `perft 3` time. How many times faster is it per position?
2. Find three places in `search.ant` where a variable is started with `int(...)`. Why is each one an integer?

## Summary

- Interpreting runs the program on Antares's virtual machine; `antares build` compiles it to a native program through Rust.
- The compiled engine is over a hundred times faster.
- Fixed tables, one type per variable, constants, ranges and compact matrices let the compiler generate fast code.

# Testing and Measuring Strength {#testing}

How do you know the engine works? And when you change something, how do you know whether it got stronger? This chapter shows the engine's tests and its match tool, and the statistics needed to read the results honestly.

## Correctness tests

The engine has four kinds of test, each catching a different kind of bug:

| Test | What it checks |
|---|---|
| `antares tests/test_perft.ant` | Move generation: 11 perft counts on 6 standard positions (Chapter 12) |
| `antares tests/test_eval.ant` | The evaluation equals the C++ engine's on 6 positions, and the incremental update equals a from-scratch one after every move of three games (Chapter 16) |
| `python tests/uci_driver.py tactics` | Mates in 1, 2 and 3 are found, at the right length |
| `python tests/uci_driver.py selfplay 150 140` | A long game against itself, with every move checked for legality by the C++ engine |

The perft test has a neat extra check: after counting, the position's key must be what it was before, which proves `make` and `unmake` match.

## Is it stronger?

Correct isn't the same as strong. Most changes to a search, such as a new pruning rule or a different constant, make the engine search differently, and the only way to know if that's better is to play games. Many games: chess results are noisy, and a change worth 10 Elo needs thousands of games to prove.

`tools/match.py` plays two versions of an engine against each other:

```shell
python tools/match.py NEW.exe OLD.exe --games 300 --tc 8+0.08
```

The important details of a fair match:

- **Openings.** Engines are deterministic, so starting every game from the initial position would just repeat a few games. `tools/openings.txt` holds 400 openings, each 8 random moves long, chosen by `tools/make_openings.py` to be roughly level.
- **Both colours.** Each opening is played twice, with each engine as White once, so neither benefits from a lucky opening.
- **Real clocks.** Time is measured by the match tool, and running out of time loses.
- **Adjudication.** Games that are clearly decided are stopped early to save time: when both engines agree on a big advantage for 4 moves in a row, or on a near-zero score for 8 moves after move 40.

## Elo and error margins

The result is reported as an **Elo difference**. If one engine scores a fraction `s` of the points (wins plus half the draws), the Elo difference is:

```diagram
   Elo = -400 * log10(1/s - 1)

   s = 0.50  ->    0 Elo         s = 0.60  ->  +70 Elo
   s = 0.55  ->  +35 Elo         s = 0.75  -> +191 Elo
```

@listing ../tools/match.py summary

Just as important is the **error margin**. From the spread of the game results, the tool works out a range that contains the true Elo difference with 95% confidence. And **LOS**, the *likelihood of superiority*, is the chance that the new version really is the stronger one.

Here is a real result. When Antares Chess 1.0's new transposition table was tested against the version before, 120 games at 8 seconds plus 0.08 per move gave 24 wins, 67 draws and 29 losses: Elo -14, with a 95% range of -56 to +27. That range includes 0, so the test showed **no measurable difference**. Honest reporting means saying exactly that, not "-14 Elo", and not "it's better because it searches fewer positions".

> **Watch out.** Don't stop a match early because the result looks good. With few games, random swings are large, and a lucky start fades as more games are played.

## Try it yourself

1. A new version scores 160 points out of 300 games. What is the Elo difference?
2. Why is each opening played twice, once with each colour?

## Summary

- Perft, evaluation, tactics and self-play tests catch different kinds of bug.
- Strength is measured by matches with many varied openings, both colours and real clocks.
- Report the Elo difference *with* its error margin; a range that includes 0 means "no measurable difference".

# Where to Go Next {#next}

You have now seen every part of Antares Chess. This last chapter suggests ways to keep learning: projects to try on the engine, and ideas used by the strongest engines that Antares Chess doesn't have yet.

## Projects to try

These start small and grow. For each, use the tests and the match tool to check your work.

1. **A `divide` command.** Add a UCI command `divide N` that prints the perft count under each legal move, like the example in Chapter 12. Other engines have it, and it's the best tool for finding move-generation bugs.
2. **Your own evaluation.** Write a hand-made evaluation (material, piece-square tables, a bonus for passed pawns) in a new file, and switch the engine to it with an option. How much weaker is it than the network? A match will tell you.
3. **Tune a constant.** Pick one pruning constant from Chapter 22, change it a little, build, and run a match of a few hundred games. Can you find a better value?
4. **MultiPV.** Let the engine report its best few moves, not just one, with a `MultiPV` option. This means searching the root again with the best moves excluded.
5. **Pondering.** Let the engine think during the opponent's time, on the move it expects the opponent to play (UCI's `go ponder` and `ponderhit`).

## Ideas from the strongest engines

- **More threads.** Strong engines search with many threads at once, sharing the transposition table (a method called *Lazy SMP*). Antares Chess uses one thread.
- **Endgame tablebases.** Perfect play for all positions with up to 7 pieces, looked up from files instead of searched.
- **An opening book.** Prepared opening moves, played instantly.
- **Training your own network.** The network was trained for the C++ engine. Generating your own training positions with the engine's search and training a network on them is the most rewarding project of all, and the biggest.

## Learning more

The chess programming community has written a great deal about everything in this book. The **Chess Programming Wiki** describes almost every idea mentioned here, with its history and references. Reading the source of other open-source engines, especially Stockfish, shows many of the same ideas written in other languages.

## A last word

A chess engine is one of the best programs to learn from. It's small enough to understand completely, it has to be both correct and fast, and you can always measure whether a change made it better. Antares Chess shows that a small, readable language can be used to write a serious one. Now it's your turn: change something, run a match, and see what happens.

## Summary

- Try the projects: divide, a hand-made evaluation, tuning, MultiPV, pondering.
- The strongest engines add threads, tablebases, opening books and networks they trained themselves.
- The Chess Programming Wiki and open-source engines are the next places to learn.

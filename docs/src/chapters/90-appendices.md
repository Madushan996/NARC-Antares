# Antares Cheat Sheet {#cheatsheet .appendix}

The parts of the Antares language used by the engine, on two pages. The book *Learn Antares* and the *Antares Language Reference* cover everything else.

## Statements

| Statement | Meaning |
|---|---|
| `x = 5` | Make or change a variable |
| `change x = x + 1` | Change a top-level variable from inside a function |
| `x = int(0) within 0 to 63` | A top-level variable with a range, checked on every change |
| `show a, b` | Print values on one line |
| `when c { ... } else when d { ... } else { ... }` | Choose |
| `while c { ... }` | Loop while `c` is `yes` |
| `repeat n { ... }`, `repeat n as i { ... }` | Loop `n` times, `i` from 1 to `n` |
| `each x in list { ... }` | Loop over a list, a row or text |
| `stop`, `skip` | Leave the loop; go on to its next round |
| `to f(a, b) { ... }`, `to f(a) = ...` | Define a function; the last value is its answer |
| `to f(sq within 0 to 63)` | A function input with a range |
| `give x` | Answer from a function at once |
| `use "board"` | Load `board.ant` from the same folder |
| `try { ... } else problem { ... }` | Catch a problem; `problem` holds its message |
| `# ...` | A comment |

## Values

| Value | Examples |
|---|---|
| Numbers (may have fractions) | `3`, `1.5`, `-40` |
| Integers (64 bits, wrap around) | `0xFF00`, `int(12)` |
| Truth values | `yes`, `no` |
| No value | `nothing` |
| Text | `"e2e4"`, `"score {cp}"` (values inside `{ }`) |
| Lists | `[1, 2, 3]`, `["a", "b"]` |
| Rows of numbers | `ints(64)`, `zeros(4096)`, `ints([1, 2, 3])` |
| Maps | `{P: 0, N: 1}` |
| Compact matrices | `compact(row, rows, cols)` |

## Operators

| Operator | Meaning |
|---|---|
| `+ - * / %` | Arithmetic (`/` always gives a number, `%` the remainder) |
| `== != < <= > >=` | Comparisons |
| `and or not` | Logic |
| `& \| xor ~ << >>` | Bits (`&` binds more tightly than comparisons) |
| `a[i]`, `a[i] = x` | Read or change an item |

## Built-in functions used by the engine

| Function | Gives |
|---|---|
| `int(x)`, `ints(n)`, `zeros(n)` | An integer; a row of `n` integers; a row of `n` numbers |
| `popcount(b)`, `lowest_bit(b)`, `highest_bit(b)` | Count the 1 bits; the lowest or highest 1 bit's position |
| `div(a, b)` | Whole-number division |
| `rand_bits()`, `seed(n)` | 64 random bits; start the random numbers at a fixed point |
| `abs`, `min`, `max`, `floor`, `trunc`, `round`, `log` | The usual maths |
| `number(x)`, `text(x)` | A value as a number; as text |
| `len(x)`, `has(x, y)`, `push(list, x)`, `join(list, sep)` | Length; contains; add an item; join into text |
| `split(t)`, `trim(t)`, `lower(t)`, `upper(t)` | Split text into words; trim spaces; change case |
| `check(c, message)`, `fail(message)` | Raise a problem |
| `clock()` | Seconds since some fixed moment, for timing |
| `input()`, `input_waiting()` | Read a line (`nothing` at the end); is a line waiting? |
| `read_binary(file, kind, start, count)` | Whole numbers from a binary file |
| `exists(file)`, `program_folder()` | Does a file exist; the running program's folder |
| `compact(x, rows, cols)`, `expand(c)` | 16-bit storage; back to an ordinary row |
| `update_rows(base, m, add, n_add, sub, n_sub)` | `base` plus some rows of `m` minus others |
| `screlu_dot(x, w, cap)` | The sum of `clip(x, 0, cap)² × w` |
| `clip(x, lo, hi)`, `sum(x)` | Clip every number; add a row up |

## Commands

| Command | Does |
|---|---|
| `antares file.ant` | Runs a program |
| `antares build file.ant out.exe` | Compiles a program; `--cpu`, `--embed file`, `--icon file.ico` |
| `ANTARES_EXPLAIN=1` | When building, explains which variables couldn't be made fast |

# Glossary {#glossary .appendix}

**Accumulator.** The network's hidden layer for one side's view, kept up to date as moves are played (Chapter 16).

**Alpha, beta.** The window of an alpha-beta search: alpha is the score the side to move is sure of, beta the score at which the opponent will avoid the position (Chapter 17).

**Alpha-beta pruning.** Skipping moves that can't change the minimax result.

**Aspiration window.** A narrow search window around the previous depth's score (Chapter 18).

**Beta cutoff.** Stopping the search of a position because a move scored at least beta.

**Bitboard.** A 64-bit integer with one bit per square (Chapter 5).

**Bound.** Whether a stored score is exact, a lower bound or an upper bound (Chapter 20).

**Bucket.** A group of entries in the transposition table; also a group of king squares, or of piece counts, sharing network weights.

**Cache line.** The 64 bytes the processor fetches from memory at once.

**Centipawn.** A hundredth of a pawn, the unit of evaluation scores.

**Continuation history.** Move-ordering scores for a move given the move before it (Chapter 21).

**Correction history.** Learned corrections to the evaluation for positions with the same pawns or pieces (Chapter 24).

**Depth.** How many more plies a search looks ahead.

**Evaluation.** A score for a position without looking ahead (Part III).

**Extension.** Searching a move deeper than normal (Chapter 23).

**FEN.** A standard line of text describing a position (Chapter 8).

**Fail high, fail low.** A search result at or above beta, or at or below alpha.

**Futility pruning.** Skipping moves that can't raise the score to alpha (Chapters 19 and 22).

**GUI.** A program that shows the board and runs engines.

**Hash move.** The best move stored in the transposition table for a position.

**History.** Move-ordering scores learned from which quiet moves caused cutoffs (Chapter 21).

**Horizon effect.** Misjudging a position because something important happens just beyond the search depth (Chapter 19).

**Iterative deepening.** Searching depth 1, 2, 3, ... until time runs out (Chapter 18).

**Killer move.** A quiet move that caused a cutoff at the same ply in a sibling position.

**King bucket.** One of 16 groups of king squares, each with its own network weights.

**LMR.** Late move reductions: searching late moves with less depth (Chapter 23).

**Magic bitboards.** Finding slider attacks with a multiplication and a table look-up (Chapter 7).

**Mate score.** A score meaning a forced checkmate, `MATE` minus the plies to mate.

**Minimax, negamax.** Choosing moves by assuming both sides play their best; negamax scores for the side to move (Chapter 17).

**Move generation.** Listing the moves in a position (Chapter 11).

**MVV.** Most valuable victim: ordering captures by what they capture.

**NNUE.** An efficiently updatable neural network, the kind of evaluation Antares Chess uses (Chapter 15).

**Node.** One position visited by the search.

**Null move.** Passing the turn, used to prune (Chapters 10 and 22).

**Null window.** A search window one point wide, answering only "better than alpha or not".

**Perft.** Counting all positions a number of plies ahead, to test move generation (Chapter 12).

**Ply.** One move by one side.

**Principal variation (PV).** The line of best play the search expects.

**Pruning.** Skipping moves or positions without searching them.

**Pseudo-legal move.** A move that follows the movement rules but may leave the king in check.

**PVS.** Principal variation search: the first move with a full window, the rest with null windows.

**Quiescence search.** A search of captures only, at the end of the main search (Chapter 19).

**Quiet move.** A move that isn't a capture or promotion.

**Reduction.** Searching a move less deeply than normal.

**SCReLU.** Squared clipped ReLU: clip to between 0 and 1, then square. The network's activation.

**SEE.** Static exchange evaluation: working out the captures on one square (Chapter 13).

**Singular extension.** Extending a hash move that is much better than every other move.

**Transposition.** The same position reached by different move orders.

**Transposition table (TT).** The table remembering search results by position key (Chapter 20).

**UCI.** The Universal Chess Interface, the text protocol between GUIs and engines (Chapter 26).

**Zobrist hashing.** Making a position key by `xor`ing random numbers for its facts (Chapter 9).

**Zugzwang.** A position where any move makes things worse.

# Map of the Source {#map .appendix}

Every function in the engine, with the line where it starts, what it does, and the chapters that show its code. This table was made from the source when the book was built.

@functionmap

# Answers to the Exercises {#answers .appendix}

## Chapter 2: How a Chess Engine Thinks

**1.** 20 × 20 = 400.
**2.** Worse, by about one and a half pawns: scores are for the side to move.

## Chapter 3: Antares for Engine Programmers

**1.** One way:

```antares
to is_set(bits, n) = bits & (1 << n) != 0
show is_set(13, 3), is_set(13, 1)
```

```output
yes no
```

**2.** One way:

```antares
squares = ints(8)
repeat 8 as i { squares[i - 1] = (i - 1) * 8 }
show squares
```

```output
[0, 8, 16, 24, 32, 40, 48, 56]
```

**3.** 8: `0xFF00` has eight 1 bits, the second byte.

## Chapter 4: Running Antares Chess

**1.** The answer depends on the computer's speed, since the engine searches as deep as two seconds allow. On the laptop used for this book it reached depth 15 and chose `g1f3`.
**2.** `position startpos moves e2e4 c7c5` then `eval` gives 17 centipawns for White, the side to move.

## Chapter 5: Bitboards

**1.** `grid(~(by_color[0] | by_color[1]))` shows ranks 3 to 6 filled.
**2.** `popcount(by_color[1])` is 16.
**3.** e4 is 4 + 3 × 8 = 28, and `1 << 28` is the bitboard of e4.

## Chapter 6: Attack Tables

**1.** `squares(knight_att[63])` gives `g6 f7`.
**2.** `attacked(20, 0)` is `yes` (e3 is attacked by the d2 and f2 pawns); `attacked(36, 0)` is `no`.
**3.** In the corner, only three of the king's eight neighbouring squares are on the board.

## Chapter 7: Magic Bitboards

**1.** The mask is b2 to g7, 6 squares, so 2<sup>6</sup> = 64 entries.
**2.** `b2 d2`: the bishop is surrounded by its own pawns, and its attacks stop at the first blocker in each direction.
**3.** One way:

```antares
use "book"
to queen_att(sq, occ) = rook_att(sq, occ) | bishop_att(sq, occ)
show popcount(queen_att(27, 0))
```

```output
27
```

## Chapter 8: The Position

**1.** `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1`
**2.** A black rook is 1 × 8 + 3 = 11; a white queen is 4.
**3.** For example `r3k2r/8/8/8/8/8/8/R3K2R w KQ - 0 1` gives `castle` = 3.

## Chapter 9: Zobrist Hashing

**1.** One way:

```antares
use "book"
set_fen(START_FEN)
before = hash
i = find_move("e2e4", 0)
make(mv_from[i], mv_to[i], mv_flag[i])
unmake(mv_from[i], mv_to[i], mv_flag[i])
show hash == before
```

```output
yes
```

**2.** The same pieces with a different side to move is a different position, with different legal moves and a different score.

## Chapter 10: Making and Taking Back Moves

**1.** 6 | (21 << 6) = 6 + 1344 = 1350, and `move_text(1350)` is `g1f3`.
**2.** `square_name(ep)` is `e3`.
**3.** 7 (binary 0111): a move from or to a8 removes Black's queen-side right (8), whether the rook moves or is captured.

## Chapter 11: Generating Moves

**1.** 31 legal moves.
**2.** For example `4k3/8/8/8/8/8/1r6/R3K3 w Q - 0 1`: the rook on b2 attacks b1, but `e1c1` is among the legal moves.
**3.** 4 captures: Qxe5, Qxf7, Qxh7 and Bxf7.

## Chapter 12: Perft

**1.** 2,812.
**2.** `e2e4`, with 13,160 positions.

## Chapter 13: Static Exchange Evaluation

**1.** Without the d1 rook, White loses the rook for a pawn: -400. `see_ge(11, 35, CAPTURE, -400)` is `yes` and `-399` is `no`.
**2.** For example `4k3/8/3p4/4n3/3P4/8/8/4K3 w - - 0 1`: `see_ge(27, 36, CAPTURE, 200)` is `yes` (the pawn wins a knight, 300, and is lost, 100).

## Chapter 14: Judging a Position

**1.** Only in positions where the two sides have different numbers of bishops, such as a bishop against a knight.
**2.** Add `knight_bonus(sq)` for each white knight and subtract it for each black knight, using the bit loop of Chapter 5 on `by_type[1] & by_color[0]` and `by_type[1] & by_color[1]`.

## Chapter 15: The Neural Network

**1.** 2304 + 5 × 64 + 3 = 2627 (the king on e1 mirrors to d1, square 3).
**2.** `view_m` is 64 and `view_base` 768: the king on g1 is on the right half, so the board is mirrored, and g1 mirrors to b1, which is bucket 1.

## Chapter 16: Accumulators

**1.** After `e1g1`, White's view needed a refresh, because White's king moved. For Black's view, the white king is just a piece that moved, so an ordinary update.
**2.** 32: every piece on the board.

## Chapter 17: Minimax and Alpha-Beta

**1.** It still returns 3, after 8 leaves: the new move's first reply is worth 1 for White, already worse than 3, so its other replies are cut off.
**2.** Move C, worth 14.

## Chapter 18: Iterative Deepening

**1.** At depth 8 the engine chose `b1c3`, with a score of 62.
**2.** An interrupted iteration has searched only some moves, and its best move may not have been compared fairly with the others.

## Chapter 19: Quiescence Search

**1.** Yes: the d4 pawn is undefended, so Qxd4 simply wins it. After Qxd4 both the evaluation and the quiescence search give -792 for White.
**2.** In check, standing pat would mean ignoring the check, which isn't allowed: every way out of check must be tried.

## Chapter 20: The Transposition Table

**1.** 64 MB / 64 bytes = 1,048,576 buckets; with 1 MB, 16,384.
**2.** Yes, with a lower bound (2), depth 4 and the move `c7c5`.
**3.** A shallower search saw less, so its score could be wrong at the depth needed now.

## Chapter 21: Move Ordering

**1.** 13 updates (it reaches 15,204).
**2.** A killer is good in the sibling positions at the *same* ply, where the same threats usually exist.

## Chapter 22: Pruning

**1.** trunc((3 + 16) / (2 - 1)) = 19.
**2.** In king and pawn endgames zugzwang is common: passing would be the best move if it were allowed, so the null-move search would think the position is better than it really is.

## Chapter 23: Reductions and Extensions

**1.** 3 - 1 - 1 = 1 ply less.
**2.** Most later moves aren't better than the first, and a null window proves that quickly. A move that does score above alpha is searched again with the full window.

## Chapter 24: Correction History

**1.** About 155, a little more than 150: the four weights add up to 136, a little more than the 128 that would cancel the factor 16 exactly.
**2.** An error may depend on who is to move: the same structure can be good for the side to move and bad for the other.

## Chapter 25: Time Management

**1.** Soft 0.330 s, hard 1.320 s.
**2.** A depth started after the soft limit would probably not finish; the hard limit must be checked inside the search, or a long depth could lose on time.

## Chapter 26: Talking UCI

**1.** Add a branch `else when cmd == "side" { when side == 0 { show "white" } else { show "black" } }` to `handle`, before the closing brace.
**2.** `play_text_move` can't find the move, so the engine answers `info string illegal move e2e5` and stops reading the moves.

## Chapter 27: Making It Fast

**1.** The built engine is several hundred times faster per position at perft.
**2.** For example `best_move = int(0)`, `buckets = int(1)` in `set_hash`, and `best_i = int(-1)` in `pick`: each holds a move code, a count or a slot number, always whole numbers.

## Chapter 28: Testing and Measuring Strength

**1.** 160 / 300 = 0.533, so Elo = -400 × log10(1/0.533 - 1) = about +23.
**2.** So that neither engine gains from an opening that happens to favour one colour.

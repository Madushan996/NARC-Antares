# Getting Started {#part-start .part}

What a chess engine is, the parts it is made of, the Antares language it is written in, and how to run it. By the end of this part you will have talked to the engine yourself, and you will know your way around its four source files.

# Welcome {#welcome}

This book takes a real, strong chess engine apart, one piece at a time, and explains every part of it. The engine is **Antares Chess**. It uses the same ideas as the world's best engines, including a neural network to judge positions, and it searches over half a million positions a second on an ordinary laptop. It is written entirely in **Antares**, a small programming language that is easy to read.

You will learn two things at once:

- **Chess engine programming.** How a computer stores a chess position, finds every legal move, judges who is better and looks ahead many moves to choose the best one. These ideas are shared by almost every strong engine, so what you learn here carries over to any engine in any language.
- **The Antares language.** Every idea is shown in real Antares code, and the language is explained as it comes up. If you already know a little Antares, you will see how its features are used in a large program that has to be fast.

## Who this book is for

You don't need to be a chess expert or an experienced programmer. You do need to know how the pieces move, and it helps to have written a few small programs before, in any language. The companion book *Learn Antares* teaches the language from the very first step; this book picks up where it leaves off, and Chapter 3 gives a quick refresher of everything the engine uses.

If you are new to chess programming, read the chapters in order: each one builds on the last. If you already know how engines work, you can jump to any chapter to see how Antares Chess does it.

## The code in this book is the real code

Most of the code in this book comes in one of two kinds of box.

A **listing** is part of the engine itself. Its dark header names the source file, the function and the line numbers:

@listing board.ant in_check

These are not copies typed into the book. Each listing was read from the engine's source files at the moment this book was made, so it is exactly the code that runs.

An **example** is a small program written for the book, followed by what it printed:

```antares
use "board"
set_fen(START_FEN)
show "White has {popcount(by_color[0])} pieces"
```

```output
White has 16 pieces
```

Many examples start with `use "board"` (or `use "search"`), which loads the engine's own code, and then experiment with it. Every one of them was run when the book was made, and the output box shows what it really printed. You can run them yourself: save the example in the engine's `src` folder and run it with `antares`, as Chapter 4 shows.

## Boxes in the margins

Four kinds of note appear in the text:

> **Chess note.** A rule or idea from chess itself, for readers who want a reminder.

> **Antares.** A feature of the Antares language, explained where the engine first uses it.

> **In the engine.** A detail of how Antares Chess does something, or why.

> **Watch out.** A mistake that is easy to make when you write your own engine.

## How this book is organised

1. **Part I, Getting Started:** what an engine is, an Antares refresher, and running the engine.
2. **Part II, The Board:** bitboards, attack tables, magic bitboards, the position, making moves, generating moves, and testing it all with perft.
3. **Part III, Evaluation:** how the engine judges a position, from counting material to the neural network it really uses.
4. **Part IV, Search:** looking ahead. Alpha-beta, iterative deepening, the transposition table, move ordering, pruning, extensions and time management.
5. **Part V, The Complete Engine:** talking to chess programs over UCI, making the engine fast, and measuring its strength.

Most chapters end with exercises. The answers are at the back, with a chess programming glossary, an Antares cheat sheet and a map of every function in the engine.

## Summary

- Antares Chess is a strong chess engine written entirely in Antares.
- This book explains all of it, teaching chess programming and Antares together.
- Listings are the engine's real code, read from its source; examples were all run.

# How a Chess Engine Thinks {#big-picture}

Before looking at any code, it helps to see the whole machine at once. This chapter describes the five parts of a chess engine and how they work together when the engine is asked for a move.

## A program that plays chess

A **chess engine** is a program that is given a chess position and answers with the move it thinks is best. That's all. It has no board to draw and no buttons to press: the pretty board you play on belongs to a separate program, a **chess GUI** (graphical user interface) such as Arena, Cute Chess or En Croissant. The GUI and the engine talk by sending lines of text to each other, in a language called **UCI**, the Universal Chess Interface.

```diagram
   +---------------------+   "position startpos moves e2e4"   +-------------------+
   |                     |   "go wtime 60000 btime 60000"     |                   |
   |      Chess GUI      | ---------------------------------> |   Antares Chess   |
   |  (draws the board)  |                                    |   (the engine)    |
   |                     | <--------------------------------- |                   |
   +---------------------+   "info depth 12 score cp 31 ..."  +-------------------+
                             "bestmove g1f3"
```

Because UCI is just text, you can also talk to an engine yourself by typing, which Chapter 4 shows.

## The five parts

Every strong engine has the same five parts. Antares Chess keeps them in four files:

| Part | What it does | File |
|---|---|---|
| **The board** | Stores the position: which piece is on which square, whose turn it is, castling rights and so on | `board.ant` |
| **Move generation** | Lists every move that can be played in a position, and plays and takes back moves | `board.ant` |
| **Evaluation** | Looks at a position *without* looking ahead and gives a score: how good it is for the side to move | `nnue.ant` |
| **Search** | Looks ahead: tries moves, then the replies, then the replies to those, and uses the evaluation at the end of each line | `search.ant` |
| **The interface** | Talks UCI with the GUI, and decides how much time to spend | `antares_chess.ant` |

A fifth, tiny file, `config.ant`, finds the neural network file the evaluation needs.

## Looking ahead

How do you choose a move? You think: "If I play this, they might play that, and then I could play this..." An engine does the same, but much faster and very systematically. It builds a **game tree**: the current position at the root, every legal move as a branch, every reply as a branch of a branch, and so on.

```diagram
                         position now
              /               |               \
          1. e4             1. d4            1. Nf3  ... (20 moves)
         /  |  \           /  |  \           /  |  \
      e5   c5   e6 ...  d5  Nf6  e6 ...   d5  Nf6  c5 ... (20 replies each)
      ...
```

The tree grows very fast. There are 20 moves in the starting position and 20 replies to each, so 400 positions after one move each. After three moves each there are about 119 million. No computer can look at all of them for long, so the art of chess programming is to look at the **right** ones. Part IV shows how Antares Chess searches over half a million positions a second, and still skips almost all of the tree.

At the end of each line it looks at, the search asks the evaluation for a score. Then it works backwards: at each step, the side to move picks the move that is best *for them*. This idea, called **minimax**, is the heart of every chess engine, and Chapter 17 explains it with small examples.

## Scores and centipawns

Engines measure advantage in **centipawns**: hundredths of a pawn. A score of +100 means "about a pawn better", +300 about a knight, and 0 an equal position. Scores are always from the point of view of one side, usually the side to move. A **mate score** is a special very large number meaning "this side can force checkmate"; Antares Chess uses 32000 minus the number of half-moves to mate.

> **Chess note.** A **ply** is one move by one side, a half-move. "Searching to depth 10" means looking 10 plies ahead: five moves by each side.

## What happens when the engine is asked to move

1. The GUI sends the position (`position ...`) and the clock times (`go ...`).
2. The interface sets up the board and works out how long it may think.
3. The search looks ahead 1 ply, then 2, then 3, and so on, each time a little deeper, until time runs out. After each depth it reports what it found.
4. Inside the search, positions are made by playing moves on the board, judged by the evaluation, and remembered in a table so they are not searched twice.
5. When time is up, the interface sends `bestmove` with the best move found.

The rest of the book follows this machine from the bottom up: first the board, then evaluation, then search, then the interface.

## Try it yourself

1. In the game tree above, how many positions are there after one move by White and one reply by Black, if there are 20 moves for each side?
2. A search reports `score cp -150`. Is the side to move better or worse, and by about how much?

## Summary

- An engine takes a position and answers with a move; a GUI draws the board, and they talk in UCI.
- The five parts are the board, move generation, evaluation, search and the interface.
- The search builds a game tree and uses minimax; scores are in centipawns.

# Antares for Engine Programmers {#antares}

This chapter is a quick tour of the parts of Antares that the engine uses. If you know Antares already, skim it. If you are new to it, read it carefully and run the examples: the rest of the book assumes you can read code like this.

## Values and variables

A variable is made by giving it a value with `=`. `show` prints values, and text can hold values inside `{ }`:

```antares
depth = 6
name = "Antares Chess"
show "{name} searches to depth {depth}"
show depth * 2, depth / 4
```

```output
Antares Chess searches to depth 6
12 1.5
```

`show` with several values separated by commas prints them on one line with spaces between. Ordinary numbers can have fractions, so `6 / 4` is 1.5.

## Integers and bits

Chess engines work with the individual **bits** of whole numbers, so Antares has **integers**: whole numbers of exactly 64 bits. A number written in hexadecimal with `0x` is an integer, and `int(x)` turns a number into one. The bit operators work on integers:

```antares
a = int(12)                # binary 1100
show a & 10, a | 3, a xor 5, a << 2, a >> 2, ~a
show popcount(0xFF), lowest_bit(0x50), highest_bit(0x50)
```

```output
8 15 9 48 3 -13
8 4 6
```

| Operator or function | Meaning |
|---|---|
| `a & b` | bits that are 1 in both |
| `a \| b` | bits that are 1 in either |
| `a xor b` | bits that are 1 in exactly one |
| `~a` | every bit flipped |
| `a << n`, `a >> n` | bits shifted left or right by `n` places |
| `popcount(a)` | how many bits are 1 |
| `lowest_bit(a)`, `highest_bit(a)` | the position of the lowest or highest 1 bit |
| `div(a, b)` | whole-number division, dropping the remainder |

Part II is built on these operators, and Chapter 5 explains them slowly with pictures.

## Lists and rows

A list is written with square brackets. Items are numbered from 0:

```antares
piece_names = ["pawn", "knight", "bishop", "rook", "queen", "king"]
show piece_names[1], len(piece_names)
values = ints(4)
values[2] = 500
show values
```

```output
knight 6
[0, 0, 500, 0]
```

`ints(n)` makes a **row** of `n` integers, all 0, and `zeros(n)` a row of `n` ordinary numbers. Rows are the engine's main data structure: almost every table in it is a row made once at the start. `ints([...])` turns a list of numbers into a row of integers.

## Decisions and loops

Antares uses `when` for "if", and `while`, `repeat` and `each` for loops. `stop` leaves a loop early and `skip` goes on to the next round:

```antares
repeat 3 as i {
    show "round {i}"
}
n = 0
while yes {
    n = n + 1
    when n % 2 == 0 { skip }
    when n > 7 { stop }
    show "odd: {n}"
}
each piece in ["queen", "rook"] {
    when piece == "queen" { show "9 points" } else { show "5 points" }
}
```

```output
round 1
round 2
round 3
odd: 1
odd: 3
odd: 5
odd: 7
9 points
5 points
```

> **Watch out.** `repeat n as i` counts `i` from **1** to `n`, but rows are numbered from **0**. That's why the engine often writes `repeat 64 as n { sq = n - 1 ... }` to visit squares 0 to 63.

## Functions

A function is written with `to`. The value of its last line is its answer, and `give` answers early. A function that fits on one line can be written with `=`:

```antares
to piece_value(kind) {
    when kind == 0 { give 100 }
    when kind == 4 { give 900 }
    300
}
to double(x) = x * 2
show piece_value(0), piece_value(4), piece_value(1), double(21)
```

```output
100 900 300 42
```

`yes` and `no` are the two truth values, and `nothing` means "no value".

## Variables in functions: change

Variables made inside a function belong to it. A function can read the program's top-level variables, but to *change* one it must say `change`:

```antares
nodes = 0
to visit() {
    change nodes = nodes + 1
}
repeat 5 { visit() }
show nodes
```

```output
5
```

The engine's position is kept in top-level variables (`side`, `hash`, `ep` and so on), so you will see `change` all over the board code. Changing *an item* of a top-level row, like `board[sq] = p`, needs no `change`: the row itself stays the same row.

## Ranges with within

A top-level variable or a function input can declare the numbers it may hold, with `within`:

<!-- error -->
```antares
to square_name(sq within 0 to 63) = "abcdefgh"[sq % 8] + text(div(sq, 8) + 1)
show square_name(12)
show square_name(64)
```

```output
e2

Problem on line 1: sq only holds numbers from 0 to 63, not 64
     1 | to square_name(sq within 0 to 63) = "abcdefgh"[sq % 8] + text(div(sq, 8) + 1)
```

Ranges catch mistakes early. They also make the compiled engine faster, because the compiler knows that a square number can never be outside the board and leaves out the checks it would otherwise need. Chapter 27 shows how much this helps.

## Maps and text

A map holds named values. The engine uses one to turn FEN letters into piece numbers:

```antares
fen_piece = {P: 0, N: 1, k: 13}
show fen_piece["N"], has(fen_piece, "Q")
words = split("position startpos moves e2e4")
show len(words), words[2], upper("e2e4"), "abc"[1]
```

```output
1 no
4 moves E2E4 b
```

## Files and problems

A program can be split into files. `use "board"` loads `board.ant` from the same folder, so its functions and variables can be used. This is how the engine's files fit together:

```diagram
   antares_chess.ant  --use-->  search.ant  --use-->  nnue.ant  --use-->  board.ant
           |
           +----------use-->  config.ant
```

When something goes wrong, Antares raises a **problem**. `check(condition, message)` raises one if a condition is false, and `try ... else problem` catches problems so the program can carry on:

```antares
try {
    check(1 + 1 == 3, "arithmetic is broken")
} else problem {
    show "caught: {problem}"
}
```

```output
caught: arithmetic is broken
```

The engine uses `check` to test its own tables as they are built, and `try` so that one bad command from a GUI never crashes it.

## Try it yourself

1. Write a function `is_set(bits, n)` that gives `yes` when bit `n` of `bits` is 1.
2. Using `repeat`, make a row `squares` of 8 integers holding 0, 8, 16, ..., 56.
3. What does `popcount(0xFF00)` give? Work it out, then run it.

## Summary

- Integers are 64 bits; `&`, `|`, `xor`, `~`, `<<`, `>>`, `popcount`, `lowest_bit` and `highest_bit` work on bits.
- `ints(n)` and `zeros(n)` make rows; most engine tables are rows.
- `when`, `while`, `repeat ... as`, `each`, `stop` and `skip` control the flow; `to` makes functions and `give` answers early.
- `change` changes a top-level variable from inside a function; `within` declares a range.
- `use` loads another file; `check` and `try` raise and catch problems.

# Running Antares Chess {#running}

Now let's meet the engine. This chapter shows how to run it, talk to it in UCI, use it from a chess GUI and build it into a fast program.

## Getting the engine

The engine's home is its GitHub repository, *Antares_Chess*. You can download a ready-made `.exe` from its releases page, or get the whole source to follow this book. The source folder looks like this:

| Path | What it holds |
|---|---|
| `src/board.ant` | The board, making moves, move generation, exchange evaluation, FEN, perft |
| `src/nnue.ant` | The neural-network evaluation |
| `src/search.ant` | The search, the transposition table, move ordering |
| `src/antares_chess.ant` | The UCI interface and time management |
| `src/config.ant` | Finds the network file |
| `networks/antares-chess.nnue` | The trained network (25 MB) |
| `tests/` | Perft and evaluation tests |
| `tools/` | Match and opening tools |
| `build.py` | Builds the `.exe` files |

To run the engine from its source you need Antares 0.5.0 (0.4.0 or later works). To build `.exe` files you also need Rust.

## Running it from source

The engine is an ordinary Antares program, so you can run it with `antares`:

```shell
antares src/antares_chess.ant
```

It prints its name and waits for UCI commands. Run like this it is **interpreted**: Antares reads the program and carries it out step by step. That is perfect for learning and experimenting, but slower than the built engine.

## Talking UCI

Here is a real session with the engine. The lines after `>` were typed; everything else is the engine's answer:

```session
Antares Chess by Madushan Dissanayake (Sri Lanka)
> uci
id name Antares Chess
id author Madushan Dissanayake (Sri Lanka)
option name Hash type spin default 64 min 1 max 256
option name Move Overhead type spin default 80 min 0 max 5000
option name EvalFile type string default embedded:antares-chess.nnue
uciok
> isready
readyok
> position startpos moves e2e4 e7e5
> d
8  r n b q k b n r
7  p p p p . p p p
6  . . . . . . . .
5  . . . . p . . .
4  . . . . P . . .
3  . . . . . . . .
2  P P P P . P P P
1  R N B Q K B N R

   a b c d e f g h
> go depth 8
info depth 1 seldepth 3 score cp 33 nodes 37 nps 37000 time 1 pv g1f3
info depth 2 seldepth 3 score cp 111 nodes 71 nps 9206 time 8 pv g1f3 a7a6 f3e5
info depth 3 seldepth 3 score cp 111 nodes 125 nps 15929 time 8 pv g1f3 a7a6 f3e5
info depth 4 seldepth 4 score cp 135 nodes 263 nps 31323 time 8 pv g1f3 c7c5 f3e5 d7d6
info depth 5 seldepth 7 score cp 56 nodes 1100 nps 112907 time 10 pv f1c4 a7a6 g1f3 d7d6 d2d4 e5d4
info depth 6 seldepth 9 score cp 27 nodes 2203 nps 193161 time 11 pv g1f3 d7d6 d2d4 e5d4 d1d4 g8f6
info depth 7 seldepth 14 score cp 25 nodes 4269 nps 293114 time 15 pv b1c3 f8c5 g1f3 d7d6 d2d4 e5d4 f3d4
info depth 8 seldepth 14 score cp 42 nodes 11686 nps 402389 time 29 pv b1c3 b8c6 g1f3 g8f6 d2d4 e5d4 f3d4 d7d6 d4c6
bestmove b1c3
> quit
```

What the commands mean:

| Command | Meaning |
|---|---|
| `uci` | "Are you a UCI engine?" The engine names itself, lists its options and ends with `uciok` |
| `isready` | "Are you ready?" The engine loads its network if needed and answers `readyok` |
| `position startpos moves e2e4 e7e5` | Set up the starting position and play these moves. `position fen ...` sets up any position |
| `go depth 8` | Think, 8 plies deep. `go movetime 1000` thinks for one second; `go wtime ... btime ...` gives the clocks |
| `stop` | Stop thinking now and answer |
| `quit` | Leave |
| `d`, `eval`, `perft 5` | Extras for people: show the board, show the evaluation, count positions (Chapter 12) |

Each `info` line is a progress report: the **depth** reached, the deepest ply looked at (**seldepth**), the **score** in centipawns for the side to move, how many positions (**nodes**) were searched, how many per second (**nps**), the time in milliseconds, and the **pv**, the principal variation: the line of best play the engine expects. Moves are written as the from-square and to-square, like `g1f3`, with a letter added for promotions (`e7e8q`).

Notice that the depth-1 search thought `g1f3` wins a pawn: one ply deep it can't see that Black would answer the attack on e5. By depth 5 the score had come back to a realistic +0.56, and by depth 8 the engine preferred `b1c3`. Deeper search sees more.

## Using it in a chess GUI

To play against the engine, add it to a chess GUI as a UCI engine. In most GUIs this is something like *Engines, Install new engine*, then choosing the `.exe`. The GUI then sends all the commands above for you. The release files come with a small logo for Arena: put the `.bmp` file next to the `.exe` of the same name.

## Building a fast engine

`antares build` translates an Antares program into a native program. The engine's `build.py` builds four versions, for different generations of processor:

```shell
python build.py            # all four, into builds/
python build.py avx2       # just one
```

Each version has the network file packed inside it, so it is one file you can copy anywhere. The built engine searches about 535,000 positions a second on a 2016 laptop, more than a hundred times faster than the interpreted one. Chapter 27 explains how.

## Running the book's examples

The examples in this book are small Antares programs that `use` the engine's own files. To run one, save it in the engine's `src` folder, for example as `src/try.ant`, and run it:

```shell
cd src
antares try.ant
```

Here is one to try. It sets up a position, shows the board and counts the legal moves:

```antares
use "board"
set_fen("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
show board_text()
n = 0
moves = generate(0, no)
repeat moves as i {
    k = i - 1
    make(mv_from[k], mv_to[k], mv_flag[k])
    when not attacked(king_sq[0], 1) { n = n + 1 }
    unmake(mv_from[k], mv_to[k], mv_flag[k])
}
show "White has {n} legal moves"
```

```output
8  r . b q k b n r
7  p p p p . p p p
6  . . n . . . . .
5  . . . . p . . .
4  . . . . P . . .
3  . . . . . N . .
2  P P P P . P P P
1  R N B Q K B . R

   a b c d e f g h
White has 27 legal moves
```

Don't worry about how it works yet. By the end of Part II you will understand every line.

## Try it yourself

1. Start the engine and ask it to think for two seconds about the starting position (`go movetime 2000`). Which move does it choose?
2. Set up the position after `1. e4 c5` and use `eval` to see the engine's score.

## Summary

- `antares src/antares_chess.ant` runs the engine interpreted; `python build.py` builds fast `.exe` files.
- The engine speaks UCI: `uci`, `isready`, `position`, `go`, `stop`, `quit`, plus `d`, `eval` and `perft`.
- `info` lines report depth, score, nodes, speed and the principal variation.
- The book's examples run from the `src` folder and use the engine's own code.

# Evaluation {#part-eval .part}

How the engine judges a position without looking ahead. We start with the simplest possible evaluation, counting material, and build up to the neural network Antares Chess really uses, and the tricks that let it judge a new position with a handful of additions instead of a full calculation.

# Judging a Position {#judging}

At the end of every line it looks at, the search needs to know: how good is this position? The **evaluation** answers with a single number. This chapter shows what an evaluation must do, and builds a simple one, before the next chapters look at the neural network the engine really uses.

## What an evaluation gives

The evaluation looks at one position, without trying any moves, and gives a score in centipawns **from the point of view of the side to move**: positive when the side to move is better, negative when it is worse. Antares Chess's `evaluate()` works this way:

```antares
use "search"
use "config"
load_network(NETWORK_FILE)
set_fen(START_FEN)
show evaluate()
set_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/R1BQKBNR w KQkq - 0 1")
show evaluate()
set_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/R1BQKBNR b KQkq - 0 1")
show evaluate()
```

```output
25
-366
417
```

In the starting position White, to move, is a little better: +25, a quarter of a pawn, for the advantage of moving first. Take away White's b1 knight and White is more than three pawns worse (-366). With Black to move in that same position, the score is from Black's side, and Black is better (+417). The two numbers aren't exactly opposite, because having the move is worth something too.

Scoring from the side to move's point of view makes the search simpler, as Chapter 17 shows: every side tries to make the score as big as possible, so the same code works for both colours.

## Counting material

The oldest evaluation is to add up the pieces. A pawn is worth 100, a knight about 320, a bishop about 330, a rook 500 and a queen 900. With bitboards, counting is one `popcount` per piece type and colour:

```antares
use "book"
values = [100, 320, 330, 500, 900, 0]
to material() {
    total = 0
    repeat 6 as k {
        t = k - 1
        total = total + values[t] * (popcount(by_type[t] & by_color[0]) - popcount(by_type[t] & by_color[1]))
    }
    when side == 0 { give total }
    -total
}
set_fen(START_FEN)
show material()
set_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/R1BQKBNR w KQkq - 0 1")
show material()
set_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/R1BQKBNR b KQkq - 0 1")
show material()
```

```output
0
-320
320
```

An engine with only this evaluation and a good search already plays reasonable chess: it won't give pieces away, and it takes pieces when it can. But it has no idea where pieces belong.

## Where pieces stand

A knight in the centre controls eight squares; in a corner it controls two. So engines add **piece-square tables**: a bonus or penalty for each piece on each square. Here is a simple one for knights, worth 10 points less for each step away from the centre:

```antares
use "book"
to knight_bonus(sq) {
    f = number(sq % 8)
    r = number(div(sq, 8))
    round(30 - 10 * (abs(f - 3.5) + abs(r - 3.5)))
}
each sq in [0, 1, 21, 27, 36, 63] {
    show "knight on {square_name(sq)}: {knight_bonus(sq)}"
}
```

```output
knight on a1: -40
knight on b1: -30
knight on f3: 0
knight on d4: 20
knight on e5: 20
knight on h8: -40
```

> **Antares.** Square numbers are integers, and Antares won't silently mix an integer with a fraction like 3.5: it asks you to say `number(x)` first. That way a calculation never loses its fractions, or its 64-bit exactness, by accident.

Add this for every knight (and similar tables for the other pieces) and the engine starts to develop its knights towards the centre.

Real hand-written evaluations have hundreds of terms like these: pawn structure (doubled, isolated and passed pawns), king safety, mobility (how many moves each piece has), rooks on open files, bishop pairs and many more, each with a carefully tuned weight. The C++ engines of the 1990s and 2000s were built this way, and some reached a very high level.

## Learning to evaluate

Since 2020, the strongest engines evaluate with a **neural network** instead. Instead of a programmer guessing what matters and how much, the network *learns* to judge positions by being shown millions of positions together with how the games actually turned out, or with the scores of deep searches.

The kind of network used is called **NNUE**, short for *Efficiently Updatable Neural Network* (the letters are reversed in a pun on the Japanese word *nue*, a mythical creature). It was invented by Yu Nasu in 2018 for the game shogi, and is now used by Stockfish and almost every strong engine. Its trick, explained in Chapter 16, is that when a move is played, the network's result can be updated with a few additions instead of being worked out again.

Antares Chess's network was trained for its C++ ancestor, NARC Genesys. It knows about everything a hand-written evaluation does, and much it doesn't, and it was never told any of it directly.

## Try it yourself

1. Change the `material` example so that a bishop is worth 350. In which positions does that make a difference?
2. Add the knight bonus to `material` for every knight on the board (White's added, Black's subtracted).

## Summary

- The evaluation scores a position without looking ahead, in centipawns, for the side to move.
- Material counting is the simplest evaluation; piece-square tables add where pieces stand.
- Hand-written evaluations have hundreds of tuned terms; modern engines learn them with a neural network (NNUE).

# The Neural Network {#network}

This chapter opens up the network: what goes in, what happens inside, and what comes out. You don't need to know anything about neural networks beforehand. Everything here is addition and multiplication.

## A network in one picture

```diagram
   INPUTS                 HIDDEN LAYER                  OUTPUT
   (which pieces are      (1024 numbers for White's     one number:
    on which squares)      view, 1024 for Black's)       the score

   white pawn on e4  --+
   black king on g8  --+-->  [ h1  h2  h3 ... h1024 ]  --+
   white knight f3   --+         (the side to move)     |
        ...          --+                                 +-->  squared, clipped,
                         -->  [ h1  h2  h3 ... h1024 ]  --+     weighted, added
                                 (the other side)                  = score
```

The network has three stages:

1. **Inputs.** Each input is a yes-or-no fact of the form "there is a white pawn on e4". There are 768 such facts: 2 colours × 6 piece types × 64 squares. In a position with 32 pieces, 32 of them are "yes" and the rest "no".
2. **The hidden layer.** 1024 numbers. Each is worked out by adding up a **weight** for every input that is "yes", plus a starting value, its **bias**. The weights are what the network learned in training: a big table of numbers, one row of 1024 for each input.
3. **The output.** Each hidden number is clipped to between 0 and 255, squared, and multiplied by an output weight; these are all added up, giving the score.

The hidden layer is worked out twice: once from White's point of view and once from Black's (the board turned round, so "my pawns" and "their pawns" swap). The side to move's view and the other side's view each have their own output weights.

## Inputs from each side's view

From each side's view, a piece is "mine" or "theirs", and the board is seen from that side. Black's view is the board flipped upside down, so that for both sides their own pieces start at the bottom. This lets one set of weights serve both colours.

The engine goes further. It also **mirrors** the board left-to-right when the king is on the e to h files, so that the king is always on the left half. And it chooses one of 16 sets of weights depending on where the king stands, called **king buckets**, so that a pawn on f2 can mean something different when your king is on g1 than when it is on c1.

The square transforms are kept in a table, `xf`, worked out at the start:

@listing nnue.ant lines from "# Square transforms." to "# The king lane"

And the 16 king buckets cover the king's square after mirroring:

@listing nnue.ant lines from "# Sixteen king buckets" to "# Square transforms."

Every square near the corner the king starts in has its own bucket (0 to 7 on the first two ranks). Further up the board, where kings rarely go, squares share buckets.

`set_view` works out the transform and bucket for one side's view, from that side's king:

@listing nnue.ant set_view

`view_m` picks the transform: 0 as the board is, 64 mirrored, 128 flipped for Black, 192 both. `view_base` is where the king bucket's 768 rows start in the weight table. Then each piece's input number is:

@listing nnue.ant feature

The input number is the bucket's base, plus 64 rows per piece type, plus the transformed square, plus 384 if the piece belongs to the other side. Let's see a few:

```antares
use "search"
set_fen(START_FEN)
set_view(0)
show "white's view: base {view_base}, knight g1 is {feature(0, 1, 6)}, black knight g8 is {feature(0, 9, 62)}"
set_view(1)
show "black's view: base {view_base}, knight g1 is {feature(1, 1, 6)}, black knight g8 is {feature(1, 9, 62)}"
```

```output
white's view: base 2304, knight g1 is 2369, black knight g8 is 2809
black's view: base 2304, knight g1 is 2809, black knight g8 is 2369
```

Both kings are on e1 and e8 at the start, which mirror to d1 and d8; seen from each side's own end, that's bucket 3, starting at row 3 × 768 = 2304. The knight on g1 mirrors to b1 (square 1), so its input is 2304 + 64 + 1 = 2369; the black knight, the other side's, adds 384 more. And as you'd hope, White's knight on g1 seen by White is exactly the same input as Black's knight on g8 seen by Black: the two views are perfectly symmetrical.

## Two lanes

Antares Chess's network has one more idea, which its author calls **twin lanes**. Of the 1024 hidden numbers, 768 use weights *shared* by all king buckets (768 rows in total), and only 256 have weights that depend on the king bucket (768 × 16 = 12,288 rows). The shared lane learns what pieces are worth in general; the king lane learns how that changes with the king's position. The file's header says how wide the shared lane is:

@listing nnue.ant lines from "# Two file formats are read." to "use \"board\""

## Loading the network

The network file holds the weights as 16-bit whole numbers. `load_network` reads them with `read_binary` and stores them as **compact** matrices:

@listing nnue.ant load_network

It checks the file's first eight bytes (the text `DRNNUE04` or `DRNNUE03`) and its shape, and then reads, in order: the shared lane's weights, the king lane's weights, the biases, the output weights for each of the 16 output rows, and the 8 output biases.

> **Antares.** `compact(x, rows, cols)` stores whole numbers from -32768 to 32767 in 2 bytes each instead of 8, as a matrix. The king lane's weights are 12,288 rows of 256 numbers, over three million numbers: compact storage makes them four times smaller, so far more of them fit in the processor's fast cache memory. `m[r]` is row `r` of a compact matrix.

## Whole numbers instead of fractions

Neural networks are usually trained with fractional numbers. To be fast, NNUE networks are **quantised**: the trained weights are multiplied by a scale and rounded to whole numbers. In this network, a hidden value of 255 stands for 1.0. That's why the hidden values are clipped to between 0 and 255, and why the final result has to be divided back down.

## The output

Here is the whole output stage:

@listing nnue.ant network_units

Step by step:

1. Count the pieces on the board. The network has 8 **output buckets**, separate output weights for positions with 2 to 5 pieces, 6 to 9 and so on up to 30 to 32, because what matters in an endgame is different from the middlegame.
2. Get the two hidden layers, the side to move's (`ours`) and the other side's (`theirs`), from the accumulators (next chapter).
3. For each, `screlu_dot` clips each value to 0 to 255, squares it, multiplies it by its output weight, and adds everything up. This is called **SCReLU**, a *squared clipped rectified linear unit*.
4. Add the shared lane's share the same way.
5. Divide down: by 255 for the squaring, add the bucket's output bias, then scale by 400 / 16320 into the network's units.

`evaluate` finally turns network units into centipawns:

@listing nnue.ant evaluate

## Try it yourself

1. In the starting position, after `set_view(0)`, what is `feature(0, 5, 4)` (the white king on e1)? Work it out before running it.
2. Move the white king to g1 in a FEN (no castling rights) and look at `view_m` and `view_base` after `set_view(0)`. Why did they change?

## Summary

- Inputs are "piece on square" facts, seen from each side, mirrored and bucketed by king square.
- The hidden layer is the bias plus the weight rows of every input present.
- The output squares each clipped hidden value, weights it and adds them up (SCReLU).
- Weights are whole numbers stored compactly; output buckets depend on how many pieces are left.

# Accumulators {#accumulators}

The hidden layer is the expensive part of the network: for each of 32 pieces, add a row of 1024 numbers, twice. Done for every position, that would make the engine far slower. This chapter shows how the engine keeps the hidden layer up to date as moves are played, so that most positions cost only a few additions.

## The key idea

The hidden layer is a **sum** of rows: the bias plus one weight row for each piece on the board. When a knight moves from g1 to f3, only two inputs change: "knight on g1" turns off and "knight on f3" turns on. So the new hidden layer is the old one, minus the row for "knight on g1", plus the row for "knight on f3". Two rows instead of thirty-two.

```diagram
   accumulator after Nf3  =  accumulator before
                             - weights["white knight on g1"]
                             + weights["white knight on f3"]
```

The running hidden layer is called the **accumulator**. A capture removes one more row; castling moves two pieces, so two rows out and two in. This is the "efficiently updatable" in NNUE.

> **Antares.** `update_rows(base, matrix, add, n_add, remove, n_remove)` gives `base`, plus the matrix rows listed in `add`, minus those listed in `remove`, in one step. It's built into Antares precisely for this job, and the compiled engine does it with fast vector instructions.

## One accumulator per ply

The search goes deep and comes back. When it takes a move back, the accumulator must go back too. Instead of subtracting again, the engine keeps a separate accumulator for every ply, all in one compact matrix:

@listing nnue.ant lines from "# accs[perspective * AH + ply]" to "to load_network"

Row `persp * AH + ply` is the accumulator for one side's view at that ply. Taking a move back costs nothing: the accumulator of the ply before is still there.

## Lazy updates

The engine is even lazier. Many positions in a search are never evaluated: they are cut off first, or are reached only to be passed through. So `make` doesn't update the accumulator at all. It only marks the next ply's accumulators as out of date:

@listing board.ant lines from "# fresh[perspective * AH + ply] = 1" to "# Generated moves"

`make` ends with `fresh[gply] = 0` and `fresh[AH + gply] = 0`. Only when `evaluate` is called does the engine bring the accumulator up to date:

@listing nnue.ant accumulator

The function:

1. If this ply's accumulator is already up to date, it's done.
2. Otherwise it walks back through the plies to the nearest one whose accumulator *is* up to date.
3. If on the way it passes a move of this side's **king**, it can't update by rows: the king's square chose the bucket and the mirroring, so *every* input of this view has changed. It refreshes the accumulator instead (below).
4. Otherwise it walks forward again, ply by ply, applying each move: subtract the moved piece on its old square, add it (or the promoted piece) on its new one, and subtract a captured piece or move a castling rook. The moves are read from the history tables `h_piece`, `h_src`, `h_dst`, `h_flag` and `h_cap` that `make` filled in.

Note that the two views are updated separately. A white king move forces a refresh of *White's* view only; Black's view of the same move is an ordinary update.

## The king-bucket cache

When the king moves, the view must be rebuilt. Adding up 32 rows from nothing is slow, so the engine keeps a cache: for each of the 64 (side, mirroring, bucket) combinations, the accumulator of the last position that used it, and the pieces of that position:

@listing nnue.ant lines from "# ----- king-bucket cache" to "# This view's accumulator for the current position"

A new position usually differs from the cached one by only a few pieces. So `refresh` compares the pieces now with the pieces then, bitboard by bitboard, and updates the cached accumulator by the differences:

@listing nnue.ant refresh

`now & ~was` is "pieces here now that weren't before", and `was & ~now` the opposite: bitboards make finding the difference two operations per piece type. This idea is called *Finny tables* in chess programming, after the programmer who popularised it.

## Checking it

Incremental updates are a classic source of hard-to-find bugs: one wrong row and the evaluation is slightly off, only in some positions. So the engine also has a slow, simple version that builds both views from scratch, `network_units_full`:

@listing nnue.ant network_units_full

`tests/test_eval.ant` plays three whole games and checks after every move that the fast and the slow version agree exactly. Here is the same idea on a short game with castling:

```antares
use "search"
use "config"
load_network(NETWORK_FILE)
set_fen(START_FEN)
each m in split("e2e4 e7e5 g1f3 b8c6 f1c4 g8f6 e1g1 f6e4 d2d4") {
    play_text_move(m)
    show "{m}: {network_units()} {network_units() == network_units_full()}  {evaluate()} cp"
}
```

```output
e2e4: -45 yes  -19 cp
e7e5: 63 yes  27 cp
g1f3: -76 yes  -33 cp
b8c6: 64 yes  27 cp
f1c4: -54 yes  -23 cp
g8f6: 53 yes  23 cp
e1g1: -107 yes  -46 cp
f6e4: 99 yes  42 cp
d2d4: -99 yes  -42 cp
```

Remember that the score is for the side to move: after White's moves it's Black's turn, so a negative score means White is better.

## Try it yourself

1. In the game above, after which move did White's accumulator need a refresh rather than an update? Why didn't Black's?
2. Use `rebuild(0)` to build White's view from scratch in the starting position. How many pieces did it add up?

## Summary

- The hidden layer is a sum of rows, so a move changes it by a few row additions and subtractions.
- Each ply has its own accumulator; taking a move back costs nothing.
- Accumulators are updated lazily, only when a position is evaluated.
- A king move forces a refresh, made quick by the king-bucket cache.
- A slow from-scratch version checks the fast one.

# Zobrist Hashing {#zobrist}

During a search the engine meets the same position again and again, reached by different move orders. To recognise a position quickly, it gives each one a 64-bit **key**: a number that is almost certainly different for every different position. This chapter explains how the key is made and kept up to date with almost no work.

## Random numbers for every fact

The method is called **Zobrist hashing**, after Albert Zobrist, who invented it in 1970. At the start, the engine makes a random 64-bit number for every fact a position can contain: "a white knight on f3", "black to move", "White may castle king-side", "en passant is possible on d6" and so on:

@listing board.ant lines from "seed(5120)" to "# Castling rights that survive"

A position's key is all the numbers of its facts combined with `xor`. `z_piece` has 16 × 64 = 1024 entries, one for each piece number and square, so the key for piece `p` on square `sq` is `z_piece[p * 64 + sq]`.

> **Antares.** `seed(5120)` starts the random-number generator at a fixed point, so `rand_bits()` gives the same "random" numbers every time the engine runs. The keys are then always the same, which makes the engine's behaviour repeatable.

## Why xor is perfect

`xor` has two properties that make it ideal:

- **Order doesn't matter:** `a xor b xor c` is the same as `c xor a xor b`. So the key depends only on *which* facts are true, not on the order the pieces were placed.
- **It undoes itself:** `a xor b xor b` is `a`. Adding a fact and removing it are the same operation.

So when a knight moves from g1 to f3, the engine doesn't rebuild the key from scratch. It `xor`s out "knight on g1" and `xor`s in "knight on f3", two operations however many pieces are on the board. That's exactly what `put_piece` and `take_piece` do, as you saw in the last chapter.

Let's watch it work. Two different move orders reach the same position, so they must give the same key:

```antares
use "book"
set_fen(START_FEN)
each m in ["e2e4", "e7e5", "g1f3", "b8c6"] { play_text_move(m) }
first = hash
set_fen(START_FEN)
each m in ["g1f3", "e7e5", "e2e4"] { play_text_move(m) }
show first == hash
play_text_move("b8c6")
show first == hash
```

```output
no
yes
```

The first answer is `no` because the positions really are different: the black knight is still on b8. Once it has moved to c6, both move orders have reached the same position, and the keys agree.

> **In the engine.** After a double pawn push, the key includes the en-passant square even when no enemy pawn could capture. So `1. e4 e5 2. Nf3` and `1. Nf3 e5 2. e4` give *different* keys: in the second, e3 is an en-passant square. It costs a few missed matches in the hash table, but keeps the code simple.

> **Watch out.** Two different positions *can* have the same key, a **collision**, but with 64-bit keys it is very rare: about one chance in 18 billion billion for any two positions. Engines accept this tiny risk; Chapter 20 shows the one place it could matter.

## Four keys, not one

The engine keeps several keys, each made from only some of the pieces:

@listing board.ant lines from "# Position keys" to "seed(5120)"

- `hash` covers everything, and identifies the whole position.
- `pawn_key` covers only the pawns.
- `np_key[colour]` covers one side's pieces that are not pawns.
- `minor_key` covers the knights, bishops and kings.

The smaller keys let the engine notice that two positions share their pawn structure, or their minor pieces, even when the rest differs. Chapter 24 uses them to correct the evaluation's mistakes.

## Draws by repetition

If the same position happens three times, the game is a draw. Inside a search, engines treat even *one* earlier occurrence as a draw: if a line of play can repeat a position, the side that is worse off can always repeat it again. The keys make the test simple:

@listing board.ant is_repetition

The engine remembers the key of every earlier position in `h_hash`, indexed by ply. It looks back two plies at a time, because the same position must have the same side to move, starting four plies back (a position can't repeat sooner). It stops at the last capture or pawn move, since no position before that can ever come back.

```antares
use "book"
set_fen(START_FEN)
each m in ["g1f3", "g8f6", "f3g1"] { play_text_move(m) }
show is_repetition()
play_text_move("f6g8")
show is_repetition()
```

```output
no
yes
```

The engine also recognises positions where neither side can possibly mate:

@listing board.ant insufficient_material

With no pawns, rooks or queens, and at most one knight or bishop on the board, the game is a draw.

## Try it yourself

1. Show that playing `e2e4` and then taking it back with `unmake` restores `hash` exactly. (Use `find_move` to get the move's slot, as in the next chapter.)
2. Why must the key include whose turn it is?

## Summary

- Every fact of a position has a random 64-bit number; the key is their `xor`.
- `xor` makes updates cheap: a move changes only a few facts.
- The pawn, non-pawn and minor-piece keys identify parts of a position.
- Repetitions are found by comparing keys with earlier positions.

# Making and Taking Back Moves {#make}

The search plays millions of moves, looks at the result, and takes them back again. This chapter shows how a move is stored in a single number, and how `make` and `unmake` change the position and restore it.

## A move in 16 bits

Every move is described by three things: the square it starts from, the square it goes to, and a **flag** saying what kind of move it is. Squares need 6 bits each (0 to 63) and the flag 4 bits, so a whole move fits in 16 bits:

```diagram
   bits:   15 14 13 12 | 11 10  9  8  7  6 |  5  4  3  2  1  0
           \___flag___/  \___to square___/   \___from square__/

   code = from | (to << 6) | (flag << 12)
```

The flags are:

@listing board.ant lines from "# move flags" to "RANK_2 = "

The numbers are chosen so that questions about a move are quick bit tests. `flag >= 8` means "a promotion". `flag & 3` picks the promotion piece: 0 knight, 1 bishop, 2 rook, 3 queen, so the new piece's type is `1 + (flag & 3)`. `flag == CAPTURE or flag >= PROMO_CAP_N` means "something is captured on the target square" (en passant captures elsewhere).

```antares
use "book"
code = 52 | (60 << 6) | (PROMO_Q << 12)
show code, move_text(code)
show code & 63, (code >> 6) & 63, code >> 12
```

```output
48948 e7e8q
52 60 11
```

Here is how a move code becomes text like `e7e8q`:

@listing board.ant move_text

## Remembering what to restore

Some things about a position can't be worked out again after a move: the castling rights before it, the en-passant square, the halfmove clock, the captured piece. So before changing anything, `make` saves them in the history tables, one entry per ply:

@listing board.ant save_state

`restore_state` puts them all back. The history tables themselves are rows of 2,400 entries, enough for a long game plus the deepest search:

@listing board.ant lines from "# What is needed to take a move back" to "# fresh[perspective"

## make

Here is the function that plays a move:

@listing board.ant make

Step by step:

1. **Save the state** and take the old castling and en-passant keys out of `hash`, because both may change.
2. **Count the move** for the fifty-move rule (`halfmove`) and for repetitions after a null move (`since_null`, Chapter 22).
3. **Remove the captured piece.** For en passant, it isn't on the target square but one square behind it: `dst - fwd`.
4. **Move the piece**: take it from `src` and put it on `dst`, or put the promotion piece there instead. For White, `us * 8 + 1 + (flag & 3)` is 1 to 4; for Black, 9 to 12.
5. **Castling** also moves the rook: from h1 to f1 (`dst + 1` to `dst - 1`) for king-side, from a1 to d1 for queen-side.
6. **A double pawn push** sets the en-passant square to the square it skipped.
7. **Reset the fifty-move count** after a capture or a pawn move.
8. **Update the castling rights**, put the new castling key and the side-to-move key into `hash`, remember the move, and hand the turn to the other side.

The castling rights use a neat table, `spoil`. For each square, it holds the rights that *survive* a move from or to that square:

@listing board.ant lines from "# Castling rights that survive" to "# What is needed to take a move back"

Most squares keep all four rights (15). A move from or to e1, the white king's square, keeps only Black's (12, binary 1100). A move from or to h1 removes White's king-side right only (14, binary 1110), whether the rook moves away or is captured there. So one line does all of it: `castle = castle & spoil[src] & spoil[dst]`.

> **In the engine.** `make` doesn't check that the move is legal. It may leave the mover's own king in check. The caller tests that afterwards with `attacked(king_sq[us], them)` and takes the move back if so. Chapter 11 explains why this is quicker.

## unmake

`unmake` reverses `make`, in the opposite order:

@listing board.ant unmake

It puts the rook back for castling, moves the piece home (a promoted piece goes back as a pawn, `us * 8`), puts back the captured piece, and restores the saved state, including the key. Notice that `unmake` doesn't undo the key changes one by one: it just restores the saved key.

Let's castle and take it back:

```antares
use "book"
set_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
before = hash
i = find_move("e1g1", 0)
make(mv_from[i], mv_to[i], mv_flag[i])
show board_text()
show "castle {castle}, side {side}"
unmake(mv_from[i], mv_to[i], mv_flag[i])
show "castle {castle}, side {side}, same key: {hash == before}"
```

```output
8  r . . . k . . r
7  . . . . . . . .
6  . . . . . . . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  R . . . . R K .

   a b c d e f g h
castle 12, side 1
castle 15, side 0, same key: yes
```

After castling, White has lost both rights (castle went from 15 to 12) and it is Black's turn. After `unmake`, everything is back.

## The null move

One special "move" passes the turn without moving anything. It isn't legal in chess, but it's a powerful search trick (Chapter 22): if a position is still good for you even when you let the opponent move twice, it is very good indeed.

@listing board.ant make_null

`h_flag[gply] = -1` marks the ply as a null move, so the rest of the engine knows no piece moved there.

## Try it yourself

1. What is the code of the move g1f3 (from 6 to 21, a quiet move)? Check your answer with `move_text`.
2. Make the move e2e4 in the starting position and show `ep` as a square name.
3. In the castling example, which number does `spoil` hold for a8 (square 56), and why?

## Summary

- A move is `from | (to << 6) | (flag << 12)`: 16 bits.
- `make` saves what can't be recomputed, then moves the pieces and updates the keys and rights.
- `unmake` reverses the move and restores the saved state.
- `spoil` updates castling rights with one `&`; `make_null` passes the turn.

# Generating Moves {#movegen}

Now the engine can play moves, but it needs to know *which* moves there are. This chapter shows how it lists every move in a position: pawns, pieces and castling.

## Legal and pseudo-legal moves

A **legal** move obeys every rule of chess, including "you may not leave your own king in check". Checking that last rule for every move while generating would be slow and complicated (think of pinned pieces and discovered checks). So, like most engines, Antares Chess generates **pseudo-legal** moves: moves that follow the movement rules but might leave the king in check. The search plays each one with `make`, checks with `attacked` whether its king is now attacked, and if so takes it back and skips it.

This sounds wasteful, but it isn't: most of the time the search finds a good move and stops looking at the others long before it would have checked them all. Work spent proving the legality of moves that are never played is saved.

## Where moves are kept

Generated moves go into big shared rows. Each search ply has its own slice of 256 slots, so the moves of different plies don't overwrite each other:

@listing board.ant lines from "# Generated moves, MOVES_PER_PLY" to "to put_piece"

Moves are kept in five parallel rows: `mv_from`, `mv_to`, `mv_flag`, the move's code in `mv_code`, and `mv_score` for move ordering (Chapter 21). `push_move` adds one:

@listing board.ant push_move

## Moves of pieces

For knights, bishops, rooks, queens and kings, generation is the same pattern: for each piece, look up its attacks, keep the squares it may move to, and add a move for each. `push_targets` does the last step, marking each move as a capture or a quiet move:

@listing board.ant push_targets

`gen_moves` is the main function. Its `mode` chooses which moves to make: all of them (0), only captures and queen promotions (1), or only the rest (2). The search uses the modes to look at captures first (Chapter 21):

@listing board.ant gen_moves

The targets bitboard does the choosing. Every piece's moves are `attacks & targets`:

- mode 1: `targets = enemy` (captures only);
- mode 2: `targets = ~occ` (empty squares only);
- mode 0: `targets = ~own` (anything except our own pieces).

Notice how queens are handled without any code of their own: they are included with the bishops (`by_type[2] | by_type[4]`) *and* with the rooks (`by_type[3] | by_type[4]`).

## Pawns

Pawns are the most complicated piece: they move one way and capture another, can move two squares from their first rank, promote, and capture en passant:

@listing board.ant gen_pawns

For each pawn, the function:

1. tries the square ahead (`sq + fwd`). If it's empty, that's a push, or four promotions if the pawn is on its seventh rank. A pawn on its second rank can then also try two squares ahead;
2. tries its captures: the squares in `pawn_att` that hold an enemy piece;
3. tries an en-passant capture, if the en-passant square is one it attacks.

The modes split promotions in a useful way: a promotion to a queen counts with the captures (mode 1), because it's almost always a strong move, while promotions to knight, rook and bishop come with the quiet moves.

## Castling

Castling has the most conditions of any move: the right must still exist, the squares between king and rook must be empty, and the king may not be in check, pass through an attacked square, or land on one:

@listing board.ant gen_castles

`k = us * 56 + 4` is the king's starting square: e1 (4) for White, e8 (60) for Black. The bits for the rights are 1 and 2 for White, 4 and 8 for Black, so `1 << (us * 2)` and `2 << (us * 2)` pick the right ones. The landing square isn't checked here: like any other king move, the search checks it after `make`.

> **Chess note.** The king may not castle out of, through or into check. The rook may pass an attacked square, and on the queen-side b1 must be empty but may be attacked.

## Generating for the search

`generate` wraps `gen_moves` for a search ply, giving back how many moves it made:

@listing board.ant generate

Here are the 20 moves of the starting position, and the moves of a position where a pinned piece makes the difference between pseudo-legal and legal:

```antares
use "book"
set_fen(START_FEN)
show len(legal_moves()), join(legal_moves(), " ")
set_fen("4k3/4r3/8/8/8/8/4N3/4K3 w - - 0 1")
show "pseudo-legal: {generate(0, no)}, legal: {len(legal_moves())}"
show join(legal_moves(), " ")
```

```output
20 a2a3 a2a4 b2b3 b2b4 c2c3 c2c4 d2d3 d2d4 e2e3 e2e4 f2f3 f2f4 g2g3 g2g4 h2h3 h2h4 b1a3 b1c3 g1f3 g1h3
pseudo-legal: 10, legal: 4
e1d1 e1f1 e1d2 e1f2
```

The knight on e2 is pinned by the rook on e7: any knight move would expose the king. `generate` makes all six knight moves anyway, and `legal_moves` (from `book.ant`) throws them out after `make` shows the king in check.

## Checking a stored move

Sometimes the search wants to play a move it remembers from somewhere else, before generating anything: the best move from the hash table (Chapter 20) or a killer move (Chapter 21). It must first make sure that move can be played *in this position*:

@listing board.ant quiet_is_playable

It checks the piece is ours, the target square is empty, and the piece can really get there.

## Try it yourself

1. Count the legal moves after `1. e4 e5 2. Nf3 Nc6 3. Bc4`.
2. Find a position where castling queen-side is legal even though b1 is attacked.
3. Using `gen_moves` with mode 1, count the captures in this position: `r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4`. (Hint: `n = gen_moves(0, 1)`.)

## Summary

- The engine generates pseudo-legal moves and checks king safety after `make`.
- Each search ply has 256 move slots; moves are kept in parallel rows.
- Piece moves are `attacks & targets`; the mode chooses the targets.
- Pawns and castling have their own functions; queens reuse the bishop and rook code.

# Perft: Testing Move Generation {#perft}

A single bug in move generation, such as a missing en-passant capture or castling through check, can make an engine play illegal moves or miss winning ones. **Perft** is the test every chess programmer uses to make sure move generation is perfect.

## Counting positions

*Perft* is short for "performance test, move path enumeration". It counts every position reachable from a starting position in exactly `n` plies, playing every legal move:

@listing board.ant perft

It's the search at its simplest: no evaluation, no pruning, every legal move played to the full depth. The counts for the starting position are well known:

| Depth | Positions |
|---:|---:|
| 1 | 20 |
| 2 | 400 |
| 3 | 8,902 |
| 4 | 197,281 |
| 5 | 4,865,609 |
| 6 | 119,060,324 |

If your generator gives these numbers, it handles all ordinary moves. Let's check the first three:

```antares
use "book"
set_fen(START_FEN)
repeat 3 as d { show "perft {d}: {perft(d, 0)}" }
```

```output
perft 1: 20
perft 2: 400
perft 3: 8902
```

## Tricky positions

The starting position doesn't test castling, en passant or promotion until deep in the tree. Chess programmers have collected positions packed with tricky moves. The most famous is called **Kiwipete**:

@board r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1 | Kiwipete: castling both ways for both sides, pins, en passant and promotions are all near.

```antares
use "book"
set_fen("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1")
show perft(1, 0), perft(2, 0)
```

```output
48 2039
```

The engine's `tests/test_perft.ant` checks 11 counts on 6 positions like this. It also checks that `hash` is the same after perft as before, which catches a `make` and `unmake` that don't match.

## Finding a bug: divide

When a perft count is wrong, how do you find the bug? The standard method is **divide**: count the positions under *each* first move separately, and compare with a program you trust (such as the `go perft` command of other engines). The move whose count differs leads towards the bug; play it and divide again, until the wrong move is found.

```antares
use "book"
set_fen(START_FEN)
total = 0
n = generate(0, no)
repeat n as k {
    i = k - 1
    make(mv_from[i], mv_to[i], mv_flag[i])
    when not attacked(king_sq[0], 1) {
        count = perft(2, 1)
        total = total + count
        when count >= 500 { show "{move_text(mv_code[i])}: {count}" }
    }
    unmake(mv_from[i], mv_to[i], mv_flag[i])
}
show "total {total}"
```

```output
d2d3: 539
d2d4: 560
e2e3: 599
e2e4: 600
total 8902
```

To keep the output short, only the moves leading to 500 positions or more are shown: the centre pawn moves, which free the bishop and the queen. Note the second argument of `perft`: the search ply, so each level uses its own slice of the move rows.

## Speed

In the built engine, `perft 5` from the start (4,865,609 positions) takes about a third of a second, and `perft 6` (119 million) about nine seconds: some 13 million positions a second, just by generating, making and unmaking moves. Interpreted, the same code manages about 18,000 a second. The `perft` command in the UCI interface prints the time too, so it doubles as a speed test for the board code.

> **Remember.** Run perft after *every* change to `board.ant`. It finds in seconds the bugs that would otherwise take days of games to show up.

## Try it yourself

1. Run perft 3 on the position `8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1`. The right answer is 2,812.
2. Change the divide example to depth 3 (`perft(2, 1)` becomes `perft(3, 1)`) and show every move's count. Which first move leads to the most positions?

## Summary

- Perft counts every position `n` plies ahead; the right answers are well known.
- Tricky positions like Kiwipete test castling, en passant and promotions.
- *Divide* splits the count by first move to track down a bug.

# Static Exchange Evaluation {#see}

Is it safe to capture that pawn? If the pawn is defended and you capture with your queen, you lose the queen for a pawn. **Static exchange evaluation**, or **SEE**, answers such questions by working out the whole sequence of captures on one square, without searching.

## An exchange on one square

Look at this position. White's rook on d2 can take the pawn on d5:

@board 4k3/8/5n2/3p4/8/8/3R4/3R2K1 w - - 0 1 | Rd2xd5: the pawn is defended by the knight, and the rook on d1 stands behind. | d2d5

If White plays Rxd5 and Black recaptures with the knight, and then White recaptures with the second rook:

| Capture | White's running total |
|---|---|
| Rd2xd5 takes a pawn | +100 |
| Nf6xd5 takes a rook | +100 - 500 = -400 |
| Rd1xd5 takes a knight | -400 + 300 = -100 |

White ends up 100 centipawns worse: a rook for a pawn and a knight. And Black doesn't have to recapture if that would be worse for Black, nor does White. SEE assumes each side keeps capturing while it pays, always with its *least valuable* attacker, and stops when it doesn't.

Notice the rook on d1. It doesn't attack d5 at first, because the rook on d2 is in the way. Once that rook has captured, the d1 rook attacks through the gap: an **x-ray** attacker. SEE must find these.

## Does it win at least this much?

Engines rarely need the exact value of an exchange. They need to ask: "does this capture win at least *threshold*?" Asking it this way is quicker, because the calculation can stop as soon as the answer is clear. The engine's function is a port of the version in the famous engine Stockfish:

@listing board.ant see_ge

How it works:

1. `swap` starts as the value of what is captured, minus the threshold. If even that is below zero, the answer is no.
2. Then it assumes the moved piece is lost. If we're *still* at or above the threshold, the answer is yes, whatever happens next.
3. Otherwise it plays the exchange out. `occ` is the occupied squares with the capturing piece removed, and `attackers` holds every piece of either colour that attacks the square (`attackers_to` from Chapter 6).
4. In the loop, the sides take turns. Each finds its least valuable attacker (`pt` from pawn upwards), and `swap` is updated. `result` flips each turn and records which side is winning the exchange so far.
5. When a piece is removed from `occ`, a bishop, rook or queen behind it may now see the square. The function looks again along the diagonals (after a pawn, bishop or queen is used) or the lines (after a rook or queen), and adds the x-ray attackers.
6. A king may capture last only if no enemy attacker is left, since it can't move into check.

The piece values used are simple: pawn 100, knight and bishop 300, rook 500, queen 900:

@listing board.ant lines from "see_type = [" to "# Does the exchange"

Let's ask about the position above, and about a safe capture:

```antares
use "book"
set_fen("4k3/8/5n2/3p4/8/8/3R4/3R2K1 w - - 0 1")
show see_ge(11, 35, CAPTURE, 0), see_ge(11, 35, CAPTURE, -100), see_ge(11, 35, CAPTURE, -99)
set_fen("4k3/8/8/3p4/8/8/3R4/6K1 w - - 0 1")
show see_ge(11, 35, CAPTURE, 0), see_ge(11, 35, CAPTURE, 100), see_ge(11, 35, CAPTURE, 101)
```

```output
no yes no
yes yes no
```

In the first position the exchange is worth exactly -100: it wins at least -100 but not -99. In the second the pawn is undefended, so the capture wins exactly 100.

## Where SEE is used

SEE is quick but it isn't perfect: it ignores pins, checks and everything happening elsewhere on the board. The engine uses it where a fast, rough answer is enough:

- **Move ordering:** captures that lose material are tried after the others (Chapter 21).
- **Pruning:** moves that lose a lot of material at low depth are not searched at all (Chapter 22).
- **Quiescence search:** losing captures are skipped (Chapter 19).

## Try it yourself

1. In the first position, remove the rook on d1. What is the exchange worth now? Check with `see_ge`.
2. Set up a position where a pawn captures a defended knight, and show that `see_ge` says it wins at least 200.

## Summary

- SEE plays out all captures on one square, each side using its least valuable attacker.
- X-ray attackers behind the captured pieces join in as the square opens up.
- `see_ge` asks "does this win at least the threshold?", which is quicker than the exact value.
- It guides move ordering and pruning.

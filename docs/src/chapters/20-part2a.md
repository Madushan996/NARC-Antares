# The Board {#part-board .part}

How a chess position is stored in a computer, how moves are played and taken back, and how every legal move is found. This part covers all of `board.ant`, the foundation the rest of the engine stands on. It ends with perft, the test that proves the foundation is right.

# Bitboards {#bitboards}

The first decision in any chess engine is how to store the board. Antares Chess uses **bitboards**, the method used by nearly every strong engine. This chapter explains what they are and the handful of bit tricks that make them work.

## Numbering the squares

A chessboard has 64 squares. The engine gives each a number from 0 to 63, row by row, starting at a1 in White's bottom-left corner:

@squares

So a1 is 0, b1 is 1, h1 is 7, a2 is 8, and h8 is 63. From a square's number it is easy to get its **file** (column a to h) and **rank** (row 1 to 8):

- file = `sq % 8` (0 for the a-file, 7 for the h-file)
- rank = `sq >> 3`, the same as `div(sq, 8)` (0 for rank 1, 7 for rank 8)
- and back again: `sq = rank * 8 + file`

Moving one square up the board adds 8; moving one square right adds 1. The engine names these steps:

@listing board.ant lines from "UP = int(8)" to "MAX_PLY"

The engine turns a square number into its name like this. Strings can be indexed like lists, so `"abcdefgh"[sq & 7]` is the file's letter (`sq & 7` is the same as `sq % 8` for these numbers):

@listing board.ant square_name

## One bit per square

An Antares integer has exactly 64 bits, numbered 0 to 63. A chessboard has exactly 64 squares, numbered 0 to 63. So one integer can answer a yes-or-no question about every square at once: bit `sq` is 1 when the answer for square `sq` is yes.

Such an integer is called a **bitboard**. For example, "where are the white pawns at the start?" is answered by the bitboard with bits 8 to 15 set, the whole second rank:

@bitboard 0xFF00 | The white pawns at the start: bits 8 to 15, the number `0xFF00`.

In hexadecimal, each digit stands for four bits, so `0xFF00` is eight 0 bits (rank 1) followed by eight 1 bits (rank 2). The engine has names for a few useful bitboards like this:

@listing board.ant lines from "RANK_2 = " to "UP = int(8)"

## Seeing bitboards

To see bitboards in the examples, the book uses a small helper file, `book.ant`. Save it in the engine's `src` folder once, and every example that says `use "book"` can use it. It loads the engine's board code too:

@listing book.ant lines

`grid` draws a bitboard, and `squares` lists its squares by name. Let's look at the white pawns and the black pieces in the starting position. `by_type[0]` holds every pawn, and `by_color[0]` every white piece, so `&` keeps the squares that are in both:

```antares
use "book"
set_fen(START_FEN)
grid(by_type[0] & by_color[0])
show squares(by_color[1] & ~by_type[0])
```

```output
8  . . . . . . . .
7  . . . . . . . .
6  . . . . . . . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  x x x x x x x x
1  . . . . . . . .
   a b c d e f g h
a8 b8 c8 d8 e8 f8 g8 h8
```

`~by_type[0]` flips every bit: "every square without a pawn". So `by_color[1] & ~by_type[0]` means "black pieces that are not pawns".

## Why bitboards are fast

The magic of bitboards is that one operation works on all 64 squares at once. With a list of 64 squares you would need a loop to answer "which squares hold a white piece that is not a pawn?". With bitboards it is one `&` and one `~`. Some examples:

| Question | Bitboard expression |
|---|---|
| Every occupied square | `by_color[0] \| by_color[1]` |
| Every empty square | `~(by_color[0] \| by_color[1])` |
| White's knights | `by_type[1] & by_color[0]` |
| Is square `sq` occupied by White? | `by_color[0] & (1 << sq) != 0` |
| How many black pawns? | `popcount(by_type[0] & by_color[1])` |
| White pawns, all moved one square up | `(by_type[0] & by_color[0]) << 8` |

The last one is lovely: shifting a bitboard left by 8 moves every bit up one rank, so all the pawns are pushed at once. Shifting left by 7 or 9 moves them diagonally, which is how the engine finds every square attacked by pawns in one step (Chapter 21).

> **Antares.** In Antares, `&` binds more tightly than `==` and `!=`, so `a & b != 0` means `(a & b) != 0`. Many other languages do it the other way round, which is a classic source of bugs there.

## Visiting every bit

Often the engine needs to do something for *each* piece in a bitboard: generate the moves of each knight, say. This loop appears dozens of times in the engine:

```antares
use "book"
set_fen(START_FEN)
rest = by_type[1]              # every knight
while rest != 0 {
    sq = lowest_bit(rest)      # the lowest square left
    rest = rest & (rest - 1)   # clear that bit
    show "a knight on {square_name(sq)}"
}
```

```output
a knight on b1
a knight on g1
a knight on b8
a knight on g8
```

`lowest_bit` gives the number of the lowest 1 bit, which is a square. The line `rest = rest & (rest - 1)` is the famous trick that **clears the lowest 1 bit**. Here is why it works. Subtracting 1 turns the lowest 1 bit into 0 and every 0 below it into 1, leaving the higher bits alone:

```diagram
   rest          = 0110 1000
   rest - 1      = 0110 0111     (the lowest 1 became 0, the 0s below became 1)
   rest & (rest-1) = 0110 0000   (only the higher bits survive)
```

So the loop visits each piece exactly once, lowest square first, and stops when no bits are left. On modern processors both `lowest_bit` and the clearing step are single instructions.

## The board in two forms

Bitboards are excellent for questions about *sets* of squares, but awkward for the question "what is on square e4?". So the engine keeps the position twice:

- `board`, a row of 64 numbers: the piece on each square, or `EMPTY`;
- `by_type` and `by_color`, bitboards of where each kind of piece and each colour is.

Chapter 8 shows how the two are always kept in agreement.

## Try it yourself

1. Write a program that uses `grid` to show every empty square in the starting position.
2. Using `popcount`, count the black pieces in the starting position.
3. What square number is e4? What is `1 << 28` as a square name?

## Summary

- Squares are numbered 0 (a1) to 63 (h8); file = `sq % 8`, rank = `sq >> 3`.
- A bitboard is a 64-bit integer with one bit per square.
- `&`, `|`, `~` and shifts answer questions about all squares at once.
- `lowest_bit` and `rest & (rest - 1)` visit each set bit in turn.
- The engine keeps both a 64-square `board` and bitboards by type and colour.

# Attack Tables {#attacks}

To generate moves, or to see whether a king is in check, the engine must know which squares each piece attacks. Working this out from scratch every time would be slow, so the engine works it out once, when it starts, and keeps the answers in tables.

## Knights, kings and pawns

A knight on d4 attacks the same eight squares in every position. Nothing can block a knight. So the engine can store, for each of the 64 squares, a bitboard of the squares a knight there attacks:

@bitboard 0x142200221400 | `knight_att[27]`: the squares a knight on d4 attacks. | 8/8/8/8/3N4/8/8/8 w - - 0 1

Kings and pawns are the same: what they attack depends only on their square (and, for pawns, their colour). The engine keeps four tables:

@listing board.ant lines from "knight_att = ints(64)" to "to on_board"

The direction lists describe how pieces step. `dir_df[k]` and `dir_dr[k]` are the change in file and rank for each of the eight directions a king or queen can go; `jump_df` and `jump_dr` are the eight knight jumps. For example, direction 0 is north (file +0, rank +1), and the first knight jump is two up and one right (file +1, rank +2).

## Building the tables

This code runs once, when `board.ant` is loaded. For each square, it tries all eight directions and all eight knight jumps, and sets a bit for each square that is still on the board:

@listing board.ant lines from "to on_board" to "# Squares a bishop on"

Three things are worth noticing.

- `on_board(f, r)` checks that a file and rank are both from 0 to 7. A knight on a1 has only two of its eight jumps on the board.
- `knights | (1 << ...)` sets one more bit in the bitboard being built.
- The same loop also builds `ray`: for each direction, every square from `sq` to the edge of the board. These rays are the starting point for sliding pieces.

> **Antares.** `each df in [-1, 1]` runs its body twice, with `df` first -1 then 1: the two diagonal captures of a pawn. `each` works on any list.

Let's check a few entries:

```antares
use "book"
show squares(knight_att[0])
show squares(king_att[4])
show squares(pawn_att[28]), "|", squares(pawn_att[64 + 28])
show popcount(knight_att[27]), popcount(knight_att[0])
```

```output
c2 b3
d1 f1 d2 e2 f2
d5 f5 | d3 f3
8 2
```

A knight in the corner (square 0, a1) attacks only b3 and c2; a king on e1 attacks five squares; a white pawn on e4 (square 28) attacks d5 and f5, and a black pawn on e4 attacks d3 and f3.

## Is a square attacked?

With these tables the engine can answer one of the most important questions in chess programming: *is this square attacked by that colour?* It is used to see whether a king is in check, whether castling is allowed and whether a move leaves the king in danger.

@listing board.ant attacked

The trick is to look *backwards* from the square. If a knight standing on `sq` would attack a square holding an enemy knight, then that enemy knight attacks `sq`, because knight moves are symmetrical. So `knight_att[sq] & by_type[1] & theirs` is "enemy knights a knight's jump from `sq`". It is the same for kings, and for bishops, rooks and queens using their attack functions.

Pawns are the one piece that isn't symmetrical: white pawns attack upwards and black pawns downwards. To find enemy pawns attacking `sq`, the engine looks at the squares a pawn of *our* colour on `sq` would attack, `pawn_att[(1 - attacker) * 64 + sq]`.

> **In the engine.** `attacked` gives back `yes` as soon as it finds any attacker. The last line, without `when`, is itself the answer: `yes` or `no`. The cheapest tests (pawns, knights, king) come first.

A related function lists *every* attacker of a square, of both colours. Chapter 13 uses it to work out exchanges:

@listing board.ant attackers_to

## Sliding pieces

Bishops, rooks and queens are harder. A rook on d4 attacks along its file and rank only *until it meets a piece*. What it attacks depends on where the other pieces are, so one table entry per square is not enough.

@bitboard 0x80876080808 | A rook on d4: it attacks up to and including the first piece in each direction. | 8/8/3p4/8/1P1R2n1/8/8/8 w - - 0 1

The engine's first answer uses the rays. Take the ray north from the rook. If no square on it is occupied, the rook attacks the whole ray. If some are, find the *first* blocker, the occupied square nearest the rook, and remove everything beyond it. "Everything beyond the blocker" is just the ray north *from the blocker*, which is already in the table:

@listing board.ant rook_ray

For directions that run towards higher square numbers (north, east), the nearest blocker is the lowest bit of `ray & occ`; for those running towards lower numbers (south, west), it is the highest bit. `xor` removes the squares beyond the blocker. The blocker itself stays in, because the rook attacks it: it may be an enemy piece to capture.

`bishop_ray` does the same on the four diagonals. These functions are correct and quite quick, but they are not what the engine uses during the search. The next chapter shows something faster, and `rook_ray` and `bishop_ray` are used only to build it.

## Try it yourself

1. Use `squares` to show where a knight on h8 (square 63) can jump.
2. Set up the starting position and use `attacked` to check whether e3 (square 20) is attacked by White, and whether e5 (square 36) is.
3. Why does a king on a1 attack exactly three squares?

## Summary

- Knight, king and pawn attacks are worked out once per square and stored in tables.
- `attacked(sq, colour)` looks backwards from the square, using the symmetry of piece moves.
- Sliding pieces need the other pieces' positions; `rook_ray` cuts each ray at its first blocker.

# Magic Bitboards {#magics}

A rook or bishop's attacks depend on the pieces around it. This chapter explains **magic bitboards**, a clever trick that finds them with one multiplication and one table look-up. It is the fastest method known, and the one Antares Chess uses.

## The idea: a table for every situation

Look again at a rook on d4. Only some squares can make a difference to its attacks: the squares on its file and rank. And not even all of those. A piece on d8 doesn't block anything, because there is nothing beyond d8 to block. So only the squares on the rook's lines, *without the edge squares*, matter. This set is called the rook's **mask**:

@bitboard 0x8080876080800 | The mask of a rook on d4: the 10 squares whose pieces can change its attacks. | 8/8/8/8/3R4/8/8/8 w - - 0 1

Ten squares, each empty or full: that's 2<sup>10</sup> = 1024 possible arrangements of blockers. If we could turn each arrangement into a number from 0 to 1023, we could keep a table of 1024 answers for d4, and look the answer up instantly.

The arrangement is `occ & mask`: the occupied squares, keeping only the ones in the mask. But that is a 64-bit number with the ten interesting bits scattered all over it. We need to squeeze them together into a 10-bit index.

## The magic multiplication

Here is the trick. Multiply `occ & mask` by a carefully chosen 64-bit number, the **magic number**, and keep only the top 10 bits of the result:

```diagram
   index = ((occ & mask) * magic) >> (64 - 10)
```

Multiplying a number by another is like adding up shifted copies of it. With the right magic, the copies land so that the ten scattered bits are gathered, in some order, into the top ten bits of the result. Different arrangements give different indexes, or, where they give the same index, they have the same attacks (and that's fine too). Shifting right by 54 then leaves a number from 0 to 1023.

Nobody works out magic numbers by hand. They are found by trying random numbers until one works for each square. Antares Chess uses the magics found for its C++ ancestor, NARC Genesys, written out in full:

@listing board.ant lines from "rook_magic = ints([" to "    0x8401800080400120"

> **Antares.** Integers in Antares wrap around: a multiplication that is too big for 64 bits keeps the lowest 64 bits of the answer, as in C and Rust. Magic bitboards depend on this.

## The tables

For each square the engine keeps four numbers: where its slice of the big table starts (the **offset**), its mask, its magic number and its shift. They are stored side by side in one row, `rook_info[sq * 4 + 0, 1, 2, 3]`, so all four are next to each other in memory:

@listing board.ant lines from "ROOK_SLOTS = 102400" to "rook_magic = ints(["

A rook in the corner has a 12-square mask and needs 4096 entries; a rook in the middle has 10 and needs 1024. Added up over all 64 squares, rooks need 102,400 entries and bishops (with smaller masks) 5,248.

The mask is built from the rays, leaving out each ray's last square:

@listing board.ant inner_ray

## Filling the tables

When `board.ant` loads, it fills the tables. For each square it visits **every subset** of the mask, every possible arrangement of blockers, works out the attacks the slow way with `rook_ray`, and stores them at the magic index:

@listing board.ant lines from "mg_rook_next = int(0)" to "    mg_mask = inner_ray(1, sq)"

Visiting every subset of a set of bits uses another lovely trick, the **carry-rippler**: `sub = (sub - mask) & mask` steps from one subset to the next, from 0 back round to 0. The `check` line makes sure no two arrangements with different attacks collide on one index. If a magic number were wrong, the engine would refuse to start instead of playing illegal moves.

## Looking attacks up

After all that preparation, finding a rook's attacks during the search is a single line:

@listing board.ant rook_att

This is the formula from the start of the chapter: `offset + ((occ & mask) * magic) >> shift`, with the four numbers read from `rook_info`. It costs one `&`, one multiplication, one shift and two table look-ups, whatever the position. A queen is a rook and a bishop together: `rook_att(sq, occ) | bishop_att(sq, occ)`.

Let's check that the fast way and the slow way agree, using the position from the last chapter:

```antares
use "book"
set_fen("8/8/3p4/8/1P1R2n1/8/8/k6K w - - 0 1")
occ = by_color[0] | by_color[1]
show squares(rook_att(27, occ))
show rook_att(27, occ) == rook_ray(27, occ)
show squares(rook_att(27, occ) & ~by_color[0])
```

```output
d1 d2 d3 b4 c4 e4 f4 g4 d5 d6
yes
d1 d2 d3 c4 e4 f4 g4 d5 d6
```

The last line removes squares holding White's own pieces (`& ~by_color[0]`): those are the squares the rook can actually move to. The rook can capture on d6 and g4 but not b4, where a white pawn stands.

> **In the engine.** The function inputs say `sq within 0 to 63`. The compiled engine therefore knows `sq * 4` is between 0 and 252, and that every table read is safe, so it leaves out the safety checks it would otherwise make (Chapter 27).

## Try it yourself

1. How many entries does a bishop on a1 need? (Its mask is the long diagonal without a1 and h8.)
2. Using `bishop_att`, list the squares a bishop on c1 attacks in the starting position. Why is the answer so short?
3. Write a function `queen_att(sq, occ)` and test it on an empty board with the queen on d4.

## Summary

- Only the squares in a slider's mask (its lines without the edges) affect its attacks.
- Multiplying `occ & mask` by a magic number and shifting gathers those bits into a table index.
- The tables are filled once at the start by visiting every subset with the carry-rippler, checking every magic.
- `rook_att` and `bishop_att` then cost one multiplication and a look-up.

# The Position {#position}

A chess position is more than where the pieces are. This chapter shows everything the engine keeps about a position, how pieces are put on and taken off the board, and how a position is read from FEN text.

## What makes a position

To know what moves are legal and whether the game is drawn, you need:

1. where every piece is;
2. whose turn it is;
3. which castling moves are still allowed;
4. whether an en-passant capture is possible, and on which square;
5. how many moves have been played since the last capture or pawn move (for the fifty-move rule);
6. the positions that came before (for repetitions).

Here is how the engine stores the first five:

@listing board.ant lines from "HIST = 2400" to "# Position keys"

Every item has a range. `side` is 0 for White and 1 for Black. `ep` is the square a pawn could capture onto *en passant*, or `NO_SQ` (64) if there is none. `castle` holds four yes-or-no facts in four bits. `gply` counts the plies played, both in the game and in the current search, and is the index into the history tables of Chapter 10.

> **Chess note.** After a pawn moves two squares, an enemy pawn beside it may capture it *en passant* ("in passing") as if it had moved one, but only on the very next move. The square it skipped over is the en-passant square.

## Numbering the pieces

Each piece is one number, built from its colour and type:

```diagram
   piece = colour * 8 + type       colour: 0 white, 1 black
                                   type:   0 pawn, 1 knight, 2 bishop, 3 rook, 4 queen, 5 king

   white:  P=0  N=1  B=2  R=3  Q=4  K=5
   black:  p=8  n=9  b=10 r=11 q=12 k=13          EMPTY = 15
```

Getting the parts back is quick with bit operators: `p & 7` is the type and `p >> 3` the colour. These piece numbers are used everywhere: in `board`, in move histories and as indexes into tables.

@listing board.ant lines from "PAWN = 0x0" to "# move flags"

## Putting a piece on the board

Every change to the position goes through two functions. `put_piece` places a piece on an empty square, and keeps every part of the position in step:

@listing board.ant put_piece

It updates the square, the type and colour bitboards, and the position keys (`hash` and its relatives, which Chapter 9 explains). If the piece is a king, it also records the king's square in `king_sq`, so the engine never has to search for a king.

`take_piece` is its mirror image, removing whatever is on a square. Because `xor` undoes itself, the same `xor` that added a piece's bit and key takes them away again:

@listing board.ant take_piece

> **Watch out.** It is easy to forget one of the copies of the position when you change it. Then the board and the bitboards disagree and the engine plays nonsense, often only in rare positions. Doing every change through two small functions is the cure.

## FEN: positions as text

Chess programs describe positions in a standard line of text called **FEN** (Forsyth-Edwards Notation). The starting position is:

```diagram
   rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
   \_________________________________________/ |  |   | |  \_ move number
                pieces, rank 8 first           |  |   | \_ halfmove clock (fifty-move rule)
                                               |  |   \_ en-passant square, or -
                                               |  \_ castling rights
                                               \_ side to move
```

In the pieces field, each rank is listed from the a-file to the h-file, ranks are separated by `/`, capital letters are White, small letters are Black, and a digit counts empty squares. `set_fen` reads it:

@listing board.ant set_fen

The function clears everything, then walks along the first field one character at a time. It starts at rank 7 (rank 8 on the board), file 0. A `/` moves down a rank; a piece letter is looked up in the map `fen_piece` and placed; a digit skips that many squares. The other fields set the side to move, the castling rights (adding up their bits), the en-passant square and the halfmove clock.

@listing board.ant lines from "fen_piece = {P: 0" to "to square_name"

> **Antares.** `each ch in fields[0]` goes through text one character at a time. `has(fen_piece, ch)` asks whether a map has a field, and `has(fields[2], "K")` whether text contains some smaller text.

## Showing the board

`board_text` turns the position back into a picture, the one the `d` command prints. The text `"PNBRQK..pnbrqk.."` is indexed by the piece number, so piece 9 is `n` and `EMPTY` (15) is `.`:

@listing board.ant board_text

Let's set up a position and look inside it:

```antares
use "book"
set_fen("r3k2r/8/8/3pP3/8/8/8/R3K2R w KQkq d6 0 1")
show board_text()
show "side {side}, castle {castle}, ep {square_name(ep)}"
show "kings on {square_name(king_sq[0])} and {square_name(king_sq[1])}"
show "e5 holds {board[36]}, d5 holds {board[35]}, e4 holds {board[28]}"
```

```output
8  r . . . k . . r
7  . . . . . . . .
6  . . . . . . . .
5  . . . p P . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  R . . . K . . R

   a b c d e f g h
side 0, castle 15, ep d6
kings on e1 and e8
e5 holds 0, d5 holds 8, e4 holds 15
```

All four castling rights give `castle` = 1 + 2 + 4 + 8 = 15. Black's last move was d7-d5, so White may capture en passant on d6.

## Try it yourself

1. Write the FEN for the position after `1. e4`. (The en-passant square is e3.) Check it with `set_fen` and `board_text`.
2. What piece numbers are a black rook and a white queen? Check with `board` in the starting position.
3. Use `set_fen` with a position where only White can castle, and show `castle`.

## Summary

- The position is the board, the side to move, castling rights, the en-passant square, the halfmove clock and the history.
- A piece is `colour * 8 + type`; `p & 7` is the type and `p >> 3` the colour.
- `put_piece` and `take_piece` make every change, keeping the board, bitboards and keys in step.
- `set_fen` reads a FEN line; `board_text` shows the board.

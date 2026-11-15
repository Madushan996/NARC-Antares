# Search {#part-search .part}

How the engine looks ahead. We start with minimax and alpha-beta on tiny game trees, then build up, one idea at a time, to the full search in `search.ant`: iterative deepening, quiescence search, the transposition table, move ordering, pruning, reductions, extensions and time management.

# Minimax and Alpha-Beta {#alphabeta}

This chapter explains the two ideas at the heart of every chess engine's search. They are easiest to see on small made-up game trees, so we'll start there and come back to chess at the end.

## Minimax

Imagine a tiny game. White moves first and has three moves; Black then has three replies to each; after that the game ends, and the numbers say how good the final position is for White:

```diagram
                              White to move
              /                     |                     \
         move A                  move B                  move C
        /   |   \               /   |   \               /   |   \
       3    12   8             2    4    6            14    5    2
```

Which move should White play? Move C has the biggest number, 14, but Black won't allow it: after move C, Black answers with the reply leading to 2. White must assume Black replies as well as possible. So:

- after move A, Black picks the smallest: 3;
- after move B, Black picks 2;
- after move C, Black picks 2.

White then picks the move whose worst case is best: move A, worth 3. This is **minimax**: one side maximises the score, the other minimises it, and the values are worked out from the bottom of the tree up.

## Negamax

Writing separate code for the maximising and minimising sides is clumsy. Instead, engines score every position **for the side to move**, as Antares Chess's `evaluate` does. Then both sides maximise: a position that is worth +3 for Black is worth -3 for White. Each position's value is the best of its children's values, *negated*:

```antares
tree = [[3, 12, 8], [2, 4, 6], [14, 5, 2]]
leaves = 0
to negamax(node) {
    when kind(node) == "number" {
        change leaves = leaves + 1
        give node
    }
    best = -1000
    each child in node { best = max(best, -negamax(child)) }
    best
}
show negamax(tree), leaves
```

```output
3 9
```

This is called **negamax**. (In this tree the leaves are positions with White to move again, so their numbers are already "for the side to move".) It visited all 9 leaves.

## Alpha-beta

Now look at the tree again and think like a human. After working out that move A is worth 3, White looks at move B. Black's first reply gives 2. Stop! White already has a move worth 3. Whatever else Black could reply to B, Black will choose 2 or something even smaller, so B is worse than A. There's no need to look at B's other replies.

This is **alpha-beta pruning**. It keeps two numbers as it searches:

- **alpha**: the score the side to move is already sure of, from moves searched so far;
- **beta**: the score the opponent is already sure of; if we find a move scoring beta or more, the opponent will never let this position happen, so we can stop. This is a **beta cutoff**.

The pair (alpha, beta) is called the **window**. In negamax form, a child is searched with the window turned round and negated, (-beta, -alpha):

```antares
tree = [[3, 12, 8], [2, 4, 6], [14, 5, 2]]
leaves = 0
to alphabeta(node, alpha, beta) {
    when kind(node) == "number" {
        change leaves = leaves + 1
        give node
    }
    each child in node {
        score = -alphabeta(child, -beta, -alpha)
        when score >= beta { give score }     # the opponent won't allow this: cut off
        alpha = max(alpha, score)
    }
    alpha
}
show alphabeta(tree, -1000, 1000), leaves
```

```output
3 7
```

The same answer, 3, from 7 leaves instead of 9. That's a small saving in a small tree, but the saving grows with depth. In a good case alpha-beta searches about the square root of the number of positions minimax does. So with the same effort, it can search **twice as deep**.

> **Remember.** Alpha-beta gives exactly the same result as minimax. It only skips moves that can't change the answer.

## Move order matters

How much alpha-beta saves depends on the order in which moves are tried. If the best move comes first, everything else is cut off quickly. If the best move comes last, alpha-beta saves nothing. Here is the same tree with White's moves in the worst order, and in each reply list the worst reply for Black first:

```antares
leaves = 0
to alphabeta(node, alpha, beta) {
    when kind(node) == "number" {
        change leaves = leaves + 1
        give node
    }
    each child in node {
        score = -alphabeta(child, -beta, -alpha)
        when score >= beta { give score }
        alpha = max(alpha, score)
    }
    alpha
}
show alphabeta([[14, 5, 2], [6, 4, 2], [12, 8, 3]], -1000, 1000), leaves
```

```output
3 9
```

All 9 leaves again. This is why move ordering (Chapter 21) is so important: a strong engine tries the best move first more than 90% of the time, which is what lets it search so deep.

## The search in Antares Chess

The real search has the same shape as `alphabeta` above, with the board instead of a list. Without all the improvements of the next chapters it would look like this:

<!-- norun -->
```antares
to search(alpha, beta, depth, ply) {
    when depth <= 0 { give evaluate() }
    us = side
    best = -INF
    n = generate(ply, no)
    each move i of the n moves {                # (sketch, not real Antares)
        make(mv_from[i], mv_to[i], mv_flag[i])
        when attacked(king_sq[us], 1 - us) {    # illegal: undo and skip
            unmake(mv_from[i], mv_to[i], mv_flag[i])
            skip
        }
        score = -search(-beta, -alpha, depth - 1, ply + 1)
        unmake(mv_from[i], mv_to[i], mv_flag[i])
        when score > best { best = score }
        when score > alpha { alpha = score }
        when alpha >= beta { stop }             # beta cutoff
    }
    best
}
```

`depth` counts how many more plies to search, and `ply` how far we are from the root. When no legal move was played, the position is checkmate (if in check) or stalemate (if not).

The real `search` in `search.ant` is about 300 lines, because it adds the ideas of the next chapters. But at its heart is this loop.

## Mate scores

Checkmate is scored as `ply - MATE`: very negative for the side that is mated, and less negative the further from the root it happens. So the engine prefers a quick mate to a slow one, and when it is losing, a slow mate to a quick one:

@listing search.ant lines from "INF = 32001" to "USED = "

`MATE_IN_MAX` is the dividing line: any score beyond it is a mate score. `NONE` marks "no score yet".

## Try it yourself

1. Change the first alpha-beta example so the tree has four moves for White, adding `[1, 20, 30]` at the end. What does it return, and how many leaves does it visit? Why so few for the new move?
2. In the minimax tree, what would White's best move be if Black always played the reply with the *biggest* number?

## Summary

- Minimax: each side picks its best move, the values worked out from the bottom up.
- Negamax scores for the side to move, so both sides maximise the negated child scores.
- Alpha-beta keeps a window (alpha, beta) and cuts off moves that can't matter; it gives the same answer as minimax.
- Good move ordering makes alpha-beta search up to twice as deep.

# Iterative Deepening {#iterative}

How deep should the engine search? It can't know in advance how long a depth will take. The answer, used by every engine, is to search 1 ply deep, then 2, then 3, and keep going until time runs out. This chapter shows that loop, `think`, and the tricks that make it better than it sounds.

## Deeper and deeper

Searching depth 1, then depth 2, then depth 3, seems wasteful: the work of the shallow searches is thrown away. But it isn't really:

- **Each depth costs much more than all the shallower ones together.** A search to depth 10 might take ten times as long as depth 9. Repeating the shallow ones adds only a little.
- **The engine always has an answer.** When time runs out, it plays the best move of the last depth it finished.
- **Shallow searches make deep ones faster.** The best moves they found are tried first at the next depth, through the transposition table (Chapter 20) and the move-ordering tables (Chapter 21). With good ordering, alpha-beta prunes far more. In practice iterative deepening is *faster* than searching straight to the final depth.

## think

Here is the main loop of the search:

@listing search.ant think

Before searching, `think` gets ready:

- it moves the transposition table on to a new **generation** (Chapter 20), resets the node count and clears the per-ply tables;
- it finds the first legal move, so that there is always a move to play even if time runs out at once;
- it sets the deepest depth allowed.

Then for each depth it searches with `search(alpha, beta, depth, 0, no)`. When the depth is finished, it takes the best move from the principal variation, reports it, and decides whether there's time for another depth.

Let's watch it from a program. `quiet_mode` turns off the `info` lines, and `depth_limit` says how deep to go:

```antares
use "search"
use "config"
load_network(NETWORK_FILE)
set_fen("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
quiet_mode = yes
repeat 7 as d {
    clear_tables()
    depth_limit = d
    best = think()
    show "depth {d}: {move_text(best)}, score {best_score}, {nodes} positions"
}
```

```output
depth 1: b1c3, score 25, 33 positions
depth 2: f1c4, score 55, 89 positions
depth 3: f1b5, score 28, 191 positions
depth 4: b1c3, score 71, 616 positions
depth 5: b1c3, score 72, 804 positions
depth 6: d2d4, score 54, 2017 positions
depth 7: d2d4, score 46, 3035 positions
```

Each line is a fresh search up to that depth (that's what `clear_tables` is for). The engine's opinion changes as it sees further: the Italian `f1c4` at depth 2, the Spanish `f1b5` at depth 3, and from depth 6 the Scotch, `d2d4`. Notice how slowly the number of positions grows: roughly doubling for each extra ply. Without alpha-beta and the other tricks of the coming chapters, each ply would multiply the work by about 30.

> **Antares.** `quiet_mode = yes` at the top level of a program changes the engine's variable directly. `change` is needed only inside a function.

## Aspiration windows

From depth 4 on, `think` doesn't search with the full window (-INF, INF). It guesses that the score will be close to the last depth's score, and searches with a narrow window around it, `prev_score - 18` to `prev_score + 18`. A narrow window prunes much more.

If the guess was wrong, the search **fails**: a score at or below alpha (**fail low**) means the position is worse than hoped; a score at or above beta (**fail high**) means it's better. Then it searches again with a wider window, widening by half again each time (`delta = delta + trunc(delta / 2)`), until the score lands inside.

```diagram
   depth 9 score was +40:   try (22, 58)
     score 70 >= 58: fail high      -> widen:  try (22, 88)
     score 75 inside the window     -> done
```

## The principal variation

The **principal variation** (PV) is the line of play the engine expects: its best move, the opponent's best reply, and so on. It's shown in the `info` lines, and its first move is the move to play. The search builds it up from the bottom: when a move becomes the best at some ply, that ply's PV becomes this move followed by the PV of the ply below:

@listing search.ant copy_pv

`pv_tab` is a square table, one row per ply. Row `ply` holds that ply's line, and `pv_len[ply]` its length.

## Reporting

After each depth, `report` prints the `info` line the GUI shows:

@listing search.ant report

Mate scores are turned into "mate in N moves": `mate 3` means the engine can mate in three moves, and `mate -2` that it will be mated in two.

## Try it yourself

1. Run the example with `repeat 8` instead of `repeat 7`. Does the best move change at depth 8?
2. Why does `think` throw away an iteration that was interrupted by the clock (`when stop_flag and depth > 1 { stop }`) instead of using its best move so far?

## Summary

- Iterative deepening searches depth 1, 2, 3, ... until time runs out; the shallow searches make the deep ones faster.
- Aspiration windows search a narrow window around the last score, widening on a fail.
- The principal variation is the expected line of best play, built up from the bottom.

# Quiescence Search {#quiescence}

Stop the search at a fixed depth and evaluate, and the engine makes terrible mistakes. This chapter explains why, and the cure: keep searching captures until the position is quiet.

## The horizon effect

Suppose the search reaches its last ply on a move where White's queen has just captured a pawn defended by another pawn. The evaluation looks at the position and sees White a pawn up. But on the very next move, Black takes the queen! The search stopped one ply too early to see it.

This is the **horizon effect**: whatever happens just beyond the search depth is invisible. An engine that evaluates in the middle of a capture sequence will happily grab defended pawns with its queen.

## Searching only captures

The cure is not to evaluate a position while captures are still possible. At depth 0, instead of evaluating, the search goes on with a special search, the **quiescence search**, that only tries captures (and queen promotions), until a quiet position is reached.

But capturing isn't compulsory. A side that doesn't like any capture can simply not capture. So in the quiescence search, the side to move can always "stand pat": accept the static evaluation as its score, and only search captures that might do better. Here is the engine's version:

@listing search.ant qsearch

The important parts:

1. **The transposition table** is checked first, as in the main search (Chapter 20).
2. **Stand pat.** If not in check, the evaluation is the starting score, `best = ev`. If that's already at least beta, stop at once. Otherwise it raises alpha.
3. **Only noisy moves.** `generate(ply, not checked)` makes only captures and queen promotions, unless the side to move is in check, when every move must be tried (standing pat isn't allowed in check: the check must be answered).
4. **Skip bad captures.** Captures that lose material by SEE are skipped (`not see_ge(src, dst, flag, 0)`).
5. **Futility pruning.** If even winning a little material (the eval plus 180) can't reach alpha, a capture that doesn't win clear material is skipped.
6. **Checkmate.** In check with no legal move, the side to move is mated.

Let's see it at work. In this position Black's queen could capture on d4, but the pawn is defended:

@board 4k3/8/8/3q4/3P4/4P3/8/4K3 b - - 0 1 | Black to move. Is the pawn on d4 a free gift? | d5d4

```antares
use "search"
use "config"
load_network(NETWORK_FILE)
set_fen("4k3/8/8/3q4/3P4/4P3/8/4K3 b - - 0 1")
show "evaluation: {evaluate()}"
show "quiescence search: {qsearch(-INF, INF, 0)}"
play_text_move("d5d4")
show "after Qxd4, evaluation for White: {evaluate()}, quiescence: {qsearch(-INF, INF, 0)}"
```

```output
evaluation: 848
quiescence search: 848
after Qxd4, evaluation for White: -783, quiescence: 77
```

After Qxd4 the plain evaluation thinks Black is far ahead (-783 for White, since White is to move), because Black has a queen and has just won a pawn. The quiescence search sees exd4, winning the queen, after which White is simply a pawn up: +77 for White. And *before* Qxd4, the quiescence search agrees with the plain evaluation, because Black's only capture loses the queen: Black's best choice is not to capture at all, standing pat.

## Why it ends

Every move in the quiescence search is a capture (unless in check), and there are only so many pieces to capture, so it always finishes. In practice the sequences are short, because SEE and futility pruning skip most captures, and standing pat cuts the rest off quickly.

## Try it yourself

1. Change the example's position so that the e3 pawn is on f2 instead. Is Qxd4 a good move now? What does the quiescence search say after it?
2. Why must the quiescence search try every move, not just captures, when the side to move is in check?

## Summary

- Stopping the search in the middle of captures gives wrong scores: the horizon effect.
- The quiescence search goes on with captures only, until the position is quiet.
- The side to move may stand pat on the evaluation; in check, every move is tried.
- Losing captures (by SEE) and hopeless ones (futility) are skipped.

# The Transposition Table {#tt}

Chess positions can be reached in many ways: 1. e4 e5 2. Nf3 and 1. Nf3 e5 2. e4 lead to the same position. Searching it twice would be a waste. The **transposition table** remembers what the search learned about each position, so it's found instead of searched again. It is one of the most important parts of any engine.

## What is stored

For every position it searches, the engine stores in the table:

- the position's **key** (Chapter 9), to recognise it again;
- the **best move** found;
- the **score**, and what kind of score it is (the **bound**);
- the **depth** it was searched to;
- the static **evaluation**, to save working it out again;
- the **age**: which search it was stored in.

The bound matters because, with alpha-beta, a score isn't always exact:

| Bound | Meaning | When |
|---|---|---|
| exact (3) | the score is the true value | a move scored between alpha and beta |
| lower (2) | the true value is at least this | a move scored beta or more and caused a cutoff |
| upper (1) | the true value is at most this | every move scored alpha or less |

## Buckets in one cache line

The table is a big array whose size is set by the `Hash` option, 64 MB by default. A key chooses a place in the array with its lowest bits, `key & tt_mask`. Many positions share a place, so each place is a **bucket** of 4 entries, and a position may use any entry of its bucket:

@listing search.ant lines from "# ----- transposition table -----" to "# ----- move ordering tables"

Each entry is two 64-bit integers: the full key, and one **packed** integer holding everything else, side by side in its bits:

```diagram
   bits  63..58   57..56   55..48       47..32         31..16          15..0
        +-------+-------+----------+--------------+--------------+------------+
        |  age  | bound |depth + 8 |  eval+32768  | score+32768  |    move    |
        +-------+-------+----------+--------------+--------------+------------+
```

A bucket is 4 × 16 = 64 bytes, exactly one **cache line**, the unit in which the processor fetches memory. Looking up a position therefore costs one trip to memory, however many entries are checked. The numbers are stored with an offset (`score + 32768`) so that negative scores become positive whole numbers that fit in 16 bits.

## Looking up and reading back

@listing search.ant tt_find

`(key & tt_mask) << 2` is the bucket's first entry: four entries per bucket. A match needs the whole key to be equal, and the entry not empty. The small functions after it unpack each part with shifts and `&`:

@listing search.ant lines from "to tt_move_at(i)" to "to clear_tables()"

## Storing

When a search of a position is finished, its result is stored. A bucket has room for only four positions, so storing a new one may mean throwing one out. Which one? The **replacement policy** decides:

@listing search.ant tt_store

1. If the position is already in the bucket, its entry is reused.
2. Otherwise an empty entry is used.
3. Otherwise the least valuable entry is replaced. An entry's value is its depth, minus 4 for every search since it was stored: deep results are worth keeping, but old ones from earlier moves of the game are probably no longer useful.

There's one more rule: a new result doesn't overwrite a *deeper* result for the same position, unless it is exact. But the new best move is still saved.

## Mate scores in the table

A mate score depends on how far the mate is from the root: "mate in 3 from here". But the same position can be reached at different distances from the root. So before storing, the engine turns the score into "mate in N from this position" by adding the ply, and when reading it back, `score_from_tt` subtracts the current ply again:

@listing search.ant score_from_tt

## Using the table in the search

At the start of `search`, the engine looks the position up:

@listing search.ant search from "# Transposition table" to "# Static evaluation"

If the stored result was searched at least as deep as we need, and its bound says it settles the question, the search returns the stored score at once without searching anything: a **TT cutoff**. A lower bound at or above beta is enough for a cutoff; an upper bound at or below alpha too; an exact score always. This isn't done in PV nodes (where `beta - alpha > 1`), to keep the principal variation accurate.

Even when there's no cutoff, the stored best move is tried first. That's the single most useful piece of move ordering, as the next chapter shows.

```antares
use "search"
use "config"
load_network(NETWORK_FILE)
set_fen(START_FEN)
quiet_mode = yes
depth_limit = 6
best = think()
i = tt_find(hash)
show "found: {i >= 0}, move {move_text(tt_move_at(i))}, depth {tt_depth_at(i)}, bound {tt_bound_at(i)}, score {tt_score_at(i)}"
show "best move {move_text(best)}"
```

```output
found: yes, move c2c4, depth 6, bound 3, score 26
best move c2c4
```

After a search to depth 6, the starting position is in the table with its best move, depth 6 and an exact score.

> **Watch out.** Two positions with the same key (a collision) would make the engine use the wrong position's move. That's why moves from the table are always checked before they are played (`quiet_is_playable`, Chapter 11, and the move generator for captures). A wrong score from a collision is rare enough to ignore.

## The Hash option

@listing search.ant set_hash

The table always has a power of two of buckets, so that `key & tt_mask` picks one with no division. 64 MB holds a million buckets, four million positions.

## Try it yourself

1. With `Hash` at 64, how many buckets are there? How many with 1 MB?
2. In the example, look up the position after `e2e4` instead. Is it in the table? What bound does it have?
3. Why is a TT cutoff not allowed when the stored depth is less than the depth needed now?

## Summary

- The transposition table stores each position's best move, score, bound, depth, evaluation and age.
- Entries are two integers; four make a 64-byte bucket, one cache line.
- Replacement keeps deep and recent results; mate scores are stored relative to the position.
- A stored result can cut the search off; the stored move is tried first.

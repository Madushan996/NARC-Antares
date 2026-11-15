# Move Ordering {#ordering}

Alpha-beta prunes the most when the best move is tried first (Chapter 17). The engine can't know the best move before searching, but it can make very good guesses. This chapter shows how it orders moves, and the tables of experience it keeps to do it.

## The order of moves

Antares Chess tries the moves at each position in roughly this order:

1. **The hash move:** the best move stored in the transposition table, from an earlier search of this position.
2. **Good captures:** captures that don't lose material by SEE, best victims first.
3. **Killer moves:** quiet moves that caused a cutoff at the same ply in a sibling position.
4. **The counter move:** the quiet move that last refuted the opponent's previous move.
5. **Other quiet moves,** ordered by their **history** score: how often they've been good before.
6. **Bad captures:** captures that lose material by SEE.

Each move gets a number in `mv_score`, and the moves are tried from the highest number down.

## Scoring the moves

@listing search.ant score_moves

The scores are chosen so the groups never mix: the hash move gets 1,073,741,824, every capture over 100,000,000, the killers 90,000,000 and 89,000,000, the counter move 88,000,000, and other quiet moves their history score (thousands, positive or negative).

Captures are ordered by **MVV**, *most valuable victim*: capturing a queen comes before capturing a pawn. The victim's value is multiplied by 10 and the capture history (below) breaks ties.

Then moves are picked one at a time, best first:

@listing search.ant pick

Picking the best remaining move each time, instead of sorting the whole list, is quicker when a cutoff comes after the first few moves, which is the usual case. A move that has been tried gets the score `USED`, so it isn't picked again.

## Killer moves

A quiet move that caused a beta cutoff in one position often does the same in its sibling positions: the positions at the same ply that differ only in an earlier move. If Qxh7 is mate after Black plays a6, it's probably mate after Black plays h6 too. The engine remembers two **killer moves** per ply, `killer1` and `killer2`, and tries them early.

## History tables

The **history** of a quiet move is a score of how often it caused cutoffs in the past, anywhere in the search. When a quiet move causes a cutoff, its history goes up; the quiet moves tried before it, which failed, go down. The engine keeps several history tables:

@listing search.ant lines from "# ----- move ordering tables" to "# Extra facts about each"

- `quiet_hist` is indexed by the side to move, the from and to squares, and whether each of those squares is attacked by the opponent. A move away from an attacked square is a very different move from the same move when nothing threatens it. This is called a **threat-split** history.
- `cont_hist`, the **continuation history**, is indexed by the previous move (its piece and square) and this move. It learns which replies work well against which moves: after the opponent's knight lands on f5, a bishop move to take it might be good.
- `cap_hist`, the **capture history**, does the same for captures.
- `counter_mv` holds the counter move for each previous move.

The squares the opponent attacks are worked out once per position with whole-bitboard shifts and the attack tables:

@listing search.ant mark_threats

## Updating a history

Each update moves an entry towards a limit of 16384, more slowly the closer it gets:

@listing search.ant hist_new

```antares
use "search"
h = 0
repeat 6 {
    h = hist_new(h, 3000)
    show h
}
show hist_new(h, -3000)
```

```output
3000
5451
7453
9089
10425
11517
6409
```

The first good result raises the entry by the full bonus, 3000; later ones by less and less, so no entry can grow without limit. A bad result brings it down quickly. This keeps the tables responsive: what was good earlier in the game slowly fades.

When a quiet move causes a cutoff, the engine updates its killers, its counter move and its histories, and penalises the quiet moves tried before it:

@listing search.ant update_quiet_stats

The bonus grows with depth, `min(170 * depth - 80, 1700)`: a cutoff found by a deep search is better evidence than one found near the leaves.

## Staged generation

The best ordering trick of all is not to generate moves at all when they aren't needed. If the hash move causes a cutoff, the other moves never need to exist. So the search generates moves in stages: the hash move first (checked with `quiet_is_playable`), then captures only (`gen_moves` mode 1), and the quiet moves (mode 2) only when the captures have run out without a cutoff:

@listing search.ant search from "# Staged move generation" to "best = -INF"

## Try it yourself

1. In the history example, how many updates of +3000 does it take to get above 15000?
2. Why are killer moves stored per ply, not for the whole search?

## Summary

- Moves are tried: hash move, good captures, killers, counter move, quiets by history, bad captures.
- Captures are ordered by victim value; quiets by history tables that learn from cutoffs.
- Histories move towards a limit, more slowly as they near it.
- Moves are generated in stages, so a cutoff often comes before most moves exist.

# Pruning {#pruning}

Alpha-beta only skips moves that *can't* change the result. Strong engines go much further: they skip moves and whole positions that *probably* don't matter, accepting a small risk of missing something for a huge saving in time. This chapter walks through the main search, `search`, and the pruning it does before and while trying moves.

## The start of a node

@listing search.ant search to "# Transposition table"

A node starts with the simple cases. At depth 0 it hands over to the quiescence search. It counts the node and checks the clock. Repetitions, the fifty-move rule and dead-drawn material score 0.

**Mate-distance pruning** comes next. A position at ply 5 can at best lead to a mate in 5 plies from here, so alpha and beta are narrowed to the best and worst possible mate scores. If even the best possible mate can't beat alpha, there's nothing to search.

Then comes the transposition table, which you saw in Chapter 20.

## The static evaluation

@listing search.ant search from "# Static evaluation" to "when not pv and not checked and excluded == 0 {"

Every node, apart from those in check, gets a **static evaluation**: the network's score, corrected by what the engine has learned about its mistakes (Chapter 24), or the stored score from the table when that's a better guess. The pruning below compares this number with alpha and beta.

**Improving** records whether the evaluation is better than it was two plies ago, at our previous move. If our position is getting better, pruning should be more careful, because there's more chance a move will turn out good.

## Node pruning

These tests can cut off a whole node before any move is tried. They are used only in non-PV nodes (`not pv`), where the window is a single point and the engine needs only to know whether the score is above or below it, and never when in check.

@listing search.ant search from "when not pv and not checked and excluded == 0 {" to "# Internal iterative reduction"

**Reverse futility pruning.** If the evaluation is far above beta, more than 69 per ply of depth left (less 63 if improving), the opponent is very unlikely to recover in so few plies. The node returns at once.

**Razoring.** The opposite case: if the evaluation is far *below* alpha at low depth, the engine checks with a quiescence search whether any capture could save it. If not, it gives up on the node.

**Null-move pruning.** The most powerful trick here. The engine *passes*: it lets the opponent move twice in a row (`make_null`) and searches the result with less depth. If our position is *still* at least beta even after giving the opponent a free move, it would certainly be at least beta with a real move. The reduction `r` is 3 plies, plus a third of the depth, plus more when the evaluation is far above beta.

> **Watch out.** Null-move pruning is wrong in **zugzwang**, positions where any move makes things worse, and passing would be best. These happen mostly in endgames with only king and pawns, so the engine doesn't try a null move unless the side to move has a piece other than pawns (`has_non_pawn(us)`). It also never makes two null moves in a row (`ss_move[sp - 1] != 0`).

**Internal iterative reduction.** In a PV or cut node with depth 4 or more and no hash move, the position has probably not been searched before, and the move ordering will be poor. The depth is reduced by one; if it turns out important, the next iteration will search it deeper, with a hash move.

## Move pruning

Inside the move loop, before a move is even played, it may be skipped:

@listing search.ant search from "# Move-level pruning" to "# Singular extension"

None of this happens at the root, or when every move so far leads to being mated (`best > -MATE_IN_MAX`).

- **Late move pruning.** After enough quiet moves have been tried at low depth (`lmp_limit`, about (3 + depth²) / 2), the rest are skipped. With good move ordering, late quiet moves rarely matter.
- **Futility pruning.** If the evaluation plus a margin (110 + 93 × depth) can't reach alpha, no quiet move is likely to help.
- **History pruning.** A quiet move with a very bad history at low depth is skipped.
- **SEE pruning.** A move that loses too much material by SEE is skipped: more than 56 × depth for quiet moves, and 28 × depth² for captures.

Each test is cheap and each saves a little. Together, they mean that the engine plays only a small fraction of the moves at most nodes.

## How much pruning helps

The constants, like 69, 110 or 93, were tuned by playing many thousands of games. Change one and the engine gets weaker in a way only long matches can measure (Chapter 28). They come from NARC Genesys 5.1, the C++ engine Antares Chess was first ported from.

## Try it yourself

1. With depth 4 and an improving position, what is `lmp_limit`? (`imp` is 1.)
2. Why would null-move pruning be dangerous in a king and pawn endgame?

## Summary

- Mate-distance pruning and the transposition table come first.
- The static evaluation, corrected, drives most pruning; *improving* makes it more careful.
- Reverse futility, razoring and null-move pruning can cut a whole node.
- Late-move, futility, history and SEE pruning skip moves before they are played.

# Reductions and Extensions {#reductions}

Pruning skips moves completely. A softer idea is to search some moves **less deeply** (reductions) and others **more deeply** (extensions). This chapter covers the rest of the move loop: late move reductions, principal variation search, check and singular extensions, and what happens when all the moves have been searched.

## Late move reductions

Thanks to move ordering, the best move is almost always one of the first few. So moves late in the list are searched with less depth. If one surprises the engine by scoring well, it's searched again at full depth. This is **late move reductions**, LMR:

@listing search.ant search from "when depth >= 3 and moves_played > late_from" to "when root { root_nodes"

The base reduction comes from a table worked out at the start, which grows with both the depth and the number of moves already tried:

@listing search.ant lines from "# Late-move reduction table" to "# ----- search state"

```antares
use "search"
each d in [3, 6, 10, 20] {
    show "depth {d}: move 2 by {lmr[d * 64 + 2]}, move 5 by {lmr[d * 64 + 5]}, move 10 by {lmr[d * 64 + 10]}, move 30 by {lmr[d * 64 + 30]}"
}
```

```output
depth 3: move 2 by 1, move 5 by 1, move 10 by 1, move 30 by 2
depth 6: move 2 by 1, move 5 by 2, move 10 by 2, move 30 by 3
depth 10: move 2 by 1, move 5 by 2, move 10 by 3, move 30 by 4
depth 20: move 2 by 1, move 5 by 2, move 10 by 3, move 30 by 5
```

Then the reduction is adjusted: more in cut nodes, less in PV nodes, when improving, or for a move that gives check, and less (or more) for a quiet move with a good (or bad) history. Captures are reduced half as much.

## Principal variation search

Look at the calls in the listing above. Most use the window `(-alpha - 1, -alpha)`, a **null window**, only one point wide. A null-window search can't find a move's exact score; it only answers "is this move better than alpha, yes or no?". But it answers much faster, because almost everything gets cut off.

This is **principal variation search** (PVS). The engine assumes the first move is the best. It searches the first move with the full window, and every later move with a null window, just to prove it isn't better. Only if a move *does* score above alpha (and below beta) is it searched again with the full window to find its real score. Since good move ordering makes the first move best most of the time, the re-searches are rare.

## Extensions

Some moves deserve *more* depth.

**Check extension.** A move that gives check gets one extra ply (`gives_check`). Checks are forcing, and lines with checks are where tactics hide.

**Singular extension.** If the hash move is much better than every other move, the position is "forced": it all depends on that one move, so it deserves a deeper look. To find out, the engine searches every *other* move with a reduced depth and a window just below the hash move's stored score, leaving the hash move out (`ss_excluded`):

@listing search.ant search from "# Singular extension" to "ss_move[sp] = code"

- If every other move fails below `s_beta`, the hash move is **singular**: it's extended by one ply, or two if the others are far below.
- If even the others reach beta, there are several good moves, and this node will cut off anyway: return at once. This is called **multi-cut**.
- If the hash move's own score is above beta but not singular, it's searched a ply *less* (a negative extension).

Extensions are limited to plies below twice the root depth (`ply < 2 * root_depth`), so the search can't run away down an endless line of checks.

## Playing the move

@listing search.ant search from "ss_move[sp] = code" to "when depth >= 3 and moves_played > late_from"

The move is recorded in the search stack (`ss_move` and `ss_pt`, used by the continuation history and counter moves of the plies below), played, and taken back at once if it leaves the king in check.

## Keeping score

@listing search.ant search from "when root { root_nodes" to "when moves_played == 0 {"

After each move, the best score is updated. When a move beats alpha, it becomes the best move here, and if alpha reaches beta, the loop stops: a beta cutoff. Moves that didn't become the best are remembered, so their histories can be lowered if another move causes a cutoff. At the root, the number of positions under each move is counted, for time management (Chapter 25).

## The end of a node

@listing search.ant search from "when moves_played == 0 {"

When the loop is over:

1. **No move played** means checkmate (in check) or stalemate (not in check). But with pruning, it could also mean every move was pruned, so `has_legal_move` checks there really are none.
2. **A cutoff** rewards the move that caused it: `update_quiet_stats` for a quiet move (killers, counter move, histories), `update_capture_stats` for a capture.
3. **The result is stored** in the transposition table with its bound: lower after a cutoff, exact if a move landed inside the window in a PV node, upper otherwise.
4. **The correction histories** learn from the difference between the search result and the static evaluation (Chapter 24).

## Try it yourself

1. Using the LMR table, how much is the 10th move reduced at depth 10, in a PV node, when improving, with a neutral history? (Start from 3, take 1 off for PV and 1 for improving.)
2. Why is it safe to search later moves with a null window?

## Summary

- Late moves are searched with reduced depth (LMR), and re-searched if they surprise.
- PVS searches the first move with the full window and the rest with a null window.
- Checks and singular hash moves are extended; multi-cut returns early when several moves beat beta.
- At the end of a node: mate or stalemate, history rewards, a table entry and correction updates.

# Correction History {#correction}

The network evaluation is good, but it has blind spots: certain kinds of position where it is consistently too optimistic or too pessimistic. The search can notice this, because it finds out what the position is really worth. **Correction history** remembers these errors and corrects the evaluation in similar positions.

## Learning from the search

Every time a node is searched, the engine knows two numbers: the static evaluation it started with (`raw_eval`) and the score the search found (`best`). If the search keeps finding scores 50 centipawns higher than the evaluation in positions with a certain pawn structure, then the evaluation is probably underrating that pawn structure, and the next position with it should be corrected upwards.

"Positions like this one" are recognised by the partial keys of Chapter 9:

@listing search.ant lines from "pawn_corr = zeros(32768)" to "order_type = "

- `pawn_corr`, by the pawn key: corrections for pawn structures;
- `np_corr`, by each side's non-pawn key: corrections for piece placements;
- `minor_corr`, by the minor-piece key;
- `cont_corr`, by the last two moves.

Each is split by the side to move. The keys are cut down to 14 bits (`pawn_key & 16383`) to choose an entry.

## Correcting

@listing search.ant corrected

The correction is a weighted sum of the five entries, scaled down by 2048, and added to the raw evaluation. The pawn correction counts most (48), then the non-pawn ones (32 each) and the minor-piece and continuation ones (24 each).

## Updating

@listing search.ant update_correction

The goal is the search's error, `(best - raw) * 16`, limited to ±6400. Each entry moves towards the goal by a weight that grows with depth: a deep search is better evidence. The weighted average `(entry * (512 - weight) + goal * weight) / 512` makes each entry a slowly moving average of the errors it has seen.

Let's watch one entry learn:

```antares
use "search"
show corrected(50, 0, 0, 16384, 0, -1)
repeat 3 {
    update_correction(50, 150, 8, 0, 0, 16384, 0, -1)
    show corrected(50, 0, 0, 16384, 0, -1), pawn_corr[0]
}
```

```output
50
66 253
80 466
92 645
```

The raw evaluation is 50 and a depth-8 search keeps finding 150. At first the correction is nothing. After each update, the corrected evaluation moves towards 150: 66, 80, 92.

## When to learn

The engine only learns when the result says something reliable about the evaluation:

- not in check (there is no static evaluation then);
- not after a capture caused the cutoff (a capture changes the material, so the evaluation of the position before it isn't at fault);
- not when the bound points the wrong way: a lower bound that is below the evaluation, or an upper bound above it, doesn't say how far off the evaluation was;
- not with mate scores.

## Try it yourself

1. In the example, keep updating. What does the corrected evaluation approach? Why doesn't it reach 150 exactly? (Hint: look at the weights 48, 32, 32 and 24.)
2. Why is each correction table split by the side to move?

## Summary

- The search learns how far the evaluation is off in positions with the same pawns, pieces or recent moves.
- `corrected` adds a weighted sum of the learned errors to the network's evaluation.
- Entries are moving averages, updated more strongly by deeper searches.

# Time Management {#time}

In a real game the engine has a clock. Think too long and it loses on time; think too little and it plays weak moves. This chapter shows how Antares Chess decides how long to think, and how it adjusts as the search goes.

## Two limits

When the GUI sends `go wtime 60000 btime 60000 winc 1000 binc 1000`, the engine works out two limits:

- the **soft limit**: after finishing a depth, don't start another if this much time has passed;
- the **hard limit**: stop at once, even in the middle of a depth, at this time.

@listing antares_chess.ant go

The calculation, for a game without `movestogo`:

1. `left` is the time on the clock, minus the **move overhead** (80 ms by default) kept back for the time it takes the GUI to pass messages.
2. The engine plans for about 30 more moves (`mtg`), so a fair share is `left / mtg`.
3. The increment is added to the soft limit in proportion to the time left: with a big reserve, the engine spends up to three quarters of the increment.
4. The hard limit is at most four times the share plus the increment, and never more than two fifths of the clock.

Some worked numbers:

| Clock | Increment | Soft limit | Hard limit |
|---|---|---|---|
| 60 s | 0 | 1.997 s | 7.988 s |
| 60 s | 1 s | 2.747 s | 11.988 s |
| 5 s | 0 | 0.164 s | 0.656 s |
| 0.5 s | 0.1 s | 0.035 s | 0.168 s |

## Checking the clock

The search checks the clock every 128 nodes, not at every one, because reading the clock takes time too:

@listing search.ant should_stop

The same function listens for commands from the GUI while searching: `stop` ends the search, `quit` ends the program, and `isready` must be answered at once even while thinking. Any other command is kept in `pending_line` and handled when the search is over.

> **Antares.** `input_waiting()` says whether a line of input is waiting, without stopping to wait for one. It's what lets the engine think and listen at the same time with only one thread.

## Spending time wisely

The soft limit is adjusted after each depth, at the end of `think`:

@listing search.ant think from "# Soft limit, scaled" to "prev_best = best_move"

Three things are measured:

- **Stability.** If the best move hasn't changed for several depths, the engine is fairly sure of it and can stop sooner: from 1.6 times the soft limit down to 0.72 times after eight stable depths.
- **A falling score.** If the score dropped since the last depth, something has gone wrong and it's worth thinking longer, up to 1.5 times. A rising score allows a little less (0.85).
- **Focus.** If most of the search's positions went to the best move (`root_nodes`), the other moves were refuted quickly and the choice is clear: stop sooner. If the best move got only a small share, the alternatives were close: think longer.

These factors are multiplied together, and by 0.75.

## Try it yourself

1. Work out the soft and hard limits for 10 seconds on the clock with no increment.
2. Why does `think` only check the soft limit between depths, while the hard limit is checked inside the search?

## Summary

- The soft limit decides whether to start another depth; the hard limit stops the search at once.
- The clock is checked every 128 nodes, together with input from the GUI.
- The soft limit shrinks when the best move is stable and focused, and grows when the score falls.

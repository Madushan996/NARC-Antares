"""Builds docs/Inside_Antares_Chess.pdf, the book about the engine's code,
from the chapters in docs/src/chapters (read in file-name order).

Needs Python 3 with `markdown`, `pygments`, `pymupdf` and `chess`
(python-chess, for the board pictures), and Google Chrome or Microsoft Edge
(used headless to lay out and print the pages).

    python docs/src/build.py

Besides ordinary Markdown, a line on its own can be one of these:

  @listing board.ant put_piece
        the function put_piece from src/board.ant, with the comment above it
  @listing search.ant search from "# Null-move" to "# Internal"
        part of a function: from the line holding the first text up to
        (not including) the line holding the second; `to` may be left out
  @listing board.ant lines from "HIST = 2400" to "# Position keys"
        part of the file outside any function, chosen the same way
  @board <FEN> | caption | e2e4 g1f3
        a chess board, optionally with arrows
  @bitboard 0x... | caption | <FEN>
        the squares of a bitboard shaded, optionally over a position
  @squares
        the board with every square's number

Listings are read from the engine's source each time the book is built, so
they always show the code as it is.
"""

import base64
import html
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import chess
import chess.svg
import fitz  # pymupdf
import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexer import RegexLexer, bygroups, include, words
from pygments.token import Comment, Keyword, Name, Number, Operator, Punctuation, String, Text

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent
ROOT = DOCS.parent
SRC = ROOT / "src"
OUT = DOCS / "Inside_Antares_Chess.pdf"
TITLE = "Inside Antares Chess"
DATE = "November 2026"
ENGINE_VERSION = "1.0"
LANG_VERSION = "0.5.0"

KEYWORDS = """and as ask by change descend each else give in learn model not or repeat
show skip stop to try use using when while with xor within problem""".split()
CONSTANTS = ["yes", "no", "nothing"]
BUILTINS = """zeros ones rand randn seed range shape reshape t sum mean max min argmax softmax
onehot grad exp log tanh sigmoid relu sqrt abs sin cos floor round trunc clip sum_rows rows
compact expand screlu sum_product screlu_dot update_rows read_binary input_waiting len int
ints popcount lowest_bit highest_bit div rand_bits push map filter reduce keys values has join
split sort reverse slice upper lower trim replace lines text number kind read write input clock
fail check json to_json save load exists program_folder key wait clear draw args env append
delete files now fixed pad code char insert remove find unique sort_by""".split()


class AntaresLexer(RegexLexer):
    name = "Antares"
    tokens = {
        "root": [
            (r"#.*$", Comment.Single),
            (r"\s+", Text),
            (r'"', String, "text"),
            (r"(to)(\s+)([A-Za-z_]\w*)", bygroups(Keyword, Text, Name.Function)),
            (r"0[xX][0-9A-Fa-f_]+", Number.Hex),
            (r"\d[\d_]*(\.\d+)?([eE][+-]?\d+)?", Number),
            (words(KEYWORDS, suffix=r"\b"), Keyword),
            (words(CONSTANTS, suffix=r"\b"), Keyword.Constant),
            (words(BUILTINS, suffix=r"\b(?=\s*\()"), Name.Builtin),
            (r"[A-Za-z_]\w*", Name),
            (r"->|=>", Operator.Word),
            (r"==|!=|<=|>=|<<|>>|[-+*/%^@<>=&|~]", Operator),
            (r"[()\[\]{},.:]", Punctuation),
        ],
        "text": [
            (r"\\.", String.Escape),
            (r"\{", String.Interpol, "interp"),
            (r'"', String, "#pop"),
            (r'[^"\\{]+', String),
        ],
        "interp": [
            (r"\}", String.Interpol, "#pop"),
            include("root"),
        ],
    }


LEXER = AntaresLexer()
FORMATTER = HtmlFormatter(nowrap=True, classprefix="tk-")


def highlight_code(src: str) -> str:
    return highlight(src, LEXER, FORMATTER).rstrip("\n")


def highlight_any(src, name):
    if name.endswith(".py"):
        from pygments.lexers import PythonLexer
        return highlight(src, PythonLexer(), FORMATTER).rstrip("\n")
    return highlight_code(src)


# ---------------------------------------------------------------------------
# Listings from the engine's source

_sources = {}
LISTED = {}          # (file, function) -> chapters whose listings show it
CURRENT = {"chapter": ""}


def note_listed(name, fname):
    chapters = LISTED.setdefault((name, fname), [])
    if CURRENT["chapter"] and CURRENT["chapter"] not in chapters:
        chapters.append(CURRENT["chapter"])


def source_lines(name):
    if name not in _sources:
        path = HERE / name if name == "book.ant" else SRC / name
        _sources[name] = path.read_text(encoding="utf-8").split("\n")
    return _sources[name]


def function_span(lines, fname):
    """First and last line index of a function, with the comment block above it."""
    py = re.compile(rf"^def {re.escape(fname)}\(")
    start = next((i for i, l in enumerate(lines) if py.match(l)), None)
    if start is not None:
        # a Python function: up to the next line that isn't indented
        end = start
        for j in range(start + 1, len(lines)):
            if lines[j].strip() and not lines[j].startswith((" ", "\t")):
                break
            end = j
        while not lines[end].strip():
            end -= 1
        return start, end
    pat = re.compile(rf"^to {re.escape(fname)}\(")
    start = next((i for i, l in enumerate(lines) if pat.match(l)), None)
    if start is None:
        raise SystemExit(f"@listing: no function {fname}")
    head = lines[start]
    if not head.rstrip().endswith("{"):
        end = start
    else:
        depth = 0
        end = start
        for j in range(start, len(lines)):
            code = re.sub(r'"(\\.|[^"\\])*"', '""', lines[j]).split("#")[0]
            depth += code.count("{") - code.count("}")
            if depth == 0:
                end = j
                break
    top = start
    while top > 0 and lines[top - 1].startswith("#"):
        top -= 1
    return top, end


def dedent(block):
    widths = [len(l) - len(l.lstrip(" ")) for l in block if l.strip()]
    cut = min(widths) if widths else 0
    return [l[cut:] for l in block]


def listing(args):
    name = args[0]
    lines = source_lines(name)
    rest = args[1:]
    if rest and rest[0] == "lines":
        lo, hi, what = 0, len(lines) - 1, None
        rest = rest[1:]
    else:
        fname = rest[0]
        lo, hi = function_span(lines, fname)
        what = fname
        rest = rest[1:]
    a, b = lo, hi
    if rest and rest[0] == "from":
        a = next((i for i in range(lo, hi + 1) if rest[1] in lines[i]), None)
        if a is None:
            raise SystemExit(f"@listing {name}: no line with {rest[1]!r}")
        rest = rest[2:]
    if rest and rest[0] == "to":
        stop = next((i for i in range(a + 1, hi + 1) if rest[1] in lines[i]), None)
        if stop is None:
            raise SystemExit(f"@listing {name}: no line with {rest[1]!r} after {a + 1}")
        b = stop - 1
        rest = rest[2:]
    while b > a and not lines[b].strip():
        b -= 1
    block = dedent(lines[a:b + 1])
    if what:
        note_listed(name, what)
    for l in lines[a:b + 1]:
        mm = re.match(r"to (\w+)\(", l)
        if mm:
            note_listed(name, mm.group(1))
    part = what and (a, b) != (lo, hi)
    if name == "book.ant":
        label = "docs/src/book.ant"
    elif name.startswith("../"):
        label = name[3:]
    else:
        label = f"src/{name}"
    where = f"line {a + 1}" if a == b else f"lines {a + 1}\u2013{b + 1}"
    if what:
        cap = f'<span class="lst-file">{label}</span><span class="lst-fn">{"part of " if part else ""}{html.escape(what)}()</span><span class="lst-lines">{where}</span>'
    else:
        cap = f'<span class="lst-file">{label}</span><span class="lst-lines">{where}</span>'
    brk = " keep" if len(block) <= 30 else ""
    return (f'<div class="listing{brk}"><div class="lst-cap">{cap}</div>'
            f'<pre class="code lst"><code>{highlight_any(chr(10).join(block), name)}</code></pre></div>')


# ---------------------------------------------------------------------------
# Board pictures

COLORS = {"square light": "#f0e4cf", "square dark": "#b58863", "margin": "#ffffff", "coord": "#6b7280",
          "square light lastmove": "#f6c89a", "square dark lastmove": "#e0975a"}


def svg_figure(svg, caption, cls="board"):
    svg = re.sub(r'^<\?xml[^>]*>\s*', "", svg)
    cap = f"<figcaption>{caption}</figcaption>" if caption else ""
    return f'<figure class="{cls}">{svg}{cap}</figure>'


def board_figure(args_text):
    parts = [p.strip() for p in args_text.split("|")]
    fen = parts[0]
    caption = parts[1] if len(parts) > 1 else ""
    arrows = []
    if len(parts) > 2 and parts[2]:
        for m in parts[2].split():
            arrows.append(chess.svg.Arrow(chess.parse_square(m[:2]), chess.parse_square(m[2:4]), color="#c2410ccc"))
    b = chess.Board(fen) if fen != "empty" else chess.Board(None)
    svg = chess.svg.board(b, size=300, arrows=arrows, colors=COLORS, coordinates=True)
    return svg_figure(svg, md_inline(caption))


def bitboard_figure(args_text):
    parts = [p.strip() for p in args_text.split("|")]
    bits = int(parts[0], 16) if parts[0].lower().startswith("0x") else int(parts[0])
    caption = parts[1] if len(parts) > 1 else ""
    fen = parts[2] if len(parts) > 2 and parts[2] else None
    b = chess.Board(fen) if fen else chess.Board(None)
    fill = {sq: "#e8743bcc" for sq in range(64) if bits >> sq & 1}
    svg = chess.svg.board(b, size=300, fill=fill, colors=COLORS, coordinates=True)
    return svg_figure(svg, md_inline(caption))


def squares_table():
    rows = []
    for r in range(7, -1, -1):
        cells = [f'<th>{r + 1}</th>']
        for f in range(8):
            sq = r * 8 + f
            dark = (r + f) % 2 == 0
            cells.append(f'<td class="{"d" if dark else "l"}"><b>{sq}</b><i>{"abcdefgh"[f]}{r + 1}</i></td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    rows.append("<tr><th></th>" + "".join(f"<th>{c}</th>" for c in "abcdefgh") + "</tr>")
    return '<figure class="squares"><table class="sqgrid">' + "".join(rows) + "</table><figcaption>Every square's number: a1 is 0, h1 is 7, a8 is 56 and h8 is 63.</figcaption></figure>"


FILES = ["board.ant", "nnue.ant", "search.ant", "antares_chess.ant", "config.ant"]

DESC = {
    "on_board": "Whether a file and rank are on the board",
    "bishop_ray": "Bishop attacks by cutting rays at blockers (builds the magic tables)",
    "rook_ray": "Rook attacks by cutting rays at blockers (builds the magic tables)",
    "inner_ray": "A ray without its last square, for the magic masks",
    "rook_att": "Rook attacks for any occupancy, by magic look-up",
    "bishop_att": "Bishop attacks for any occupancy, by magic look-up",
    "put_piece": "Puts a piece on a square, updating bitboards and keys",
    "take_piece": "Removes the piece on a square, updating bitboards and keys",
    "attacked": "Whether a square is attacked by a colour",
    "in_check": "Whether the side to move is in check",
    "attackers_to": "Every piece of both colours attacking a square",
    "has_non_pawn": "Whether a side has a piece other than pawns and king",
    "save_state": "Saves what a move can't undo, for this ply",
    "restore_state": "Restores the saved state",
    "make": "Plays a move",
    "unmake": "Takes a move back",
    "make_null": "Passes the turn (null move)",
    "unmake_null": "Takes a null move back",
    "is_repetition": "Whether the position occurred before",
    "insufficient_material": "Whether neither side can mate",
    "push_move": "Adds a move to the move rows",
    "push_targets": "Adds a move to each square of a bitboard",
    "gen_pawns": "Generates pawn moves",
    "gen_castles": "Generates castling moves",
    "gen_moves": "Generates all moves, captures only, or quiet moves only",
    "generate": "Generates the moves for a search ply",
    "quiet_is_playable": "Whether a stored quiet move can be played here",
    "has_legal_move": "Whether any legal move exists",
    "see_ge": "Whether an exchange wins at least a threshold (SEE)",
    "square_name": "A square's name, like e4",
    "move_text": "A move as text, like e7e8q",
    "set_fen": "Sets up a position from FEN",
    "find_move": "Finds a legal move by its text",
    "play_text_move": "Plays a move given as text",
    "board_text": "The board as a picture in text",
    "perft": "Counts the positions a number of plies ahead",
    "load_network": "Reads a network file",
    "set_view": "Chooses the mirroring and king bucket for one side's view",
    "feature": "The input number of a piece on a square",
    "rebuild": "A view's king-lane hidden layer from scratch",
    "rebuild_s": "A view's shared-lane hidden layer from scratch",
    "refresh": "A view's accumulator from the king-bucket cache",
    "accumulator": "Brings a view's accumulator up to date",
    "network_units": "The network's output, using the accumulators",
    "full_lane": "One lane's output from scratch",
    "network_units_full": "The network's output from scratch, as a check",
    "evaluate": "The evaluation in centipawns",
    "elapsed_ms": "Milliseconds since the search started",
    "set_hash": "Sets the transposition table's size",
    "clear_tt": "Empties the transposition table",
    "tt_find": "Finds a position's entry in the transposition table",
    "tt_move_at": "The move of a table entry",
    "tt_score_at": "The score of a table entry",
    "tt_eval_at": "The static evaluation of a table entry",
    "tt_depth_at": "The depth of a table entry",
    "tt_bound_at": "The bound of a table entry",
    "clear_tables": "Clears the table and the histories for a new game",
    "should_stop": "Checks the clock, node limit and GUI input",
    "hist_new": "A history entry after a bonus",
    "tt_store": "Stores a search result in the table",
    "score_from_tt": "A stored score with mate distance from this ply",
    "mark_threats": "The squares the opponent attacks",
    "score_moves": "Gives each move an ordering score",
    "pick": "The best-scored move not yet tried",
    "corrected": "The evaluation plus the learned corrections",
    "corr_new": "A correction entry moved towards a goal",
    "update_correction": "Learns from the search's result",
    "quiet_bonus": "Updates a quiet move's histories",
    "update_quiet_stats": "Killers, counter move and histories after a cutoff",
    "update_capture_stats": "Capture history after a cutoff",
    "copy_pv": "Builds the principal variation",
    "qsearch": "The quiescence search",
    "search": "The main alpha-beta search",
    "report": "Prints an info line",
    "think": "Iterative deepening: searches and gives the best move",
    "ensure_network": "Loads the network if not loaded yet",
    "set_position": "The position command",
    "go_value": "A number from the go command",
    "go": "The go command: time limits and search",
    "set_option": "The setoption command",
    "handle": "Handles one UCI command",
    "find_network": "Finds the network file",
}


def function_map():
    parts = []
    for name in FILES:
        rows = []
        for i, l in enumerate(source_lines(name)):
            m = re.match(r"to (\w+)\(", l)
            if not m:
                continue
            f = m.group(1)
            chs = ", ".join(LISTED.get((name, f), [])) or "–"
            rows.append(f"<tr><td><code>{f}</code></td><td>{i + 1}</td><td>{html.escape(DESC.get(f, ''))}</td><td>{chs}</td></tr>")
        parts.append(f'<h3>src/{name}</h3><table class="fmap"><thead><tr><th>Function</th><th>Line</th>'
                     f'<th>What it does</th><th>Chapter</th></tr></thead><tbody>{"".join(rows)}</tbody></table>')
    return "".join(parts)


def md_inline(s):
    out = markdown.markdown(s)
    return re.sub(r"^<p>(.*)</p>$", r"\1", out, flags=re.S)


def expand_directives(md_text):
    """Replaces @ lines by placeholders; gives the text and the HTML for each."""
    stash = []

    def keep(h):
        stash.append(h)
        return f"\n\nSTASHEDBLOCK{len(stash) - 1}END\n\n"

    out = []
    in_fence = False
    for line in md_text.split("\n"):
        if line.startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("@listing "):
            out.append(keep(listing(shlex.split(line[len("@listing "):]))))
        elif not in_fence and line.startswith("@board "):
            out.append(keep(board_figure(line[len("@board "):])))
        elif not in_fence and line.startswith("@bitboard "):
            out.append(keep(bitboard_figure(line[len("@bitboard "):])))
        elif not in_fence and line.strip() == "@squares":
            out.append(keep(squares_table()))
        elif not in_fence and line.strip() == "@functionmap":
            out.append(keep(function_map()))
        else:
            out.append(line)
    return "\n".join(out), stash


def restore(s, stash):
    s = re.sub(r"<p>STASHEDBLOCK(\d+)END</p>", lambda m: stash[int(m.group(1))], s)
    return re.sub(r"STASHEDBLOCK(\d+)END", lambda m: stash[int(m.group(1))], s)


# ---------------------------------------------------------------------------
# Markdown to HTML


def convert(md_text: str):
    chapters = re.split(r"(?m)^(?=# .*\{#[\w-]+[^}]*\}\s*$)", md_text)
    chapters = [c for c in chapters if c.strip()]
    body, toc = [], []
    chap_no, app_no, part_no = 0, 0, 0
    for chunk in chapters:
        m = re.match(r"# (.+?)\s*\{#([\w-]+)(\s+\.(appendix|part))?\}\s*\n", chunk)
        title, cid, kind = m.group(1), m.group(2), m.group(4)
        rest = chunk[m.end():]
        if kind == "part":
            part_no += 1
            roman = ["I", "II", "III", "IV", "V", "VI", "VII"][part_no - 1]
            intro = markdown.markdown(rest)
            toc.append((f"Part {roman}", title, cid, [], "part"))
            body.append(f'<section class="part" id="{cid}"><div class="part-label">Part {roman}</div>'
                        f'<h1 class="part-title">{html.escape(title)}</h1><div class="part-intro">{intro}</div></section>')
            continue
        if kind == "appendix":
            label = "Appendix " + chr(ord("A") + app_no)
            prefix = chr(ord("A") + app_no)
            app_no += 1
        else:
            chap_no += 1
            label = f"Chapter {chap_no}"
            prefix = str(chap_no)
        CURRENT["chapter"] = prefix
        text, stash = expand_directives(rest)
        md = markdown.Markdown(extensions=["tables", "fenced_code", "attr_list", "sane_lists"])
        inner = md.convert(text)
        inner = process_code(inner)
        inner = process_callouts(inner)
        inner = process_images(inner)
        inner = restore(inner, stash)
        sections = []
        sec_no = 0

        def number_h2(mm):
            nonlocal sec_no
            sec_no += 1
            text = mm.group(1)
            sid = f"{cid}-{sec_no}"
            num = f"{prefix}.{sec_no}"
            if strip_tags(text) not in ("Try it yourself", "Summary") and not strip_tags(text).startswith("Chapter "):
                sections.append((num, strip_tags(text), sid))
            return f'<h2 id="{sid}"><span class="secno">{num}</span>{text}</h2>'

        inner = re.sub(r"<h2>(.*?)</h2>", number_h2, inner)
        toc.append((label, title, cid, sections, kind))
        body.append(
            f'<section class="chapter{" appendix" if kind == "appendix" else ""}" id="{cid}">'
            f'<div class="chap-head"><div class="chap-label">{label}</div>'
            f'<h1>{html.escape(title)}</h1></div>{inner}</section>'
        )
    return "\n".join(body), toc


def strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s))


CODE_RE = re.compile(r'<pre><code(?: class="language-(\w+)")?>(.*?)</code></pre>', re.S)
LABELS = {"output": "Output", "shell": "Terminal", "session": "UCI session", "diagram": None}


def process_code(s: str) -> str:
    def repl(m):
        lang = m.group(1) or "antares"
        src = html.unescape(m.group(2)).rstrip("\n")
        lines = src.count("\n") + 1
        brk = " keep" if lines <= 32 else ""
        if lang == "antares":
            return f'<pre class="code{brk}"><code>{highlight_code(src)}</code></pre>'
        label = LABELS.get(lang)
        body = html.escape(src)
        if lang == "shell":
            body = "\n".join(f'<span class="prompt">$</span> {line}' if line.strip() else line for line in body.split("\n"))
        if lang == "session":
            # lines typed to the engine start with "> "
            body = "\n".join(f'<span class="typed">{line[5:]}</span>' if line.startswith("&gt; ") else line for line in body.split("\n"))
        tag = f'<span class="blk-label">{label}</span>' if label else ""
        return f'<pre class="blk {lang}{brk}">{tag}<code>{body}</code></pre>'

    return CODE_RE.sub(repl, s)


CALLOUTS = {"Tip.": "tip", "Try it.": "try", "Remember.": "remember", "Watch out.": "warn", "In the engine.": "engine",
            "Chess note.": "chess", "Antares.": "lang"}


def process_images(s: str) -> str:
    def repl(m):
        alt, src = html.unescape(m.group(1)), m.group(2)
        data = base64.b64encode((HERE / src).read_bytes()).decode("ascii")
        kind = "png" if src.lower().endswith(".png") else "jpeg"
        return (f'<figure><img src="data:image/{kind};base64,{data}" alt="{html.escape(alt)}">'
                f'<figcaption>{html.escape(alt)}</figcaption></figure>')

    return re.sub(r'<p>\s*<img alt="([^"]*)" src="([^"]+)"\s*/?>\s*</p>', repl, s)


def process_callouts(s: str) -> str:
    def repl(m):
        inner = m.group(1)
        kind = next((k for word, k in CALLOUTS.items() if f"<strong>{word}" in inner), "note")
        return f'<aside class="callout {kind}">{inner}</aside>'

    return re.sub(r"<blockquote>\s*(.*?)\s*</blockquote>", repl, s, flags=re.S)


# ---------------------------------------------------------------------------
# Page furniture


def toc_html(toc, pages):
    rows = []
    for label, title, cid, sections, kind in toc:
        if kind == "part":
            rows.append(f'<li class="toc-part"><a href="#{cid}"><span class="toc-title">{label}: {html.escape(title)}</span>'
                        f'<span class="toc-pg">{pages.get(cid, "00")}</span></a></li>')
            continue
        short = label.replace("Chapter ", "").replace("Appendix ", "")
        rows.append(
            f'<li class="toc-ch"><a href="#{cid}"><span class="toc-num">{short}</span>'
            f'<span class="toc-title">{html.escape(title)}</span>'
            f'<span class="toc-pg">{pages.get(cid, "00")}</span></a></li>'
        )
        for num, stitle, sid in sections:
            rows.append(
                f'<li class="toc-sec"><a href="#{sid}"><span class="toc-num">{num}</span>'
                f'<span class="toc-title">{html.escape(stitle)}</span>'
                f'<span class="toc-pg">{pages.get(sid, "00")}</span></a></li>'
            )
    return '<section class="toc"><h1 class="toc-h">Contents</h1><ol>' + "".join(rows) + "</ol></section>"


def cover_html():
    lines = source_lines("board.ant")
    a, b = function_span(lines, "attacked")
    code = highlight_code("\n".join(lines[a + 1:b + 1]))
    logo = base64.b64encode((ROOT / "builds" / "logo" / "antares-chess-icon.png").read_bytes()).decode("ascii")
    return f'''<section class="cover">
  <img class="cover-logo" src="data:image/png;base64,{logo}" alt="">
  <div class="cover-top">
    <div class="cover-kicker">Chess engine programming with Antares</div>
    <div class="cover-title">Inside<br>Antares Chess</div>
    <div class="cover-sub">A beginner's guide to how a chess engine works, line by line</div>
    <div class="cover-tag">Every listing in this book is the engine's real code, read from its source when the
    book was made. Learn how computers play chess, and the Antares language they are written in, at the same time.</div>
  </div>
  <pre class="cover-code"><code>{code}</code></pre>
  <div class="cover-foot">
    <div><span class="cf-k">Engine</span>Antares Chess {ENGINE_VERSION}</div>
    <div><span class="cf-k">Language</span>Antares {LANG_VERSION}</div>
    <div><span class="cf-k">Edition</span>{DATE}</div>
  </div>
</section>'''


def page_html(body, toc, pages):
    css = (HERE / "style.css").read_text(encoding="utf-8")
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{html.escape(TITLE)}</title>
<style>{css}</style></head>
<body>{cover_html()}{toc_html(toc, pages)}{body}</body></html>'''


# ---------------------------------------------------------------------------
# Printing


def find_browser():
    for p in [
        os.environ.get("CHROME", ""),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]:
        if p and Path(p).exists():
            return p
    for name in ["google-chrome", "chromium", "chromium-browser", "chrome", "msedge"]:
        found = shutil.which(name)
        if found:
            return found
    sys.exit("Couldn't find Chrome or Edge. Set the CHROME environment variable to its path.")


def print_pdf(browser, html_text, pdf_path, work):
    src = Path(work) / "book.html"
    src.write_text(html_text, encoding="utf-8")
    profile = Path(work) / "profile"
    subprocess.run(
        [browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         f"--user-data-dir={profile}", f"--print-to-pdf={pdf_path}", src.as_uri()],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300,
    )


def heading_pages(pdf_path, ids):
    doc = fitz.open(pdf_path)
    found = {}
    for page in doc:
        for link in page.get_links():
            name = link.get("nameddest")
            if name in ids and link.get("page", -1) >= 0:
                found[name] = link["page"] + 1
    doc.close()
    missing = [i for i in ids if i not in found]
    if missing:
        sys.exit(f"No page found for {len(missing)} headings, e.g. {missing[:3]}")
    return found


def read_book():
    files = sorted((HERE / "chapters").glob("*.md"))
    return "\n\n".join(f.read_text(encoding="utf-8").strip() + "\n" for f in files)


def main():
    body, toc = convert(read_book())
    ids = []
    for _, _, cid, sections, _ in toc:
        ids.append(cid)
        ids += [sid for _, _, sid in sections]
    if "--html" in sys.argv:
        (DOCS / "book.html").write_text(page_html(body, toc, {}), encoding="utf-8")
        print("wrote docs/book.html")
        return
    browser = find_browser()
    with tempfile.TemporaryDirectory() as work:
        first = Path(work) / "pass1.pdf"
        print_pdf(browser, page_html(body, toc, {}), first, work)
        pages = heading_pages(first, ids)
        final = Path(work) / "pass2.pdf"
        print_pdf(browser, page_html(body, toc, pages), final, work)
        check = heading_pages(final, ids)
        if check != pages:
            sys.exit("Page numbers moved between passes; run again")

        doc = fitz.open(final)
        outline = []
        for label, title, cid, sections, kind in toc:
            outline.append([1, f"{label}: {title}", pages[cid]])
            outline += [[2, f"{num}  {stitle}", pages[sid]] for num, stitle, sid in sections]
        doc.set_toc([[1, "Cover", 1], [1, "Contents", 2]] + outline)
        doc.set_metadata({
            "title": TITLE,
            "subject": "How the Antares Chess engine works, and the Antares language it is written in",
            "keywords": "chess engine, chess programming, Antares, bitboards, alpha-beta, NNUE",
            "creator": "docs/src/build.py",
            "producer": "Chrome + PyMuPDF",
        })
        doc.save(OUT, garbage=3, deflate=True)
        n = doc.page_count
        doc.close()
    print(f"Wrote {OUT} ({n} pages)")


if __name__ == "__main__":
    main()

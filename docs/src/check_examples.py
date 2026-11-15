"""Runs every ```antares example in the book and compares it with the
```output box after it, so the book stays right as the engine changes.

  python docs/src/check_examples.py              every chapter in docs/src/chapters
  python docs/src/check_examples.py file.md ...  just these

Examples are run from the engine's src folder, so they can `use "board"`,
`use "nnue"` or `use "search"` and work with the real engine code.
Uses `antares` on the PATH (or the ANTARES environment variable).

Markers on the line before a code box:
  <!-- norun -->   not run (a fragment, or it needs typing or other files)
  <!-- error -->   expected to stop with a problem; the output box holds the message
"""
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent.parent / "src"
ANTARES = os.environ.get("ANTARES", "antares")

FENCE = re.compile(r"^```(\w*)\s*$")


def blocks(text):
    lines = text.split("\n")
    out = []
    i = 0
    marker = None
    while i < len(lines):
        line = lines[i]
        m = FENCE.match(line)
        if m:
            lang = m.group(1) or "antares"
            start = i + 1
            j = start
            while not lines[j].startswith("```"):
                j += 1
            out.append({"lang": lang, "code": "\n".join(lines[start:j]), "line": i + 1, "end": j + 1, "marker": marker})
            marker = None
            i = j + 1
            continue
        s = line.strip()
        if s.startswith("<!--"):
            marker = s[4:-3].strip()
        elif s:
            marker = None
        i += 1
    return out


def clean(s):
    lines = [l.rstrip() for l in s.replace("\r\n", "\n").split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def main():
    bad = 0
    total = 0
    paths = sys.argv[1:] or [str(p) for p in sorted((HERE / "chapters").glob("*.md"))]
    # the book's helper file, which examples load with `use "book"`
    helper = SRC / "book.ant"
    placed = not helper.exists()
    if placed:
        helper.write_text((HERE / "book.ant").read_text(encoding="utf-8"), encoding="utf-8")
    try:
        return run_all(paths)
    finally:
        if placed:
            helper.unlink()


def run_all(paths):
    bad = 0
    total = 0
    for path in paths:
        text = open(path, encoding="utf-8").read()
        all_lines = text.split("\n")
        bs = blocks(text)
        for k, b in enumerate(bs):
            if b["lang"] != "antares" or b["marker"] == "norun":
                continue
            total += 1
            expected = None
            if k + 1 < len(bs) and bs[k + 1]["lang"] == "output":
                between = all_lines[b["end"]:bs[k + 1]["line"] - 1]
                if all(not l.strip() for l in between):
                    expected = bs[k + 1]["code"]
            src = SRC / f"_book_example_{os.getpid()}.ant"
            src.write_text(b["code"] + "\n", encoding="utf-8")
            try:
                p = subprocess.run([ANTARES, src.name], capture_output=True, text=True, encoding="utf-8",
                                   stdin=subprocess.DEVNULL, cwd=SRC, timeout=300)
            finally:
                src.unlink()
            got = p.stdout + (p.stderr if b["marker"] == "error" else "")
            got = got.replace(src.name, "example.ant")
            problem = None
            if b["marker"] == "error":
                if p.returncode == 0:
                    problem = "expected a problem, but it ran"
            elif p.returncode != 0:
                problem = "stopped with a problem:\n" + clean(p.stderr)
            if problem is None and expected is not None and clean(got) != clean(expected):
                problem = "output differs:\n--- expected\n" + clean(expected) + "\n--- got\n" + clean(got)
            if problem:
                bad += 1
                print(f"{path}:{b['line']}: {problem}\n")
    print(f"{total - bad} of {total} examples ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

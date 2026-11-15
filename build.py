"""Builds the engine binaries into builds/.

  python build.py            every variant
  python build.py avx2       just one (generic, sse42, avx2 or native)

Needs the `antares` command and Rust (cargo) installed. Each variant takes
about a minute. The network file is embedded, so every binary runs on its own,
and so is the icon (on Windows; it needs Antares 0.2.0 or later).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "Antares-Chess"

# variant name -> processor level passed to `antares build --cpu`
VARIANTS = {
    "generic": "x86-64",       # any 64-bit PC
    "sse42": "x86-64-v2",      # SSE4.2 and POPCNT (2009 and later)
    "avx2": "x86-64-v3",       # AVX2 and BMI2 (2013 and later)
    "native": "native",        # exactly the machine doing the build
}


def main():
    wanted = sys.argv[1:] or list(VARIANTS)
    os.makedirs(os.path.join(HERE, "builds"), exist_ok=True)
    for v in wanted:
        if v not in VARIANTS:
            print(f"unknown variant {v}; choose from {', '.join(VARIANTS)}")
            return 1
        out = os.path.join(HERE, "builds", f"{NAME}-{v}.exe")
        print(f"building {v} ...", flush=True)
        network = os.path.join(HERE, "networks", "antares-chess.nnue")
        icon = os.path.join(HERE, "builds", "logo", "antares-chess.ico")
        r = subprocess.run(["antares", "build", os.path.join(HERE, "src", "antares_chess.ant"), out, "--cpu", VARIANTS[v], "--embed", network, "--icon", icon])
        if r.returncode != 0:
            return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())

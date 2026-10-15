"""Check a Lean snippet against the FSOT hub.

The hub stays read-only. The snippet is written under this folder and
compiled with the hub's pinned toolchain through `lake env`, so the
check uses Lean 4.31.0 from FSOT-2.1-Lean/lean-toolchain.

A catalog formula string is not Lean. Pass a declaration, for example:

    theorem demo : True := by trivial
"""

from __future__ import annotations

import argparse
import subprocess
import textwrap
from pathlib import Path

HUB = Path(r"C:\Users\damia\Desktop\FSOT-2.1-Lean")
CHECK_DIR = Path(r"C:\Users\damia\Desktop\math si\checks")
LAKE = Path(r"C:\Users\damia\.elan\bin\lake.exe")


def write_file(code: str) -> Path:
    CHECK_DIR.mkdir(parents=True, exist_ok=True)
    body = textwrap.dedent(
        """\
        import FSOT.Scalar

        namespace MathSiCheck
        """
    )
    path = CHECK_DIR / "Candidate.lean"
    path.write_text(body + "\n" + code.strip() + "\n\nend MathSiCheck\n", encoding="utf-8")
    return path


def check(code: str, timeout: int) -> int:
    path = write_file(code)
    command = [str(LAKE), "env", "lean", str(path)]
    completed = subprocess.run(
        command,
        cwd=HUB,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    print(completed.stdout, end="")
    print(completed.stderr, end="")
    print(f"EXIT {completed.returncode}")
    return completed.returncode


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, help="File of Lean code to append after importing FSOT.Scalar")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Compile #check FSOT.k. Proves the hub import path, not a new theorem.",
    )
    args = parser.parse_args()
    if args.smoke:
        code = "#check FSOT.k"
    elif args.file:
        code = args.file.read_text(encoding="utf-8")
    else:
        parser.error("Pass --smoke or --file")
        return
    raise SystemExit(check(code, args.timeout))


if __name__ == "__main__":
    main()

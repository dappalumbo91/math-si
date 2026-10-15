"""Check the dial contract in Lean and the same table in Python.

Does not load Gemma, does not write the hub, and does not append the ledger.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\damia\Desktop\math si")
sys.path.insert(0, str(ROOT))

from dial.engine import gate
from dial.score import kill_metric, score_row
from lean_check import check

LEDGER = ROOT / "ledger" / "attempts.jsonl"
CONTRACT = ROOT / "checks" / "Contract.lean"


def kill_table() -> None:
    cases = [
        (None, "unscored", True),
        (score_row(1.0, 1.0, None), "no_published_uncertainty", True),
        (score_row(3.0, 1.0, 100.0), "outside_published_uncertainty", True),
        (score_row(2.0, 1.0, 100.0), "inside_published_uncertainty", False),
        (score_row(1.0, 1.0, 10.0), "inside_published_uncertainty", False),
    ]
    for score, reason, killed in cases:
        got = kill_metric(score)
        if got["reason"] != reason or got["killed"] is not killed or got["send"] is not False:
            raise SystemExit(f"python kill table drifted: {got} expected {reason}")
    blocked = gate("phi*1.25")
    if blocked["ok"] or "decimal_literal" not in blocked["reasons"]:
        raise SystemExit(f"decimal gate drifted: {blocked}")


def model_lines() -> dict:
    """Apply the declaration rule to proposals the model already logged."""
    declarations = ("theorem ", "lemma ", "def ")
    seen = 0
    lean_shaped = 0
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("source") != "usage-kill":
            continue
        seen += 1
        text = str(row.get("proposal") or "").lstrip()
        if text.startswith(declarations):
            lean_shaped += 1
    return {"usage_proposals": seen, "lean_declarations": lean_shaped}


def main() -> None:
    kill_table()
    logged = model_lines()
    if logged["lean_declarations"] != 0:
        raise SystemExit(f"a logged proposal is shaped like Lean: {logged}")
    code = CONTRACT.read_text(encoding="utf-8")
    exit_code = check(code, timeout=180)
    if exit_code != 0:
        raise SystemExit(exit_code)
    print(json.dumps({"lean": "accepted", "python_kill_table": "matched", **logged}))


if __name__ == "__main__":
    main()

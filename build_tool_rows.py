"""Build proposal rows from recorded expressions that already pass the gate.

The target is the recorded formula. It is not a number fitted to the measurement.
"""

from __future__ import annotations

import json
from pathlib import Path

from dial.catalog import rows
from dial.engine import gate
from dial.prompt import RECORD_USER, chat_example, proposal_prompt, proposal_target

ROOT = Path(r"C:\Users\damia\Desktop\math si\corpus")
TOOL_PATH = ROOT / "tool_train.jsonl"
COMBINED_PATH = ROOT / "combined.jsonl"
RECORD_PATH = ROOT / "train.jsonl"


def main() -> None:
    kept = 0
    dropped = 0
    with TOOL_PATH.open("w", encoding="utf-8") as handle:
        for row in rows():
            formula = str(row.get("formula") or "")
            decision = gate(formula)
            if not decision["ok"]:
                dropped += 1
                continue
            example = chat_example(proposal_prompt(row), proposal_target(formula))
            handle.write(json.dumps(example, ensure_ascii=False) + "\n")
            kept += 1
    record_rows = 0
    with COMBINED_PATH.open("w", encoding="utf-8") as handle:
        for line in TOOL_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                handle.write(line + "\n")
                record_rows += 1
        for line in RECORD_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            example = chat_example(RECORD_USER, item["text"])
            handle.write(json.dumps(example, ensure_ascii=False) + "\n")
            record_rows += 1
    print(json.dumps({"tool_rows_kept": kept, "tool_rows_dropped": dropped, "combined": record_rows}, indent=2))


if __name__ == "__main__":
    main()

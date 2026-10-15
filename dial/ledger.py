"""Append-only attempt ledger. A line here is not a hub commit."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

LEDGER = Path(r"C:\Users\damia\Desktop\math si\ledger\attempts.jsonl")


def log_attempt(record: dict) -> dict:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": datetime.now(timezone.utc).isoformat(), **record}
    with LEDGER.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row

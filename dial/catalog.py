"""Read the exported formula points. The hub JSON stays where it is."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

POINTS = Path(r"C:\Users\damia\Desktop\math si\corpus\formula_points.jsonl")


def _bar_pct(row: dict) -> float | None:
    sigma = row.get("sigma_equivalent")
    error = row.get("error_pct")
    try:
        sigma_f = float(sigma)
        error_f = abs(float(error))
    except (TypeError, ValueError):
        return None
    if sigma_f <= 0 or error_f <= 0:
        return None
    return error_f / sigma_f


@lru_cache(maxsize=1)
def rows() -> tuple[dict, ...]:
    if not POINTS.exists():
        raise FileNotFoundError(POINTS)
    loaded: list[dict] = []
    for line in POINTS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        row["reference_uncertainty_pct"] = _bar_pct(row)
        loaded.append(row)
    return tuple(loaded)


def lookup(name: str, property_name: str | None = None) -> dict | None:
    wanted = name.strip().lower()
    prop = property_name.strip().lower() if property_name else None
    for row in rows():
        row_name = str(row.get("name") or "").lower()
        row_prop = str(row.get("property") or "").lower()
        if row_name != wanted:
            continue
        if prop is not None and row_prop != prop:
            continue
        return row
    return None


def neighbors(row: dict, limit: int = 5) -> list[dict]:
    domain = row.get("domain")
    name = row.get("name")
    found: list[dict] = []
    for other in rows():
        if other.get("domain") != domain or other.get("name") == name:
            continue
        found.append(
            {
                "name": other.get("name"),
                "property": other.get("property"),
                "formula": other.get("formula"),
            }
        )
        if len(found) >= limit:
            break
    return found

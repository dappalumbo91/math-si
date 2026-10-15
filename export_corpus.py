"""Export recorded FSOT math from the Lean hub.

Reads C:\\Users\\damia\\Desktop\\FSOT-2.1-Lean and writes JSONL under corpus/.
Does not modify the hub, does not invent a formula, and does not mix a
second pin into the engine. A row is kept only when the file already
states it.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

HUB = Path(r"C:\Users\damia\Desktop\FSOT-2.1-Lean")
OUT = Path(r"C:\Users\damia\Desktop\math si\corpus")
MAX_JSON_BYTES = 200 * 1024 * 1024
MAX_LEAN_CHARS = 4000
SKIP_DIR_NAMES = {".lake", ".git", "climate_cache", "figures", "audit_gauntlet_20260909"}

DECL_RE = re.compile(
    r"^(?:@\S+\s+)*(?:(?:private|protected|noncomputable|unsafe)\s+)*"
    r"(theorem|lemma|def|abbrev)\s+(\S+)"
)
PY_DEF_RE = re.compile(r"^(def|class)\s+(\w+)")

RULE = (
    "This is a recorded FSOT data point from the Lean hub. "
    "Repeat the recorded formula and the recorded numbers. "
    "Do not invent a coefficient. "
    "A new formal statement counts only after Lean 4 accepts it."
)


def rel(path: Path) -> str:
    return path.relative_to(HUB).as_posix()


def skip_dir(path: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in path.parts)


EXPR_KEYS = ("formula", "leaf", "math", "expression", "closed_form")
MATH_MARKS = set("*^/+-()=") | set("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺")


def is_math_expression(text: str) -> bool:
    """Keep a recorded expression. Drop status labels and bare chemical formulas."""
    if any(mark in text for mark in MATH_MARKS):
        return True
    lowered = text.lower()
    return any(token in lowered for token in ("phi", "pi", "sqrt", "exp", "log", "sin", "cos"))


def recorded_expression(node: dict) -> str | None:
    for key in EXPR_KEYS:
        value = node.get(key)
        if isinstance(value, str) and is_math_expression(value.strip()):
            return value.strip()
    return None


def walk_formulas(node, found: list[dict]) -> None:
    if isinstance(node, dict):
        formula = recorded_expression(node)
        if formula:
            measure = node.get("scientific_measurement")
            if not isinstance(measure, dict):
                measure = {}
            sigma = measure.get("sigma_equivalent")
            if sigma is None:
                sigma = node.get("sigmas_above_bar")
            found.append(
                {
                    "formula": formula,
                    "name": node.get("name"),
                    "property": node.get("property"),
                    "lab": node.get("lab"),
                    "computed": node.get("computed"),
                    "measured": node.get("measured"),
                    "error_pct": node.get("error_pct"),
                    "formula_branch": node.get("formula_branch"),
                    "domain": node.get("domain_display_name") or node.get("domain") or node.get("fsot_domain"),
                    "display_name": node.get("display_name"),
                    "record_source": node.get("source") if isinstance(node.get("source"), str) else None,
                    "sigma_equivalent": sigma,
                    "precision_tier": measure.get("precision_tier") or node.get("accuracy_class"),
                }
            )
        for value in node.values():
            walk_formulas(value, found)
    elif isinstance(node, list):
        for item in node:
            walk_formulas(item, found)


def point_key(row: dict) -> str:
    raw = "|".join(
        str(row.get(field))
        for field in ("formula", "name", "property", "computed", "measured", "domain")
    )
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()


def export_formulas() -> dict:
    out_path = OUT / "formula_points.jsonl"
    seen: set[str] = set()
    written = 0
    raw = 0
    files = 0
    skipped: list[str] = []
    roots = [HUB / "data", HUB / "predictions", HUB / "results"]
    with out_path.open("w", encoding="utf-8") as handle:
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*.json"):
                if skip_dir(path):
                    continue
                if path.stat().st_size > MAX_JSON_BYTES:
                    skipped.append(rel(path))
                    continue
                files += 1
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, json.JSONDecodeError):
                    skipped.append(rel(path))
                    continue
                found: list[dict] = []
                walk_formulas(payload, found)
                for row in found:
                    raw += 1
                    key = point_key(row)
                    if key in seen:
                        continue
                    seen.add(key)
                    row["source_file"] = rel(path)
                    row["kind"] = "formula_point"
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    written += 1
    return {
        "files_read": files,
        "raw_formula_objects": raw,
        "unique_formula_points": written,
        "skipped": skipped,
        "path": str(out_path),
    }


def export_lean() -> dict:
    out_path = OUT / "lean_decls.jsonl"
    written = 0
    with out_path.open("w", encoding="utf-8") as handle:
        for path in (HUB / "FSOT").rglob("*.lean"):
            if skip_dir(path):
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            starts = [i for i, line in enumerate(lines) if DECL_RE.match(line)]
            for index, start in enumerate(starts):
                end = starts[index + 1] if index + 1 < len(starts) else len(lines)
                match = DECL_RE.match(lines[start])
                text = "\n".join(lines[start:end]).strip()
                if len(text) > MAX_LEAN_CHARS:
                    text = text[:MAX_LEAN_CHARS] + "\n-- truncated for the training row"
                row = {
                    "kind": "lean_decl",
                    "decl_kind": match.group(1),
                    "name": match.group(2),
                    "source_file": rel(path),
                    "line": start + 1,
                    "text": text,
                }
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                written += 1
    return {"lean_decls": written, "path": str(out_path)}


def flatten_constants(node, prefix: str, rows: list[dict]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            flatten_constants(value, child, rows)
    elif isinstance(node, str) and node[:1].isdigit() or (
        isinstance(node, str) and node[:1] == "-" and len(node) > 1 and node[1].isdigit()
    ):
        rows.append({"kind": "constant", "name": prefix, "value": node, "source_file": "data/canonical_constants.json"})


def export_constants_and_engine() -> dict:
    const_path = HUB / "data" / "canonical_constants.json"
    rows: list[dict] = []
    if const_path.exists():
        flatten_constants(json.loads(const_path.read_text(encoding="utf-8")), "", rows)
    engine = HUB / "vendor" / "fsot_compute.py"
    engine_rows = 0
    out_path = OUT / "law_and_constants.jsonl"
    with out_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        if engine.exists():
            lines = engine.read_text(encoding="utf-8", errors="replace").splitlines()
            starts = [i for i, line in enumerate(lines) if PY_DEF_RE.match(line)]
            for index, start in enumerate(starts):
                end = starts[index + 1] if index + 1 < len(starts) else min(len(lines), start + 80)
                match = PY_DEF_RE.match(lines[start])
                text = "\n".join(lines[start:end]).strip()
                if len(text) > MAX_LEAN_CHARS:
                    text = text[:MAX_LEAN_CHARS]
                row = {
                    "kind": "engine_def",
                    "decl_kind": match.group(1),
                    "name": match.group(2),
                    "source_file": "vendor/fsot_compute.py",
                    "line": start + 1,
                    "text": text,
                }
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                engine_rows += 1
    return {
        "constants": len(rows),
        "engine_defs": engine_rows,
        "path": str(out_path),
    }


def render_formula(row: dict) -> str:
    lines = [
        RULE,
        f"FILE: {row.get('source_file')}",
        f"DOMAIN: {row.get('domain')}",
        f"NAME: {row.get('name')}",
        f"PROPERTY: {row.get('property')}",
        f"FORMULA: {row.get('formula')}",
        f"COMPUTED: {row.get('computed')}",
        f"MEASURED: {row.get('measured')}",
        f"ERROR_PCT: {row.get('error_pct')}",
        f"SIGMA: {row.get('sigma_equivalent')}",
    ]
    return "\n".join(lines)


def render_decl(row: dict) -> str:
    return "\n".join(
        [
            RULE,
            f"FILE: {row.get('source_file')}",
            f"DECL: {row.get('decl_kind')} {row.get('name')}",
            "SOURCE:",
            row.get("text") or "",
        ]
    )


def render_constant(row: dict) -> str:
    return "\n".join(
        [
            RULE,
            f"FILE: {row.get('source_file')}",
            f"CONSTANT: {row.get('name')}",
            f"VALUE: {row.get('value')}",
        ]
    )


def build_train(counts: dict) -> dict:
    out_path = OUT / "train.jsonl"
    written = 0
    with out_path.open("w", encoding="utf-8") as handle:
        sources = [
            (OUT / "formula_points.jsonl", render_formula),
            (OUT / "lean_decls.jsonl", render_decl),
            (OUT / "law_and_constants.jsonl", None),
        ]
        for path, renderer in sources:
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if renderer is None:
                    text = render_constant(row) if row.get("kind") == "constant" else render_decl(row)
                else:
                    text = renderer(row)
                handle.write(json.dumps({"text": text}, ensure_ascii=False) + "\n")
                written += 1
    counts["train_rows"] = written
    counts["train_path"] = str(out_path)
    return counts


def main() -> None:
    if not HUB.exists():
        raise SystemExit(f"Lean hub not found: {HUB}")
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {
        "hub": str(HUB),
        "formulas": export_formulas(),
        "lean": export_lean(),
        "law": export_constants_and_engine(),
    }
    summary = build_train(summary)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

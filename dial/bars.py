"""Published uncertainty for the kill metric.

A number enters the kill only from the formula row's own sigma or from the
hub's cited literature anchors. Dataset lines and arXiv hits tell the
retrieval where a published uncertainty would come from. A stated ± in an
abstract is a comparison. It is not copied into the kill percent.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ANCHORS_PATH = Path(r"C:\Users\damia\Desktop\FSOT-2.1-Lean\data\literature_uncertainty_anchors.json")
SPECIES_PATH = Path(
    r"I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full\vendor\species\fsot_species_catalog.json"
)
ARXIV_LOCATIONS = Path(r"C:\Users\damia\Desktop\math si\corpus\arxiv_bar_locations.jsonl")
ARXIV_SNAPSHOT = Path(r"D:\training data\arXiv Dataset\arxiv-metadata-oai-snapshot.json")
CODATA_ASCII = Path(r"K:\FSOT-PublicData\open_science_large\codata\allascii.txt")

# Property names on formula rows that share one arXiv search.
ARXIV_QUERY = {
    "acoustic_impedance_MRayl": "acoustic_impedance",
    "acoustic_impedance": "acoustic_impedance",
    "work_function_eV": "work_function",
    "thermal_cond_W_mK": "thermal_cond",
    "h_fus_kJ_mol": "h_fus",
    "bulk_GPa": "bulk_modulus",
    "resistivity_uOhm_cm": "resistivity",
    "grueneisen": "grueneisen",
    "cp_J_molK": "specific_heat",
    "expansion_e6_per_K": "thermal_expansion",
    "poisson_ratio": "poisson",
    "boiling_K": "boiling",
    "refractive_index": "refractive_index",
    "youngs_GPa": "youngs",
    "vapor_p_kPa": "vapor_pressure",
}


@lru_cache(maxsize=1)
def anchors() -> dict[str, dict]:
    if not ANCHORS_PATH.exists():
        return {}
    document = json.loads(ANCHORS_PATH.read_text(encoding="utf-8"))
    return dict(document.get("anchors") or {})


@lru_cache(maxsize=1)
def arxiv_locations() -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    if not ARXIV_LOCATIONS.exists():
        return grouped
    for line in ARXIV_LOCATIONS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        grouped.setdefault(str(row.get("query") or ""), []).append(row)
    return grouped


def _measured(row: dict) -> float | None:
    try:
        value = row.get("measured")
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _matches(center: float, uncertainty: float, measured: float) -> bool:
    span = max(uncertainty, 0.01 * abs(measured))
    return abs(center - measured) <= span


def arxiv_compare(prop: str, measured: float | None) -> str:
    """One retrieval line. Matching abstracts stay out of the kill percent."""
    query = ARXIV_QUERY.get(prop, "")
    if not query:
        return "ARXIV_COMPARE: this property was not in the local snapshot search"
    hits = arxiv_locations().get(query, [])
    phrase = query.replace("_", " ")
    if not hits:
        return f"ARXIV_COMPARE: no abstract states a ± next to {phrase}"
    matched: list[str] = []
    stated: list[str] = []
    for hit in hits:
        for item in hit.get("stated") or []:
            text = str(item.get("text") or "")
            if text and text not in stated:
                stated.append(text)
            if measured is None:
                continue
            try:
                center = float(item["center"])
                uncertainty = float(item["uncertainty"])
            except (KeyError, TypeError, ValueError):
                continue
            if _matches(center, uncertainty, measured):
                matched.append(f"{hit.get('id')} states {text}")
    if matched:
        shown = "; ".join(matched[:2])
        return (
            f"ARXIV_CANDIDATE: {shown}. The center is near MEASURED {measured}. "
            "It stays out of the kill percent."
        )
    shown = "; ".join(stated[:3]) if stated else "none parsed"
    measured_text = "missing" if measured is None else str(measured)
    return (
        f"ARXIV_COMPARE: {len(hits)} abstracts state a ± next to {phrase}. "
        f"Stated values include {shown}. None match MEASURED {measured_text}. "
        "They stay out of the kill percent."
    )


def resolve_bar(row: dict) -> dict:
    """Return the published percent uncertainty, or a missing bar with locations."""
    pct = row.get("reference_uncertainty_pct")
    try:
        pct_f = float(pct) if pct is not None else None
    except (TypeError, ValueError):
        pct_f = None
    if pct_f is not None and pct_f > 0:
        return {
            "pct": pct_f,
            "reference": None,
            "source": "sigma_equivalent",
            "status": "published",
            "arxiv": [],
        }

    prop = str(row.get("property") or "")
    anchor = anchors().get(prop)
    if anchor and anchor.get("measured_uncertainty_pct") is not None:
        return {
            "pct": float(anchor["measured_uncertainty_pct"]),
            "reference": anchor.get("reference"),
            "source": "data/literature_uncertainty_anchors.json",
            "status": "published",
            "arxiv": [],
        }

    query = ARXIV_QUERY.get(prop, "")
    return {
        "pct": None,
        "reference": None,
        "source": "missing",
        "status": "missing",
        "arxiv": arxiv_locations().get(query, [])[:3],
        "compare": arxiv_compare(prop, _measured(row)),
        "looked_in": [
            str(SPECIES_PATH),
            str(ANCHORS_PATH),
            str(ARXIV_SNAPSHOT),
            str(CODATA_ASCII),
        ],
    }


def bar_lines(row: dict) -> list[str]:
    """Lines the proposal retrieval shows beside the measurement."""
    bar = resolve_bar(row)
    if bar["status"] == "published":
        lines = [f"PUBLISHED_UNCERTAINTY_PCT: {bar['pct']}"]
        if bar.get("reference"):
            lines.append(f"REFERENCE: {bar['reference']}")
        lines.append(f"BAR_SOURCE: {bar['source']}")
        return lines
    prop = str(row.get("property") or "")
    lines = [
        "PUBLISHED_UNCERTAINTY_PCT: missing",
        "BAR_SOURCE: missing",
        f"DATASET: {SPECIES_PATH} | uncertainty_column=no | measured center only",
        f"DATASET: {ANCHORS_PATH} | entry_for_{prop}=no",
        f"DATASET: {ARXIV_SNAPSHOT} | kind=abstract index | uncertainty_table=no",
        f"DATASET: {CODATA_ASCII} | uncertainty_column=yes | fundamental constants",
        str(bar.get("compare") or ""),
    ]
    return [line for line in lines if line]

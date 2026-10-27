"""Evaluate a recorded expression with the pinned hub engine.

The numeric names come from vendor/fsot_compute.py. The parser is the hub's
scripts/math_formula_eval.py. This module does not write either file and
does not use the portable core_context() mirror.
"""

from __future__ import annotations

import importlib
import json
import math
import re
import sys
from functools import lru_cache
from pathlib import Path

HUB = Path(r"C:\Users\damia\Desktop\FSOT-2.1-Lean")

_SUPERSCRIPTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


def _load_hub():
    vendor = str(HUB / "vendor")
    scripts = str(HUB / "scripts")
    for entry in (vendor, scripts):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    compute = importlib.import_module("fsot_compute")
    parser = importlib.import_module("math_formula_eval")
    return compute, parser


# Formula names the hub leaves unbound, and the CODATA record that measures them.
# Bare c and bare g stay Catalan's constant. The hub normalizer already rewrites them.
_CODATA_ALIAS = {
    "h": "Planck_constant",
    "m_e": "electron_mass",
    "m_p": "proton_mass",
    "m_proton": "proton_mass",
    "m_n": "neutron_mass",
    "m_mu": "muon_mass",
    "m_u": "atomic_mass_constant",
    "mu_0": "vacuum_magnetic_permeability",
    "mu0": "vacuum_magnetic_permeability",
    "epsilon_0": "vacuum_electric_permittivity",
    "eps0": "vacuum_electric_permittivity",
    "k_b": "Boltzmann_constant",
    "c_light": "speed_of_light_in_vacuum",
}


def _records_by_name(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    found: dict[str, float] = {}
    for key in ("records", "material_records"):
        for row in document.get(key) or []:
            name = row.get("name")
            measured = row.get("measured")
            if name and isinstance(measured, (int, float)):
                found[str(name)] = float(measured)
    return found


def _higgs_gev() -> float | None:
    points = Path(__file__).resolve().parents[1] / "corpus" / "formula_points.jsonl"
    if not points.exists():
        return None
    for line in points.read_text(encoding="utf-8").splitlines():
        if '"m_H"' not in line:
            continue
        row = json.loads(line)
        if row.get("name") == "m_H" and row.get("property") == "m_H":
            measured = row.get("measured")
            if isinstance(measured, (int, float)):
                return float(measured)
    return None


def _cesium_hz(hub: Path) -> float | None:
    path = hub / "data" / "atomic_physics_gap_fill_benchmark.json"
    if not path.exists():
        return None
    document = json.loads(path.read_text(encoding="utf-8"))
    for key in ("records", "material_records"):
        for row in document.get(key) or []:
            if row.get("property") == "hyperfine transition frequency of Cs-133":
                measured = row.get("measured")
                if isinstance(measured, (int, float)):
                    return float(measured)
    return None


@lru_cache(maxsize=1)
def environment() -> dict[str, float]:
    compute, _parser = _load_hub()
    pairs = {
        "pi": compute.PI,
        "e": compute.E,
        "phi": compute.PHI,
        "gamma": compute.GAMMA,
        "g_cat": compute.G_CAT,
        "g_catalan": compute.G_CAT,
        "catalan": compute.G_CAT,
        "catalan_g": compute.G_CAT,
        "alpha": compute.ALPHA,
        "psi_con": compute.PSI_CON,
        "psicon": compute.PSI_CON,
        "eta_eff": compute.ETA_EFF,
        "eta": compute.ETA_EFF,
        "beta": compute.BETA,
        "gamma_c": compute.GAMMA_C,
        "omega": compute.OMEGA,
        "theta_s": compute.THETA_S,
        "theta": compute.THETA_S,
        "thetas": compute.THETA_S,
        "poof": compute.POOF,
        "c_eff": compute.C_EFF,
        "ceff": compute.C_EFF,
        "a_bleed": compute.A_BLEED,
        "ableed": compute.A_BLEED,
        "p_var": compute.P_VAR,
        "b_in": compute.B_IN,
        "a_in": compute.A_IN,
        "ain": compute.A_IN,
        "suction": compute.SUCTION,
        "chaos": compute.CHAOS,
        "p_base": compute.P_BASE,
        "pbase": compute.P_BASE,
        "p_new": compute.P_NEW,
        "pnew": compute.P_NEW,
        "c_factor": compute.C_FACTOR,
        "k": compute.K,
        "c_cosm": compute.C_COSM,
        "ln2": math.log(2.0),
        "log2": math.log(2.0),
        "sqrt2": math.sqrt(2.0),
    }
    published = _records_by_name(Path(HUB) / "data" / "codata_full_table_open_benchmark.json")
    for alias, source in _CODATA_ALIAS.items():
        if alias not in pairs and source in published:
            pairs[alias] = published[source]
    if "h" in pairs and "pi" in pairs:
        hbar = float(pairs["h"]) / (2.0 * float(pairs["pi"]))
        for alias in ("hbar", "h_bar"):
            if alias not in pairs:
                pairs[alias] = hbar
    cesium = _cesium_hz(Path(HUB))
    if cesium is not None:
        pairs.setdefault("nu_cs", cesium)
    higgs = _higgs_gev()
    if higgs is not None:
        pairs.setdefault("m_h", higgs)
    return {name: float(value) for name, value in pairs.items()}


def prepare_formula(formula: str) -> str:
    """Turn unicode superscripts into caret powers before the hub parser."""
    chars: list[str] = []
    pending_power = False
    for char in formula:
        mapped = char.translate(_SUPERSCRIPTS)
        if mapped != char and mapped.isdigit():
            if not pending_power:
                chars.append("^")
                pending_power = True
            chars.append(mapped)
            continue
        pending_power = False
        chars.append(char)
    return "".join(chars)


def evaluate(formula: str) -> float:
    _compute, parser = _load_hub()
    return float(parser.evaluate_formula(prepare_formula(formula), environment()))


def allowed_names() -> list[str]:
    return sorted(environment())


_DECIMAL = re.compile(r"\d+\.\d+|\d+[eE][+-]?\d+")
_MIDPOINT = re.compile(r"\([^()]{0,120}\+[^()]{0,120}\)/2(?!\d)")
# Characters the hub tokenizer keeps or rewrites. A bar or a colon is dropped
# before evaluation, so a proposal that contains one is not the value scored.
_ALLOWED = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
    "+-*/^()., \t\n"
    "φπγαβωψθηΦΠΓΨΘΗΩ"
    "·•×−–—⁄"
    "⁰¹²³⁴⁵⁶⁷⁸⁹"
)


def gate(formula: str) -> dict:
    """Reject forms the dial rules already forbid. A pass is not a promotion."""
    text = (formula or "").strip()
    reasons: list[str] = []
    if not text:
        return {"ok": False, "reasons": ["empty"], "value": None}
    if _DECIMAL.search(text):
        reasons.append("decimal_literal")
    stray = "".join(sorted({char for char in text if char not in _ALLOWED}))
    if stray:
        reasons.append(f"stray_character {stray!r}")
    compact = re.sub(r"\s+", "", text)
    if _MIDPOINT.search(compact):
        reasons.append("unweighted_midpoint")
    value = None
    if "decimal_literal" not in reasons and not stray:
        try:
            value = evaluate(text)
        except KeyError as exc:
            reasons.append(f"unknown_name:{exc}")
        except Exception as exc:  # parser and arithmetic failures stay on the row
            reasons.append(f"eval:{type(exc).__name__}:{exc}")
    return {"ok": not reasons, "reasons": reasons, "value": value}

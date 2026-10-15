"""Run one dial attempt.

Replay checks the recorded expression. A hand-passed proposal is evaluated
the same way. The model is optional and is not Ollama. Nothing here writes
the Lean hub or the pin.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dial.bars import resolve_bar
from dial.catalog import lookup, neighbors
from dial.engine import allowed_names, environment, gate
from dial.ledger import log_attempt
from dial.prompt import proposal_prompt
from dial.score import kill_metric, score_row


def lean_status(proposal: str, enabled: bool) -> dict:
    stripped = proposal.strip()
    if not enabled:
        return {"status": "skipped", "accepted": False}
    if not stripped.startswith(("theorem ", "lemma ", "def ")):
        return {"status": "not_lean", "accepted": False}
    from lean_check import check

    code = check(stripped, timeout=180)
    return {"status": "checked", "accepted": code == 0, "exit": code}


def attempt(name: str, proposal: str, source: str, use_lean: bool, property_name: str | None = None) -> dict:
    row = lookup(name, property_name)
    if row is None:
        raise SystemExit(f"No recorded row named {name}")
    decision = gate(proposal)
    bar = resolve_bar(row)
    scored = None
    if decision["value"] is not None and row.get("measured") is not None:
        scored = score_row(
            float(decision["value"]),
            float(row["measured"]),
            bar.get("pct"),
        )
    formal = lean_status(proposal, use_lean and decision["ok"])
    verdict = kill_metric(scored)
    record = {
        "source": source,
        "name": row.get("name"),
        "property": row.get("property"),
        "domain": row.get("domain"),
        "source_file": row.get("source_file"),
        "proposal": proposal,
        "recorded_formula": row.get("formula"),
        "recorded_computed": row.get("computed"),
        "measured": row.get("measured"),
        "gate_ok": decision["ok"],
        "gate_reasons": decision["reasons"],
        "engine_value": decision["value"],
        "published_bar": bar,
        "score": scored,
        "kill": verdict,
        "lean": formal,
        "neighbors": neighbors(row),
        "promoted": False,
        "send": False,
    }
    log_attempt(record)
    return record


def self_test() -> None:
    env = environment()
    k = env["k"]
    if abs(k - 0.4201087636498879) > 1e-12:
        raise SystemExit(f"live K drifted: {k}")
    formula = "e^3*phi^4 - psi_con - (POOF*SUCTION)^2*(C_factor^2/P_base)"
    record = attempt("inverse_fine-structure_constant", formula, "self-test", False)
    value = record["engine_value"]
    if value is None or abs(value - 137.03599916594285) > 1e-6:
        raise SystemExit(f"engine value {value}")
    if not record["score"]["inside_bar"]:
        raise SystemExit(f"recorded row fell outside its own bar: {record['score']}")
    if record["kill"]["killed"] or record["kill"]["reason"] != "inside_published_uncertainty":
        raise SystemExit(f"inside-bar row was killed: {record['kill']}")
    if record["send"] or record["promoted"]:
        raise SystemExit("self-test tried to send or promote")
    outside = kill_metric(score_row(1.0, 137.035999177, record["score"]["error_pct"] / record["score"]["z"]))
    if not outside["killed"] or outside["reason"] != "outside_published_uncertainty" or outside["send"]:
        raise SystemExit(f"outside-bar proposal was not killed: {outside}")
    missing = kill_metric(score_row(1.0, 1.0, None))
    if not missing["killed"] or missing["reason"] != "no_published_uncertainty":
        raise SystemExit(f"missing bar was not killed: {missing}")
    blocked = gate("phi*1.25")
    if blocked["ok"] or "decimal_literal" not in blocked["reasons"]:
        raise SystemExit(f"decimal gate failed: {blocked}")
    unknown = gate("phi*not_a_seed")
    if unknown["ok"] or not any(reason.startswith("unknown_name") for reason in unknown["reasons"]):
        raise SystemExit(f"unknown-name gate failed: {unknown}")
    print(
        json.dumps(
            {
                "k": k,
                "engine_value": value,
                "z": record["score"]["z"],
                "inside_bar": record["score"]["inside_bar"],
                "names": len(allowed_names()),
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--name")
    parser.add_argument("--property")
    parser.add_argument("--proposal")
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--lean", action="store_true")
    parser.add_argument(
        "--model",
        action="store_true",
        help="Ask the local Hugging Face Gemma weights for one proposal. Does not use Ollama.",
    )
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if not args.name:
        parser.error("Pass --name or --self-test")
    row = lookup(args.name, args.property)
    if row is None:
        raise SystemExit(f"No recorded row named {args.name}")
    if args.model:
        from dial.local_model import propose

        proposal = propose(proposal_prompt(row))
        source = "local-hf"
    elif args.replay:
        proposal = str(row["formula"])
        source = "replay"
    elif args.proposal:
        proposal = args.proposal
        source = "cli"
    else:
        parser.error("Pass --replay or --proposal")
        return
    print(json.dumps(attempt(args.name, proposal, source, args.lean, args.property), indent=2))


if __name__ == "__main__":
    main()

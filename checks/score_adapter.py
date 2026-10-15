"""Score one adapter on rows that have a published bar.

The loss is not rerun. The engine computes the proposal. The kill uses the
published percent. A theory match is the recorded formula. Nothing is sent.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForMultimodalLM, AutoTokenizer, BitsAndBytesConfig

ROOT = Path(r"C:\Users\damia\Desktop\math si")
sys.path.insert(0, str(ROOT))

from dial.bars import resolve_bar
from dial.catalog import neighbors, rows
from dial.engine import gate, prepare_formula
from dial.ledger import log_attempt
from dial.prompt import proposal_prompt
from dial.score import kill_metric, score_row

MODEL_DIR = Path(r"D:\models\gemma-4-E4B-it")
DEFAULT_OUT = ROOT / "logs" / "epoch2_score.jsonl"


def norm(text: str) -> str:
    return re.sub(r"\s+", "", prepare_formula(text or "")).casefold()


def published_rows() -> list[dict]:
    chosen: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows():
        bar = resolve_bar(row)
        if bar["status"] != "published":
            continue
        key = (str(row.get("name")), str(row.get("property")), str(row.get("formula")))
        if key in seen:
            continue
        seen.add(key)
        chosen.append(row)
    return chosen


def load(adapter: Path):
    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForMultimodalLM.from_pretrained(
        MODEL_DIR,
        quantization_config=quant,
        device_map="auto",
        dtype=torch.bfloat16,
    )
    model = PeftModel.from_pretrained(model, adapter)
    model.eval()
    return tokenizer, model


def generate(tokenizer, model, prompt: str) -> str:
    messages = [{"role": "user", "content": prompt}]
    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
        add_generation_prompt=True,
        enable_thinking=False,
    ).to(model.device)
    output = model.generate(**inputs, max_new_tokens=128, do_sample=False)
    text = tokenizer.decode(output[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True)
    for line in text.splitlines():
        if line.strip().upper().startswith("PROPOSAL:"):
            return line.split(":", 1)[1].strip()
    return text.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--source", default="epoch2-score")
    args = parser.parse_args()
    chosen = published_rows()
    if args.limit:
        chosen = chosen[: args.limit]
    print(f"ROWS {len(chosen)}", flush=True)
    tokenizer, model = load(args.adapter)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    hits = 0
    with args.out.open("w", encoding="utf-8") as handle:
        for index, row in enumerate(chosen, start=1):
            proposal = generate(tokenizer, model, proposal_prompt(row))
            decision = gate(proposal)
            bar = resolve_bar(row)
            scored = None
            measured = row.get("measured")
            if decision["value"] is not None and measured is not None:
                scored = score_row(float(decision["value"]), float(measured), bar.get("pct"))
            verdict = kill_metric(scored)
            theory = norm(proposal) == norm(str(row.get("formula") or ""))
            if theory or (scored and scored.get("inside_bar")):
                hits += 1
            record = {
                "source": args.source,
                "adapter": str(args.adapter),
                "name": row.get("name"),
                "property": row.get("property"),
                "domain": row.get("domain"),
                "proposal": proposal,
                "recorded_formula": row.get("formula"),
                "theory_match": theory,
                "measured": measured,
                "gate_ok": decision["ok"],
                "gate_reasons": decision["reasons"],
                "engine_value": decision["value"],
                "published_bar": {"pct": bar.get("pct"), "source": bar.get("source"), "status": bar.get("status")},
                "score": scored,
                "kill": verdict,
                "neighbors": neighbors(row),
                "promoted": False,
                "send": False,
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            log_attempt(record)
            z = None if not scored else scored.get("z")
            print(
                f"{index}/{len(chosen)} theory={theory} z={z} kill={verdict['reason']} {row.get('name')} {row.get('property')}",
                flush=True,
            )
    print(json.dumps({"rows": len(chosen), "hits": hits, "send": False}))


if __name__ == "__main__":
    main()

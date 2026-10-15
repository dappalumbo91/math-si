"""LoRA-tune Gemma 4 E4B on recorded FSOT chat turns.

The base weights are google/gemma-4-E4B-it. Ollama's GGUF cannot be
the training base. This script loads the Hugging Face weights in 4-bit
and trains a small adapter on corpus/combined.jsonl.

Each row is a user turn plus an assistant turn. Thinking stays off.
The assistant target is a recorded formula or a PROPOSAL line, not a
number fitted to a measurement. A generated line is not a result until
the engine scores it and, for a formal statement, Lean accepts it.

Example smoke, after the weights are on disk:

    python train_lora.py --max-steps 20
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

from dial.kv_share import enable_kv_share

CORPUS = Path(r"C:\Users\damia\Desktop\math si\corpus\combined.jsonl")
MODEL_DIR = Path(r"D:\models\gemma-4-E4B-it")
OUTPUT_DIR = Path(r"C:\Users\damia\Desktop\math si\adapter")
TEXT_TARGETS = ("q_proj", "k_proj", "v_proj", "o_proj")


def text_modules(model) -> list[str]:
    names: list[str] = []
    for name, module in model.named_modules():
        if "language_model" not in name:
            continue
        if name.endswith(TEXT_TARGETS) and hasattr(module, "weight"):
            names.append(name)
    if not names:
        raise SystemExit("No language-model attention modules found to adapt.")
    return names


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--logging-steps", type=int, default=5)
    parser.add_argument("--save-steps", type=int, default=200)
    parser.add_argument("--resume-adapter", type=Path)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    output_dir = args.output_dir
    if args.resume_adapter and args.resume_adapter.resolve() == output_dir.resolve():
        raise SystemExit("Refusing to resume into the same adapter directory.")
    corpus = args.corpus
    if not corpus.exists():
        raise SystemExit(f"Missing {corpus}. Run export_corpus.py and build_tool_rows.py first.")
    with corpus.open(encoding="utf-8") as handle:
        sample = json.loads(handle.readline())
    if "prompt" not in sample or "completion" not in sample:
        raise SystemExit("Corpus rows must be chat prompt/completion pairs. Run build_tool_rows.py.")
    if not (MODEL_DIR / "config.json").exists():
        raise SystemExit(
            "Gemma 4 E4B weights are not in D:\\models\\gemma-4-E4B-it yet. "
            "The Ollama copy is a GGUF and cannot take this adapter."
        )

    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForImageTextToText.from_pretrained(
        MODEL_DIR,
        quantization_config=quant,
        device_map="auto",
        dtype=torch.bfloat16,
    )
    model = prepare_model_for_kbit_training(model)
    if args.resume_adapter:
        if not (args.resume_adapter / "adapter_config.json").exists():
            raise SystemExit(f"No adapter at {args.resume_adapter}")
        model = PeftModel.from_pretrained(model, args.resume_adapter, is_trainable=True)
        print(f"RESUME {args.resume_adapter}")
    else:
        targets = text_modules(model)
        model = get_peft_model(
            model,
            LoraConfig(
                r=16,
                lora_alpha=32,
                lora_dropout=0.05,
                bias="none",
                task_type="CAUSAL_LM",
                target_modules=targets,
            ),
        )
    enable_kv_share(model)
    model.print_trainable_parameters()
    print(f"OUTPUT {output_dir}")

    dataset = load_dataset("json", data_files=str(corpus), split="train")
    trainer = SFTTrainer(
        model=model,
        args=SFTConfig(
            output_dir=str(output_dir),
            max_steps=args.max_steps,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=8,
            learning_rate=args.learning_rate,
            logging_steps=args.logging_steps,
            save_steps=args.save_steps,
            save_total_limit=2,
            bf16=True,
            gradient_checkpointing=True,
            max_length=768,
            dataset_text_field="text",
            report_to="none",
            packing=False,
        ),
        train_dataset=dataset,
        processing_class=tokenizer,
    )
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(output_dir)
    print(f"ADAPTER {output_dir}")


if __name__ == "__main__":
    main()

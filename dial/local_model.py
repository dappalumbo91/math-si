"""One proposal from the local Gemma 4 weights.

Uses the Hugging Face checkpoint on disk. Ollama is not involved.
An adapter directory is loaded when it exists.
The prompt is the user turn. Thinking stays off.
"""

from __future__ import annotations

from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForMultimodalLM, AutoTokenizer, BitsAndBytesConfig

MODEL_DIR = Path(r"D:\models\gemma-4-E4B-it")
ADAPTER_DIR = Path(r"C:\Users\damia\Desktop\math si\adapter")


def propose(prompt: str, max_new_tokens: int = 128) -> str:
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
    adapter_config = ADAPTER_DIR / "adapter_config.json"
    if adapter_config.exists():
        model = PeftModel.from_pretrained(model, ADAPTER_DIR)
    messages = [{"role": "user", "content": prompt}]
    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
        add_generation_prompt=True,
        enable_thinking=False,
    ).to(model.device)
    output = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
    )
    text = tokenizer.decode(output[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True)
    for line in text.splitlines():
        if line.strip().upper().startswith("PROPOSAL:"):
            return line.split(":", 1)[1].strip()
    return text.strip()

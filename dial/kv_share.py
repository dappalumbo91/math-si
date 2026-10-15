"""Keep Gemma 4 E4B key-value sharing on during training.

Later E4B layers reuse an earlier layer's keys and values. The stock
forward only sets up that reuse when a generation cache exists. Training
calls the model with use_cache false, and gradient checkpointing then
drops any cache that is passed in, so those layers invent their own keys.
The share buffer lives on the attention modules instead of in that cache.
Generation still uses the real cache.
"""

from __future__ import annotations

from transformers.models.gemma4.modeling_gemma4 import Gemma4TextAttention


class ShareCache:
    def __init__(self) -> None:
        self.shared_layers: dict = {}

    def update(self, key_states, value_states, layer_idx: int, *args, **kwargs):
        return key_states, value_states


_ATTENTION_PATCHED = False


def _patch_attention() -> None:
    global _ATTENTION_PATCHED
    if _ATTENTION_PATCHED:
        return
    original = Gemma4TextAttention.forward

    def forward(self, *args, **kwargs):
        share = getattr(self, "_fsot_share", None)
        if kwargs.get("past_key_values") is None and share is not None:
            kwargs["past_key_values"] = share
        return original(self, *args, **kwargs)

    Gemma4TextAttention.forward = forward
    _ATTENTION_PATCHED = True


def enable_kv_share(model) -> None:
    language = None
    for module in model.modules():
        if module.__class__.__name__ == "Gemma4TextModel":
            language = module
            break
    if language is None:
        raise RuntimeError("Gemma4TextModel was not found. KV sharing was not enabled.")
    _patch_attention()
    if getattr(language, "_fsot_kv_share", False):
        return
    original = language.forward

    def forward(*args, **kwargs):
        # A new buffer each call. It stays on the modules through backward,
        # because checkpointing recomputes the layers after this returns.
        # Training turns the generation cache off. Checkpointing can also flip
        # use_cache after this wrapper, so key off training mode instead.
        if language.training and kwargs.get("past_key_values") is None:
            share = ShareCache()
            for layer in language.layers:
                layer.self_attn._fsot_share = share
        return original(*args, **kwargs)

    language.forward = forward
    language._fsot_kv_share = True

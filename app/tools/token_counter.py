"""Token counting utilities for tool-surface measurement.

Supports:
- tiktoken (cl100k_base for Claude Sonnet compat; o200k_base for GPT-4o)
- Anthropic messages/count_tokens API (exact for Claude, if ANTHROPIC_API_KEY set)
- Character-based approximation as fallback when tiktoken unavailable
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any


# Empirical ratios for approximation fallback (when tiktoken is unavailable).
# Measured on Russian sample strings against cl100k_base: ~2.3 chars/token.
# English text averages ~4 chars/token.
APPROX_RU_RATIO = 2.3
APPROX_EN_RATIO = 4.0

# `tiktoken` lazily downloads BPE files on first use. In local/offline
# smoke runs we prefer an explicit cache location; if the files are absent
# and network is unavailable, counting falls back to approx-ru below.
DEFAULT_TIKTOKEN_CACHE_DIR = "/tmp/tiktoken-cache"
os.environ.setdefault("TIKTOKEN_CACHE_DIR", DEFAULT_TIKTOKEN_CACHE_DIR)


@lru_cache(maxsize=4)
def _get_tiktoken_encoding(name: str):
    """Lazy import tiktoken — optional dep. Returns None on failure."""
    try:
        import tiktoken
        return tiktoken.get_encoding(name)
    except Exception:
        return None


def count_tokens(text: str, *, tokenizer: str = "cl100k_base") -> int:
    """Count tokens in text using specified tokenizer.

    tokenizer:
      - 'cl100k_base' (default): GPT-3.5/4, approx. for Anthropic Sonnet
      - 'o200k_base': GPT-4o (better multilingual)
      - 'approx-ru': chars / APPROX_RU_RATIO (fallback, Russian)
      - 'approx-en': chars / APPROX_EN_RATIO (fallback, English)
    """
    if not text:
        return 0
    if tokenizer.startswith("approx"):
        ratio = APPROX_RU_RATIO if tokenizer == "approx-ru" else APPROX_EN_RATIO
        return max(1, int(len(text) / ratio))
    enc = _get_tiktoken_encoding(tokenizer)
    if enc is None:
        return count_tokens(text, tokenizer="approx-ru")
    return len(enc.encode(text))


def tokenizer_backend(tokenizer: str) -> str:
    """Return the concrete backend used for `tokenizer`.

    This prevents reports from silently labelling an approximate fallback as
    `cl100k_base`/`o200k_base` when tiktoken data is unavailable.
    """
    if tokenizer.startswith("approx"):
        return tokenizer
    enc = _get_tiktoken_encoding(tokenizer)
    if enc is None:
        return "approx-ru-fallback"
    return f"tiktoken:{tokenizer}"


def count_tokens_json(
    obj: Any,
    *,
    tokenizer: str = "cl100k_base",
    compact: bool = False,
) -> int:
    """Serialize obj to JSON and count tokens.

    compact=False (default): indent=2 — matches how MCP clients usually
    present tool schemas to the model, yielding realistic counts.
    compact=True: separators-minified — minimum possible size.
    """
    if obj is None:
        return 0
    if compact:
        txt = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    else:
        txt = json.dumps(obj, ensure_ascii=False, indent=2)
    return count_tokens(txt, tokenizer=tokenizer)


def count_tokens_anthropic(
    text: str,
    *,
    api_key: str | None = None,
    model: str = "claude-sonnet-4-5",
) -> int | None:
    """Exact token count via Anthropic messages/count_tokens API.

    Returns None if ANTHROPIC_API_KEY is not available or request fails.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        resp = client.messages.count_tokens(
            model=model,
            messages=[{"role": "user", "content": text}],
        )
        return resp.input_tokens
    except Exception:
        return None


def compare_tokenizers(text: str) -> dict[str, int]:
    """Return token counts across all supported tokenizers for comparison."""
    return {
        "cl100k_base": count_tokens(text, tokenizer="cl100k_base"),
        "o200k_base": count_tokens(text, tokenizer="o200k_base"),
        "approx_ru": count_tokens(text, tokenizer="approx-ru"),
        "approx_en": count_tokens(text, tokenizer="approx-en"),
        "chars": len(text),
    }

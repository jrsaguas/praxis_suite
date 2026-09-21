"""Canonical Markdown contracts for mathematical document pipelines."""
from __future__ import annotations
import re
from typing import Iterable

def validate_canonical_markdown(text: str) -> dict:
    raw = str(text or "")
    equations = len(re.findall(r"\\$\\$[\\s\\S]*?\\$\\$", raw))
    inline = len(re.findall(r"(?<!\\$)\\$[^$\\n]+?\\$(?!\\$)", raw))
    return {"canonical": True, "math_block_count": equations, "inline_math_count": inline, "preserves_dollar_delimiters": equations > 0 or inline > 0, "has_raw_latex": bool(re.search(r"\\+(?:frac|sqrt|sum|int|partial|nabla|alpha|beta|gamma)", raw))}

def assemble_markdown(parts: Iterable[str]) -> str:
    cleaned = [str(x).strip() for x in parts if str(x).strip()]
    return "\n\n".join(cleaned).strip() + ("\n" if cleaned else "")
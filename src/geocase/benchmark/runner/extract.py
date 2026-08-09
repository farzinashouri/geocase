"""Tolerant code-block extraction from a model reply.

Accepts ```python / ```py / bare ``` fences and a missing closing fence; when
several blocks are present the last one wins (models often iterate in-reply).
An unparseable reply is the caller's cue to record MISSING."""

from __future__ import annotations

import re

_FENCE = re.compile(
    r"```[ \t]*(?:python|py)?[ \t]*\n(.*?)(?:\n```|\Z)",
    re.DOTALL | re.IGNORECASE,
)


def extract_code_block(text: str) -> str | None:
    blocks = [m.group(1).strip() for m in _FENCE.finditer(text)]
    blocks = [b for b in blocks if b]
    return blocks[-1] if blocks else None

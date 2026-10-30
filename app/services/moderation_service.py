"""Lightweight abuse / prompt-injection guard for user inputs. Pure stdlib.
This is a first line only; it never replaces SSRF/rate-limit controls."""
from __future__ import annotations

import re

_BLOCKED = re.compile(r"(?i)\b(ignore (all )?previous instructions|system prompt|"
                      r"reveal (your )?api key|bypass (rate|quota)|jailbreak)\b")


def moderate(text: str) -> tuple[bool, str]:
    if not text or len(text) > 10000:
        return False, "input too long or empty"
    if _BLOCKED.search(text):
        return False, "input looks like an instruction-injection attempt"
    return True, ""

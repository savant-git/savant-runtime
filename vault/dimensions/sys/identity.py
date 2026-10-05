#!/usr/bin/env python3

from __future__ import annotations

import hashlib


def identity(*parts: str) -> str:
    return hashlib.sha256(
        "\x1f".join(parts).encode("utf-8")
    ).hexdigest()

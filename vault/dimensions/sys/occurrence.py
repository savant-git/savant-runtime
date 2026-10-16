#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Occurrence:
    id: str
    class_key: str
    path: Path
    line: int
    column: int
    text: str
    digest: str
    authority: str
    reason: str
    mutable: bool
    confidence: float

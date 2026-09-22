#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass

from occurrence import Occurrence


@dataclass(frozen=True, slots=True)
class Classification:
    occurrence: Occurrence
    class_key: str
    confidence: float
    authority: str
    reason: str

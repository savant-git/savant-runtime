#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Verification:
    passed: bool
    failures: tuple[str, ...]
    warnings: tuple[str, ...]

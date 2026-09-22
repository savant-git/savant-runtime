#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Audit:
    id: str
    operation: str
    passed: bool
    digest: str

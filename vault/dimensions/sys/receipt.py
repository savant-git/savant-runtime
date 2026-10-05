#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Receipt:
    transformation_id: str
    operation: str
    timestamp: str
    passed: bool
    digest: str

#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Transformation:
    id: str
    source: str
    destination: str
    authority: str
    trigger: str
    planner: str
    verifier: str
    receipt: str
    rollback: str

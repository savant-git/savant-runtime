#!/usr/bin/env python3

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Decision:
    id: str
    authority: str
    outcome: str
    rationale: str

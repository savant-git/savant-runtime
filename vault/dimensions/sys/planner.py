#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass

from classification import Classification


@dataclass(frozen=True, slots=True)
class PlannedMutation:
    classification: Classification
    approved: bool
    reason: str

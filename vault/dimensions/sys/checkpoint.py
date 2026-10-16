#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Checkpoint:
    id: str
    digest: str
    timestamp: str

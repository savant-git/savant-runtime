#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Journal:
    id: str
    entries: tuple[str, ...]
    digest: str

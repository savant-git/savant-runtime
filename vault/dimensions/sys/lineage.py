#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Lineage:
    parent: str | None
    children: tuple[str, ...]
    origin: str

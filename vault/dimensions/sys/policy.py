#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Policy:
    key: str
    mutable: bool
    authoritative: bool
    digest_bound: bool
    requires_review: bool
    allow_projection: bool
    allow_history: bool
    allow_shadow: bool
    allow_transform: bool

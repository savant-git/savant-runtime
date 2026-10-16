#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Mutation:
    occurrence_id: str
    before: str
    after: str
    authority: str
    digest_before: str
    digest_after: str

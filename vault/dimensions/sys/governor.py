#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass

from authority import Authority


@dataclass(frozen=True, slots=True)
class Governor:
    authority: Authority
    allow_transform: bool
    allow_override: bool

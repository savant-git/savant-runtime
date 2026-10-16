#!/usr/bin/env python3

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Rationale:
    id: str
    statement: str
    authority: str

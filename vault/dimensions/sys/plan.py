#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass

from mutation import Mutation


@dataclass(frozen=True, slots=True)
class Plan:
    id: str
    mutations: tuple[Mutation, ...]
    authority: str
    approved: bool

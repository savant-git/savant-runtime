#!/usr/bin/env python3

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Event:
    id: str
    type: str
    timestamp: str
    object_id: str

#!/usr/bin/env python3
"""Accepted, non-authoritative composition projection for guise."""

from __future__ import annotations

import hashlib
import json
from types import MappingProxyType
from typing import Any


SCHEMA = "savant.guise.composition.v1"

OWNER = ("carbon", "oriel", "guise")

_STRUCTURE = (
    ("veil", ("nom", "mien", "aura")),
    ("creed", ("oath", "vow", "rift")),
    ("fervor", ("yen", "pang", "fret")),
    ("gait", ("lilt", "bent", "whim")),
    ("kith", ("ally", "thrum", "feud")),
    ("myth", ("yore", "scar", "vestige")),
    ("wry", ("quip", "slant", "barb")),
    ("eon", ("molt", "sway", "wake")),
    ("rune", ("clue", "seam", "rift")),
)

TRAITS = MappingProxyType(dict(_STRUCTURE))

MOTES = frozenset(
    mote
    for _, motes in _STRUCTURE
    for mote in motes
)


def canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical(value).encode("utf-8")
    ).hexdigest()


def trait_motes(trait: str) -> tuple[str, ...]:
    return TRAITS[trait]


def mote_traits(mote: str) -> tuple[str, ...]:
    if mote not in MOTES:
        raise KeyError(mote)

    return tuple(
        trait
        for trait, motes in _STRUCTURE
        if mote in motes
    )


def composition() -> dict[str, Any]:
    traits = []

    for trait, motes in _STRUCTURE:
        traits.append(
            {
                "identity": trait,
                "kind": "trait",
                "owner": list(OWNER),
                "motes": [
                    {
                        "identity": mote,
                        "kind": "mote",
                        "relation": "references",
                        "shared": (
                            len(mote_traits(mote)) > 1
                        ),
                    }
                    for mote in motes
                ],
            }
        )

    result = {
        "schema": SCHEMA,
        "owner": list(OWNER),
        "kind": "quirk",
        "traits": traits,
        "trait_count": len(_STRUCTURE),
        "mote_positions": sum(
            len(motes)
            for _, motes in _STRUCTURE
        ),
        "unique_motes": len(MOTES),
        "authoritative": False,
    }

    result["digest"] = digest(result)

    return result


def validate() -> bool:
    if len(_STRUCTURE) != 9:
        raise ValueError("expected nine traits")

    if len(TRAITS) != 9:
        raise ValueError("duplicate trait identity")

    if any(
        len(motes) != 3
        for _, motes in _STRUCTURE
    ):
        raise ValueError(
            "expected three mote positions per trait"
        )

    if len(MOTES) != 26:
        raise ValueError(
            "expected 26 unique mote identities"
        )

    if mote_traits("rift") != ("creed", "rune"):
        raise ValueError(
            "shared rift reference is inconsistent"
        )

    return True


validate()

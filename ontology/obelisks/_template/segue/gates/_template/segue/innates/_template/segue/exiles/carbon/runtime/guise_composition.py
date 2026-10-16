#!/usr/bin/env python3
"""Deterministic composition of the accepted guise hierarchy."""

from __future__ import annotations

import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping


class GuiseCompositionError(ValueError):
    """Invalid guise composition or reference."""


SCHEMA = "savant://carbon/oriel/guise/composition/1"

OWNER = "carbon"
PRODIGAL = "oriel"
QUIRK = "guise"

_TRAITS = (
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

TRAITS = MappingProxyType(
    {name: tuple(motes) for name, motes in _TRAITS}
)

MOTES = frozenset(
    mote
    for _, motes in _TRAITS
    for mote in motes
)


def canonical_json(value: Any) -> str:
    """Serialize a projection deterministically."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def digest(value: Any) -> str:
    """Return the stable content digest of a projection."""
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def _name(value: str) -> str:
    if not isinstance(value, str):
        raise GuiseCompositionError(
            "identity must be a string"
        )

    if not value or value != value.strip():
        raise GuiseCompositionError(
            "identity must be nonempty and normalized"
        )

    return value


def trait_motes(trait: str) -> tuple[str, ...]:
    """Return mote references belonging to one trait."""
    name = _name(trait)

    try:
        return TRAITS[name]
    except KeyError as exc:
        raise GuiseCompositionError(
            f"unknown guise trait: {name}"
        ) from exc


def mote_traits(mote: str) -> tuple[str, ...]:
    """Return all traits referencing a mote."""
    name = _name(mote)

    if name not in MOTES:
        raise GuiseCompositionError(
            f"unknown guise mote: {name}"
        )

    return tuple(
        trait
        for trait, motes in _TRAITS
        if name in motes
    )


def composition() -> dict[str, Any]:
    """Project the accepted composition without storing copies."""
    traits = [
        {
            "identity": trait,
            "motes": list(motes),
        }
        for trait, motes in _TRAITS
    ]

    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "prodigal": PRODIGAL,
        "quirk": QUIRK,
        "traits": traits,
        "mote_identities": sorted(MOTES),
        "trait_count": len(_TRAITS),
        "mote_positions": sum(
            len(motes) for _, motes in _TRAITS
        ),
        "unique_motes": len(MOTES),
    }


def references() -> list[dict[str, str]]:
    """Project stable, typed composition references."""
    return [
        {
            "source": f"{OWNER}/{PRODIGAL}/{QUIRK}",
            "target": (
                f"{OWNER}/{PRODIGAL}/{QUIRK}/{trait}"
            ),
            "relation": "composes",
        }
        for trait, _ in _TRAITS
    ] + [
        {
            "source": (
                f"{OWNER}/{PRODIGAL}/{QUIRK}/{trait}"
            ),
            "target": f"mote/{mote}",
            "relation": "references",
        }
        for trait, motes in _TRAITS
        for mote in motes
    ]


def fingerprint() -> str:
    """Identify this exact accepted composition."""
    return digest(composition())


def validate() -> bool:
    """Check structural invariants without modifying state."""
    if len(_TRAITS) != 9:
        raise GuiseCompositionError(
            "guise requires nine traits"
        )

    if len(TRAITS) != len(_TRAITS):
        raise GuiseCompositionError(
            "duplicate trait identity"
        )

    if any(len(motes) != 3 for _, motes in _TRAITS):
        raise GuiseCompositionError(
            "each trait requires three mote references"
        )

    if any(
        len(set(motes)) != len(motes)
        for _, motes in _TRAITS
    ):
        raise GuiseCompositionError(
            "duplicate mote within a trait"
        )

    if len(MOTES) != 26:
        raise GuiseCompositionError(
            "unexpected unique mote count"
        )

    if mote_traits("rift") != ("creed", "rune"):
        raise GuiseCompositionError(
            "shared rift identity was altered"
        )

    return True


validate()

#!/usr/bin/env python3

from __future__ import annotations

"""
Canonical Riot lexical Linka over the historical ENTITY_* service family.

Authority:
    entity -> riot
    adapter -> linka
    graph -> gridd
    projection -> wavre
    validator -> cert

This file does not duplicate the historical implementation. It composes the
existing service family behind current canonical Savant terminology so new
callers no longer need to write superseded vocabulary.

Historical ENTITY_* modules remain compatibility surfaces until their
dependents have migrated.
"""

from pathlib import Path
from typing import Any

from ENTITY_DISCOVERY import discover_entities
from ENTITY_FACTORY import create_entity
from ENTITY_GRAPH import build_entity_graph
from ENTITY_MODEL import Entity, entity_to_dict, read_entity
from ENTITY_VALIDATOR import validate_entities


# Canonical type surface.
Riot = Entity


def read_riot(
    path: Path,
) -> Riot | None:
    return read_entity(
        path
    )


def riot_to_dict(
    riot: Riot,
) -> dict[str, Any]:
    return entity_to_dict(
        riot
    )


def discover_riots(
    root: Path | None = None,
) -> list[Riot]:
    if root is None:
        return list(
            discover_entities()
        )

    return list(
        discover_entities(
            root
        )
    )


def create_riot(
    path: Path,
    *,
    riot_id: str,
    riot_type: str,
    purpose: str = "",
    status: str = "planned",
) -> None:
    create_entity(
        path,
        entity_id=riot_id,
        entity_type=riot_type,
        purpose=purpose,
        status=status,
    )


def build_riot_gridd() -> dict[str, Any]:
    return build_entity_graph()


def cert_riots() -> dict[str, Any]:
    return validate_entities()


def wavre_riot_docs() -> list[dict[str, Any]]:
    return [
        {
            "id": riot.id,
            "type": riot.type,
            "status": riot.status,
            "path": riot.path,
            "purpose": riot.data.get(
                "purpose",
                "",
            ),
            "rule": riot.data.get(
                "rule",
                "",
            ),
        }
        for riot in discover_riots()
    ]


def wavre_riot_paths() -> dict[str, str]:
    return {
        riot.id: riot.path
        for riot in discover_riots()
    }


__all__ = [
    "Riot",
    "build_riot_gridd",
    "cert_riots",
    "create_riot",
    "discover_riots",
    "read_riot",
    "riot_to_dict",
    "wavre_riot_docs",
    "wavre_riot_paths",
]

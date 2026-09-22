#!/usr/bin/env python3

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml


LEXICON_ROOT = Path("/root/savant-runtime/lexicon")
REGISTRY_PATH = LEXICON_ROOT / "registry.yaml"

KINDRED_ID = "lex:service:kindred"
KINDRED_ID = "lex:core:kindred"
MODUS_LEXEME_ID = "lex:exile:modus"

EXTERNAL_MODUS_ID = "exile:modus"


def timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .strftime("%Y%m%dT%H%M%SZ")
    )


def load_registry() -> dict[str, Any]:
    payload = yaml.safe_load(
        REGISTRY_PATH.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(payload, dict):
        raise TypeError(
            "registry must be an object"
        )

    if not isinstance(
        payload.get("lexemes"),
        list,
    ):
        raise TypeError(
            "registry.lexemes must be a list"
        )

    return payload


def write_registry(
    registry: Mapping[str, Any],
) -> None:
    REGISTRY_PATH.write_text(
        yaml.safe_dump(
            dict(registry),
            sort_keys=False,
            allow_unicode=True,
            width=100,
        ),
        encoding="utf-8",
    )


def ensure_modus_lexeme(
    registry: dict[str, Any],
) -> dict[str, Any]:
    lexemes = registry["lexemes"]

    matches = [
        lexeme
        for lexeme in lexemes
        if isinstance(lexeme, dict)
        and (
            lexeme.get("id")
            == MODUS_LEXEME_ID
            or (
                str(
                    lexeme.get(
                        "canonical",
                        "",
                    )
                ).casefold()
                == "modus"
                and lexeme.get(
                    "status"
                )
                == "active"
            )
        )
    ]

    if len(matches) > 1:
        raise RuntimeError(
            "Multiple active Modus lexemes exist"
        )

    if matches:
        modus = matches[0]

    else:
        modus = {
            "id": MODUS_LEXEME_ID,
            "canonical": "Modus",
            "concept": (
                "Canonical Exile for modularity, "
                "composition modes, and module boundaries"
            ),
            "description": (
                "Lexical identity for the accepted Modus Exile. "
                "The constitutional graph identity remains exile:modus."
            ),
            "layer": "shard00",
            "status": "active",
            "lineage": {
                "supersedes": [],
                "superseded_by": None,
                "history": [],
            },
            "provenance": {
                "sources": [
                    "accepted-graph:exile:modus",
                    "canon-system/authority/exiles/modus.yaml",
                ],
                "authority": "accepted",
                "confidence": "confirmed",
            },
            "metadata": {
                "external_identity": EXTERNAL_MODUS_ID,
                "kind": "exile",
                "canonical_status": "accepted",
            },
        }

        lexemes.append(modus)

    modus["id"] = MODUS_LEXEME_ID
    modus["canonical"] = "Modus"
    modus["status"] = "active"

    metadata = modus.get("metadata")

    if not isinstance(metadata, dict):
        metadata = {}

    metadata.update(
        {
            "external_identity": EXTERNAL_MODUS_ID,
            "kind": "exile",
            "canonical_status": "accepted",
        }
    )

    modus["metadata"] = metadata

    return modus


def repair_kindred(
    registry: dict[str, Any],
) -> None:
    lexemes = registry["lexemes"]

    kindred_matches = [
        lexeme
        for lexeme in lexemes
        if isinstance(lexeme, dict)
        and lexeme.get("id")
        == KINDRED_ID
    ]

    if len(kindred_matches) != 1:
        raise RuntimeError(
            "Expected exactly one Kindred lexeme"
        )

    kindred = kindred_matches[0]

    relationships = kindred.get(
        "relationships"
    )

    if not isinstance(
        relationships,
        list,
    ):
        relationships = []

    repaired: list[dict[str, Any]] = []

    seen: set[
        tuple[str, str]
    ] = set()

    for relationship in relationships:
        if not isinstance(
            relationship,
            Mapping,
        ):
            continue

        relation_type = str(
            relationship.get(
                "type",
                "",
            )
        )

        target = str(
            relationship.get(
                "target",
                "",
            )
        )

        if (
            relation_type
            == "implemented_through"
            and target
            == EXTERNAL_MODUS_ID
        ):
            target = MODUS_LEXEME_ID

        key = (
            relation_type,
            target,
        )

        if key in seen:
            continue

        seen.add(key)

        repaired.append(
            {
                "type": relation_type,
                "target": target,
            }
        )

    required = [
        (
            "depends_on",
            KINDRED_ID,
        ),
        (
            "implemented_through",
            MODUS_LEXEME_ID,
        ),
    ]

    for relation_type, target in required:
        key = (
            relation_type,
            target,
        )

        if key not in seen:
            repaired.append(
                {
                    "type": relation_type,
                    "target": target,
                }
            )

            seen.add(key)

    kindred[
        "relationships"
    ] = repaired

    dependencies = kindred.get(
        "dependencies"
    )

    if not isinstance(
        dependencies,
        list,
    ):
        dependencies = []

    normalized_dependencies: list[str] = []

    for dependency in dependencies:
        value = str(
            dependency
        )

        if value == EXTERNAL_MODUS_ID:
            value = MODUS_LEXEME_ID

        if value not in normalized_dependencies:
            normalized_dependencies.append(
                value
            )

    for required_dependency in (
        KINDRED_ID,
        MODUS_LEXEME_ID,
    ):
        if (
            required_dependency
            not in normalized_dependencies
        ):
            normalized_dependencies.append(
                required_dependency
            )

    kindred[
        "dependencies"
    ] = normalized_dependencies

    metadata = kindred.get(
        "metadata"
    )

    if not isinstance(metadata, dict):
        metadata = {}

    metadata.update(
        {
            "external_service_identity": "service:kindred",
            "external_kindred_identity": "system:kindred",
            "external_modus_identity": EXTERNAL_MODUS_ID,
            "lexicon_kindred_identity": KINDRED_ID,
            "lexicon_modus_identity": MODUS_LEXEME_ID,
            "implementation_ref": "runtime/kindred",
        }
    )

    kindred["metadata"] = metadata


def validate(
    registry: Mapping[str, Any],
) -> None:
    lexemes = registry[
        "lexemes"
    ]

    by_id = {
        str(
            lexeme["id"]
        ): lexeme
        for lexeme in lexemes
        if isinstance(
            lexeme,
            Mapping,
        )
        and lexeme.get(
            "id"
        )
    }

    if MODUS_LEXEME_ID not in by_id:
        raise RuntimeError(
            "Modus lexeme missing"
        )

    kindred = by_id.get(
        KINDRED_ID
    )

    if kindred is None:
        raise RuntimeError(
            "Kindred lexeme missing"
        )

    relationships = kindred.get(
        "relationships",
        [],
    )

    if not isinstance(
        relationships,
        list,
    ):
        raise RuntimeError(
            "Kindred relationships invalid"
        )

    targets = {
        (
            str(
                relationship.get(
                    "type",
                    "",
                )
            ),
            str(
                relationship.get(
                    "target",
                    "",
                )
            ),
        )
        for relationship
        in relationships
        if isinstance(
            relationship,
            Mapping,
        )
    }

    if (
        "implemented_through",
        MODUS_LEXEME_ID,
    ) not in targets:
        raise RuntimeError(
            "Kindred -> Modus relationship missing"
        )

    if (
        "depends_on",
        KINDRED_ID,
    ) not in targets:
        raise RuntimeError(
            "Kindred -> Kindred relationship missing"
        )

    for _, target in targets:
        if target not in by_id:
            raise RuntimeError(
                "Unresolved Lexicon relationship "
                f"target: {target}"
            )

    modus = by_id[
        MODUS_LEXEME_ID
    ]

    if (
        modus.get(
            "metadata",
            {}
        ).get(
            "external_identity"
        )
        != EXTERNAL_MODUS_ID
    ):
        raise RuntimeError(
            "Modus external identity missing"
        )


def main() -> int:
    registry = load_registry()

    backup_root = (
        LEXICON_ROOT
        / "backups"
        / "kindred-modus-reference"
        / timestamp()
    )

    backup_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        REGISTRY_PATH,
        backup_root
        / "registry.yaml",
    )

    ensure_modus_lexeme(
        registry
    )

    repair_kindred(
        registry
    )

    registry["lexemes"] = sorted(
        registry["lexemes"],
        key=lambda lexeme: (
            0
            if lexeme.get(
                "status"
            )
            == "active"
            else 1,
            str(
                lexeme.get(
                    "id",
                    "",
                )
            ),
        ),
    )

    validate(
        registry
    )

    write_registry(
        registry
    )

    print(
        "KINDRED/MODUS LEXICON REFERENCE: complete"
    )

    print(
        f"MODUS LEXEME: {MODUS_LEXEME_ID}"
    )

    print(
        f"EXTERNAL MODUS: {EXTERNAL_MODUS_ID}"
    )

    print(
        f"BACKUP: {backup_root}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

#!/usr/bin/env python3

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml


LEXICON_ROOT = Path("/root/savant-runtime/lexicon")

REGISTRY_PATH = (
    LEXICON_ROOT
    / "registry.yaml"
)

TERMINOLOGY_PATH = (
    LEXICON_ROOT
    / "TERMINOLOGY_EVOLUTION.yaml"
)

REGISTRY_SCHEMA_PATH = (
    LEXICON_ROOT
    / "schemas"
    / "registry.schema.yaml"
)

KINDRED_ID = "lex:core:kindred"
KINSHIP_ID = "lex:service:kinship"


def stamp() -> str:
    return (
        datetime.now(timezone.utc)
        .strftime("%Y%m%dT%H%M%SZ")
    )


def load_yaml(
    path: Path,
) -> dict[str, Any]:
    payload = yaml.safe_load(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            f"{path}: expected YAML object"
        )

    return payload


def write_yaml(
    path: Path,
    payload: Mapping[str, Any],
) -> None:
    path.write_text(
        yaml.safe_dump(
            dict(payload),
            sort_keys=False,
            allow_unicode=True,
            width=100,
        ),
        encoding="utf-8",
    )


def backup(
    path: Path,
    root: Path,
) -> None:
    relative = path.relative_to(
        LEXICON_ROOT
    )

    destination = (
        root
        / relative
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        path,
        destination,
    )


def ensure_lineage(
    lexeme: dict[str, Any],
) -> dict[str, Any]:
    lineage = lexeme.get(
        "lineage"
    )

    if not isinstance(
        lineage,
        dict,
    ):
        lineage = {}

    supersedes = lineage.get(
        "supersedes"
    )

    if not isinstance(
        supersedes,
        list,
    ):
        supersedes = []

    history = lineage.get(
        "history"
    )

    if not isinstance(
        history,
        list,
    ):
        history = []

    lineage[
        "supersedes"
    ] = supersedes

    lineage[
        "history"
    ] = history

    lineage.setdefault(
        "superseded_by",
        None,
    )

    lexeme[
        "lineage"
    ] = lineage

    return lineage


def ensure_provenance(
    lexeme: dict[str, Any],
) -> None:
    provenance = lexeme.get(
        "provenance"
    )

    if isinstance(
        provenance,
        dict,
    ):
        return

    if isinstance(
        provenance,
        list,
    ):
        lexeme[
            "provenance"
        ] = {
            "sources": [
                str(value)
                for value
                in provenance
            ],
            "authority": "accepted",
            "confidence": "confirmed",
        }

        return

    lexeme[
        "provenance"
    ] = {
        "sources": [
            "lexical-authority-reconciliation-20260809"
        ],
        "authority": "accepted",
        "confidence": "confirmed",
    }


def reconcile_registry(
    registry: dict[str, Any],
) -> None:
    lexemes = registry.get(
        "lexemes"
    )

    if not isinstance(
        lexemes,
        list,
    ):
        raise TypeError(
            "registry.lexemes must be a list"
        )

    kindred_candidates = [
        item
        for item in lexemes
        if isinstance(
            item,
            dict,
        )
        and str(
            item.get(
                "canonical",
                "",
            )
        ).casefold()
        == "kindred"
    ]

    if len(
        kindred_candidates
    ) != 1:
        raise RuntimeError(
            "Expected exactly one Kindred "
            "lexeme before reconciliation"
        )

    kindred = (
        kindred_candidates[0]
    )

    kindred[
        "id"
    ] = KINDRED_ID

    kindred[
        "canonical"
    ] = "Kindred"

    kindred[
        "concept"
    ] = (
        "Canonical relationship methodology "
        "and universal typed relationship system"
    )

    kindred[
        "description"
    ] = (
        "Defines Savant relationship families, "
        "typed relationship semantics, constraints, "
        "cardinality, authority, lineage, provenance, "
        "validity, and graph-addressable relationship "
        "structure."
    )

    kindred[
        "status"
    ] = "active"

    ensure_provenance(
        kindred
    )

    kindred_lineage = (
        ensure_lineage(
            kindred
        )
    )

    kinship_identifiers = {
        "lex:history:kinship",
        KINSHIP_ID,
    }

    kindred_lineage[
        "supersedes"
    ] = [
        value
        for value
        in kindred_lineage[
            "supersedes"
        ]
        if str(value)
        not in kinship_identifiers
    ]

    kindred_lineage[
        "history"
    ] = [
        event
        for event
        in kindred_lineage[
            "history"
        ]
        if not (
            isinstance(
                event,
                Mapping,
            )
            and (
                str(
                    event.get(
                        "predecessor",
                        "",
                    )
                )
                in kinship_identifiers
                or str(
                    event.get(
                        "historical_term",
                        "",
                    )
                ).casefold()
                == "kinship"
            )
        )
    ]

    kindred_lineage[
        "superseded_by"
    ] = None

    lexemes[:] = [
        item
        for item in lexemes
        if not (
            isinstance(
                item,
                dict,
            )
            and str(
                item.get(
                    "id",
                    "",
                )
            )
            == "lex:history:kinship"
        )
    ]

    kinship_candidates = [
        item
        for item in lexemes
        if isinstance(
            item,
            dict,
        )
        and str(
            item.get(
                "canonical",
                "",
            )
        ).casefold()
        == "kinship"
    ]

    if len(
        kinship_candidates
    ) > 1:
        raise RuntimeError(
            "Multiple Kinship lexemes exist"
        )

    if kinship_candidates:
        kinship = (
            kinship_candidates[0]
        )

    else:
        kinship = {}

        lexemes.append(
            kinship
        )

    kinship.update(
        {
            "id": KINSHIP_ID,
            "canonical": "Kinship",
            "concept": (
                "Functional relationship-plane service"
            ),
            "description": (
                "Active Savant service that compiles "
                "functional relationship planes from "
                "Kindred relationship authority."
            ),
            "layer": "shard00",
            "status": "active",
            "dependencies": [
                KINDRED_ID
            ],
            "relationships": [
                {
                    "type": "depends_on",
                    "target": KINDRED_ID,
                },
                {
                    "type": "implemented_through",
                    "target": "exile:modus",
                },
            ],
            "metadata": {
                "accepted_graph_id": (
                    "service:kinship"
                ),
                "system_dependency": (
                    "system:kindred"
                ),
                "implementation_ref": (
                    "runtime/kinship"
                ),
                "implemented_through": (
                    "exile:modus"
                ),
                "role": (
                    "compile-functional-relationship-planes"
                ),
            },
        }
    )

    kinship[
        "lineage"
    ] = {
        "supersedes": [],
        "superseded_by": None,
        "history": [],
    }

    kinship[
        "provenance"
    ] = {
        "sources": [
            "accepted-graph:service:kinship",
            "accepted-graph:system:kindred",
            "runtime/kinship/",
        ],
        "authority": "accepted",
        "confidence": "confirmed",
    }

    reserved = registry.get(
        "reserved"
    )

    if isinstance(
        reserved,
        list,
    ):
        registry[
            "reserved"
        ] = [
            value
            for value
            in reserved
            if str(value).casefold()
            != "kinship"
        ]


def remove_false_change(
    changes: list[Any],
) -> list[Any]:
    result: list[Any] = []

    false_ids = {
        "lexchange:kinship-kindred",
        "lexchange:kindred-kinship",
    }

    for change in changes:
        if not isinstance(
            change,
            Mapping,
        ):
            result.append(
                change
            )

            continue

        change_id = str(
            change.get(
                "change_id",
                "",
            )
        )

        if change_id in false_ids:
            continue

        canonical = change.get(
            "canonical"
        )

        lineage = change.get(
            "lineage"
        )

        if (
            isinstance(
                canonical,
                Mapping,
            )
            and str(
                canonical.get(
                    "term",
                    "",
                )
            ).casefold()
            == "kindred"
            and isinstance(
                lineage,
                Mapping,
            )
            and any(
                str(value).casefold()
                == "kinship"
                for value
                in lineage.get(
                    "supersedes",
                    [],
                )
            )
        ):
            continue

        result.append(
            change
        )

    return result


def reconcile_terminology(
    ledger: dict[str, Any],
) -> None:
    changes = ledger.get(
        "changes"
    )

    if not isinstance(
        changes,
        list,
    ):
        changes = []

    changes = remove_false_change(
        changes
    )

    changes.extend(
        [
            {
                "change_id": (
                    "lexchange:kindred-distinct"
                ),
                "concept_id": (
                    "concept:kindred"
                ),
                "status": "accepted",
                "canonical": {
                    "term": "kindred",
                    "display": "Kindred",
                },
                "definition": (
                    "Canonical relationship methodology "
                    "and universal typed relationship system."
                ),
                "lineage": {
                    "sequence": [
                        "kindred"
                    ],
                    "supersedes": [],
                    "superseded_by": None,
                },
                "compatibility": {
                    "aliases": {},
                    "write_policy": {
                        "canonical_only": True,
                    },
                    "read_policy": {
                        "historical_aliases_allowed": True,
                    },
                },
                "relationships": [
                    {
                        "type": "consumed_by",
                        "target": "service:kinship",
                    }
                ],
                "provenance": {
                    "authority": "accepted",
                    "source": (
                        "constitutional-bootstrap "
                        "and current user directive"
                    ),
                    "date": "2026-08-09",
                },
            },
            {
                "change_id": (
                    "lexchange:kinship-distinct"
                ),
                "concept_id": (
                    "concept:service:kinship"
                ),
                "status": "accepted",
                "canonical": {
                    "term": "kinship",
                    "display": "Kinship",
                },
                "definition": (
                    "Functional relationship-plane "
                    "service consuming Kindred."
                ),
                "lineage": {
                    "sequence": [
                        "kinship"
                    ],
                    "supersedes": [],
                    "superseded_by": None,
                },
                "dependencies": [
                    "system:kindred"
                ],
                "relationships": [
                    {
                        "type": "depends_on",
                        "target": "system:kindred",
                    },
                    {
                        "type": "implemented_through",
                        "target": "exile:modus",
                    },
                ],
                "implementation": {
                    "service": (
                        "service:kinship"
                    ),
                    "runtime": (
                        "runtime/kinship"
                    ),
                },
                "compatibility": {
                    "aliases": {},
                    "write_policy": {
                        "canonical_only": True,
                    },
                    "read_policy": {
                        "historical_aliases_allowed": True,
                    },
                },
                "provenance": {
                    "authority": "accepted",
                    "source": (
                        "constitutional-bootstrap "
                        "and current user directive"
                    ),
                    "date": "2026-08-09",
                },
            },
        ]
    )

    ledger[
        "changes"
    ] = changes

    compatibility = ledger.get(
        "compatibility"
    )

    if isinstance(
        compatibility,
        dict,
    ):
        aliases = compatibility.get(
            "aliases"
        )

        if isinstance(
            aliases,
            dict,
        ):
            for key in list(
                aliases
            ):
                if str(
                    key
                ).casefold() == "kinship":
                    aliases.pop(
                        key,
                        None,
                    )

    retained = ledger.get(
        "retained_terms"
    )

    if not isinstance(
        retained,
        dict,
    ):
        retained = {}

    retained[
        "kindred"
    ] = {
        "canonical": "kindred",
        "role": (
            "relationship-methodology-system"
        ),
        "distinct_from": [
            "kinship"
        ],
    }

    retained[
        "kinship"
    ] = {
        "canonical": "kinship",
        "role": (
            "functional-relationship-plane-service"
        ),
        "depends_on": [
            "system:kindred"
        ],
        "distinct_from": [
            "kindred"
        ],
    }

    ledger[
        "retained_terms"
    ] = retained

    invariants = ledger.get(
        "invariants"
    )

    if not isinstance(
        invariants,
        dict,
    ):
        invariants = {}

    invariants.update(
        {
            "kindred_is_active": True,
            "kinship_is_active": True,
            "kindred_is_not_kinship": True,
            "kinship_is_not_kindred": True,
            "kinship_depends_on_kindred": True,
            "kinship_does_not_supersede_kindred": True,
            "kindred_does_not_supersede_kinship": True,
        }
    )

    ledger[
        "invariants"
    ] = invariants


def reconcile_schema(
    schema: dict[str, Any],
) -> None:
    special = schema.get(
        "special_rules"
    )

    if not isinstance(
        special,
        dict,
    ):
        special = {}

    kindred = special.get(
        "kindred"
    )

    if not isinstance(
        kindred,
        dict,
    ):
        kindred = {}

    kindred.clear()

    kindred.update(
        {
            "canonical": "Kindred",
            "status": "active",
            "role": (
                "relationship-methodology-system"
            ),
            "distinct_from": [
                "Kinship"
            ],
            "supersedes_kinship": False,
            "superseded_by_kinship": False,
        }
    )

    special[
        "kindred"
    ] = kindred

    special[
        "kinship"
    ] = {
        "canonical": "Kinship",
        "status": "active",
        "role": (
            "functional-relationship-plane-service"
        ),
        "distinct_from": [
            "Kindred"
        ],
        "depends_on": [
            "Kindred"
        ],
        "supersedes_kindred": False,
        "superseded_by_kindred": False,
    }

    schema[
        "special_rules"
    ] = special

    compatibility = schema.get(
        "compatibility"
    )

    if isinstance(
        compatibility,
        dict,
    ):
        aliases = compatibility.get(
            "aliases"
        )

        if isinstance(
            aliases,
            dict,
        ):
            for key in list(
                aliases
            ):
                if str(
                    key
                ).casefold() == "kinship":
                    aliases.pop(
                        key,
                        None,
                    )

    invariants = schema.get(
        "invariants"
    )

    if not isinstance(
        invariants,
        dict,
    ):
        invariants = {}

    invariants.update(
        {
            "kindred_active": True,
            "kinship_active": True,
            "kindred_and_kinship_distinct": True,
            "kinship_depends_on_kindred": True,
            "no_kindred_kinship_alias": True,
            "no_kindred_kinship_supersession": True,
        }
    )

    schema[
        "invariants"
    ] = invariants


def validate(
    registry: Mapping[str, Any],
    ledger: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> None:
    lexemes = registry.get(
        "lexemes"
    )

    if not isinstance(
        lexemes,
        list,
    ):
        raise RuntimeError(
            "registry.lexemes missing"
        )

    kindred = [
        item
        for item in lexemes
        if isinstance(
            item,
            Mapping,
        )
        and str(
            item.get(
                "canonical",
                "",
            )
        ).casefold()
        == "kindred"
        and item.get(
            "status"
        )
        == "active"
    ]

    kinship = [
        item
        for item in lexemes
        if isinstance(
            item,
            Mapping,
        )
        and str(
            item.get(
                "canonical",
                "",
            )
        ).casefold()
        == "kinship"
        and item.get(
            "status"
        )
        == "active"
    ]

    if len(kindred) != 1:
        raise RuntimeError(
            "Kindred cardinality invalid"
        )

    if len(kinship) != 1:
        raise RuntimeError(
            "Kinship cardinality invalid"
        )

    if (
        kindred[0]["id"]
        == kinship[0]["id"]
    ):
        raise RuntimeError(
            "Kindred and Kinship share identity"
        )

    dependencies = kinship[0].get(
        "dependencies",
        [],
    )

    if (
        KINDRED_ID
        not in dependencies
    ):
        raise RuntimeError(
            "Kinship lacks Kindred dependency"
        )

    kindred_lineage = ensure_lineage(
        dict(kindred[0])
    )

    if any(
        str(value)
        in {
            KINSHIP_ID,
            "lex:history:kinship",
        }
        for value
        in kindred_lineage[
            "supersedes"
        ]
    ):
        raise RuntimeError(
            "False Kindred/Kinship "
            "supersession remains"
        )

    aliases = (
        ledger.get(
            "compatibility",
            {}
        )
        .get(
            "aliases",
            {}
        )
    )

    if isinstance(
        aliases,
        Mapping,
    ):
        if any(
            str(key).casefold()
            == "kinship"
            for key in aliases
        ):
            raise RuntimeError(
                "False Kinship alias remains "
                "in terminology ledger"
            )

    schema_aliases = (
        schema.get(
            "compatibility",
            {}
        )
        .get(
            "aliases",
            {}
        )
    )

    if isinstance(
        schema_aliases,
        Mapping,
    ):
        if any(
            str(key).casefold()
            == "kinship"
            for key in schema_aliases
        ):
            raise RuntimeError(
                "False Kinship alias remains "
                "in registry schema"
            )


def main() -> int:
    backup_root = (
        LEXICON_ROOT
        / "backups"
        / "kindred-kinship-separation"
        / stamp()
    )

    for path in (
        REGISTRY_PATH,
        TERMINOLOGY_PATH,
        REGISTRY_SCHEMA_PATH,
    ):
        backup(
            path,
            backup_root,
        )

    registry = load_yaml(
        REGISTRY_PATH
    )

    terminology = load_yaml(
        TERMINOLOGY_PATH
    )

    schema = load_yaml(
        REGISTRY_SCHEMA_PATH
    )

    reconcile_registry(
        registry
    )

    reconcile_terminology(
        terminology
    )

    reconcile_schema(
        schema
    )

    validate(
        registry,
        terminology,
        schema,
    )

    write_yaml(
        REGISTRY_PATH,
        registry,
    )

    write_yaml(
        TERMINOLOGY_PATH,
        terminology,
    )

    write_yaml(
        REGISTRY_SCHEMA_PATH,
        schema,
    )

    print(
        "KINDRED/KINSHIP AUTHORITY "
        "RECONCILIATION: complete"
    )

    print(
        "Kindred = active relationship "
        "methodology/system"
    )

    print(
        "Kinship = active functional "
        "relationship-plane service"
    )

    print(
        "Kinship -> depends_on -> Kindred"
    )

    print(
        f"BACKUP: {backup_root}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

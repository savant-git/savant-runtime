#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml


LEXICON_ROOT = Path("/root/savant-runtime/lexicon")
REGISTRY_PATH = LEXICON_ROOT / "registry.yaml"

SPECIAL_NON_SUPERSESSION = {
    (
        "lex:identity:mote",
        "shard",
    ),
}

VALID_CONFIDENCE = {
    "confirmed",
    "inferred",
    "projected",
}


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def normalize_term(value: str) -> str:
    return " ".join(
        str(value).strip().casefold().split()
    )


def slugify(value: str) -> str:
    value = normalize_term(value)

    value = re.sub(
        r"[^a-z0-9_-]+",
        "-",
        value,
    )

    value = re.sub(
        r"-+",
        "-",
        value,
    ).strip("-")

    if not value:
        value = "historical"

    if not value[0].isalpha():
        value = f"h-{value}"

    return value


def load_registry() -> dict[str, Any]:
    payload = yaml.safe_load(
        REGISTRY_PATH.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(payload, dict):
        raise TypeError(
            "registry must be a YAML object"
        )

    lexemes = payload.get("lexemes")

    if not isinstance(lexemes, list):
        raise TypeError(
            "registry.lexemes must be a list"
        )

    return payload


def provenance_object(
    value: Any,
) -> dict[str, Any]:
    if isinstance(value, Mapping):
        result = dict(value)

        confidence = result.get(
            "confidence"
        )

        if (
            confidence is not None
            and confidence
            not in VALID_CONFIDENCE
        ):
            raise ValueError(
                "invalid existing provenance "
                f"confidence: {confidence!r}"
            )

        return result

    if isinstance(value, list):
        sources = [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

        return {
            "sources": sources,
            "confidence": "confirmed",
        }

    if isinstance(value, str):
        source = value.strip()

        return {
            "sources": (
                [source]
                if source
                else []
            ),
            "confidence": "confirmed",
        }

    if value is None:
        return {
            "sources": [],
            "confidence": "confirmed",
        }

    raise TypeError(
        "unsupported provenance shape: "
        f"{type(value).__name__}"
    )


def ensure_lineage(
    lexeme: dict[str, Any],
) -> dict[str, Any]:
    lineage = lexeme.get("lineage")

    if lineage is None:
        lineage = {}

    if not isinstance(lineage, dict):
        raise TypeError(
            f"{lexeme.get('id')}: lineage "
            "must be an object"
        )

    supersedes = lineage.get(
        "supersedes"
    )

    if supersedes is None:
        supersedes = []

    if not isinstance(supersedes, list):
        raise TypeError(
            f"{lexeme.get('id')}: "
            "lineage.supersedes must be a list"
        )

    history = lineage.get("history")

    if history is None:
        history = []

    if not isinstance(history, list):
        raise TypeError(
            f"{lexeme.get('id')}: "
            "lineage.history must be a list"
        )

    lineage["supersedes"] = list(
        supersedes
    )

    lineage.setdefault(
        "superseded_by",
        None,
    )

    lineage["history"] = list(history)

    lexeme["lineage"] = lineage

    return lineage


def build_indexes(
    lexemes: list[dict[str, Any]],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, list[dict[str, Any]]],
]:
    by_id: dict[str, dict[str, Any]] = {}
    by_canonical: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for lexeme in lexemes:
        lexeme_id = str(
            lexeme.get("id", "")
        ).strip()

        canonical = str(
            lexeme.get("canonical", "")
        ).strip()

        if not lexeme_id:
            raise ValueError(
                "lexeme missing id"
            )

        if lexeme_id in by_id:
            raise ValueError(
                f"duplicate lexeme id: "
                f"{lexeme_id}"
            )

        by_id[lexeme_id] = lexeme

        if canonical:
            by_canonical.setdefault(
                normalize_term(canonical),
                [],
            ).append(lexeme)

    return by_id, by_canonical


def unique_history_id(
    predecessor: str,
    successor_id: str,
    by_id: Mapping[
        str,
        dict[str, Any],
    ],
) -> str:
    base = (
        "lex:history:"
        f"{slugify(predecessor)}"
    )

    if base not in by_id:
        return base

    existing = by_id[base]

    if (
        normalize_term(
            existing.get(
                "canonical",
                "",
            )
        )
        == normalize_term(predecessor)
        and ensure_lineage(
            existing
        ).get(
            "superseded_by"
        )
        == successor_id
    ):
        return base

    digest = hashlib.sha256(
        (
            predecessor
            + "\0"
            + successor_id
        ).encode("utf-8")
    ).hexdigest()[:10]

    candidate = (
        f"{base}-{digest}"
    )

    if candidate in by_id:
        existing = by_id[candidate]

        if (
            normalize_term(
                existing.get(
                    "canonical",
                    "",
                )
            )
            != normalize_term(
                predecessor
            )
        ):
            raise ValueError(
                "historical lexeme id "
                f"collision: {candidate}"
            )

    return candidate


def add_history_event(
    lineage: dict[str, Any],
    event: dict[str, Any],
) -> None:
    history = lineage.setdefault(
        "history",
        [],
    )

    if event not in history:
        history.append(event)


def materialize_predecessor(
    *,
    predecessor_name: str,
    successor: dict[str, Any],
    lexemes: list[dict[str, Any]],
    by_id: dict[
        str,
        dict[str, Any],
    ],
    by_canonical: dict[
        str,
        list[dict[str, Any]],
    ],
) -> str | None:
    successor_id = str(
        successor["id"]
    )

    normalized = normalize_term(
        predecessor_name
    )

    if (
        successor_id,
        normalized,
    ) in SPECIAL_NON_SUPERSESSION:
        successor_lineage = (
            ensure_lineage(successor)
        )

        add_history_event(
            successor_lineage,
            {
                "event": (
                    "historical-label-replaced"
                ),
                "historical_term": (
                    predecessor_name
                ),
                "current_term": successor.get(
                    "canonical"
                ),
                "scope": (
                    "identity-tier-2-only"
                ),
                "global_supersession": False,
            },
        )

        return None

    if predecessor_name in by_id:
        predecessor = by_id[
            predecessor_name
        ]

        predecessor_id = (
            predecessor_name
        )

    else:
        matches = by_canonical.get(
            normalized,
            [],
        )

        if len(matches) > 1:
            raise ValueError(
                "ambiguous predecessor "
                f"canonical term: "
                f"{predecessor_name!r}"
            )

        if matches:
            predecessor = matches[0]
            predecessor_id = str(
                predecessor["id"]
            )

        else:
            predecessor_id = (
                unique_history_id(
                    predecessor_name,
                    successor_id,
                    by_id,
                )
            )

            predecessor = {
                "id": predecessor_id,
                "canonical": (
                    predecessor_name
                ),
                "concept": (
                    "Historical predecessor of "
                    f"{successor.get('canonical')}"
                ),
                "layer": successor.get(
                    "layer",
                    "shard00",
                ),
                "status": "superseded",
                "lineage": {
                    "supersedes": [],
                    "superseded_by": (
                        successor_id
                    ),
                    "history": [
                        {
                            "event": (
                                "superseded"
                            ),
                            "successor": (
                                successor_id
                            ),
                        }
                    ],
                },
                "provenance": {
                    "sources": [
                        (
                            "lexical-migration-"
                            "20260809"
                        )
                    ],
                    "confidence": (
                        "confirmed"
                    ),
                },
            }

            lexemes.append(
                predecessor
            )

            by_id[
                predecessor_id
            ] = predecessor

            by_canonical.setdefault(
                normalized,
                [],
            ).append(
                predecessor
            )

            return predecessor_id

    if predecessor is successor:
        raise ValueError(
            f"{successor_id} cannot "
            "supersede itself"
        )

    predecessor_status = str(
        predecessor.get(
            "status",
            "",
        )
    ).strip()

    if predecessor_status == "active":
        predecessor["status"] = (
            "superseded"
        )

    elif predecessor_status not in {
        "superseded",
        "deprecated",
        "reserved",
    }:
        predecessor["status"] = (
            "superseded"
        )

    if (
        predecessor.get("status")
        != "superseded"
    ):
        predecessor["status"] = (
            "superseded"
        )

    predecessor_lineage = (
        ensure_lineage(
            predecessor
        )
    )

    current_successor = (
        predecessor_lineage.get(
            "superseded_by"
        )
    )

    if (
        current_successor
        not in (
            None,
            "",
            successor_id,
        )
    ):
        raise ValueError(
            f"{predecessor_id} already "
            "superseded by "
            f"{current_successor}, cannot "
            f"also supersede to "
            f"{successor_id}"
        )

    predecessor_lineage[
        "superseded_by"
    ] = successor_id

    add_history_event(
        predecessor_lineage,
        {
            "event": "superseded",
            "successor": successor_id,
        },
    )

    predecessor["provenance"] = (
        provenance_object(
            predecessor.get(
                "provenance"
            )
        )
    )

    return predecessor_id


def normalize_registry(
    registry: dict[str, Any],
) -> dict[str, Any]:
    raw_lexemes = registry[
        "lexemes"
    ]

    lexemes: list[
        dict[str, Any]
    ] = []

    for raw in raw_lexemes:
        if not isinstance(raw, Mapping):
            raise TypeError(
                "every lexeme must be an object"
            )

        lexeme = dict(raw)

        lexeme["provenance"] = (
            provenance_object(
                lexeme.get(
                    "provenance"
                )
            )
        )

        ensure_lineage(lexeme)

        lexemes.append(lexeme)

    registry["lexemes"] = lexemes

    by_id, by_canonical = (
        build_indexes(lexemes)
    )

    original_lexemes = list(
        lexemes
    )

    for successor in original_lexemes:
        successor_id = str(
            successor["id"]
        )

        lineage = ensure_lineage(
            successor
        )

        original_predecessors = list(
            lineage.get(
                "supersedes",
                [],
            )
        )

        resolved_ids: list[str] = []

        for predecessor_value in (
            original_predecessors
        ):
            predecessor_name = str(
                predecessor_value
            ).strip()

            if not predecessor_name:
                continue

            resolved = (
                materialize_predecessor(
                    predecessor_name=(
                        predecessor_name
                    ),
                    successor=successor,
                    lexemes=lexemes,
                    by_id=by_id,
                    by_canonical=(
                        by_canonical
                    ),
                )
            )

            if (
                resolved
                and resolved
                not in resolved_ids
            ):
                resolved_ids.append(
                    resolved
                )

                add_history_event(
                    lineage,
                    {
                        "event": (
                            "supersedes"
                        ),
                        "predecessor": (
                            resolved
                        ),
                        "successor": (
                            successor_id
                        ),
                    },
                )

        lineage["supersedes"] = (
            resolved_ids
        )

    by_id, by_canonical = (
        build_indexes(lexemes)
    )

    for lexeme in lexemes:
        lexeme_id = str(
            lexeme["id"]
        )

        lineage = ensure_lineage(
            lexeme
        )

        superseded_by = (
            lineage.get(
                "superseded_by"
            )
        )

        if superseded_by:
            successor = by_id.get(
                str(superseded_by)
            )

            if successor is None:
                raise ValueError(
                    f"{lexeme_id}: unresolved "
                    "superseded_by "
                    f"{superseded_by}"
                )

            successor_lineage = (
                ensure_lineage(
                    successor
                )
            )

            if (
                lexeme_id
                not in successor_lineage[
                    "supersedes"
                ]
            ):
                successor_lineage[
                    "supersedes"
                ].append(
                    lexeme_id
                )

                add_history_event(
                    successor_lineage,
                    {
                        "event": (
                            "supersedes"
                        ),
                        "predecessor": (
                            lexeme_id
                        ),
                        "successor": str(
                            successor["id"]
                        ),
                    },
                )

    registry["lexemes"] = sorted(
        lexemes,
        key=lambda item: (
            0
            if item.get("status")
            == "active"
            else 1,
            str(
                item.get(
                    "id",
                    "",
                )
            ),
        ),
    )

    return registry


def validate_normalized(
    registry: Mapping[str, Any],
) -> None:
    lexemes = registry.get(
        "lexemes"
    )

    if not isinstance(lexemes, list):
        raise TypeError(
            "normalized lexemes missing"
        )

    by_id = {
        str(item["id"]): item
        for item in lexemes
    }

    if len(by_id) != len(lexemes):
        raise ValueError(
            "duplicate lexeme ids after "
            "normalization"
        )

    canonical_owners: dict[
        str,
        list[str],
    ] = {}

    for lexeme in lexemes:
        lexeme_id = str(
            lexeme["id"]
        )

        provenance = lexeme.get(
            "provenance"
        )

        if not isinstance(
            provenance,
            Mapping,
        ):
            raise TypeError(
                f"{lexeme_id}: provenance "
                "is not an object"
            )

        lineage = lexeme.get(
            "lineage"
        )

        if not isinstance(
            lineage,
            Mapping,
        ):
            raise TypeError(
                f"{lexeme_id}: lineage "
                "is not an object"
            )

        supersedes = lineage.get(
            "supersedes"
        )

        if not isinstance(
            supersedes,
            list,
        ):
            raise TypeError(
                f"{lexeme_id}: supersedes "
                "is not a list"
            )

        if supersedes and not isinstance(
            lineage.get("history"),
            list,
        ):
            raise TypeError(
                f"{lexeme_id}: "
                "supersession lacks history"
            )

        for predecessor_id in supersedes:
            predecessor = by_id.get(
                str(predecessor_id)
            )

            if predecessor is None:
                raise ValueError(
                    f"{lexeme_id}: unresolved "
                    "predecessor "
                    f"{predecessor_id}"
                )

            if (
                predecessor.get("status")
                != "superseded"
            ):
                raise ValueError(
                    f"{predecessor_id}: "
                    "predecessor not superseded"
                )

            predecessor_lineage = (
                predecessor.get(
                    "lineage"
                )
            )

            if (
                not isinstance(
                    predecessor_lineage,
                    Mapping,
                )
                or predecessor_lineage.get(
                    "superseded_by"
                )
                != lexeme_id
            ):
                raise ValueError(
                    f"{predecessor_id}: "
                    "bidirectional "
                    "supersession mismatch"
                )

        canonical = str(
            lexeme.get(
                "canonical",
                "",
            )
        ).strip()

        if canonical:
            canonical_owners.setdefault(
                normalize_term(canonical),
                [],
            ).append(
                lexeme_id
            )

    duplicates = {
        canonical: owners
        for canonical, owners
        in canonical_owners.items()
        if len(owners) > 1
    }

    if duplicates:
        raise ValueError(
            "duplicate canonical spellings "
            f"after normalization: "
            f"{duplicates}"
        )

    shard = [
        item
        for item in lexemes
        if normalize_term(
            item.get(
                "canonical",
                "",
            )
        )
        == "shard"
        and item.get("status")
        == "active"
    ]

    mote = [
        item
        for item in lexemes
        if normalize_term(
            item.get(
                "canonical",
                "",
            )
        )
        == "mote"
        and item.get("status")
        == "active"
    ]

    if len(shard) != 1:
        raise ValueError(
            "global Shard must remain "
            "exactly one active lexeme"
        )

    if len(mote) != 1:
        raise ValueError(
            "Mote must remain exactly one "
            "active lexeme"
        )

    mote_supersedes = set(
        ensure_lineage(
            mote[0]
        ).get(
            "supersedes",
            [],
        )
    )

    if str(shard[0]["id"]) in (
        mote_supersedes
    ):
        raise ValueError(
            "Mote must not supersede "
            "global Shard"
        )


def main() -> int:
    registry = load_registry()

    timestamp = (
        datetime.now(timezone.utc)
        .strftime("%Y%m%dT%H%M%SZ")
    )

    backup = (
        REGISTRY_PATH.parent
        / "backups"
        / "lexical-migration-20260809"
        / timestamp
        / "registry.yaml"
    )

    backup.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        REGISTRY_PATH,
        backup,
    )

    normalized = normalize_registry(
        registry
    )

    validate_normalized(
        normalized
    )

    output = yaml.safe_dump(
        normalized,
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )

    REGISTRY_PATH.write_text(
        output,
        encoding="utf-8",
    )

    print(
        "LEXICON REGISTRY NORMALIZATION: "
        "complete"
    )

    print(
        f"REGISTRY: {REGISTRY_PATH}"
    )

    print(
        f"BACKUP: {backup}"
    )

    print(
        "LEXEMES: "
        f"{len(normalized['lexemes'])}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

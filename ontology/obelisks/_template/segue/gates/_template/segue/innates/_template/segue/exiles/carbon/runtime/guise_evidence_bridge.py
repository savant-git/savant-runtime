#!/usr/bin/env python3
"""Non-authoritative evidence projection for guise composition."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

from guise_composition import TRAITS, mote_traits


class GuiseEvidenceError(ValueError):
    """Invalid evidence or composition reference."""


SCHEMA = "savant://carbon/oriel/guise/evidence/1"

STATUSES = frozenset(
    {
        "accepted",
        "proposed",
        "historical",
        "superseded",
        "rejected",
        "unresolved",
        "simulated",
    }
)


def canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def fingerprint(value: Any) -> str:
    return hashlib.sha256(
        canonical(value).encode("utf-8")
    ).hexdigest()


def required(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise GuiseEvidenceError(
            f"{name} must be text"
        )

    if not value or value != value.strip():
        raise GuiseEvidenceError(
            f"{name} must be nonempty and normalized"
        )

    return value


def normalize(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize an evidence reference without changing authority."""

    if not isinstance(record, Mapping):
        raise GuiseEvidenceError(
            "evidence must be a mapping"
        )

    character = required(
        record.get("character"),
        "character",
    )
    source = required(
        record.get("source"),
        "source",
    )
    locator = required(
        record.get("locator"),
        "locator",
    )
    mote = required(
        record.get("mote"),
        "mote",
    )
    status = required(
        record.get("status"),
        "status",
    )

    if status not in STATUSES:
        raise GuiseEvidenceError(
            f"unsupported status: {status}"
        )

    if mote not in {
        name
        for names in TRAITS.values()
        for name in names
    }:
        raise GuiseEvidenceError(
            f"unknown mote: {mote}"
        )

    content = record.get("content")

    if not isinstance(content, str) or not content.strip():
        raise GuiseEvidenceError(
            "content must be nonempty text"
        )

    authority = record.get("authority")

    if authority is not None:
        authority = required(
            authority,
            "authority",
        )

    normalized = {
        "schema": SCHEMA,
        "character": character,
        "source": source,
        "locator": locator,
        "mote": mote,
        "status": status,
        "content": content,
        "authority": authority,
    }

    normalized["identity"] = (
        "guise:evidence:"
        + fingerprint(normalized)[:32]
    )

    return normalized


def project(
    records: Iterable[Mapping[str, Any]],
    character: str,
) -> dict[str, Any]:
    """Build a deterministic, non-authoritative character view."""

    character = required(
        character,
        "character",
    )

    indexed: dict[str, dict[str, Any]] = {}

    for record in records:
        item = normalize(record)

        if item["character"] != character:
            continue

        indexed[item["identity"]] = item

    evidence = [
        indexed[identity]
        for identity in sorted(indexed)
    ]

    traits = []

    for trait, motes in TRAITS.items():
        slots = []

        for mote in motes:
            matching = [
                item["identity"]
                for item in evidence
                if item["mote"] == mote
            ]

            slots.append(
                {
                    "mote": mote,
                    "evidence": matching,
                }
            )

        traits.append(
            {
                "trait": trait,
                "motes": slots,
            }
        )

    return {
        "schema": SCHEMA,
        "character": character,
        "authoritative": False,
        "traits": traits,
        "evidence": evidence,
        "evidence_count": len(evidence),
        "digest": fingerprint(evidence),
    }


def shared_motes() -> dict[str, list[str]]:
    """Expose mote identities referenced by multiple traits."""

    names = sorted(
        {
            mote
            for motes in TRAITS.values()
            for mote in motes
        }
    )

    return {
        mote: list(mote_traits(mote))
        for mote in names
        if len(mote_traits(mote)) > 1
    }


def unresolved(
    records: Iterable[Mapping[str, Any]],
    character: str,
) -> list[dict[str, Any]]:
    """Project evidence requiring an authority decision."""

    view = project(records, character)

    return [
        item
        for item in view["evidence"]
        if item["status"] == "unresolved"
    ]

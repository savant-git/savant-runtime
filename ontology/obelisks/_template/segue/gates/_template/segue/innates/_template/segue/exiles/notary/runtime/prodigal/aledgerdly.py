#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


OWNER = "exile:notary"
PRODIGAL = "prodigal:aledgerdly"

SCHEMA = (
    "savant://runtime/notary/"
    "prodigal/aledgerdly/1.0.0"
)


class AledgerdlyError(RuntimeError):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def normalize_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return str(
        value
    ).strip()


def normalize_terms(
    values: Sequence[Any],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                term
                for value in values
                if (
                    term
                    := normalize_text(
                        value
                    )
                )
            }
        )
    )


def require_mapping(
    value: Any,
    name: str,
) -> Mapping[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise AledgerdlyError(
            f"{name} must be a mapping"
        )

    return value


@dataclass(
    frozen=True,
    slots=True,
)
class LedgerEntry:
    subject: str
    source_ref: str
    source_digest: str
    entry_kind: str
    sequence: int
    predecessor_ref: str | None
    provenance: Any
    lineage: Any
    dependencies: tuple[str, ...]

    @property
    def entry_id(
        self,
    ) -> str:
        material = {
            "subject": self.subject,
            "source_ref": (
                self.source_ref
            ),
            "source_digest": (
                self.source_digest
            ),
            "entry_kind": (
                self.entry_kind
            ),
            "sequence": (
                self.sequence
            ),
            "predecessor_ref": (
                self.predecessor_ref
            ),
            "provenance": (
                self.provenance
            ),
            "lineage": (
                self.lineage
            ),
            "dependencies": list(
                self.dependencies
            ),
        }

        return (
            "aledgerdly-entry:"
            + digest(
                material
            )[:32]
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "entry_id": (
                self.entry_id
            ),
            "subject": self.subject,
            "source_ref": (
                self.source_ref
            ),
            "source_digest": (
                self.source_digest
            ),
            "entry_kind": (
                self.entry_kind
            ),
            "sequence": (
                self.sequence
            ),
            "predecessor_ref": (
                self.predecessor_ref
            ),
            "provenance": (
                self.provenance
            ),
            "lineage": (
                self.lineage
            ),
            "dependencies": list(
                self.dependencies
            ),
            "owner": OWNER,
            "prodigal": PRODIGAL,
            "append_intent": True,
            "immutable_entry": True,
            "history_preserved": True,
            "ledger_projection": True,
            "persistent_append": False,
            "ledger_mutated": False,
            "canon_mutated": False,
            "source_mutated": False,
            "verification_decision": None,
            "evidence_admitted": False,
            "attested": False,
            "authority_created": False,
            "authority_mutated": False,
            "authority_transferred": False,
            "authoritative": False,
            "authority_effect": "none",
            "rebuildable": True,
            "deterministic": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


def entry_from_earmark(
    earmark_projection: Mapping[
        str,
        Any,
    ],
    *,
    sequence: int,
    predecessor_ref: str | None = None,
    entry_kind: str = "earmark",
) -> LedgerEntry:
    projection = require_mapping(
        earmark_projection,
        "earmark_projection",
    )

    if (
        normalize_text(
            projection.get(
                "prodigal"
            )
        )
        != "prodigal:earmarkd"
    ):
        raise AledgerdlyError(
            "projection is not owned by "
            "Earmarkd"
        )

    subject = normalize_text(
        projection.get(
            "subject"
        )
    )

    if not subject:
        raise AledgerdlyError(
            "subject is required"
        )

    source_ref = normalize_text(
        projection.get(
            "earmark_id"
        )
    )

    if not source_ref:
        raise AledgerdlyError(
            "earmark_id is required"
        )

    source_digest = normalize_text(
        projection.get(
            "digest"
        )
    )

    if not source_digest:
        raise AledgerdlyError(
            "source digest is required"
        )

    if isinstance(
        sequence,
        bool,
    ):
        raise AledgerdlyError(
            "sequence must be an integer"
        )

    try:
        normalized_sequence = int(
            sequence
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise AledgerdlyError(
            "sequence must be an integer"
        ) from exc

    if normalized_sequence < 0:
        raise AledgerdlyError(
            "sequence cannot be negative"
        )

    normalized_predecessor = (
        normalize_text(
            predecessor_ref
        )
        or None
    )

    normalized_kind = (
        normalize_text(
            entry_kind
        )
    )

    if not normalized_kind:
        raise AledgerdlyError(
            "entry_kind is required"
        )

    return LedgerEntry(
        subject=subject,
        source_ref=source_ref,
        source_digest=source_digest,
        entry_kind=normalized_kind,
        sequence=normalized_sequence,
        predecessor_ref=(
            normalized_predecessor
        ),
        provenance=(
            projection.get(
                "provenance"
            )
        ),
        lineage=(
            projection.get(
                "lineage"
            )
        ),
        dependencies=normalize_terms(
            tuple(
                projection.get(
                    "dependencies"
                )
                or ()
            )
        ),
    )


def append_projection(
    entries: Sequence[
        LedgerEntry
    ],
) -> dict[str, Any]:
    normalized = tuple(
        sorted(
            entries,
            key=lambda entry: (
                entry.sequence,
                entry.entry_id,
            ),
        )
    )

    seen_sequences: set[int] = set()
    seen_entries: set[str] = set()

    projections: list[
        dict[str, Any]
    ] = []

    for entry in normalized:
        if entry.sequence in seen_sequences:
            raise AledgerdlyError(
                "duplicate ledger sequence"
            )

        if entry.entry_id in seen_entries:
            raise AledgerdlyError(
                "duplicate ledger entry"
            )

        seen_sequences.add(
            entry.sequence
        )
        seen_entries.add(
            entry.entry_id
        )
        projections.append(
            entry.projection()
        )

    payload = {
        "schema": (
            "savant://runtime/notary/"
            "prodigal/aledgerdly/"
            "append-projection/1.0.0"
        ),
        "owner": OWNER,
        "prodigal": PRODIGAL,
        "entries": projections,
        "entry_count": len(
            projections
        ),
        "append_order": [
            entry["entry_id"]
            for entry in projections
        ],
        "append_only": True,
        "immutable_history": True,
        "persistent_append": False,
        "ledger_mutated": False,
        "canon_mutated": False,
        "source_mutated": False,
        "authority_created": False,
        "authority_mutated": False,
        "authority_transferred": False,
        "authoritative": False,
        "authority_effect": "none",
        "rebuildable": True,
        "deterministic": True,
    }

    payload["digest"] = digest(
        payload
    )

    return payload


def status() -> dict[str, Any]:
    payload = {
        "schema": (
            "savant://runtime/notary/"
            "prodigal/aledgerdly/"
            "status/1.0.0"
        ),
        "owner": OWNER,
        "prodigal": PRODIGAL,
        "purpose": (
            "derive immutable ordered "
            "ledger-entry projections while "
            "preserving append-only history"
        ),
        "capabilities": [
            "immutable-ledger-entry",
            "append-order-projection",
            "history-preservation",
            "predecessor-reference",
            "sequence-conflict-detection",
            "duplicate-entry-detection",
            "provenance-preservation",
            "lineage-preservation",
            "dependency-preservation",
            "earmarkd-composition",
            "deterministic-ledger-projection",
        ],
        "verification_owner": OWNER,
        "can_verify": False,
        "can_admit_evidence": False,
        "can_attest": False,
        "can_persist_ledger": False,
        "can_mutate_ledger": False,
        "can_mutate_canon": False,
        "creates_authority": False,
        "mutates_authority": False,
        "persistent_store": False,
        "authoritative": False,
        "authority_effect": "none",
        "rebuildable": True,
    }

    payload["digest"] = digest(
        payload
    )

    return payload


def main() -> int:
    print(
        json.dumps(
            status(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

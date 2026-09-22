#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


OWNER = "exile:notary"
PRODIGAL = "prodigal:earmarkd"

SCHEMA = (
    "savant://runtime/notary/"
    "prodigal/earmarkd/1.0.0"
)


class EarmarkdError(RuntimeError):
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


def normalize_mapping(
    value: Mapping[
        str,
        Any,
    ]
    | None,
) -> dict[str, Any]:
    if value is None:
        return {}

    if not isinstance(
        value,
        Mapping,
    ):
        raise EarmarkdError(
            "metadata must be a mapping"
        )

    return {
        str(key): value[key]
        for key in sorted(
            value,
            key=lambda item: str(
                item
            ),
        )
    }


@dataclass(
    frozen=True,
    slots=True,
)
class Earmark:
    subject: str
    source_digest: str
    tags: tuple[str, ...]
    indices: tuple[str, ...]
    metadata: Mapping[str, Any]
    semantic_lattice: Mapping[str, Any]
    provenance: Any
    lineage: Any
    dependencies: tuple[str, ...]

    @property
    def earmark_id(
        self,
    ) -> str:
        material = {
            "subject": self.subject,
            "source_digest": (
                self.source_digest
            ),
            "tags": list(
                self.tags
            ),
            "indices": list(
                self.indices
            ),
            "metadata": dict(
                self.metadata
            ),
            "semantic_lattice": dict(
                self.semantic_lattice
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
            "earmark:"
            + digest(
                material
            )[:32]
        )

    @property
    def immutable_state_digest(
        self,
    ) -> str:
        return digest(
            {
                "source_digest": (
                    self.source_digest
                ),
                "tags": list(
                    self.tags
                ),
                "indices": list(
                    self.indices
                ),
                "metadata": dict(
                    self.metadata
                ),
                "semantic_lattice": dict(
                    self.semantic_lattice
                ),
            }
        )

    @property
    def hashloom_ref(
        self,
    ) -> str:
        return (
            "hashloom:"
            + digest(
                {
                    "subject": self.subject,
                    "source_digest": (
                        self.source_digest
                    ),
                    "state_digest": (
                        self.immutable_state_digest
                    ),
                }
            )[:32]
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "earmark_id": (
                self.earmark_id
            ),
            "subject": self.subject,
            "source_digest": (
                self.source_digest
            ),
            "tags": list(
                self.tags
            ),
            "indices": list(
                self.indices
            ),
            "metadata": dict(
                self.metadata
            ),
            "semantic_lattice": dict(
                self.semantic_lattice
            ),
            "immutable_state_digest": (
                self.immutable_state_digest
            ),
            "hashloom_ref": (
                self.hashloom_ref
            ),
            "snapshot_digest": digest(
                {
                    "earmark_id": (
                        self.earmark_id
                    ),
                    "state": (
                        self.immutable_state_digest
                    ),
                }
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
            "metadata_extracted": True,
            "hash_state_condensed": True,
            "semantic_lattice_extracted": True,
            "hash_reference_derived": True,
            "snapshot_derived": True,
            "verification_decision": None,
            "evidence_admitted": False,
            "attested": False,
            "canon_mutated": False,
            "ledger_mutated": False,
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


def earmark(
    *,
    subject: str,
    source: Any,
    tags: Sequence[Any] = (),
    indices: Sequence[Any] = (),
    metadata: Mapping[
        str,
        Any,
    ]
    | None = None,
    semantic_lattice: Mapping[
        str,
        Any,
    ]
    | None = None,
    provenance: Any = None,
    lineage: Any = None,
    dependencies: Sequence[Any] = (),
) -> Earmark:
    normalized_subject = (
        normalize_text(
            subject
        )
    )

    if not normalized_subject:
        raise EarmarkdError(
            "subject is required"
        )

    return Earmark(
        subject=normalized_subject,
        source_digest=digest(
            source
        ),
        tags=normalize_terms(
            tags
        ),
        indices=normalize_terms(
            indices
        ),
        metadata=normalize_mapping(
            metadata
        ),
        semantic_lattice=(
            normalize_mapping(
                semantic_lattice
            )
        ),
        provenance=provenance,
        lineage=lineage,
        dependencies=normalize_terms(
            dependencies
        ),
    )


def from_scrible(
    atom_projection: Mapping[
        str,
        Any,
    ],
    *,
    indices: Sequence[Any] = (),
    metadata: Mapping[
        str,
        Any,
    ]
    | None = None,
    semantic_lattice: Mapping[
        str,
        Any,
    ]
    | None = None,
) -> Earmark:
    if not isinstance(
        atom_projection,
        Mapping,
    ):
        raise EarmarkdError(
            "atom_projection must be a mapping"
        )

    if (
        normalize_text(
            atom_projection.get(
                "prodigal"
            )
        )
        != "prodigal:scrible"
    ):
        raise EarmarkdError(
            "projection is not a Scrible atom"
        )

    subject = normalize_text(
        atom_projection.get(
            "subject"
        )
    )

    if not subject:
        raise EarmarkdError(
            "Scrible subject is required"
        )

    return earmark(
        subject=subject,
        source=atom_projection,
        tags=tuple(
            atom_projection.get(
                "tags"
            )
            or ()
        ),
        indices=indices,
        metadata=metadata,
        semantic_lattice=(
            semantic_lattice
        ),
        provenance=(
            atom_projection.get(
                "provenance"
            )
        ),
        lineage=(
            atom_projection.get(
                "lineage"
            )
        ),
        dependencies=tuple(
            atom_projection.get(
                "dependencies"
            )
            or ()
        ),
    )


def status() -> dict[str, Any]:
    payload = {
        "schema": (
            "savant://runtime/notary/"
            "prodigal/earmarkd/"
            "status/1.0.0"
        ),
        "owner": OWNER,
        "prodigal": PRODIGAL,
        "purpose": (
            "derive deterministic tags, "
            "indices, metadata, hashes, "
            "lattice metadata, and snapshots"
        ),
        "capabilities": [
            "tag-normalization",
            "index-normalization",
            "metadata-normalization",
            "immutable-hash-state",
            "semantic-lattice-metadata",
            "hash-pattern-reference",
            "entropy-snapshot-digest",
            "provenance-preservation",
            "lineage-preservation",
            "dependency-preservation",
            "scrible-composition",
        ],
        "verification_owner": OWNER,
        "can_verify": False,
        "can_admit_evidence": False,
        "can_attest": False,
        "can_mutate_canon": False,
        "can_mutate_ledger": False,
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

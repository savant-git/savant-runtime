#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


OWNER = "exile:notary"
PRODIGAL = "prodigal:scrible"

SCHEMA = (
    "savant://runtime/notary/"
    "prodigal/scrible/1.0.0"
)


class ScribleError(RuntimeError):
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
        raise ScribleError(
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
class ScribleAtom:
    subject: str
    material: Any
    provenance: Any
    lineage: Any
    dependencies: tuple[str, ...]
    tags: tuple[str, ...]
    metadata: Mapping[str, Any]
    complete: bool

    @property
    def material_digest(
        self,
    ) -> str:
        return digest(
            self.material
        )

    @property
    def atom_id(
        self,
    ) -> str:
        identity = {
            "subject": self.subject,
            "material_digest": (
                self.material_digest
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
            "tags": list(
                self.tags
            ),
            "metadata": dict(
                self.metadata
            ),
            "complete": self.complete,
        }

        return (
            "scrible-atom:"
            + digest(
                identity
            )[:32]
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "atom_id": self.atom_id,
            "subject": self.subject,
            "material": self.material,
            "material_digest": (
                self.material_digest
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
            "tags": list(
                self.tags
            ),
            "metadata": dict(
                self.metadata
            ),
            "complete": self.complete,
            "recordable": self.complete,
            "held_incomplete": (
                not self.complete
            ),
            "owner": OWNER,
            "prodigal": PRODIGAL,
            "structured_log_atom": True,
            "normalized": True,
            "archival_identity": True,
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


def shape_atom(
    *,
    subject: str,
    material: Any,
    provenance: Any = None,
    lineage: Any = None,
    dependencies: Sequence[Any] = (),
    tags: Sequence[Any] = (),
    metadata: Mapping[
        str,
        Any,
    ]
    | None = None,
    complete: bool | None = None,
) -> ScribleAtom:
    normalized_subject = (
        normalize_text(
            subject
        )
    )

    if not normalized_subject:
        raise ScribleError(
            "subject is required"
        )

    normalized_dependencies = (
        normalize_terms(
            dependencies
        )
    )

    normalized_tags = (
        normalize_terms(
            tags
        )
    )

    normalized_metadata = (
        normalize_mapping(
            metadata
        )
    )

    if complete is None:
        resolved_complete = (
            material is not None
        )
    else:
        resolved_complete = bool(
            complete
        )

    return ScribleAtom(
        subject=normalized_subject,
        material=material,
        provenance=provenance,
        lineage=lineage,
        dependencies=(
            normalized_dependencies
        ),
        tags=normalized_tags,
        metadata=normalized_metadata,
        complete=resolved_complete,
    )


def normalize_delta(
    delta: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    if not isinstance(
        delta,
        Mapping,
    ):
        raise ScribleError(
            "delta must be a mapping"
        )

    normalized = {
        str(key): delta[key]
        for key in sorted(
            delta,
            key=lambda item: str(
                item
            ),
        )
    }

    payload = {
        "schema": (
            "savant://runtime/notary/"
            "prodigal/scrible/delta/1.0.0"
        ),
        "delta": normalized,
        "normalized": True,
        "source_mutated": False,
        "authority_effect": "none",
    }

    payload["digest"] = digest(
        payload
    )

    return payload


def status() -> dict[str, Any]:
    payload = {
        "schema": (
            "savant://runtime/notary/"
            "prodigal/scrible/"
            "status/1.0.0"
        ),
        "owner": OWNER,
        "prodigal": PRODIGAL,
        "purpose": (
            "shape raw material into "
            "deterministic structured atoms"
        ),
        "capabilities": [
            "structured-log-atoms",
            "normalized-mutation-deltas",
            "incomplete-material-holding",
            "archival-identity",
            "dependency-preservation",
            "provenance-preservation",
            "lineage-preservation",
            "deterministic-projection",
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

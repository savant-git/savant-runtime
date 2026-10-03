#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from runtime.translucent.blot_projection_session import (
    ProjectionSessionResult,
)


name = "blot."
schema = "savant.translucent.blot.projection-handoff.v1"
authority_effect = "none"
mutation_effect = "none"
projection_only = True

source_owner = "blot."
destination_owner = "consumer"


class BlotProjectionHandoffError(ValueError):
    pass


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise BlotProjectionHandoffError(
            "value is not canonical-json compatible"
        ) from exc


def _digest(value: Any) -> str:
    if isinstance(value, bytes):
        raw = value
    elif isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = _canonical(value).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def _text(
    value: Any,
    field_name: str,
) -> str:
    result = str(value or "").strip()

    if not result:
        raise BlotProjectionHandoffError(
            f"{field_name} is required"
        )

    return result


def _unique(
    values: Iterable[Any],
) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        token = str(value or "").strip()

        if not token or token in seen:
            continue

        seen.add(token)
        result.append(token)

    return tuple(result)


def _normalized(
    value: Any,
    field_name: str,
) -> dict[str, Any]:
    if hasattr(value, "normalized"):
        result = value.normalized()
    elif isinstance(value, Mapping):
        result = dict(value)
    else:
        raise BlotProjectionHandoffError(
            f"{field_name} must provide normalized() "
            "or be a mapping"
        )

    if not isinstance(result, Mapping):
        raise BlotProjectionHandoffError(
            f"{field_name}.normalized() must return a mapping"
        )

    return dict(result)


@dataclass(frozen=True)
class ProjectionReference:
    projection_id: str
    profile_id: str
    projection_digest: str
    lock_digest: str
    entry_digest: str

    def normalized(self) -> dict[str, Any]:
        body = {
            "projection_id":
                _text(
                    self.projection_id,
                    "projection_id",
                ),

            "profile_id":
                _text(
                    self.profile_id,
                    "profile_id",
                ),

            "projection_digest":
                _text(
                    self.projection_digest,
                    "projection_digest",
                ),

            "lock_digest":
                _text(
                    self.lock_digest,
                    "lock_digest",
                ),

            "entry_digest":
                _text(
                    self.entry_digest,
                    "entry_digest",
                ),
        }

        return {
            **body,
            "digest":
                _digest(body),
        }


@dataclass(frozen=True)
class ProjectionHandoff:
    source_digest: str
    construction_digest: str
    execution_digest: str
    projection_set_digest: str
    projections: tuple[ProjectionReference, ...]
    lineage: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        projections = tuple(
            item.normalized()
            for item in self.projections
        )

        if not projections:
            raise BlotProjectionHandoffError(
                "handoff requires at least one projection"
            )

        projection_ids = [
            item[
                "projection_id"
            ]
            for item in projections
        ]

        if len(
            projection_ids
        ) != len(
            set(
                projection_ids
            )
        ):
            raise BlotProjectionHandoffError(
                "handoff contains duplicate projection ids"
            )

        profile_ids = [
            item[
                "profile_id"
            ]
            for item in projections
        ]

        if len(
            profile_ids
        ) != len(
            set(
                profile_ids
            )
        ):
            raise BlotProjectionHandoffError(
                "handoff contains duplicate projection profiles"
            )

        body = {
            "schema":
                schema,

            "name":
                name,

            "source_digest":
                _text(
                    self.source_digest,
                    "source_digest",
                ),

            "construction_digest":
                _text(
                    self.construction_digest,
                    "construction_digest",
                ),

            "execution_digest":
                _text(
                    self.execution_digest,
                    "execution_digest",
                ),

            "projection_set_digest":
                _text(
                    self.projection_set_digest,
                    "projection_set_digest",
                ),

            "projections":
                list(
                    projections
                ),

            "lineage":
                list(
                    _unique(
                        self.lineage
                    )
                ),

            "provenance":
                list(
                    _unique(
                        self.provenance
                    )
                ),

            "authority_effect":
                authority_effect,

            "mutation_effect":
                mutation_effect,

            "projection_only":
                projection_only,

            "source_owner":
                source_owner,

            "destination_owner":
                destination_owner,

            "projection_is_authority":
                False,

            "handoff_is_authority":
                False,

            "canonical_source":
                "construction-graph",
        }

        return {
            **body,
            "digest":
                _digest(body),
        }


def from_session(
    session: ProjectionSessionResult
    | Mapping[str, Any],
    *,
    require_complete: bool = True,
    lineage: Iterable[str] = (),
    provenance: Iterable[str] = (),
) -> ProjectionHandoff:
    session_data = _normalized(
        session,
        "session",
    )

    receipt = session_data.get(
        "receipt"
    )

    if not isinstance(
        receipt,
        Mapping,
    ):
        raise BlotProjectionHandoffError(
            "session receipt is required"
        )

    projection_set = session_data.get(
        "projection_set"
    )

    if not isinstance(
        projection_set,
        Mapping,
    ):
        raise BlotProjectionHandoffError(
            "session projection set is required"
        )

    if (
        require_complete
        and not bool(
            projection_set.get(
                "complete",
                False,
            )
        )
    ):
        raise BlotProjectionHandoffError(
            "complete projection set is required"
        )

    source_digest = _text(
        projection_set.get(
            "source_digest"
        ),
        "source_digest",
    )

    construction_digest = _text(
        projection_set.get(
            "construction_digest"
        ),
        "construction_digest",
    )

    execution_digest = _text(
        projection_set.get(
            "execution_digest"
        ),
        "execution_digest",
    )

    receipt_source = _text(
        receipt.get(
            "source_digest"
        ),
        "receipt.source_digest",
    )

    receipt_construction = _text(
        receipt.get(
            "construction_digest"
        ),
        "receipt.construction_digest",
    )

    receipt_execution = _text(
        receipt.get(
            "execution_digest"
        ),
        "receipt.execution_digest",
    )

    if receipt_source != source_digest:
        raise BlotProjectionHandoffError(
            "session source digest mismatch"
        )

    if (
        receipt_construction
        != construction_digest
    ):
        raise BlotProjectionHandoffError(
            "session construction digest mismatch"
        )

    if (
        receipt_execution
        != execution_digest
    ):
        raise BlotProjectionHandoffError(
            "session execution digest mismatch"
        )

    projection_set_digest = _text(
        projection_set.get(
            "digest"
        )
        or _digest(
            projection_set
        ),
        "projection_set_digest",
    )

    receipt_set_digest = receipt.get(
        "projection_set_digest"
    )

    if (
        receipt_set_digest is not None
        and receipt_set_digest
        != projection_set_digest
    ):
        raise BlotProjectionHandoffError(
            "session projection set digest mismatch"
        )

    entries = projection_set.get(
        "entries"
    )

    if not isinstance(
        entries,
        (
            list,
            tuple,
        ),
    ):
        raise BlotProjectionHandoffError(
            "projection set entries must be a sequence"
        )

    projections: list[
        ProjectionReference
    ] = []

    for entry in entries:
        if not isinstance(
            entry,
            Mapping,
        ):
            raise BlotProjectionHandoffError(
                "projection set entry must be a mapping"
            )

        reference = ProjectionReference(
            projection_id=
                _text(
                    entry.get(
                        "projection_id"
                    ),
                    "projection_id",
                ),

            profile_id=
                _text(
                    entry.get(
                        "profile_id"
                    ),
                    "profile_id",
                ),

            projection_digest=
                _text(
                    entry.get(
                        "projection_digest"
                    ),
                    "projection_digest",
                ),

            lock_digest=
                _text(
                    entry.get(
                        "lock_digest"
                    ),
                    "lock_digest",
                ),

            entry_digest=
                _text(
                    entry.get(
                        "entry_digest"
                    )
                    or entry.get(
                        "digest"
                    )
                    or _digest(
                        entry
                    ),
                    "entry_digest",
                ),
        )

        reference.normalized()

        projections.append(
            reference
        )

    result = ProjectionHandoff(
        source_digest=
            source_digest,

        construction_digest=
            construction_digest,

        execution_digest=
            execution_digest,

        projection_set_digest=
            projection_set_digest,

        projections=
            tuple(
                projections
            ),

        lineage=
            tuple(
                lineage
            ),

        provenance=
            tuple(
                provenance
            ),
    )

    result.normalized()

    return result


def manifest() -> dict[str, Any]:
    body = {
        "schema":
            schema,

        "name":
            name,

        "authority_effect":
            authority_effect,

        "mutation_effect":
            mutation_effect,

        "projection_only":
            projection_only,

        "source_owner":
            source_owner,

        "destination_owner":
            destination_owner,

        "input":
            "finalized-projection-session",

        "output":
            "typed-projection-reference-handoff",

        "transfers":
            [
                "projection-identity",
                "profile-identity",
                "projection-digest",
                "lock-digest",
                "entry-digest",
                "construction-lineage",
                "provenance",
            ],

        "does_not_transfer":
            [
                "authority",
                "canonical-substance-ownership",
                "construction-mutation-rights",
            ],

        "canonical_source":
            "construction-graph",

        "projection_is_authority":
            False,

        "handoff_is_authority":
            False,

        "creates_authority":
            False,
    }

    return {
        **body,
        "digest":
            _digest(body),
    }


__all__ = [
    "BlotProjectionHandoffError",
    "ProjectionHandoff",
    "ProjectionReference",
    "authority_effect",
    "destination_owner",
    "from_session",
    "manifest",
    "mutation_effect",
    "name",
    "projection_only",
    "schema",
    "source_owner",
]


if __name__ == "__main__":
    print(
        json.dumps(
            manifest(),
            indent=2,
            sort_keys=True,
        )
    )

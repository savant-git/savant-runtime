#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from runtime.translucent.blot_projection_finalize import (
    FinalizationResult,
)
from runtime.translucent.blot_projection_registry import (
    ProjectionEntry,
)


name = "blot."
schema = "savant.translucent.blot.projection-set.v1"
authority_effect = "none"
mutation_effect = "none"
projection_only = True

canonical_profiles = (
    "presentation",
    "standard",
    "flat",
    "monochrome",
    "micro",
)


class BlotProjectionSetError(ValueError):
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
        raise BlotProjectionSetError(
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
        raise BlotProjectionSetError(
            f"{field_name} is required"
        )

    return result


def _normalized(
    value: Any,
    field_name: str,
) -> dict[str, Any]:
    if hasattr(value, "normalized"):
        result = value.normalized()
    elif isinstance(value, Mapping):
        result = dict(value)
    else:
        raise BlotProjectionSetError(
            f"{field_name} must provide normalized() "
            "or be a mapping"
        )

    if not isinstance(result, Mapping):
        raise BlotProjectionSetError(
            f"{field_name}.normalized() must return a mapping"
        )

    return dict(result)


@dataclass(frozen=True)
class ProjectionSetEntry:
    profile_id: str
    projection_id: str
    projection_digest: str
    lock_digest: str
    entry_digest: str

    def normalized(self) -> dict[str, Any]:
        body = {
            "profile_id":
                _text(
                    self.profile_id,
                    "profile_id",
                ),

            "projection_id":
                _text(
                    self.projection_id,
                    "projection_id",
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
class ProjectionSet:
    source_digest: str
    construction_digest: str
    execution_digest: str
    entries: tuple[
        ProjectionSetEntry,
        ...
    ]
    complete: bool

    def normalized(self) -> dict[str, Any]:
        entries = tuple(
            item.normalized()
            for item in self.entries
        )

        profile_ids = [
            item["profile_id"]
            for item in entries
        ]

        if len(profile_ids) != len(
            set(profile_ids)
        ):
            raise BlotProjectionSetError(
                "projection set contains duplicate profiles"
            )

        required = set(
            canonical_profiles
        )

        observed = set(
            profile_ids
        )

        computed_complete = (
            required
            <= observed
        )

        if bool(self.complete) != computed_complete:
            raise BlotProjectionSetError(
                "projection set completeness does "
                "not match contained profiles"
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

            "entries":
                list(entries),

            "required_profiles":
                list(
                    canonical_profiles
                ),

            "complete":
                computed_complete,

            "authority_effect":
                authority_effect,

            "mutation_effect":
                mutation_effect,

            "projection_only":
                projection_only,

            "projection_is_authority":
                False,

            "canonical_source":
                "construction-graph",
        }

        return {
            **body,
            "digest":
                _digest(body),
        }


class ProjectionSetBuilder:
    def __init__(
        self,
        *,
        source_digest: str,
        construction_digest: str,
        execution_digest: str,
    ) -> None:
        self.source_digest = _text(
            source_digest,
            "source_digest",
        )

        self.construction_digest = _text(
            construction_digest,
            "construction_digest",
        )

        self.execution_digest = _text(
            execution_digest,
            "execution_digest",
        )

        self._entries: dict[
            str,
            ProjectionSetEntry,
        ] = {}

    def add_entry(
        self,
        entry: ProjectionEntry
        | Mapping[str, Any],
    ) -> ProjectionSetEntry:
        data = _normalized(
            entry,
            "entry",
        )

        if (
            data.get(
                "source_digest"
            )
            != self.source_digest
        ):
            raise BlotProjectionSetError(
                "projection source digest mismatch"
            )

        if (
            data.get(
                "construction_digest"
            )
            != self.construction_digest
        ):
            raise BlotProjectionSetError(
                "projection construction digest mismatch"
            )

        if (
            data.get(
                "execution_digest"
            )
            != self.execution_digest
        ):
            raise BlotProjectionSetError(
                "projection execution digest mismatch"
            )

        profile_id = _text(
            data.get(
                "profile_id"
            ),
            "profile_id",
        )

        result = ProjectionSetEntry(
            profile_id=
                profile_id,

            projection_id=
                _text(
                    data.get(
                        "projection_id"
                    ),
                    "projection_id",
                ),

            projection_digest=
                _text(
                    data.get(
                        "projection_digest"
                    ),
                    "projection_digest",
                ),

            lock_digest=
                _text(
                    data.get(
                        "lock_digest"
                    ),
                    "lock_digest",
                ),

            entry_digest=
                _text(
                    data.get(
                        "digest"
                    )
                    or _digest(data),
                    "entry_digest",
                ),
        )

        normalized = (
            result.normalized()
        )

        existing = self._entries.get(
            profile_id
        )

        if existing is not None:
            if (
                existing.normalized()[
                    "digest"
                ]
                != normalized[
                    "digest"
                ]
            ):
                raise BlotProjectionSetError(
                    "projection profile identity conflict"
                )

            return existing

        self._entries[
            profile_id
        ] = result

        return result

    def add_finalization(
        self,
        result: FinalizationResult
        | Mapping[str, Any],
    ) -> ProjectionSetEntry:
        data = _normalized(
            result,
            "finalization",
        )

        if not data.get(
            "finalized",
            False,
        ):
            raise BlotProjectionSetError(
                "cannot add an unfinished projection"
            )

        entry = data.get(
            "projection_entry"
        )

        if not isinstance(
            entry,
            Mapping,
        ):
            raise BlotProjectionSetError(
                "finalization has no projection entry"
            )

        return self.add_entry(
            entry
        )

    def entries(
        self,
    ) -> tuple[
        ProjectionSetEntry,
        ...
    ]:
        return tuple(
            self._entries[key]
            for key in sorted(
                self._entries
            )
        )

    def build(
        self,
    ) -> ProjectionSet:
        entries = self.entries()

        observed = {
            item.profile_id
            for item in entries
        }

        complete = (
            set(
                canonical_profiles
            )
            <= observed
        )

        result = ProjectionSet(
            source_digest=
                self.source_digest,

            construction_digest=
                self.construction_digest,

            execution_digest=
                self.execution_digest,

            entries=
                entries,

            complete=
                complete,
        )

        result.normalized()

        return result


def projection_set(
    results: Iterable[
        FinalizationResult
        | Mapping[str, Any]
    ],
) -> ProjectionSet:
    materialized = tuple(
        results
    )

    if not materialized:
        raise BlotProjectionSetError(
            "at least one finalization result is required"
        )

    first = _normalized(
        materialized[0],
        "finalization",
    )

    verification = first.get(
        "verification"
    )

    if not isinstance(
        verification,
        Mapping,
    ):
        raise BlotProjectionSetError(
            "finalization verification is required"
        )

    builder = ProjectionSetBuilder(
        source_digest=
            _text(
                verification.get(
                    "source_digest"
                ),
                "source_digest",
            ),

        construction_digest=
            _text(
                verification.get(
                    "construction_digest"
                ),
                "construction_digest",
            ),

        execution_digest=
            _text(
                verification.get(
                    "execution_digest"
                ),
                "execution_digest",
            ),
    )

    for result in materialized:
        builder.add_finalization(
            result
        )

    return builder.build()


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

        "required_profiles":
            list(
                canonical_profiles
            ),

        "canonical_source":
            "construction-graph",

        "projection_is_authority":
            False,

        "set_is_authority":
            False,

        "shared_construction_required":
            True,

        "shared_execution_required":
            True,

        "profile_specific_projection":
            True,
    }

    return {
        **body,
        "digest":
            _digest(body),
    }


__all__ = [
    "BlotProjectionSetError",
    "ProjectionSet",
    "ProjectionSetBuilder",
    "ProjectionSetEntry",
    "authority_effect",
    "canonical_profiles",
    "manifest",
    "mutation_effect",
    "name",
    "projection_only",
    "projection_set",
    "schema",
]


if __name__ == "__main__":
    print(
        json.dumps(
            manifest(),
            indent=2,
            sort_keys=True,
        )
    )

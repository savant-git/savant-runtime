#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from .dependency import StraubDependencyIndex
from .model import (
    StraubValidationError,
    content_digest,
)


schema = "savant.straub.materialized.v1"
owner = "savant"
authority_effect = "none"


def _authority_key(
    value: Any,
) -> str:
    return content_digest(
        value
    )


def _sorted_map(
    value: Mapping[
        str,
        set[str],
    ],
) -> dict[str, list[str]]:
    return {
        key:
            sorted(
                values
            )
        for key, values
        in sorted(
            value.items()
        )
    }


class StraubIsotopeIndex:
    def __init__(
        self,
        capsule: Mapping[str, Any],
    ) -> None:
        if not isinstance(
            capsule,
            Mapping,
        ):
            raise StraubValidationError(
                "isotope index requires "
                "straub capsule"
            )

        if (
            capsule.get(
                "schema"
            )
            != "savant.straub.capsule.v2"
        ):
            raise StraubValidationError(
                "isotope index requires "
                "capsule v2"
            )

        self._capsule = deepcopy(
            dict(
                capsule
            )
        )

        self._source_digest = str(
            capsule.get(
                "digest"
            )
            or ""
        )

        if not self._source_digest:
            raise StraubValidationError(
                "capsule digest missing"
            )

        self._by_kind: dict[
            str,
            set[str],
        ] = {}

        self._by_authority: dict[
            str,
            set[str],
        ] = {}

        self._by_dependency: dict[
            str,
            set[str],
        ] = {}

        self._by_metadata_definition: dict[
            str,
            set[str],
        ] = {}

        self._by_relation: dict[
            str,
            set[str],
        ] = {}

        self._record_digests: dict[
            str,
            str,
        ] = {}

        self._build()

    def _build(
        self,
    ) -> None:
        instances = self._capsule.get(
            "instances"
        )

        membranes = self._capsule.get(
            "membranes"
        )

        if not isinstance(
            instances,
            list,
        ):
            raise StraubValidationError(
                "capsule instances invalid"
            )

        if not isinstance(
            membranes,
            list,
        ):
            raise StraubValidationError(
                "capsule membranes invalid"
            )

        instance_map: dict[
            str,
            dict[str, Any],
        ] = {}

        for raw in instances:
            if not isinstance(
                raw,
                Mapping,
            ):
                raise StraubValidationError(
                    "capsule instance invalid"
                )

            record = deepcopy(
                dict(
                    raw
                )
            )

            record_id = str(
                record.get(
                    "id"
                )
                or ""
            ).strip()

            if not record_id:
                raise StraubValidationError(
                    "indexed instance id missing"
                )

            instance_map[
                record_id
            ] = record

            kind = str(
                record.get(
                    "kind"
                )
                or "unknown"
            )

            self._by_kind.setdefault(
                kind,
                set(),
            ).add(
                record_id
            )

            authority_key = (
                _authority_key(
                    record.get(
                        "authority"
                    )
                )
            )

            self._by_authority.setdefault(
                authority_key,
                set(),
            ).add(
                record_id
            )

            for dependency in (
                record.get(
                    "dependencies"
                )
                or []
            ):
                dependency_id = str(
                    dependency
                    or ""
                ).strip()

                if dependency_id:
                    self._by_dependency.setdefault(
                        dependency_id,
                        set(),
                    ).add(
                        record_id
                    )

            self._record_digests[
                record_id
            ] = str(
                record.get(
                    "digest"
                )
                or ""
            )

        for raw in membranes:
            if not isinstance(
                raw,
                Mapping,
            ):
                raise StraubValidationError(
                    "capsule membrane invalid"
                )

            membrane_id = str(
                raw.get(
                    "id"
                )
                or ""
            ).strip()

            relation = str(
                raw.get(
                    "relation"
                )
                or ""
            ).strip()

            source = str(
                raw.get(
                    "from"
                )
                or ""
            ).strip()

            target = str(
                raw.get(
                    "to"
                )
                or ""
            ).strip()

            if not membrane_id:
                raise StraubValidationError(
                    "indexed membrane id missing"
                )

            self._record_digests[
                membrane_id
            ] = str(
                raw.get(
                    "digest"
                )
                or ""
            )

            if relation:
                self._by_relation.setdefault(
                    relation,
                    set(),
                ).add(
                    membrane_id
                )

            for dependency in (
                raw.get(
                    "dependencies"
                )
                or []
            ):
                dependency_id = str(
                    dependency
                    or ""
                ).strip()

                if dependency_id:
                    self._by_dependency.setdefault(
                        dependency_id,
                        set(),
                    ).add(
                        membrane_id
                    )

            if source:
                self._by_dependency.setdefault(
                    source,
                    set(),
                ).add(
                    membrane_id
                )

            if target:
                self._by_dependency.setdefault(
                    target,
                    set(),
                ).add(
                    membrane_id
                )

            target_record = (
                instance_map.get(
                    target
                )
            )

            if not isinstance(
                target_record,
                Mapping,
            ):
                continue

            if (
                target_record.get(
                    "kind"
                )
                != "umbra.value"
            ):
                continue

            payload = target_record.get(
                "payload"
            )

            if not isinstance(
                payload,
                Mapping,
            ):
                continue

            definition = str(
                payload.get(
                    "definition"
                )
                or ""
            ).strip()

            if (
                definition
                and source
            ):
                self._by_metadata_definition.setdefault(
                    definition,
                    set(),
                ).add(
                    source
                )

    @property
    def source_digest(
        self,
    ) -> str:
        return self._source_digest

    def materialize(
        self,
    ) -> dict[str, Any]:
        projection = {
            "schema":
                "savant.straub."
                "materialized-isotope.v1",
            "kind":
                "isotope",
            "source_capsule_digest":
                self._source_digest,
            "indexes": {
                "by_kind":
                    _sorted_map(
                        self._by_kind
                    ),
                "by_authority":
                    _sorted_map(
                        self._by_authority
                    ),
                "by_dependency":
                    _sorted_map(
                        self._by_dependency
                    ),
                "by_metadata_definition":
                    _sorted_map(
                        self._by_metadata_definition
                    ),
                "by_relation":
                    _sorted_map(
                        self._by_relation
                    ),
                "record_digests":
                    dict(
                        sorted(
                            self._record_digests.items()
                        )
                    ),
            },
            "rebuildable":
                True,
            "projection_only":
                True,
            "authority_effect":
                "none",
        }

        projection[
            "digest"
        ] = content_digest(
            projection
        )

        return projection

    def candidates(
        self,
        *,
        kind: str | None = None,
        authority: Any = None,
        authority_filter_enabled: bool = False,
        dependency: str | None = None,
        metadata_definition: str | None = None,
    ) -> dict[str, Any]:
        sets: list[
            set[str]
        ] = []

        if kind is not None:
            sets.append(
                set(
                    self._by_kind.get(
                        kind,
                        set(),
                    )
                )
            )

        if authority_filter_enabled:
            authority_key = (
                _authority_key(
                    authority
                )
            )

            sets.append(
                set(
                    self._by_authority.get(
                        authority_key,
                        set(),
                    )
                )
            )

        if dependency is not None:
            sets.append(
                set(
                    self._by_dependency.get(
                        dependency,
                        set(),
                    )
                )
            )

        if metadata_definition is not None:
            sets.append(
                set(
                    self._by_metadata_definition.get(
                        metadata_definition,
                        set(),
                    )
                )
            )

        if not sets:
            candidate_ids = set(
                self._record_digests
            )

        else:
            candidate_ids = sets[
                0
            ]

            for candidate_set in sets[
                1:
            ]:
                candidate_ids = (
                    candidate_ids
                    & candidate_set
                )

        result = {
            "schema":
                "savant.straub."
                "index-candidates-isotope.v1",
            "kind":
                "isotope",
            "source_capsule_digest":
                self._source_digest,
            "candidate_count":
                len(
                    candidate_ids
                ),
            "candidates":
                sorted(
                    candidate_ids
                ),
            "projection_only":
                True,
            "authority_effect":
                "none",
        }

        result[
            "digest"
        ] = content_digest(
            result
        )

        return result

    def invalidation(
        self,
        changed_ids: list[str],
    ) -> dict[str, Any]:
        dependency = (
            StraubDependencyIndex(
                self._capsule
            )
        )

        closure = dependency.invalidation(
            changed_ids
        )

        invalid_ids = sorted(
            set(
                closure[
                    "changed"
                ]
            )
            | set(
                closure[
                    "affected"
                ]
            )
        )

        projection = {
            "schema":
                "savant.straub."
                "materialized-invalidation-isotope.v1",
            "kind":
                "isotope",
            "source_capsule_digest":
                self._source_digest,
            "changed":
                deepcopy(
                    closure[
                        "changed"
                    ]
                ),
            "affected":
                deepcopy(
                    closure[
                        "affected"
                    ]
                ),
            "invalidate_records":
                invalid_ids,
            "rebuild_required":
                bool(
                    invalid_ids
                ),
            "mutation_performed":
                False,
            "projection_only":
                True,
            "authority_effect":
                "none",
        }

        projection[
            "digest"
        ] = content_digest(
            projection
        )

        return projection


def validate_materialized(
    projection: Mapping[str, Any],
    *,
    capsule_digest: str,
) -> dict[str, Any]:
    if (
        projection.get(
            "schema"
        )
        != "savant.straub."
        "materialized-isotope.v1"
    ):
        raise StraubValidationError(
            "unsupported materialized isotope"
        )

    supplied_digest = str(
        projection.get(
            "digest"
        )
        or ""
    )

    unsigned = deepcopy(
        dict(
            projection
        )
    )

    unsigned.pop(
        "digest",
        None,
    )

    if (
        supplied_digest
        != content_digest(
            unsigned
        )
    ):
        raise StraubValidationError(
            "materialized isotope "
            "digest mismatch"
        )

    source_digest = str(
        projection.get(
            "source_capsule_digest"
        )
        or ""
    )

    fresh = (
        source_digest
        == capsule_digest
    )

    return {
        "schema":
            schema,
        "valid":
            True,
        "fresh":
            fresh,
        "source_capsule_digest":
            source_digest,
        "current_capsule_digest":
            capsule_digest,
        "rebuild_required":
            not fresh,
        "authority_effect":
            authority_effect,
    }


class AtomicIsotopeCache:
    durable = True
    authoritative = False
    projection_only = True

    def __init__(
        self,
        path: str | Path,
    ) -> None:
        self.path = Path(
            path
        ).resolve()

    def save(
        self,
        projection: Mapping[str, Any],
    ) -> None:
        source_digest = str(
            projection.get(
                "source_capsule_digest"
            )
            or ""
        )

        validate_materialized(
            projection,
            capsule_digest=(
                source_digest
            ),
        )

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        os.chmod(
            self.path.parent,
            0o700,
        )

        fd, temporary_name = (
            tempfile.mkstemp(
                prefix=(
                    "."
                    + self.path.name
                    + "."
                ),
                suffix=".tmp",
                dir=str(
                    self.path.parent
                ),
                text=True,
            )
        )

        temporary_path = Path(
            temporary_name
        )

        try:
            os.fchmod(
                fd,
                0o600,
            )

            with os.fdopen(
                fd,
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    dict(
                        projection
                    ),
                    handle,
                    sort_keys=True,
                    separators=(
                        ",",
                        ":",
                    ),
                    ensure_ascii=False,
                )

                handle.write(
                    "\n"
                )

                handle.flush()

                os.fsync(
                    handle.fileno()
                )

            os.replace(
                temporary_path,
                self.path,
            )

            os.chmod(
                self.path,
                0o600,
            )

            directory_fd = os.open(
                str(
                    self.path.parent
                ),
                os.O_RDONLY,
            )

            try:
                os.fsync(
                    directory_fd
                )
            finally:
                os.close(
                    directory_fd
                )

        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    def load(
        self,
        *,
        capsule_digest: str,
    ) -> dict[str, Any] | None:
        try:
            raw = self.path.read_text(
                encoding="utf-8"
            )
        except FileNotFoundError:
            return None

        try:
            projection = json.loads(
                raw
            )
        except json.JSONDecodeError as exc:
            raise StraubValidationError(
                "materialized isotope cache "
                "is invalid json"
            ) from exc

        status = validate_materialized(
            projection,
            capsule_digest=(
                capsule_digest
            ),
        )

        return {
            "projection":
                projection,
            "status":
                status,
        }

    def rebuild(
        self,
        capsule: Mapping[str, Any],
    ) -> dict[str, Any]:
        projection = (
            StraubIsotopeIndex(
                capsule
            ).materialize()
        )

        self.save(
            projection
        )

        return projection

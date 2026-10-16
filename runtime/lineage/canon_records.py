#!/usr/bin/env python3
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

from .model import (
    VALID_CONTINUATIONS,
    LineageValidationError,
    stable_binding_id,
    stable_hash,
)
from .registry import LineageRoleRegistry


class CanonRecordError(LineageValidationError):
    """Raised when canon authority cannot be projected safely."""


_PARENT_ID_KEYS = (
    "id",
    "parent",
    "source",
    "target",
    "ref",
)

_TARGET_ID_KEYS = (
    "target",
    "to",
    "id",
    "ref",
    "child",
    "parent",
)

_PARENT_FIRST_RELATIONSHIPS = {
    "contains": (
        "composition",
        "neutral",
    ),
    "composition": (
        "composition",
        "neutral",
    ),
    "composes": (
        "composition",
        "neutral",
    ),
    "owns": (
        "ownership",
        "neutral",
    ),
    "owner_of": (
        "ownership",
        "neutral",
    ),
    "parent_of": (
        "generic",
        "neutral",
    ),
    "classifies": (
        "classification",
        "preserving",
    ),
    "includes": (
        "membership",
        "preserving",
    ),
    "precedes": (
        "sequence",
        "neutral",
    ),
    "projects": (
        "projection",
        "projecting",
    ),
    "exposes": (
        "exposure",
        "projecting",
    ),
}

_TARGET_FIRST_RELATIONSHIPS = {
    "child_of": (
        "generic",
        "neutral",
    ),
    "member_of": (
        "membership",
        "preserving",
    ),
    "classified_by": (
        "classification",
        "preserving",
    ),
    "depends_on": (
        "dependency",
        "neutral",
    ),
    "requires": (
        "dependency",
        "neutral",
    ),
    "derived_from": (
        "source",
        "neutral",
    ),
    "source": (
        "source",
        "neutral",
    ),
    "inherits": (
        "pattern",
        "preserving",
    ),
    "extends": (
        "pattern",
        "preserving",
    ),
    "implements": (
        "implementation",
        "projecting",
    ),
    "supersedes": (
        "supersession",
        "transforming",
    ),
    "attached_to": (
        "attachment",
        "neutral",
    ),
    "view_of": (
        "projection",
        "projecting",
    ),
}


def _as_mapping(
    value: Any,
) -> dict[str, Any]:
    if isinstance(
        value,
        Mapping,
    ):
        return deepcopy(
            dict(value)
        )

    return {}


def _sequence(
    value: Any,
) -> list[Any]:
    if value is None:
        return []

    if isinstance(
        value,
        list,
    ):
        return value

    if isinstance(
        value,
        tuple,
    ):
        return list(
            value
        )

    return [
        value
    ]


def _first_identifier(
    value: Mapping[
        str,
        Any,
    ],
    keys: Sequence[str],
) -> str:
    for key in keys:
        candidate = value.get(
            key
        )

        if (
            isinstance(
                candidate,
                str,
            )
            and candidate.strip()
        ):
            return candidate.strip()

    return ""


def reference_identifier(
    value: Any,
) -> str:
    if isinstance(
        value,
        str,
    ):
        return value.strip()

    if isinstance(
        value,
        Mapping,
    ):
        return _first_identifier(
            value,
            _TARGET_ID_KEYS,
        )

    return ""


def _source_provenance(
    record: Mapping[
        str,
        Any,
    ],
    source_path: Path | str | None,
    source_field: str,
) -> dict[str, Any]:
    provenance = _as_mapping(
        record.get(
            "provenance"
        )
    )

    provenance.setdefault(
        "created_by",
        "canon_system",
    )

    provenance[
        "source_record_id"
    ] = str(
        record.get(
            "id",
            "",
        )
    )

    provenance[
        "source_field"
    ] = source_field

    if source_path is not None:
        source = str(
            source_path
        )

        sources = provenance.get(
            "source_files",
            [],
        )

        if isinstance(
            sources,
            str,
        ):
            sources = [
                sources
            ]

        elif not isinstance(
            sources,
            list,
        ):
            sources = []

        if source not in sources:
            sources.append(
                source
            )

        provenance[
            "source_files"
        ] = sources

    return provenance


def _binding_metadata(
    record: Mapping[
        str,
        Any,
    ],
    source_path: Path | str | None,
    source_field: str,
    extra: Mapping[
        str,
        Any,
    ] | None = None,
) -> dict[str, Any]:
    metadata: dict[
        str,
        Any,
    ] = {
        "adapter": (
            "canon_record_compiler"
        ),
        "source_record_id": str(
            record.get(
                "id",
                "",
            )
        ),
        "source_field": (
            source_field
        ),
    }

    if source_path is not None:
        metadata[
            "source_path"
        ] = str(
            source_path
        )

    if extra:
        metadata.update(
            deepcopy(
                dict(extra)
            )
        )

    return metadata


class CanonRecordCompiler:
    def __init__(
        self,
        registry: LineageRoleRegistry,
    ) -> None:
        self.registry = registry

    def _canonical_role(
        self,
        role: Any,
    ) -> str:
        raw = str(
            role
            or "generic"
        ).strip() or "generic"

        return (
            self.registry
            .canonical_name(
                raw
            )
        )

    def _binding(
        self,
        *,
        record: Mapping[
            str,
            Any,
        ],
        parent: str,
        child: str,
        role: str,
        continuation: str = (
            "neutral"
        ),
        scope: str = "canon",
        order: int = 0,
        status: str = "active",
        authority: Any = (
            "FOUNDATION-008"
        ),
        version: Any = "1.0.0",
        inheritance: Mapping[
            str,
            Any,
        ] | None = None,
        propagation: Mapping[
            str,
            Any,
        ] | None = None,
        validity: Mapping[
            str,
            Any,
        ] | None = None,
        provenance: Mapping[
            str,
            Any,
        ] | None = None,
        metadata: Mapping[
            str,
            Any,
        ] | None = None,
        extensions: Mapping[
            str,
            Any,
        ] | None = None,
        future_extensions: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> dict[str, Any]:
        parent_id = str(
            parent
        ).strip()

        child_id = str(
            child
        ).strip()

        if (
            not parent_id
            or not child_id
        ):
            raise CanonRecordError(
                "canon lineage binding "
                "requires parent and child"
            )

        if parent_id == child_id:
            raise CanonRecordError(
                "canon record may not "
                f"parent itself: {parent_id}"
            )

        canonical_role = (
            self._canonical_role(
                role
            )
        )

        role_definition = (
            self.registry.get(
                canonical_role
            )
        )

        continuation_value = str(
            continuation
            or "neutral"
        ).strip()

        if (
            continuation_value
            not in VALID_CONTINUATIONS
        ):
            raise CanonRecordError(
                "unsupported continuation "
                f"mode: {continuation_value}"
            )

        if (
            isinstance(
                order,
                bool,
            )
            or not isinstance(
                order,
                int,
            )
        ):
            raise CanonRecordError(
                "canon lineage order "
                "must be an integer"
            )

        scope_value = str(
            scope
            or "canon"
        ).strip() or "canon"

        binding = {
            "id": stable_binding_id(
                parent_id,
                child_id,
                canonical_role,
                scope_value,
                order,
            ),
            "kind": "segue",
            "type": "lineage",
            "status": str(
                status
                or "active"
            ),
            "authority": deepcopy(
                authority
            ),
            "version": str(
                version
                or "1.0.0"
            ),
            "parent": parent_id,
            "child": child_id,
            "role": canonical_role,
            "axis": (
                role_definition.axis
            ),
            "continuation": (
                continuation_value
            ),
            "scope": scope_value,
            "order": order,
            "inheritance": deepcopy(
                dict(
                    inheritance
                    or role_definition
                    .default_inheritance
                )
            ),
            "propagation": deepcopy(
                dict(
                    propagation
                    or {
                        "enabled": (
                            role_definition
                            .propagates_changes
                        ),
                        "channels": [
                            "validation",
                            "projection",
                            "regeneration",
                        ],
                    }
                )
            ),
            "validity": deepcopy(
                dict(
                    validity
                    or {}
                )
            ),
            "provenance": deepcopy(
                dict(
                    provenance
                    or {}
                )
            ),
            "metadata": deepcopy(
                dict(
                    metadata
                    or {}
                )
            ),
            "extensions": deepcopy(
                dict(
                    extensions
                    or {}
                )
            ),
            "future_extensions": (
                deepcopy(
                    dict(
                        future_extensions
                        or {}
                    )
                )
            ),
        }

        binding[
            "metadata"
        ].setdefault(
            "source_record_id",
            str(
                record.get(
                    "id",
                    "",
                )
            ),
        )

        return binding

    def _parent_binding(
        self,
        record: Mapping[
            str,
            Any,
        ],
        spec: Any,
        *,
        source_path: (
            Path
            | str
            | None
        ),
        source_field: str,
        default_role: str,
        default_continuation: str,
        default_order: int,
    ) -> dict[str, Any] | None:
        child_id = str(
            record.get(
                "id",
                "",
            )
        ).strip()

        if isinstance(
            spec,
            str,
        ):
            parent_id = (
                spec.strip()
            )

            if not parent_id:
                return None

            return self._binding(
                record=record,
                parent=parent_id,
                child=child_id,
                role=default_role,
                continuation=(
                    default_continuation
                ),
                order=default_order,
                provenance=(
                    _source_provenance(
                        record,
                        source_path,
                        source_field,
                    )
                ),
                metadata=(
                    _binding_metadata(
                        record,
                        source_path,
                        source_field,
                        {
                            "legacy_scalar_reference": (
                                True
                            )
                        },
                    )
                ),
            )

        if not isinstance(
            spec,
            Mapping,
        ):
            raise CanonRecordError(
                f"{child_id} "
                f"{source_field} entry "
                "must be a string or object"
            )

        value = dict(
            spec
        )

        parent_id = (
            _first_identifier(
                value,
                _PARENT_ID_KEYS,
            )
        )

        if not parent_id:
            raise CanonRecordError(
                f"{child_id} "
                f"{source_field} object "
                "lacks a parent identifier"
            )

        metadata = (
            _binding_metadata(
                record,
                source_path,
                source_field,
                _as_mapping(
                    value.get(
                        "metadata"
                    )
                ),
            )
        )

        provenance = (
            _source_provenance(
                record,
                source_path,
                source_field,
            )
        )

        provenance.update(
            _as_mapping(
                value.get(
                    "provenance"
                )
            )
        )

        return self._binding(
            record=record,
            parent=parent_id,
            child=child_id,
            role=value.get(
                "role",
                default_role,
            ),
            continuation=value.get(
                "continuation",
                default_continuation,
            ),
            scope=value.get(
                "scope",
                "canon",
            ),
            order=value.get(
                "order",
                default_order,
            ),
            status=value.get(
                "status",
                "active",
            ),
            authority=value.get(
                "authority",
                "FOUNDATION-008",
            ),
            version=value.get(
                "version",
                "1.0.0",
            ),
            inheritance=(
                _as_mapping(
                    value.get(
                        "inheritance"
                    )
                )
            ),
            propagation=(
                _as_mapping(
                    value.get(
                        "propagation"
                    )
                )
            ),
            validity=_as_mapping(
                value.get(
                    "validity"
                )
            ),
            provenance=provenance,
            metadata=metadata,
            extensions=_as_mapping(
                value.get(
                    "extensions"
                )
            ),
            future_extensions=(
                _as_mapping(
                    value.get(
                        "future_extensions"
                    )
                )
            ),
        )

    def _child_binding(
        self,
        record: Mapping[
            str,
            Any,
        ],
        spec: Any,
        *,
        source_path: (
            Path
            | str
            | None
        ),
        source_field: str,
        role: str,
        continuation: str,
        order: int,
    ) -> dict[str, Any] | None:
        parent_id = str(
            record.get(
                "id",
                "",
            )
        ).strip()

        child_id = (
            reference_identifier(
                spec
            )
        )

        if not child_id:
            if spec in (
                None,
                "",
            ):
                return None

            raise CanonRecordError(
                f"{parent_id} "
                f"{source_field} entry "
                "lacks a child identifier"
            )

        value = (
            dict(spec)
            if isinstance(
                spec,
                Mapping,
            )
            else {}
        )

        metadata = (
            _binding_metadata(
                record,
                source_path,
                source_field,
                _as_mapping(
                    value.get(
                        "metadata"
                    )
                ),
            )
        )

        metadata[
            "inverse_compatibility_input"
        ] = True

        provenance = (
            _source_provenance(
                record,
                source_path,
                source_field,
            )
        )

        provenance.update(
            _as_mapping(
                value.get(
                    "provenance"
                )
            )
        )

        return self._binding(
            record=record,
            parent=parent_id,
            child=child_id,
            role=value.get(
                "role",
                role,
            ),
            continuation=value.get(
                "continuation",
                continuation,
            ),
            scope=value.get(
                "scope",
                "canon",
            ),
            order=value.get(
                "order",
                order,
            ),
            status=value.get(
                "status",
                "active",
            ),
            authority=value.get(
                "authority",
                "FOUNDATION-008",
            ),
            version=value.get(
                "version",
                "1.0.0",
            ),
            inheritance=(
                _as_mapping(
                    value.get(
                        "inheritance"
                    )
                )
            ),
            propagation=(
                _as_mapping(
                    value.get(
                        "propagation"
                    )
                )
            ),
            validity=_as_mapping(
                value.get(
                    "validity"
                )
            ),
            provenance=provenance,
            metadata=metadata,
            extensions=_as_mapping(
                value.get(
                    "extensions"
                )
            ),
            future_extensions=(
                _as_mapping(
                    value.get(
                        "future_extensions"
                    )
                )
            ),
        )

    def _recognized_relationship_binding(
        self,
        record: Mapping[
            str,
            Any,
        ],
        relationship: Mapping[
            str,
            Any,
        ],
        *,
        source_path: (
            Path
            | str
            | None
        ),
        order: int,
    ) -> dict[str, Any] | None:
        source_id = str(
            record.get(
                "id",
                "",
            )
        ).strip()

        relation = str(
            relationship.get(
                "type"
            )
            or relationship.get(
                "relation"
            )
            or relationship.get(
                "kind"
            )
            or ""
        ).strip().casefold()

        target_id = (
            _first_identifier(
                relationship,
                _TARGET_ID_KEYS,
            )
        )

        if (
            not relation
            or not target_id
        ):
            return None

        if (
            relation
            in _PARENT_FIRST_RELATIONSHIPS
        ):
            (
                role,
                continuation,
            ) = (
                _PARENT_FIRST_RELATIONSHIPS[
                    relation
                ]
            )

            parent_id = source_id
            child_id = target_id

        elif (
            relation
            in _TARGET_FIRST_RELATIONSHIPS
        ):
            (
                role,
                continuation,
            ) = (
                _TARGET_FIRST_RELATIONSHIPS[
                    relation
                ]
            )

            parent_id = target_id
            child_id = source_id

        else:
            return None

        metadata = (
            _binding_metadata(
                record,
                source_path,
                "relationships",
                {
                    "relationship_type": (
                        relation
                    ),
                    **_as_mapping(
                        relationship.get(
                            "metadata"
                        )
                    ),
                },
            )
        )

        provenance = (
            _source_provenance(
                record,
                source_path,
                "relationships",
            )
        )

        provenance.update(
            _as_mapping(
                relationship.get(
                    "provenance"
                )
            )
        )

        return self._binding(
            record=record,
            parent=parent_id,
            child=child_id,
            role=relationship.get(
                "role",
                role,
            ),
            continuation=(
                relationship.get(
                    "continuation",
                    continuation,
                )
            ),
            scope=relationship.get(
                "scope",
                "canon",
            ),
            order=relationship.get(
                "order",
                order,
            ),
            status=relationship.get(
                "status",
                "active",
            ),
            authority=(
                relationship.get(
                    "authority",
                    "FOUNDATION-008",
                )
            ),
            version=relationship.get(
                "version",
                "1.0.0",
            ),
            inheritance=(
                _as_mapping(
                    relationship.get(
                        "inheritance"
                    )
                )
            ),
            propagation=(
                _as_mapping(
                    relationship.get(
                        "propagation"
                    )
                )
            ),
            validity=_as_mapping(
                relationship.get(
                    "validity"
                )
            ),
            provenance=provenance,
            metadata=metadata,
            extensions=_as_mapping(
                relationship.get(
                    "extensions"
                )
            ),
            future_extensions=(
                _as_mapping(
                    relationship.get(
                        "future_extensions"
                    )
                )
            ),
        )

    def lineage_bindings(
        self,
        record: Mapping[
            str,
            Any,
        ],
        *,
        source_path: (
            Path
            | str
            | None
        ) = None,
    ) -> list[dict[str, Any]]:
        record_id = str(
            record.get(
                "id",
                "",
            )
        ).strip()

        if not record_id:
            raise CanonRecordError(
                "canon record lacks id"
            )

        bindings: list[
            dict[str, Any]
        ] = []

        lineage = record.get(
            "lineage"
        )

        lineage_map = (
            dict(lineage)
            if isinstance(
                lineage,
                Mapping,
            )
            else {}
        )

        parent_fields = (
            (
                "parents",
                "generic",
                "neutral",
            ),
            (
                "mothers",
                "source",
                "neutral",
            ),
            (
                "fathers",
                "pattern",
                "preserving",
            ),
            (
                "composed_from",
                "source",
                "neutral",
            ),
        )

        for (
            field_name,
            role,
            continuation,
        ) in parent_fields:
            for order, spec in enumerate(
                _sequence(
                    lineage_map.get(
                        field_name
                    )
                )
            ):
                binding = (
                    self._parent_binding(
                        record,
                        spec,
                        source_path=(
                            source_path
                        ),
                        source_field=(
                            "lineage."
                            + field_name
                        ),
                        default_role=(
                            role
                        ),
                        default_continuation=(
                            continuation
                        ),
                        default_order=(
                            order
                        ),
                    )
                )

                if binding is not None:
                    bindings.append(
                        binding
                    )

        for order, spec in enumerate(
            _sequence(
                lineage_map.get(
                    "supersedes"
                )
            )
        ):
            binding = (
                self._parent_binding(
                    record,
                    spec,
                    source_path=(
                        source_path
                    ),
                    source_field=(
                        "lineage."
                        "supersedes"
                    ),
                    default_role=(
                        "supersession"
                    ),
                    default_continuation=(
                        "transforming"
                    ),
                    default_order=(
                        order
                    ),
                )
            )

            if binding is not None:
                bindings.append(
                    binding
                )

        for order, spec in enumerate(
            _sequence(
                lineage_map.get(
                    "superseded_by"
                )
            )
        ):
            binding = (
                self._child_binding(
                    record,
                    spec,
                    source_path=(
                        source_path
                    ),
                    source_field=(
                        "lineage."
                        "superseded_by"
                    ),
                    role=(
                        "supersession"
                    ),
                    continuation=(
                        "transforming"
                    ),
                    order=order,
                )
            )

            if binding is not None:
                bindings.append(
                    binding
                )

        child_fields = (
            (
                "children",
                "generic",
                "neutral",
            ),
            (
                "daughters",
                "generic",
                "preserving",
            ),
            (
                "sons",
                "generic",
                "projecting",
            ),
        )

        for (
            field_name,
            role,
            continuation,
        ) in child_fields:
            for order, spec in enumerate(
                _sequence(
                    lineage_map.get(
                        field_name
                    )
                )
            ):
                binding = (
                    self._child_binding(
                        record,
                        spec,
                        source_path=(
                            source_path
                        ),
                        source_field=(
                            "lineage."
                            + field_name
                        ),
                        role=role,
                        continuation=(
                            continuation
                        ),
                        order=order,
                    )
                )

                if binding is not None:
                    bindings.append(
                        binding
                    )

        for order, spec in enumerate(
            _sequence(
                record.get(
                    "dependencies"
                )
            )
        ):
            binding = (
                self._parent_binding(
                    record,
                    spec,
                    source_path=(
                        source_path
                    ),
                    source_field=(
                        "dependencies"
                    ),
                    default_role=(
                        "dependency"
                    ),
                    default_continuation=(
                        "neutral"
                    ),
                    default_order=(
                        order
                    ),
                )
            )

            if binding is not None:
                bindings.append(
                    binding
                )

        for order, relationship in enumerate(
            _sequence(
                record.get(
                    "relationships"
                )
            )
        ):
            if isinstance(
                relationship,
                str,
            ):
                relationship = {
                    "type": (
                        "related_to"
                    ),
                    "target": (
                        relationship
                    ),
                }

            if not isinstance(
                relationship,
                Mapping,
            ):
                raise CanonRecordError(
                    f"{record_id} "
                    "relationship must be "
                    "a string or object"
                )

            binding = (
                self
                ._recognized_relationship_binding(
                    record,
                    relationship,
                    source_path=(
                        source_path
                    ),
                    order=order,
                )
            )

            if binding is not None:
                bindings.append(
                    binding
                )

        deduplicated: dict[
            tuple[
                str,
                str,
                str,
                str,
                int,
            ],
            dict[str, Any],
        ] = {}

        for binding in bindings:
            signature = (
                binding[
                    "parent"
                ],
                binding[
                    "child"
                ],
                binding[
                    "role"
                ],
                binding[
                    "scope"
                ],
                binding[
                    "order"
                ],
            )

            existing = (
                deduplicated.get(
                    signature
                )
            )

            if existing is None:
                deduplicated[
                    signature
                ] = binding
                continue

            if existing != binding:
                raise CanonRecordError(
                    "conflicting canon "
                    "lineage binding for "
                    f"signature: {signature}"
                )

        return sorted(
            deduplicated.values(),
            key=lambda item: (
                self.registry
                .get(
                    item[
                        "role"
                    ]
                )
                .precedence,
                item[
                    "order"
                ],
                item[
                    "parent"
                ],
                item[
                    "child"
                ],
                item[
                    "id"
                ],
            ),
        )

    def relationship_rows(
        self,
        record: Mapping[
            str,
            Any,
        ],
    ) -> list[dict[str, Any]]:
        source_id = str(
            record.get(
                "id",
                "",
            )
        ).strip()

        rows: list[
            dict[str, Any]
        ] = []

        for order, relationship in enumerate(
            _sequence(
                record.get(
                    "relationships"
                )
            )
        ):
            if isinstance(
                relationship,
                str,
            ):
                rows.append({
                    "source_id": (
                        source_id
                    ),
                    "relation": (
                        "related_to"
                    ),
                    "target_id": (
                        relationship
                    ),
                    "order": order,
                    "metadata": {},
                })

                continue

            if not isinstance(
                relationship,
                Mapping,
            ):
                continue

            target_id = (
                _first_identifier(
                    relationship,
                    _TARGET_ID_KEYS,
                )
            )

            if not target_id:
                continue

            rows.append({
                "source_id": (
                    source_id
                ),
                "relation": str(
                    relationship.get(
                        "type"
                    )
                    or relationship.get(
                        "relation"
                    )
                    or relationship.get(
                        "kind"
                    )
                    or "related_to"
                ),
                "target_id": (
                    target_id
                ),
                "order": (
                    relationship.get(
                        "order",
                        order,
                    )
                ),
                "metadata": (
                    _as_mapping(
                        relationship.get(
                            "metadata"
                        )
                    )
                ),
            })

        return rows

    def reference_rows(
        self,
        record: Mapping[
            str,
            Any,
        ],
    ) -> list[dict[str, Any]]:
        source_id = str(
            record.get(
                "id",
                "",
            )
        ).strip()

        rows: list[
            dict[str, Any]
        ] = []

        for kind in (
            "dependencies",
            "attachments",
        ):
            for order, spec in enumerate(
                _sequence(
                    record.get(
                        kind
                    )
                )
            ):
                target = (
                    reference_identifier(
                        spec
                    )
                )

                if not target:
                    continue

                metadata = (
                    _as_mapping(
                        spec
                    )
                    if isinstance(
                        spec,
                        Mapping,
                    )
                    else {}
                )

                rows.append({
                    "source_id": (
                        source_id
                    ),
                    "reference_kind": (
                        kind[:-1]
                        if kind.endswith(
                            "s"
                        )
                        else kind
                    ),
                    "target": target,
                    "order": order,
                    "metadata": (
                        metadata
                    ),
                })

        provenance = record.get(
            "provenance"
        )

        if isinstance(
            provenance,
            Mapping,
        ):
            sources = provenance.get(
                "sources",
                [],
            )

            for order, source in enumerate(
                _sequence(
                    sources
                )
            ):
                target = (
                    reference_identifier(
                        source
                    )
                )

                if not target:
                    continue

                rows.append({
                    "source_id": (
                        source_id
                    ),
                    "reference_kind": (
                        "provenance_source"
                    ),
                    "target": target,
                    "order": order,
                    "metadata": {},
                })

        return rows

    def project_records(
        self,
        records: Iterable[
            tuple[
                Path | str,
                Mapping[
                    str,
                    Any,
                ],
            ]
        ],
        *,
        source_root: (
            Path
            | str
            | None
        ) = None,
    ) -> dict[str, Any]:
        root = (
            Path(
                source_root
            ).resolve()
            if source_root
            is not None
            else None
        )

        nodes: list[
            dict[str, Any]
        ] = []

        bindings: list[
            dict[str, Any]
        ] = []

        relationships: list[
            dict[str, Any]
        ] = []

        references: list[
            dict[str, Any]
        ] = []

        source_manifest: list[
            dict[str, Any]
        ] = []

        seen_ids: set[str] = set()
        binding_ids: set[str] = set()

        for (
            raw_path,
            record,
        ) in records:
            path = Path(
                raw_path
            )

            record_id = str(
                record.get(
                    "id",
                    "",
                )
            ).strip()

            if not record_id:
                raise CanonRecordError(
                    "canon record lacks id: "
                    f"{path}"
                )

            if record_id in seen_ids:
                raise CanonRecordError(
                    "duplicate canon "
                    f"record id: {record_id}"
                )

            seen_ids.add(
                record_id
            )

            node = deepcopy(
                dict(
                    record
                )
            )

            node.setdefault(
                "metadata",
                {},
            )

            if not isinstance(
                node[
                    "metadata"
                ],
                Mapping,
            ):
                node[
                    "metadata"
                ] = {
                    "original": deepcopy(
                        node[
                            "metadata"
                        ]
                    )
                }

            node[
                "metadata"
            ] = dict(
                node[
                    "metadata"
                ]
            )

            node[
                "metadata"
            ][
                "canon_authority_path"
            ] = str(
                path
            )

            nodes.append(
                node
            )

            record_bindings = (
                self.lineage_bindings(
                    record,
                    source_path=path,
                )
            )

            for binding in (
                record_bindings
            ):
                if (
                    binding[
                        "id"
                    ]
                    in binding_ids
                ):
                    continue

                binding_ids.add(
                    binding[
                        "id"
                    ]
                )

                bindings.append(
                    binding
                )

            relationships.extend(
                self.relationship_rows(
                    record
                )
            )

            references.extend(
                self.reference_rows(
                    record
                )
            )

            display_path = str(
                path
            )

            if root is not None:
                try:
                    display_path = str(
                        path.resolve()
                        .relative_to(
                            root
                        )
                    )
                except ValueError:
                    pass

            source_manifest.append({
                "id": record_id,
                "path": display_path,
                "sha256": stable_hash(
                    record
                ),
            })

        nodes.sort(
            key=lambda item: str(
                item[
                    "id"
                ]
            )
        )

        bindings.sort(
            key=lambda item: item[
                "id"
            ]
        )

        relationships.sort(
            key=lambda item: (
                item[
                    "source_id"
                ],
                item[
                    "relation"
                ],
                item[
                    "order"
                ],
                item[
                    "target_id"
                ],
            )
        )

        references.sort(
            key=lambda item: (
                item[
                    "source_id"
                ],
                item[
                    "reference_kind"
                ],
                item[
                    "order"
                ],
                item[
                    "target"
                ],
            )
        )

        source_manifest.sort(
            key=lambda item: item[
                "id"
            ]
        )

        deterministic_core = {
            "schema": (
                "savant."
                "canon_lineage_projection.v1"
            ),
            "nodes": nodes,
            "bindings": bindings,
            "relationships": (
                relationships
            ),
            "references": references,
            "source_manifest": (
                source_manifest
            ),
        }

        return {
            **deterministic_core,
            "node_count": len(
                nodes
            ),
            "binding_count": len(
                bindings
            ),
            "relationship_count": (
                len(
                    relationships
                )
            ),
            "reference_count": len(
                references
            ),
            "deterministic_hash": (
                stable_hash(
                    deterministic_core
                )
            ),
        }

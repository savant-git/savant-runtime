#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .model import (
    StraubValidationError,
    content_digest,
)


schema = "savant.straub.composition.v1"
owner = "carbon"
module = "straub"
authority_effect = "none"


VALUE_TYPES = (
    "any",
    "boolean",
    "integer",
    "number",
    "string",
    "object",
    "array",
    "null",
)


def _require_string(
    value: Any,
    field: str,
) -> str:
    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):
        raise StraubValidationError(
            f"{field} must be a non-empty string"
        )

    return value.strip()


def _normalize_ids(
    values: Sequence[str] | None,
    field: str,
) -> list[str]:
    if values is None:
        return []

    if isinstance(
        values,
        (str, bytes),
    ):
        raise StraubValidationError(
            f"{field} must be a sequence of ids"
        )

    normalized: list[str] = []

    for value in values:
        item = _require_string(
            value,
            field,
        )

        if item not in normalized:
            normalized.append(
                item
            )

    return normalized


def validate_value_type(
    value_type: str,
) -> str:
    normalized = _require_string(
        value_type,
        "value_type",
    ).lower()

    if normalized not in VALUE_TYPES:
        raise StraubValidationError(
            "unsupported Straub value type: "
            f"{normalized}"
        )

    return normalized


def validate_value(
    value: Any,
    value_type: str,
) -> Any:
    normalized_type = (
        validate_value_type(
            value_type
        )
    )

    valid = False

    if normalized_type == "any":
        valid = True

    elif normalized_type == "boolean":
        valid = isinstance(
            value,
            bool,
        )

    elif normalized_type == "integer":
        valid = (
            isinstance(
                value,
                int,
            )
            and not isinstance(
                value,
                bool,
            )
        )

    elif normalized_type == "number":
        valid = (
            isinstance(
                value,
                (int, float),
            )
            and not isinstance(
                value,
                bool,
            )
        )

    elif normalized_type == "string":
        valid = isinstance(
            value,
            str,
        )

    elif normalized_type == "object":
        valid = isinstance(
            value,
            Mapping,
        )

    elif normalized_type == "array":
        valid = isinstance(
            value,
            (list, tuple),
        )

    elif normalized_type == "null":
        valid = value is None

    if not valid:
        raise StraubValidationError(
            "value does not satisfy "
            f"Straub type {normalized_type!r}"
        )

    return deepcopy(
        value
    )


def definition_group(
    *,
    group_id: str,
    definition_ids: Sequence[str],
    label: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_group_id = (
        _require_string(
            group_id,
            "group_id",
        )
    )

    normalized_definition_ids = (
        _normalize_ids(
            definition_ids,
            "definition_ids",
        )
    )

    if not normalized_definition_ids:
        raise StraubValidationError(
            "definition group requires "
            "at least one definition"
        )

    result: dict[str, Any] = {
        "schema":
            "savant.straub."
            "definition-group.v1",
        "kind":
            "definition_group",
        "id":
            normalized_group_id,
        "definition_ids":
            normalized_definition_ids,
        "metadata":
            deepcopy(
                dict(
                    metadata
                    or {}
                )
            ),
        "authority_effect":
            "none",
    }

    if label is not None:
        result[
            "label"
        ] = _require_string(
            label,
            "label",
        )

    result[
        "digest"
    ] = content_digest(
        {
            key: value
            for key, value
            in result.items()
            if key != "digest"
        }
    )

    return result


def composition(
    *,
    composition_id: str,
    member_ids: Sequence[str],
    group_ids: Sequence[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_composition_id = (
        _require_string(
            composition_id,
            "composition_id",
        )
    )

    normalized_member_ids = (
        _normalize_ids(
            member_ids,
            "member_ids",
        )
    )

    normalized_group_ids = (
        _normalize_ids(
            group_ids,
            "group_ids",
        )
    )

    if not normalized_member_ids:
        raise StraubValidationError(
            "composition requires "
            "at least one member"
        )

    result = {
        "schema":
            "savant.straub."
            "composition.v1",
        "kind":
            "composition",
        "id":
            normalized_composition_id,
        "member_ids":
            normalized_member_ids,
        "group_ids":
            normalized_group_ids,
        "metadata":
            deepcopy(
                dict(
                    metadata
                    or {}
                )
            ),
        "authority_effect":
            "none",
    }

    result[
        "digest"
    ] = content_digest(
        {
            key: value
            for key, value
            in result.items()
            if key != "digest"
        }
    )

    return result


def effective_definition_digest(
    definitions: Mapping[str, Any],
) -> str:
    if not isinstance(
        definitions,
        Mapping,
    ):
        raise StraubValidationError(
            "effective definitions "
            "must be a mapping"
        )

    return content_digest(
        deepcopy(
            dict(
                definitions
            )
        )
    )


def project_effective_definitions(
    *,
    definitions: Mapping[str, Mapping[str, Any]],
    groups: Sequence[Mapping[str, Any]] | None = None,
    compositions: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if not isinstance(
        definitions,
        Mapping,
    ):
        raise StraubValidationError(
            "definitions must be a mapping"
        )

    normalized_definitions: dict[
        str,
        dict[str, Any],
    ] = {}

    for definition_id in sorted(
        definitions
    ):
        normalized_id = (
            _require_string(
                definition_id,
                "definition_id",
            )
        )

        definition = (
            definitions[
                definition_id
            ]
        )

        if not isinstance(
            definition,
            Mapping,
        ):
            raise StraubValidationError(
                "definition must be a mapping: "
                f"{normalized_id}"
            )

        normalized_definitions[
            normalized_id
        ] = deepcopy(
            dict(
                definition
            )
        )

    normalized_groups: list[
        dict[str, Any]
    ] = []

    for group in (
        groups
        or []
    ):
        if not isinstance(
            group,
            Mapping,
        ):
            raise StraubValidationError(
                "group must be a mapping"
            )

        normalized_groups.append(
            deepcopy(
                dict(
                    group
                )
            )
        )

    normalized_groups.sort(
        key=lambda item: str(
            item.get(
                "id",
                "",
            )
        )
    )

    normalized_compositions: list[
        dict[str, Any]
    ] = []

    for item in (
        compositions
        or []
    ):
        if not isinstance(
            item,
            Mapping,
        ):
            raise StraubValidationError(
                "composition must be a mapping"
            )

        normalized_compositions.append(
            deepcopy(
                dict(
                    item
                )
            )
        )

    normalized_compositions.sort(
        key=lambda item: str(
            item.get(
                "id",
                "",
            )
        )
    )

    effective = deepcopy(
        normalized_definitions
    )

    projection = {
        "schema":
            "savant.straub."
            "effective-definitions.v1",
        "kind":
            "effective_definitions",
        "definitions":
            effective,
        "groups":
            normalized_groups,
        "compositions":
            normalized_compositions,
        "definition_count":
            len(
                effective
            ),
        "group_count":
            len(
                normalized_groups
            ),
        "composition_count":
            len(
                normalized_compositions
            ),
        "deterministic":
            True,
        "projection_only":
            True,
        "semantic_mutation":
            False,
        "semantic_authority":
            False,
        "authority_effect":
            authority_effect,
    }

    projection[
        "digest"
    ] = content_digest(
        {
            key: value
            for key, value
            in projection.items()
            if key != "digest"
        }
    )

    return projection

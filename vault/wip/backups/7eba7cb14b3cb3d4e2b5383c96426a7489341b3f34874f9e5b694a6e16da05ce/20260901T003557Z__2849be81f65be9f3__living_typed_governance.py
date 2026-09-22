#!/usr/bin/env python3

from __future__ import annotations

import re

from typing import Any, Mapping


from runtime.living_governance import (
    append_event,
    history,
    next_version,
    normalize_record,
    project,
    stream_records,
    utc_now,
)

from runtime.living_policy import (
    canonical_name,
    effects,
    enforcement_modes,
    parse_time,
)


owner = "living-governance"
authority_effect = "governance"

governance_types = {
    "policy",
    "rule",
    "permission",
    "invariant",
    "exception",
    "override",
}

epistemic_classes = {
    "fact",
    "assertion",
    "inference",
    "estimate",
    "speculation",
    "unknown",
    "projection",
}

typed_fields = (
    "type",
    "epistemic_class",
    "scope",
    "subject",
    "target",
    "action",
    "predicate",
    "effect",
    "enforcement_mode",
    "reason_code",
    "valid_from",
    "valid_until",
    "exceptions",
    "override",
    "evidence",
    "remediation",
    "completion_criteria",
)

reason_code_pattern = re.compile(
    r"^[a-z0-9][a-z0-9._-]*$"
)


class living_typed_governance_error(
    RuntimeError
):
    pass


def _mapping(
    value: Any,
    *,
    field: str,
) -> dict[str, Any] | None:
    if value is None:
        return None

    if not isinstance(
        value,
        Mapping,
    ):
        raise living_typed_governance_error(
            (
                field
                + " must be an object"
            )
        )

    return dict(
        value
    )


def _mapping_list(
    value: Any,
    *,
    field: str,
) -> list[dict[str, Any]] | None:
    if value is None:
        return None

    if not isinstance(
        value,
        list,
    ):
        raise living_typed_governance_error(
            (
                field
                + " must be a list"
            )
        )

    output = []

    for item in value:
        if not isinstance(
            item,
            Mapping,
        ):
            raise living_typed_governance_error(
                (
                    field
                    + " entries must be objects"
                )
            )

        output.append(
            dict(
                item
            )
        )

    return output


def _evidence(
    value: Any,
) -> list[Any] | None:
    if value is None:
        return None

    if not isinstance(
        value,
        list,
    ):
        raise living_typed_governance_error(
            "evidence must be a list"
        )

    output = []

    for item in value:
        if isinstance(
            item,
            str,
        ):
            candidate = item.strip()

            if candidate:
                output.append(
                    candidate
                )

            continue

        if isinstance(
            item,
            Mapping,
        ):
            output.append(
                dict(
                    item
                )
            )

            continue

        raise living_typed_governance_error(
            (
                "evidence entries must be "
                "strings or objects"
            )
        )

    return output


def _completion_criteria(
    value: Any,
) -> list[Any] | None:
    if value is None:
        return None

    if not isinstance(
        value,
        list,
    ):
        raise living_typed_governance_error(
            (
                "completion_criteria "
                "must be a list"
            )
        )

    output = []

    for item in value:
        if isinstance(
            item,
            str,
        ):
            candidate = item.strip()

            if candidate:
                output.append(
                    candidate
                )

            continue

        if isinstance(
            item,
            Mapping,
        ):
            output.append(
                dict(
                    item
                )
            )

            continue

        raise living_typed_governance_error(
            (
                "completion_criteria entries "
                "must be strings or objects"
            )
        )

    return output


def _timestamp(
    value: Any,
    *,
    field: str,
) -> str | None:
    if value is None:
        return None

    candidate = str(
        value
    ).strip()

    if not candidate:
        return None

    if parse_time(
        candidate
    ) is None:
        raise living_typed_governance_error(
            (
                field
                + " must be an ISO timestamp"
            )
        )

    return candidate


def normalize_typed_fields(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    output: dict[
        str,
        Any,
    ] = {}

    if "type" in value:
        record_type = canonical_name(
            value.get(
                "type"
            )
        )

        if record_type not in governance_types:
            raise living_typed_governance_error(
                (
                    "unsupported governance type: "
                    + record_type
                )
            )

        output[
            "type"
        ] = record_type

    if "epistemic_class" in value:
        epistemic_class = canonical_name(
            value.get(
                "epistemic_class"
            )
        )

        if (
            epistemic_class
            not in epistemic_classes
        ):
            raise living_typed_governance_error(
                (
                    "unsupported epistemic class: "
                    + epistemic_class
                )
            )

        output[
            "epistemic_class"
        ] = epistemic_class

    for field in (
        "scope",
        "subject",
        "target",
        "action",
        "predicate",
        "override",
    ):
        if field not in value:
            continue

        normalized = _mapping(
            value.get(
                field
            ),
            field=field,
        )

        if normalized is not None:
            output[
                field
            ] = normalized

    if "effect" in value:
        effect = canonical_name(
            value.get(
                "effect"
            )
        )

        if effect not in effects:
            raise living_typed_governance_error(
                (
                    "unsupported policy effect: "
                    + effect
                )
            )

        output[
            "effect"
        ] = effect

    if "enforcement_mode" in value:
        enforcement_mode = canonical_name(
            value.get(
                "enforcement_mode"
            )
        )

        if (
            enforcement_mode
            not in enforcement_modes
        ):
            raise living_typed_governance_error(
                (
                    "unsupported enforcement mode: "
                    + enforcement_mode
                )
            )

        output[
            "enforcement_mode"
        ] = enforcement_mode

    if "reason_code" in value:
        reason_code = canonical_name(
            value.get(
                "reason_code"
            )
        )

        if (
            not reason_code
            or not reason_code_pattern.fullmatch(
                reason_code
            )
        ):
            raise living_typed_governance_error(
                "reason_code is invalid"
            )

        output[
            "reason_code"
        ] = reason_code

    for field in (
        "valid_from",
        "valid_until",
    ):
        if field not in value:
            continue

        normalized = _timestamp(
            value.get(
                field
            ),
            field=field,
        )

        if normalized is not None:
            output[
                field
            ] = normalized

    if (
        "valid_from"
        in output
        and "valid_until"
        in output
    ):
        valid_from = parse_time(
            output[
                "valid_from"
            ]
        )

        valid_until = parse_time(
            output[
                "valid_until"
            ]
        )

        if (
            valid_from is not None
            and valid_until is not None
            and valid_until < valid_from
        ):
            raise living_typed_governance_error(
                (
                    "valid_until may not precede "
                    "valid_from"
                )
            )

    if "exceptions" in value:
        normalized = _mapping_list(
            value.get(
                "exceptions"
            ),
            field="exceptions",
        )

        if normalized is not None:
            output[
                "exceptions"
            ] = normalized

    if "evidence" in value:
        normalized = _evidence(
            value.get(
                "evidence"
            )
        )

        if normalized is not None:
            output[
                "evidence"
            ] = normalized

    if "completion_criteria" in value:
        normalized = _completion_criteria(
            value.get(
                "completion_criteria"
            )
        )

        if normalized is not None:
            output[
                "completion_criteria"
            ] = normalized

    if "remediation" in value:
        remediation = str(
            value.get(
                "remediation",
                "",
            )
        ).strip()

        if remediation:
            output[
                "remediation"
            ] = remediation

    if "effect" in output:
        if "type" not in output:
            raise living_typed_governance_error(
                (
                    "executable typed record "
                    "requires explicit type"
                )
            )

        if output[
            "type"
        ] not in {
            "policy",
            "rule",
            "permission",
            "invariant",
        }:
            raise living_typed_governance_error(
                (
                    "effect is only valid for "
                    "executable governance records"
                )
            )

    return output


def typed_record(
    record: Mapping[str, Any],
) -> bool:
    return any(
        field in record
        for field
        in typed_fields
    )


def current_record(
    *,
    stream: str,
    semantic_id: str,
) -> dict[str, Any] | None:
    for record in stream_records(
        stream
    ):
        if str(
            record.get(
                "id",
                "",
            )
        ) == semantic_id:
            return dict(
                record
            )

    return None


def semantic_history_exists(
    *,
    stream: str,
    semantic_id: str,
) -> bool:
    return bool(
        history(
            stream=stream,
            semantic_id=semantic_id,
        )
    )


def build_record(
    *,
    stream: str,
    semantic_id: str,
    text: str,
    authority: str,
    priority: int,
    status: str,
    supersedes: list[str],
    dependencies: list[str],
    relationships: list[
        dict[
            str,
            str,
        ]
    ],
    asserted_by: str,
    source: list[str],
    typed: Mapping[str, Any],
) -> dict[str, Any]:
    provenance = {
        "asserted_by":
            asserted_by,

        "method":
            (
                "living-governance-"
                "typed-contribution"
            ),

        "sources":
            sorted(
                set(
                    source
                )
            ),

        "created_at":
            utc_now(),
    }

    base = normalize_record(
        {
            "id":
                semantic_id,

            "version":
                next_version(
                    stream,
                    semantic_id,
                ),

            "priority":
                priority,

            "text":
                text,

            "status":
                status,

            "authority":
                authority,

            "supersedes":
                supersedes,

            "dependencies":
                dependencies,

            "relationships":
                relationships,

            "provenance":
                provenance,
        },
        stream=stream,
        default_authority=authority,
        default_provenance=provenance,
    )

    extension = normalize_typed_fields(
        typed
    )

    base.update(
        extension
    )

    return base


def assert_typed_record(
    *,
    stream: str,
    semantic_id: str,
    text: str,
    authority: str,
    priority: int = 1000,
    status: str = "active",
    supersedes: list[str] | None = None,
    dependencies: list[str] | None = None,
    relationships: list[
        dict[
            str,
            str,
        ]
    ] | None = None,
    asserted_by: str = "user",
    source: list[str] | None = None,
    typed: Mapping[str, Any],
    allow_existing: bool = False,
) -> dict[str, Any]:
    if (
        semantic_history_exists(
            stream=stream,
            semantic_id=semantic_id,
        )
        and not allow_existing
    ):
        raise living_typed_governance_error(
            (
                "semantic id already exists; "
                "use evolution: "
                + semantic_id
            )
        )

    record = build_record(
        stream=stream,
        semantic_id=semantic_id,
        text=text,
        authority=authority,
        priority=priority,
        status=status,
        supersedes=list(
            supersedes
            or []
        ),
        dependencies=list(
            dependencies
            or []
        ),
        relationships=list(
            relationships
            or []
        ),
        asserted_by=asserted_by,
        source=list(
            source
            or []
        ),
        typed=typed,
    )

    event = append_event(
        record
    )

    projection = project()

    return {
        "schema":
            (
                "savant.living-governance."
                "typed-assertion.v1"
            ),

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "event":
            event,

        "projection":
            projection,
    }


def evolve_typed_record(
    *,
    stream: str,
    semantic_id: str,
    text: str | None = None,
    authority: str | None = None,
    priority: int | None = None,
    status: str | None = None,
    dependencies: list[str] | None = None,
    relationships: list[
        dict[
            str,
            str,
        ]
    ] | None = None,
    asserted_by: str = "user",
    source: list[str] | None = None,
    typed: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    current = current_record(
        stream=stream,
        semantic_id=semantic_id,
    )

    if current is None:
        raise living_typed_governance_error(
            (
                "current semantic record "
                "does not exist: "
                + semantic_id
            )
        )

    inherited_typed = {
        field:
            current[
                field
            ]
        for field
        in typed_fields
        if field in current
    }

    if typed:
        for field, value in typed.items():
            if value is None:
                inherited_typed.pop(
                    field,
                    None,
                )

            else:
                inherited_typed[
                    field
                ] = value

    return assert_typed_record(
        stream=stream,
        semantic_id=semantic_id,
        text=(
            text
            if text is not None
            else str(
                current[
                    "text"
                ]
            )
        ),
        authority=(
            authority
            if authority is not None
            else str(
                current[
                    "authority"
                ]
            )
        ),
        priority=(
            priority
            if priority is not None
            else int(
                current.get(
                    "priority",
                    1000,
                )
            )
        ),
        status=(
            status
            if status is not None
            else str(
                current.get(
                    "status",
                    "active",
                )
            )
        ),
        supersedes=[
            semantic_id
        ],
        dependencies=(
            dependencies
            if dependencies is not None
            else [
                str(
                    value
                )
                for value
                in current.get(
                    "dependencies",
                    [],
                )
            ]
        ),
        relationships=(
            relationships
            if relationships is not None
            else [
                {
                    "kind":
                        str(
                            relationship[
                                "kind"
                            ]
                        ),

                    "target":
                        str(
                            relationship[
                                "target"
                            ]
                        ),
                }
                for relationship
                in current.get(
                    "relationships",
                    [],
                )
            ]
        ),
        asserted_by=asserted_by,
        source=list(
            source
            or []
        ),
        typed=inherited_typed,
        allow_existing=True,
    )


def validate_typed_record(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    errors = []

    try:
        normalized = normalize_typed_fields(
            {
                field:
                    record[
                        field
                ]
                for field
                in typed_fields
                if field in record
            }
        )

    except living_typed_governance_error as exc:
        errors.append(
            str(
                exc
            )
        )

        normalized = {}

    if (
        "effect" in record
        and "reason_code" not in record
    ):
        errors.append(
            (
                "executable typed record "
                "requires stable reason_code"
            )
        )

    return {
        "schema":
            (
                "savant.living-governance."
                "typed-validation.v1"
            ),

        "owner":
            owner,

        "authority_effect":
            "none",

        "id":
            record.get(
                "id"
            ),

        "stream":
            record.get(
                "stream"
            ),

        "typed":
            typed_record(
                record
            ),

        "valid":
            not errors,

        "errors":
            errors,

        "normalized":
            normalized,
    }


def status() -> dict[str, Any]:
    typed_records = []

    for stream in (
        "rules",
        "permissions",
        "invariants",
        "decisions",
        "masterplan",
    ):
        for record in stream_records(
            stream
        ):
            if typed_record(
                record
            ):
                typed_records.append(
                    record
                )

    executable = [
        record
        for record
        in typed_records
        if "effect" in record
    ]

    return {
        "schema":
            (
                "savant.living-governance."
                "typed-status.v1"
            ),

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "authority_store":
            "existing-living-ledger",

        "typed_fields":
            list(
                typed_fields
            ),

        "governance_types":
            sorted(
                governance_types
            ),

        "epistemic_classes":
            sorted(
                epistemic_classes
            ),

        "typed_record_count":
            len(
                typed_records
            ),

        "executable_record_count":
            len(
                executable
            ),

        "backwards_compatible":
            True,

        "ready":
            True,
    }


__all__ = [
    "assert_typed_record",
    "build_record",
    "current_record",
    "evolve_typed_record",
    "governance_types",
    "normalize_typed_fields",
    "status",
    "typed_fields",
    "typed_record",
    "validate_typed_record",
]

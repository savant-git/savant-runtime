#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .model import (
    StraubValidationError,
    content_digest,
    normalize_instance,
    normalize_string_list,
)


schema = "savant.straub.step.v1"
owner = "savant"
authority_effect = "none"


def function_instance(
    *,
    instance_id: str,
    label: str,
    step_ids: Sequence[str],
    purpose: str = "",
    owner_id: str | None = None,
    dependencies: Sequence[str] | None = None,
    provenance: Mapping[str, Any] | None = None,
    lineage: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    steps = normalize_string_list(
        step_ids
    )

    if not steps:
        raise StraubValidationError(
            "function instance requires "
            "at least one step"
        )

    dependency_ids = set(
        normalize_string_list(
            dependencies
        )
    )

    dependency_ids.update(
        steps
    )

    owner_ref = str(
        owner_id or ""
    ).strip()

    if owner_ref:
        dependency_ids.add(
            owner_ref
        )

    return normalize_instance(
        {
            "id":
                instance_id,
            "kind":
                "function",
            "payload": {
                "label":
                    str(
                        label
                    ).strip(),
                "purpose":
                    str(
                        purpose
                    ).strip(),
                "owner":
                    (
                        owner_ref
                        or None
                    ),
                "steps":
                    steps,
            },
            "metadata":
                deepcopy(
                    dict(
                        metadata
                        or {}
                    )
                ),
            "dependencies":
                sorted(
                    dependency_ids
                ),
            "provenance":
                provenance,
            "lineage":
                lineage,
        }
    )


def function_step(
    *,
    instance_id: str,
    label: str,
    operation: str,
    ordinal: int,
    input_contract: Mapping[str, Any] | None = None,
    output_contract: Mapping[str, Any] | None = None,
    dependencies: Sequence[str] | None = None,
    owner_id: str | None = None,
    deterministic: bool = True,
    side_effect_class: str = "none",
    provenance: Mapping[str, Any] | None = None,
    lineage: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if (
        not isinstance(
            ordinal,
            int,
        )
        or isinstance(
            ordinal,
            bool,
        )
        or ordinal < 1
    ):
        raise StraubValidationError(
            "function step ordinal "
            "must be a positive integer"
        )

    operation_id = str(
        operation or ""
    ).strip().lower()

    if not operation_id:
        raise StraubValidationError(
            "function step operation "
            "is required"
        )

    side_effect = str(
        side_effect_class
        or "none"
    ).strip().lower()

    dependency_ids = set(
        normalize_string_list(
            dependencies
        )
    )

    owner_ref = str(
        owner_id or ""
    ).strip()

    if owner_ref:
        dependency_ids.add(
            owner_ref
        )

    return normalize_instance(
        {
            "id":
                instance_id,
            "kind":
                "function.step",
            "payload": {
                "label":
                    str(
                        label
                    ).strip(),
                "operation":
                    operation_id,
                "ordinal":
                    ordinal,
                "owner":
                    (
                        owner_ref
                        or None
                    ),
                "input_contract":
                    deepcopy(
                        dict(
                            input_contract
                            or {}
                        )
                    ),
                "output_contract":
                    deepcopy(
                        dict(
                            output_contract
                            or {}
                        )
                    ),
                "deterministic":
                    bool(
                        deterministic
                    ),
                "side_effect_class":
                    side_effect,
            },
            "metadata":
                deepcopy(
                    dict(
                        metadata
                        or {}
                    )
                ),
            "dependencies":
                sorted(
                    dependency_ids
                ),
            "provenance":
                provenance,
            "lineage":
                lineage,
        }
    )


def step_execution(
    *,
    instance_id: str,
    step_id: str,
    execution_id: str,
    status: str,
    input_digest: str | None = None,
    output_digest: str | None = None,
    previous_execution_id: str | None = None,
    dependencies: Sequence[str] | None = None,
    provenance: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    step_ref = str(
        step_id or ""
    ).strip()

    execution_ref = str(
        execution_id or ""
    ).strip()

    state = str(
        status or ""
    ).strip().lower()

    if not step_ref:
        raise StraubValidationError(
            "step execution requires step_id"
        )

    if not execution_ref:
        raise StraubValidationError(
            "step execution requires execution_id"
        )

    if not state:
        raise StraubValidationError(
            "step execution requires status"
        )

    dependency_ids = set(
        normalize_string_list(
            dependencies
        )
    )

    dependency_ids.add(
        step_ref
    )

    previous = str(
        previous_execution_id
        or ""
    ).strip()

    if previous:
        dependency_ids.add(
            previous
        )

    lineage = {
        "derived_from":
            (
                [previous]
                if previous
                else []
            ),
        "supersedes":
            [],
        "superseded_by":
            None,
        "history":
            [],
    }

    return normalize_instance(
        {
            "id":
                instance_id,
            "kind":
                "function.step.execution",
            "payload": {
                "step":
                    step_ref,
                "execution":
                    execution_ref,
                "status":
                    state,
                "input_digest":
                    (
                        str(
                            input_digest
                        ).strip()
                        if input_digest
                        else None
                    ),
                "output_digest":
                    (
                        str(
                            output_digest
                        ).strip()
                        if output_digest
                        else None
                    ),
                "previous_execution":
                    (
                        previous
                        or None
                    ),
            },
            "metadata":
                deepcopy(
                    dict(
                        metadata
                        or {}
                    )
                ),
            "dependencies":
                sorted(
                    dependency_ids
                ),
            "provenance":
                provenance,
            "lineage":
                lineage,
        }
    )


def validate_function_steps(
    *,
    function_record: Mapping[str, Any],
    instances: Mapping[
        str,
        Mapping[str, Any],
    ],
) -> dict[str, Any]:
    if (
        function_record.get(
            "kind"
        )
        != "function"
    ):
        raise StraubValidationError(
            "function-step validation "
            "requires function instance"
        )

    payload = function_record.get(
        "payload"
    )

    if not isinstance(
        payload,
        Mapping,
    ):
        raise StraubValidationError(
            "function payload missing"
        )

    step_ids = normalize_string_list(
        payload.get(
            "steps"
        )
    )

    if not step_ids:
        raise StraubValidationError(
            "function has no steps"
        )

    ordered: list[
        tuple[
            int,
            str,
        ]
    ] = []

    for step_id in step_ids:
        step = instances.get(
            step_id
        )

        if step is None:
            raise StraubValidationError(
                "function step missing: "
                f"{step_id}"
            )

        if (
            step.get(
                "kind"
            )
            != "function.step"
        ):
            raise StraubValidationError(
                "function member is not "
                "function.step: "
                f"{step_id}"
            )

        step_payload = step.get(
            "payload"
        )

        if not isinstance(
            step_payload,
            Mapping,
        ):
            raise StraubValidationError(
                "function step payload missing: "
                f"{step_id}"
            )

        ordinal = step_payload.get(
            "ordinal"
        )

        if (
            not isinstance(
                ordinal,
                int,
            )
            or isinstance(
                ordinal,
                bool,
            )
            or ordinal < 1
        ):
            raise StraubValidationError(
                "function step ordinal invalid: "
                f"{step_id}"
            )

        ordered.append(
            (
                ordinal,
                step_id,
            )
        )

    ordinals = [
        ordinal
        for ordinal, _
        in ordered
    ]

    if (
        len(
            ordinals
        )
        != len(
            set(
                ordinals
            )
        )
    ):
        raise StraubValidationError(
            "function contains duplicate "
            "step ordinals"
        )

    ordered.sort()

    expected = list(
        range(
            1,
            len(
                ordered
            )
            + 1,
        )
    )

    actual = [
        ordinal
        for ordinal, _
        in ordered
    ]

    if actual != expected:
        raise StraubValidationError(
            "function step ordinals "
            "must be contiguous"
        )

    projection = {
        "schema":
            "savant.straub."
            "function-steps-isotope.v1",
        "kind":
            "isotope",
        "function":
            str(
                function_record.get(
                    "id"
                )
                or ""
            ),
        "step_count":
            len(
                ordered
            ),
        "steps":
            [
                {
                    "ordinal":
                        ordinal,
                    "step":
                        step_id,
                    "digest":
                        str(
                            instances[
                                step_id
                            ].get(
                                "digest"
                            )
                            or ""
                        ),
                }
                for ordinal, step_id
                in ordered
            ],
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


def execution_trace(
    *,
    function_id: str,
    execution_id: str,
    instances: Mapping[
        str,
        Mapping[str, Any],
    ],
) -> dict[str, Any]:
    function_ref = str(
        function_id or ""
    ).strip()

    execution_ref = str(
        execution_id or ""
    ).strip()

    if not function_ref:
        raise StraubValidationError(
            "execution trace requires "
            "function_id"
        )

    if not execution_ref:
        raise StraubValidationError(
            "execution trace requires "
            "execution_id"
        )

    function_record = instances.get(
        function_ref
    )

    if function_record is None:
        raise StraubValidationError(
            "function instance missing: "
            f"{function_ref}"
        )

    steps_projection = (
        validate_function_steps(
            function_record=(
                function_record
            ),
            instances=instances,
        )
    )

    step_order = {
        row[
            "step"
        ]:
            row[
                "ordinal"
            ]
        for row
        in steps_projection[
            "steps"
        ]
    }

    executions: list[
        dict[str, Any]
    ] = []

    for record in instances.values():
        if (
            record.get(
                "kind"
            )
            != "function.step.execution"
        ):
            continue

        payload = record.get(
            "payload"
        )

        if not isinstance(
            payload,
            Mapping,
        ):
            continue

        if (
            str(
                payload.get(
                    "execution"
                )
                or ""
            )
            != execution_ref
        ):
            continue

        step_id = str(
            payload.get(
                "step"
            )
            or ""
        )

        if step_id not in step_order:
            continue

        executions.append(
            {
                "ordinal":
                    step_order[
                        step_id
                    ],
                "step":
                    step_id,
                "execution_instance":
                    str(
                        record.get(
                            "id"
                        )
                        or ""
                    ),
                "status":
                    str(
                        payload.get(
                            "status"
                        )
                        or ""
                    ),
                "input_digest":
                    payload.get(
                        "input_digest"
                    ),
                "output_digest":
                    payload.get(
                        "output_digest"
                    ),
                "previous_execution":
                    payload.get(
                        "previous_execution"
                    ),
                "digest":
                    str(
                        record.get(
                            "digest"
                        )
                        or ""
                    ),
            }
        )

    executions.sort(
        key=lambda row: (
            row[
                "ordinal"
            ],
            row[
                "execution_instance"
            ],
        )
    )

    ordinal_counts: dict[
        int,
        int,
    ] = {}

    for row in executions:
        ordinal = int(
            row[
                "ordinal"
            ]
        )

        ordinal_counts[
            ordinal
        ] = (
            ordinal_counts.get(
                ordinal,
                0,
            )
            + 1
        )

    duplicate_ordinals = sorted(
        ordinal
        for ordinal, count
        in ordinal_counts.items()
        if count > 1
    )

    covered = sorted(
        ordinal_counts
    )

    expected = list(
        range(
            1,
            steps_projection[
                "step_count"
            ]
            + 1,
        )
    )

    projection = {
        "schema":
            "savant.straub."
            "step-execution-trace-isotope.v1",
        "kind":
            "isotope",
        "function":
            function_ref,
        "execution":
            execution_ref,
        "step_count":
            steps_projection[
                "step_count"
            ],
        "execution_record_count":
            len(
                executions
            ),
        "covered_ordinals":
            covered,
        "duplicate_ordinals":
            duplicate_ordinals,
        "complete":
            (
                covered
                == expected
                and not duplicate_ordinals
            ),
        "executions":
            executions,
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

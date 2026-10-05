#!/usr/bin/env python3

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence


from runtime.living_governance import (
    stream_records,
)

from runtime.living_policy import (
    evaluate_predicate,
)


owner = "living-governance"
authority_effect = "none"
stream = "masterplan"

complete_statuses = {
    "complete",
    "completed",
    "done",
}

blocked_statuses = {
    "blocked",
    "waiting",
}

open_statuses = {
    "active",
    "planned",
    "ready",
    "in_progress",
}


class living_plan_evidence_error(
    RuntimeError
):
    pass


def records() -> list[dict[str, Any]]:
    return [
        dict(
            record
        )
        for record
        in stream_records(
            stream
        )
    ]


def completion_state(
    record: Mapping[str, Any],
) -> str:
    return str(
        record.get(
            "status",
            "active",
        )
    ).strip().lower()


def evidence_ids(
    evidence: Sequence[Any],
) -> set[str]:
    output = set()

    for item in evidence:
        if isinstance(
            item,
            Mapping,
        ):
            identifier = item.get(
                "id"
            )

            if identifier is not None:
                output.add(
                    str(
                        identifier
                    )
                )

        else:
            output.add(
                str(
                    item
                )
            )

    return output


def evaluate_criterion(
    criterion: Any,
    context: Mapping[str, Any],
    present_evidence: set[str],
) -> dict[str, Any]:
    if isinstance(
        criterion,
        str,
    ):
        satisfied = (
            criterion
            in present_evidence
        )

        return {
            "kind":
                "evidence",

            "id":
                criterion,

            "satisfied":
                satisfied,

            "outcome":
                (
                    "pass"
                    if satisfied
                    else "unknown"
                ),

            "reason":
                (
                    "required evidence is present"
                    if satisfied
                    else "required evidence is absent"
                ),
        }

    if not isinstance(
        criterion,
        Mapping,
    ):
        return {
            "kind":
                "invalid",

            "satisfied":
                None,

            "outcome":
                "unknown",

            "reason":
                (
                    "completion criterion must be "
                    "a string or object"
                ),
        }

    if "evidence_id" in criterion:
        identifier = str(
            criterion.get(
                "evidence_id",
                "",
            )
        ).strip()

        if not identifier:
            return {
                "kind":
                    "evidence",

                "satisfied":
                    None,

                "outcome":
                    "unknown",

                "reason":
                    "evidence_id is empty",
            }

        satisfied = (
            identifier
            in present_evidence
        )

        return {
            "kind":
                "evidence",

            "id":
                identifier,

            "satisfied":
                satisfied,

            "outcome":
                (
                    "pass"
                    if satisfied
                    else "unknown"
                ),

            "reason":
                (
                    "required evidence is present"
                    if satisfied
                    else "required evidence is absent"
                ),
        }

    predicate = (
        criterion.get(
            "predicate"
        )
        if "predicate" in criterion
        else criterion
    )

    result = evaluate_predicate(
        predicate,
        context,
    )

    predicate_result = result.get(
        "result"
    )

    return {
        "kind":
            "predicate",

        "satisfied":
            predicate_result,

        "outcome":
            (
                "pass"
                if predicate_result is True
                else (
                    "fail"
                    if predicate_result is False
                    else "unknown"
                )
            ),

        "reason":
            (
                "completion predicate satisfied"
                if predicate_result is True
                else (
                    "completion predicate failed"
                    if predicate_result is False
                    else (
                        "completion predicate could "
                        "not be resolved"
                    )
                )
            ),

        "trace":
            result.get(
                "trace",
                [],
            ),
    }


def completion_evaluation(
    record: Mapping[str, Any],
    *,
    evidence: Sequence[Any] | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    criteria = record.get(
        "completion_criteria",
        []
    )

    if criteria is None:
        criteria = []

    if not isinstance(
        criteria,
        list,
    ):
        return {
            "schema":
                (
                    "savant.living-plan."
                    "completion-evaluation.v1"
                ),

            "id":
                record.get(
                    "id"
                ),

            "criteria_defined":
                True,

            "criteria_count":
                0,

            "satisfied":
                None,

            "outcome":
                "unknown",

            "reason":
                "completion_criteria is not a list",

            "criteria": [],
        }

    present = evidence_ids(
        list(
            evidence
            or []
        )
    )

    evaluation_context = dict(
        context
        or {}
    )

    evaluation_context.setdefault(
        "evidence",
        list(
            evidence
            or []
        ),
    )

    evaluations = [
        evaluate_criterion(
            criterion,
            evaluation_context,
            present,
        )
        for criterion
        in criteria
    ]

    if not criteria:
        satisfied: bool | None = None
        outcome = "unknown"
        reason = (
            "no authoritative completion "
            "criteria are defined"
        )

    elif any(
        item.get(
            "satisfied"
        )
        is False
        for item
        in evaluations
    ):
        satisfied = False
        outcome = "fail"
        reason = (
            "one or more completion "
            "criteria failed"
        )

    elif any(
        item.get(
            "satisfied"
        )
        is None
        or item.get(
            "outcome"
        )
        == "unknown"
        for item
        in evaluations
    ):
        satisfied = None
        outcome = "unknown"
        reason = (
            "completion cannot be established "
            "from available evidence"
        )

    else:
        satisfied = True
        outcome = "pass"
        reason = (
            "all authoritative completion "
            "criteria are satisfied"
        )

    return {
        "schema":
            (
                "savant.living-plan."
                "completion-evaluation.v1"
            ),

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "id":
            record.get(
                "id"
            ),

        "criteria_defined":
            bool(
                criteria
            ),

        "criteria_count":
            len(
                criteria
            ),

        "satisfied":
            satisfied,

        "outcome":
            outcome,

        "reason":
            reason,

        "criteria":
            evaluations,
    }


def dependency_state(
    record: Mapping[str, Any],
    index: Mapping[
        str,
        Mapping[
            str,
            Any,
        ]
    ],
) -> dict[str, Any]:
    dependencies = [
        str(
            value
        )
        for value
        in record.get(
            "dependencies",
            [],
        )
    ]

    unresolved = []

    incomplete = []

    complete = []

    for dependency in dependencies:
        dependency_record = index.get(
            dependency
        )

        if dependency_record is None:
            unresolved.append(
                dependency
            )

            continue

        state = completion_state(
            dependency_record
        )

        if state in complete_statuses:
            complete.append(
                dependency
            )

        else:
            incomplete.append(
                {
                    "id":
                        dependency,

                    "status":
                        state,
                }
            )

    ready = (
        not unresolved
        and not incomplete
    )

    return {
        "ready":
            ready,

        "dependencies":
            dependencies,

        "complete":
            complete,

        "incomplete":
            incomplete,

        "unresolved":
            unresolved,
    }


def evaluate_record(
    record: Mapping[str, Any],
    *,
    index: Mapping[
        str,
        Mapping[
            str,
            Any,
        ]
    ],
    evidence: Sequence[Any] | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    state = completion_state(
        record
    )

    dependencies = dependency_state(
        record,
        index,
    )

    completion = completion_evaluation(
        record,
        evidence=evidence,
        context=context,
    )

    already_complete = (
        state
        in complete_statuses
    )

    explicitly_blocked = (
        state
        in blocked_statuses
    )

    if already_complete:
        recommended_action = "none"

    elif explicitly_blocked:
        recommended_action = "blocked"

    elif not dependencies[
        "ready"
    ]:
        recommended_action = "wait-dependencies"

    elif completion[
        "satisfied"
    ] is True:
        recommended_action = "mark-complete"

    else:
        recommended_action = "work"

    return {
        "id":
            record.get(
                "id"
            ),

        "status":
            state,

        "priority":
            int(
                record.get(
                    "priority",
                    1000,
                )
            ),

        "text":
            record.get(
                "text"
            ),

        "dependency_ready":
            dependencies[
                "ready"
            ],

        "dependencies":
            dependencies,

        "completion":
            completion,

        "completion_ready":
            completion[
                "satisfied"
            ]
            is True,

        "recommended_action":
            recommended_action,
    }


def projection(
    *,
    evidence: Sequence[Any] | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    values = records()

    index = {
        str(
            record.get(
                "id"
            )
        ):
            record
        for record
        in values
        if record.get(
            "id"
        )
    }

    evaluated = [
        evaluate_record(
            record,
            index=index,
            evidence=evidence,
            context=context,
        )
        for record
        in values
    ]

    action_counts = defaultdict(
        int
    )

    for item in evaluated:
        action_counts[
            str(
                item[
                    "recommended_action"
                ]
            )
        ] += 1

    next_items = sorted(
        [
            item
            for item
            in evaluated
            if item[
                "recommended_action"
            ]
            in {
                "mark-complete",
                "work",
            }
        ],
        key=lambda item: (
            0
            if item[
                "recommended_action"
            ]
            == "mark-complete"
            else 1,
            int(
                item[
                    "priority"
                ]
            ),
            str(
                item[
                    "id"
                ]
            ),
        ),
    )

    return {
        "schema":
            (
                "savant.living-plan."
                "evidence-projection.v1"
            ),

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "stream":
            stream,

        "projection_only":
            True,

        "auto_mutation":
            False,

        "record_count":
            len(
                evaluated
            ),

        "action_counts":
            dict(
                sorted(
                    action_counts.items()
                )
            ),

        "next":
            next_items,

        "records":
            sorted(
                evaluated,
                key=lambda item: (
                    int(
                        item[
                            "priority"
                        ]
                    ),
                    str(
                        item[
                            "id"
                        ]
                    ),
                ),
            ),
    }


def one(
    semantic_id: str,
    *,
    evidence: Sequence[Any] | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    values = records()

    index = {
        str(
            record.get(
                "id"
            )
        ):
            record
        for record
        in values
        if record.get(
            "id"
        )
    }

    record = index.get(
        semantic_id
    )

    if record is None:
        raise living_plan_evidence_error(
            (
                "unknown masterplan id: "
                + semantic_id
            )
        )

    return {
        "schema":
            (
                "savant.living-plan."
                "evidence-record.v1"
            ),

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "record":
            evaluate_record(
                record,
                index=index,
                evidence=evidence,
                context=context,
            ),
    }


def status() -> dict[str, Any]:
    values = records()

    criteria_records = [
        record
        for record
        in values
        if record.get(
            "completion_criteria"
        )
    ]

    return {
        "schema":
            (
                "savant.living-plan."
                "evidence-status.v1"
            ),

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "stream":
            stream,

        "masterplan_records":
            len(
                values
            ),

        "records_with_completion_criteria":
            len(
                criteria_records
            ),

        "projection_only":
            True,

        "auto_completion":
            False,

        "operations": [
            "status",
            "show",
            "next",
        ],

        "ready":
            True,
    }


__all__ = [
    "completion_evaluation",
    "evaluate_criterion",
    "evaluate_record",
    "one",
    "projection",
    "status",
]

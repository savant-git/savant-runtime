#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import heapq
import json

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Mapping, Sequence


from oriel import (
    oriel_engine,
    oriel_error,
    parse_datetime,
    to_utc,
)


owner = "carbon"
component = "oriel-inverse"
authority_effect = "none"

schema = "savant.carbon.oriel-inverse.v1"

mutable_source_classes = {
    "simulation",
    "derived",
    "estimate",
    "unknown",
}

immutable_source_classes = {
    "verified_external",
    "admitted_evidence",
}

classifications = {
    "pass":
        "viable",

    "advisory":
        "conditional",

    "unknown":
        "unresolved",

    "fail":
        "infeasible",
}

enhancements = (
    "desired-event inverse search",
    "best-first counterfactual repair search",
    "minimal-edit preference",
    "weighted temporal displacement cost",
    "historical-anchor immutability",
    "admitted-evidence immutability",
    "locked-event immutability",
    "explicit mutable override support",
    "candidate temporal displacement",
    "candidate geographic relocation",
    "transport-mode alternatives",
    "blocking-event extraction",
    "prior-event backward displacement",
    "future-event forward displacement",
    "bounded uncertainty preservation",
    "source-class preservation",
    "external-constraint preservation",
    "branch-local document projection",
    "non-mutating repair states",
    "deterministic state identity",
    "duplicate-state suppression",
    "search-budget enforcement",
    "search-depth enforcement",
    "temporal-resolution control",
    "maximum-shift enforcement",
    "lexicographic repair ranking",
    "repair provenance",
    "reason-code ancestry",
    "constraint ancestry",
    "feasibility delta reporting",
    "nearest-viable solution",
    "multiple viable alternatives",
    "conditional-solution retention",
    "unresolved-solution retention",
    "historical violation rejection",
    "minimum prior intervention discovery",
    "candidate-only zero-history repair",
    "earlier-history intervention classification",
    "future-history intervention classification",
    "spacetime intervention classification",
    "quantum-ready repair packets",
    "canon-neutral output",
    "evidence-neutral output",
    "source-state preservation",
)


class oriel_inverse_error(
    RuntimeError
):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
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


def stable_id(
    prefix: str,
    value: Any,
) -> str:
    return (
        prefix
        + ":"
        + digest(
            value
        )[
            :24
        ]
    )


def clone(
    value: Any,
) -> Any:
    return copy.deepcopy(
        value
    )


def normalized_strings(
    value: Sequence[Any] | None,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(
                    item
                ).strip()
                for item
                in (
                    value
                    or []
                )
                if str(
                    item
                ).strip()
            }
        )
    )


def classification(
    evaluation: Mapping[str, Any],
) -> str:
    outcome = str(
        evaluation.get(
            "outcome",
            "unknown",
        )
    ).strip().lower()

    return classifications.get(
        outcome,
        "unresolved",
    )


def reason_codes(
    evaluation: Mapping[str, Any],
) -> list[str]:
    validation = evaluation.get(
        "validation",
        evaluation,
    )

    if not isinstance(
        validation,
        Mapping,
    ):
        return []

    return sorted(
        {
            str(
                check.get(
                    "reason_code",
                    "",
                )
            ).strip()
            for check
            in validation.get(
                "checks",
                []
            )
            if (
                isinstance(
                    check,
                    Mapping,
                )
                and str(
                    check.get(
                        "reason_code",
                        "",
                    )
                ).strip()
            )
        }
    )


def blocking_event_ids(
    evaluation: Mapping[str, Any],
    candidate_id: str,
) -> list[str]:
    validation = evaluation.get(
        "validation",
        evaluation,
    )

    if not isinstance(
        validation,
        Mapping,
    ):
        return []

    output = set()

    for check in validation.get(
        "checks",
        [],
    ):
        if not isinstance(
            check,
            Mapping,
        ):
            continue

        if check.get(
            "outcome"
        ) not in {
            "fail",
            "advisory",
            "unknown",
        }:
            continue

        evidence = check.get(
            "evidence"
        )

        if not isinstance(
            evidence,
            Mapping,
        ):
            continue

        for key in (
            "previous",
            "current",
            "left",
            "right",
            "event",
        ):
            value = evidence.get(
                key
            )

            if (
                value is not None
                and str(
                    value
                )
                != candidate_id
            ):
                output.add(
                    str(
                        value
                    )
                )

    return sorted(
        output
    )


def event_index(
    document: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    result = {}

    for value in document.get(
        "events",
        [],
    ):
        if not isinstance(
            value,
            Mapping,
        ):
            continue

        identifier = str(
            value.get(
                "id",
                "",
            )
        ).strip()

        if identifier:
            result[
                identifier
            ] = clone(
                dict(
                    value
                )
            )

    return result


def event_source_class(
    event_value: Mapping[str, Any],
) -> str:
    return str(
        event_value.get(
            "source_class",
            "unknown",
        )
    ).strip().lower()


def temporal_locked(
    value: Any,
) -> bool:
    return bool(
        isinstance(
            value,
            Mapping,
        )
        and value.get(
            "locked",
            False,
        )
    )


def event_locked(
    event_value: Mapping[str, Any],
) -> bool:
    metadata = event_value.get(
        "metadata"
    )

    metadata_locked = (
        isinstance(
            metadata,
            Mapping,
        )
        and bool(
            metadata.get(
                "locked",
                False,
            )
        )
    )

    return (
        bool(
            event_value.get(
                "locked",
                False,
            )
        )
        or metadata_locked
        or temporal_locked(
            event_value.get(
                "start"
            )
        )
        or temporal_locked(
            event_value.get(
                "end"
            )
        )
    )


def event_mutable(
    event_value: Mapping[str, Any],
) -> bool:
    if event_locked(
        event_value
    ):
        return False

    metadata = event_value.get(
        "metadata"
    )

    if (
        isinstance(
            metadata,
            Mapping,
        )
        and metadata.get(
            "mutable"
        )
        is True
    ):
        return True

    source_class = event_source_class(
        event_value
    )

    if (
        source_class
        in immutable_source_classes
    ):
        return False

    return (
        source_class
        in mutable_source_classes
    )


def datetime_from_temporal(
    value: Any,
) -> datetime:
    if isinstance(
        value,
        Mapping,
    ):
        if value.get(
            "at"
        ) is not None:
            return parse_datetime(
                value[
                    "at"
                ],
                timezone_name=(
                    str(
                        value.get(
                            "timezone"
                        )
                    )
                    if value.get(
                        "timezone"
                    )
                    is not None
                    else None
                ),
            )

        if value.get(
            "earliest"
        ) is not None:
            return parse_datetime(
                value[
                    "earliest"
                ],
                timezone_name=(
                    str(
                        value.get(
                            "timezone"
                        )
                    )
                    if value.get(
                        "timezone"
                    )
                    is not None
                    else None
                ),
            )

    return parse_datetime(
        value
    )


def event_start_time(
    event_value: Mapping[str, Any],
) -> datetime:
    return to_utc(
        datetime_from_temporal(
            event_value.get(
                "start"
            )
        )
    )


def shift_datetime_text(
    value: str,
    minutes: int,
) -> str:
    parsed = parse_datetime(
        value
    )

    return (
        parsed
        + timedelta(
            minutes=minutes
        )
    ).isoformat()


def shift_temporal(
    value: Any,
    minutes: int,
) -> Any:
    if value is None:
        return None

    if isinstance(
        value,
        str,
    ):
        return shift_datetime_text(
            value,
            minutes,
        )

    if isinstance(
        value,
        datetime,
    ):
        return (
            value
            + timedelta(
                minutes=minutes
            )
        ).isoformat()

    if not isinstance(
        value,
        Mapping,
    ):
        raise oriel_inverse_error(
            (
                "unsupported temporal value "
                "for inverse shift"
            )
        )

    output = clone(
        dict(
            value
        )
    )

    timezone_name = (
        str(
            value.get(
                "timezone"
            )
        )
        if value.get(
            "timezone"
        )
        is not None
        else None
    )

    for key in (
        "at",
        "earliest",
        "latest",
    ):
        if value.get(
            key
        ) is None:
            continue

        parsed = parse_datetime(
            value[
                key
            ],
            timezone_name=
                timezone_name,
        )

        output[
            key
        ] = (
            parsed
            + timedelta(
                minutes=minutes
            )
        ).isoformat()

    return output


def shift_event(
    event_value: Mapping[str, Any],
    minutes: int,
) -> dict[str, Any]:
    output = clone(
        dict(
            event_value
        )
    )

    output[
        "start"
    ] = shift_temporal(
        output.get(
            "start"
        ),
        minutes,
    )

    if output.get(
        "end"
    ) is not None:
        output[
            "end"
        ] = shift_temporal(
            output.get(
                "end"
            ),
            minutes,
        )

    return output


def replace_event(
    document: Mapping[str, Any],
    replacement: Mapping[str, Any],
) -> dict[str, Any]:
    identifier = str(
        replacement.get(
            "id",
            "",
        )
    ).strip()

    output = clone(
        dict(
            document
        )
    )

    values = []

    replaced = False

    for event_value in output.get(
        "events",
        [],
    ):
        if (
            isinstance(
                event_value,
                Mapping,
            )
            and str(
                event_value.get(
                    "id",
                    "",
                )
            )
            == identifier
        ):
            values.append(
                clone(
                    dict(
                        replacement
                    )
                )
            )

            replaced = True

        else:
            values.append(
                clone(
                    event_value
                )
            )

    if not replaced:
        raise oriel_inverse_error(
            (
                "event does not exist: "
                + identifier
            )
        )

    output[
        "events"
    ] = values

    return output


@dataclass(
    frozen=True,
    slots=True,
)
class SearchPolicy:
    resolution_minutes: int = 30

    maximum_candidate_shift_minutes:
        int = 1440

    maximum_existing_shift_minutes:
        int = 720

    maximum_depth:
        int = 3

    maximum_states:
        int = 500

    solution_limit:
        int = 8

    candidate_shift_cost:
        float = 1.0

    existing_shift_cost:
        float = 4.0

    location_change_cost:
        float = 240.0

    mode_change_cost:
        float = 180.0

    edit_cost:
        float = 25.0

    conditional_penalty:
        float = 500.0

    unresolved_penalty:
        float = 1000.0

    earlier_change_bonus:
        float = 0.0

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[
            str,
            Any,
        ] | None,
    ) -> SearchPolicy:
        values = dict(
            value
            or {}
        )

        result = cls(
            resolution_minutes=int(
                values.get(
                    "resolution_minutes",
                    30,
                )
            ),
            maximum_candidate_shift_minutes=int(
                values.get(
                    "maximum_candidate_shift_minutes",
                    1440,
                )
            ),
            maximum_existing_shift_minutes=int(
                values.get(
                    "maximum_existing_shift_minutes",
                    720,
                )
            ),
            maximum_depth=int(
                values.get(
                    "maximum_depth",
                    3,
                )
            ),
            maximum_states=int(
                values.get(
                    "maximum_states",
                    500,
                )
            ),
            solution_limit=int(
                values.get(
                    "solution_limit",
                    8,
                )
            ),
            candidate_shift_cost=float(
                values.get(
                    "candidate_shift_cost",
                    1.0,
                )
            ),
            existing_shift_cost=float(
                values.get(
                    "existing_shift_cost",
                    4.0,
                )
            ),
            location_change_cost=float(
                values.get(
                    "location_change_cost",
                    240.0,
                )
            ),
            mode_change_cost=float(
                values.get(
                    "mode_change_cost",
                    180.0,
                )
            ),
            edit_cost=float(
                values.get(
                    "edit_cost",
                    25.0,
                )
            ),
            conditional_penalty=float(
                values.get(
                    "conditional_penalty",
                    500.0,
                )
            ),
            unresolved_penalty=float(
                values.get(
                    "unresolved_penalty",
                    1000.0,
                )
            ),
            earlier_change_bonus=float(
                values.get(
                    "earlier_change_bonus",
                    0.0,
                )
            ),
        )

        if result.resolution_minutes <= 0:
            raise oriel_inverse_error(
                (
                    "resolution_minutes "
                    "must be positive"
                )
            )

        if result.maximum_depth < 0:
            raise oriel_inverse_error(
                (
                    "maximum_depth may not "
                    "be negative"
                )
            )

        if result.maximum_states <= 0:
            raise oriel_inverse_error(
                (
                    "maximum_states must "
                    "be positive"
                )
            )

        if result.solution_limit <= 0:
            raise oriel_inverse_error(
                (
                    "solution_limit must "
                    "be positive"
                )
            )

        return result


@dataclass(
    slots=True,
)
class SearchState:
    document: dict[str, Any]

    candidate: dict[str, Any]

    mode: str

    edits: list[dict[str, Any]]

    cost: float

    depth: int

    candidate_shift_minutes: int = 0

    existing_shifts: dict[str, int] | None = None

    def __post_init__(
        self,
    ) -> None:
        if self.existing_shifts is None:
            self.existing_shifts = {}

    def identity(
        self,
    ) -> str:
        return digest(
            {
                "document":
                    self.document,

                "candidate":
                    self.candidate,

                "mode":
                    self.mode,
            }
        )


def edit_cost(
    policy: SearchPolicy,
    *,
    kind: str,
    minutes: int = 0,
) -> float:
    if kind == "candidate-time":
        variable = (
            abs(
                minutes
            )
            * policy.candidate_shift_cost
        )

    elif kind == "existing-time":
        variable = (
            abs(
                minutes
            )
            * policy.existing_shift_cost
        )

    elif kind == "location":
        variable = (
            policy.location_change_cost
        )

    elif kind == "mode":
        variable = (
            policy.mode_change_cost
        )

    else:
        variable = 0.0

    return (
        variable
        + policy.edit_cost
    )


def evaluation_rank_penalty(
    label: str,
    policy: SearchPolicy,
) -> float:
    if label == "conditional":
        return policy.conditional_penalty

    if label == "unresolved":
        return policy.unresolved_penalty

    if label == "infeasible":
        return (
            policy.unresolved_penalty
            * 2
        )

    return 0.0


def solution_rank(
    value: Mapping[str, Any],
) -> tuple[
    int,
    int,
    float,
    int,
    str,
]:
    label = str(
        value.get(
            "classification",
            "unresolved",
        )
    )

    class_rank = {
        "viable":
            0,

        "conditional":
            1,

        "unresolved":
            2,

        "infeasible":
            3,
    }.get(
        label,
        4,
    )

    edits = value.get(
        "edits",
        []
    )

    historical_edit_count = sum(
        1
        for edit
        in edits
        if (
            isinstance(
                edit,
                Mapping,
            )
            and edit.get(
                "target_class"
            )
            == "existing-event"
        )
    )

    return (
        class_rank,
        historical_edit_count,
        float(
            value.get(
                "cost",
                0.0,
            )
        ),
        len(
            edits
        ),
        str(
            value.get(
                "id",
                "",
            )
        ),
    )


class OrielInverseEngine:
    def _evaluate(
        self,
        state: SearchState,
    ) -> dict[str, Any]:
        engine = (
            oriel_engine.from_document(
                state.document
            )
        )

        result = engine.evaluate_candidate(
            state.candidate,
            mode=state.mode,
        )

        return {
            "evaluation":
                result,

            "classification":
                classification(
                    result
                ),

            "reason_codes":
                reason_codes(
                    result
                ),

            "blocking_event_ids":
                blocking_event_ids(
                    result,
                    str(
                        state.candidate.get(
                            "id",
                            "",
                        )
                    ),
                ),
        }

    def _solution(
        self,
        state: SearchState,
        evaluation: Mapping[str, Any],
        *,
        source_document_digest: str,
        source_candidate_digest: str,
    ) -> dict[str, Any]:
        label = str(
            evaluation[
                "classification"
            ]
        )

        history_edits = [
            edit
            for edit
            in state.edits
            if (
                edit.get(
                    "target_class"
                )
                == "existing-event"
            )
        ]

        earlier = [
            edit
            for edit
            in history_edits
            if edit.get(
                "temporal_direction"
            )
            == "earlier"
        ]

        later = [
            edit
            for edit
            in history_edits
            if edit.get(
                "temporal_direction"
            )
            == "later"
        ]

        material = {
            "source_document_digest":
                source_document_digest,

            "source_candidate_digest":
                source_candidate_digest,

            "candidate":
                state.candidate,

            "document":
                state.document,

            "mode":
                state.mode,

            "edits":
                state.edits,

            "classification":
                label,
        }

        return {
            "schema":
                schema,

            "kind":
                "inverse-solution",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "id":
                stable_id(
                    "carbon-oriel-inverse-solution",
                    material,
                ),

            "classification":
                label,

            "cost":
                round(
                    state.cost,
                    6,
                ),

            "depth":
                state.depth,

            "mode":
                state.mode,

            "candidate":
                clone(
                    state.candidate
                ),

            "candidate_document":
                clone(
                    state.document
                ),

            "candidate_document_digest":
                digest(
                    state.document
                ),

            "edits":
                clone(
                    state.edits
                ),

            "edit_count":
                len(
                    state.edits
                ),

            "existing_event_edit_count":
                len(
                    history_edits
                ),

            "earlier_intervention_count":
                len(
                    earlier
                ),

            "later_intervention_count":
                len(
                    later
                ),

            "candidate_only":
                not history_edits,

            "minimum_prior_intervention":
                (
                    len(
                        history_edits
                    )
                    == 1
                ),

            "reason_codes":
                list(
                    evaluation[
                        "reason_codes"
                    ]
                ),

            "blocking_event_ids":
                list(
                    evaluation[
                        "blocking_event_ids"
                    ]
                ),

            "evaluation":
                clone(
                    evaluation[
                        "evaluation"
                    ]
                ),

            "source_state_mutated":
                False,

            "canon_effect":
                "none",

            "evidence_admission":
                False,

            "requires_explicit_selection":
                True,
        }

    def _candidate_time_neighbors(
        self,
        state: SearchState,
        policy: SearchPolicy,
    ) -> list[SearchState]:
        output = []

        for delta in (
            -policy.resolution_minutes,
            policy.resolution_minutes,
        ):
            total = (
                state.candidate_shift_minutes
                + delta
            )

            if (
                abs(
                    total
                )
                > policy.maximum_candidate_shift_minutes
            ):
                continue

            candidate = shift_event(
                state.candidate,
                delta,
            )

            direction = (
                "earlier"
                if delta < 0
                else "later"
            )

            edit = {
                "kind":
                    "temporal-shift",

                "target_class":
                    "candidate-event",

                "target":
                    state.candidate.get(
                        "id"
                    ),

                "minutes":
                    delta,

                "cumulative_minutes":
                    total,

                "temporal_direction":
                    direction,

                "authority_effect":
                    "none",
            }

            output.append(
                SearchState(
                    document=clone(
                        state.document
                    ),
                    candidate=candidate,
                    mode=state.mode,
                    edits=[
                        *clone(
                            state.edits
                        ),
                        edit,
                    ],
                    cost=(
                        state.cost
                        + edit_cost(
                            policy,
                            kind="candidate-time",
                            minutes=delta,
                        )
                    ),
                    depth=(
                        state.depth
                        + 1
                    ),
                    candidate_shift_minutes=
                        total,
                    existing_shifts=
                        clone(
                            state.existing_shifts
                        ),
                )
            )

        return output

    def _location_neighbors(
        self,
        state: SearchState,
        candidate_locations:
            Sequence[str],
        policy: SearchPolicy,
    ) -> list[SearchState]:
        output = []

        current = str(
            state.candidate.get(
                "location_id",
                "",
            )
        )

        for location_id in (
            candidate_locations
        ):
            destination = str(
                location_id
            ).strip()

            if (
                not destination
                or destination == current
            ):
                continue

            candidate = clone(
                state.candidate
            )

            candidate[
                "location_id"
            ] = destination

            output.append(
                SearchState(
                    document=clone(
                        state.document
                    ),
                    candidate=candidate,
                    mode=state.mode,
                    edits=[
                        *clone(
                            state.edits
                        ),
                        {
                            "kind":
                                "location-change",

                            "target_class":
                                "candidate-event",

                            "target":
                                candidate.get(
                                    "id"
                                ),

                            "from":
                                current,

                            "to":
                                destination,

                            "authority_effect":
                                "none",
                        },
                    ],
                    cost=(
                        state.cost
                        + edit_cost(
                            policy,
                            kind="location",
                        )
                    ),
                    depth=(
                        state.depth
                        + 1
                    ),
                    candidate_shift_minutes=
                        state.candidate_shift_minutes,
                    existing_shifts=
                        clone(
                            state.existing_shifts
                        ),
                )
            )

        return output

    def _mode_neighbors(
        self,
        state: SearchState,
        transport_modes:
            Sequence[str],
        policy: SearchPolicy,
    ) -> list[SearchState]:
        output = []

        for mode in transport_modes:
            candidate_mode = str(
                mode
            ).strip().lower()

            if (
                not candidate_mode
                or candidate_mode
                == state.mode
            ):
                continue

            output.append(
                SearchState(
                    document=clone(
                        state.document
                    ),
                    candidate=clone(
                        state.candidate
                    ),
                    mode=candidate_mode,
                    edits=[
                        *clone(
                            state.edits
                        ),
                        {
                            "kind":
                                "transport-mode-change",

                            "target_class":
                                "simulation-logistics",

                            "from":
                                state.mode,

                            "to":
                                candidate_mode,

                            "authority_effect":
                                "none",
                        },
                    ],
                    cost=(
                        state.cost
                        + edit_cost(
                            policy,
                            kind="mode",
                        )
                    ),
                    depth=(
                        state.depth
                        + 1
                    ),
                    candidate_shift_minutes=
                        state.candidate_shift_minutes,
                    existing_shifts=
                        clone(
                            state.existing_shifts
                        ),
                )
            )

        return output

    def _existing_event_neighbors(
        self,
        state: SearchState,
        blocking_ids:
            Sequence[str],
        policy: SearchPolicy,
    ) -> list[SearchState]:
        index = event_index(
            state.document
        )

        output = []

        candidate_time = event_start_time(
            state.candidate
        )

        for identifier in blocking_ids:
            value = index.get(
                identifier
            )

            if value is None:
                continue

            if not event_mutable(
                value
            ):
                continue

            current_total = (
                state.existing_shifts
                or {}
            ).get(
                identifier,
                0,
            )

            existing_time = (
                event_start_time(
                    value
                )
            )

            if existing_time <= candidate_time:
                deltas = (
                    -policy.resolution_minutes,
                )

            else:
                deltas = (
                    policy.resolution_minutes,
                )

            for delta in deltas:
                total = (
                    current_total
                    + delta
                )

                if (
                    abs(
                        total
                    )
                    > policy.maximum_existing_shift_minutes
                ):
                    continue

                replacement = shift_event(
                    value,
                    delta,
                )

                document = replace_event(
                    state.document,
                    replacement,
                )

                direction = (
                    "earlier"
                    if delta < 0
                    else "later"
                )

                shifts = clone(
                    state.existing_shifts
                    or {}
                )

                shifts[
                    identifier
                ] = total

                source_class = (
                    event_source_class(
                        value
                    )
                )

                edit = {
                    "kind":
                        "temporal-shift",

                    "target_class":
                        "existing-event",

                    "target":
                        identifier,

                    "source_class":
                        source_class,

                    "minutes":
                        delta,

                    "cumulative_minutes":
                        total,

                    "temporal_direction":
                        direction,

                    "relation_to_desired_event":
                        (
                            "earlier-history"
                            if existing_time
                            <= candidate_time
                            else "future-history"
                        ),

                    "authority_effect":
                        "none",
                }

                output.append(
                    SearchState(
                        document=document,
                        candidate=clone(
                            state.candidate
                        ),
                        mode=state.mode,
                        edits=[
                            *clone(
                                state.edits
                            ),
                            edit,
                        ],
                        cost=(
                            state.cost
                            + edit_cost(
                                policy,
                                kind="existing-time",
                                minutes=delta,
                            )
                        ),
                        depth=(
                            state.depth
                            + 1
                        ),
                        candidate_shift_minutes=
                            state.candidate_shift_minutes,
                        existing_shifts=
                            shifts,
                    )
                )

        return output

    def search(
        self,
        document: Mapping[str, Any],
        desired_event: Mapping[str, Any],
        *,
        mode: str = "tour_bus",
        candidate_locations:
            Sequence[str] = (),
        transport_modes:
            Sequence[str] = (),
        policy:
            SearchPolicy
            | Mapping[str, Any]
            | None = None,
    ) -> dict[str, Any]:
        if not isinstance(
            document,
            Mapping,
        ):
            raise oriel_inverse_error(
                (
                    "Oriel document must "
                    "be an object"
                )
            )

        if not isinstance(
            desired_event,
            Mapping,
        ):
            raise oriel_inverse_error(
                (
                    "desired_event must "
                    "be an object"
                )
            )

        candidate_id = str(
            desired_event.get(
                "id",
                "",
            )
        ).strip()

        if not candidate_id:
            raise oriel_inverse_error(
                (
                    "desired_event requires "
                    "an id"
                )
            )

        if isinstance(
            policy,
            SearchPolicy,
        ):
            search_policy = policy

        else:
            search_policy = (
                SearchPolicy.from_mapping(
                    policy
                )
            )

        source_document = clone(
            dict(
                document
            )
        )

        source_candidate = clone(
            dict(
                desired_event
            )
        )

        source_document_digest = digest(
            source_document
        )

        source_candidate_digest = digest(
            source_candidate
        )

        initial = SearchState(
            document=source_document,
            candidate=source_candidate,
            mode=str(
                mode
            ).strip().lower(),
            edits=[],
            cost=0.0,
            depth=0,
            candidate_shift_minutes=0,
            existing_shifts={},
        )

        queue = []

        counter = 0

        heapq.heappush(
            queue,
            (
                0.0,
                0,
                counter,
                initial,
            ),
        )

        visited = set()

        viable = []
        conditional = []
        unresolved = []

        evaluated_count = 0

        best_infeasible = None

        while (
            queue
            and evaluated_count
            < search_policy.maximum_states
        ):
            (
                _rank,
                _depth,
                _counter,
                state,
            ) = heapq.heappop(
                queue
            )

            identity = state.identity()

            if identity in visited:
                continue

            visited.add(
                identity
            )

            evaluated_count += 1

            evaluation = self._evaluate(
                state
            )

            label = evaluation[
                "classification"
            ]

            solution = self._solution(
                state,
                evaluation,
                source_document_digest=
                    source_document_digest,
                source_candidate_digest=
                    source_candidate_digest,
            )

            if label == "viable":
                viable.append(
                    solution
                )

                if (
                    len(
                        viable
                    )
                    >= search_policy.solution_limit
                ):
                    break

                continue

            if label == "conditional":
                conditional.append(
                    solution
                )

            elif label == "unresolved":
                unresolved.append(
                    solution
                )

            else:
                if (
                    best_infeasible is None
                    or solution_rank(
                        solution
                    )
                    < solution_rank(
                        best_infeasible
                    )
                ):
                    best_infeasible = (
                        solution
                    )

            if (
                state.depth
                >= search_policy.maximum_depth
            ):
                continue

            neighbors = []

            neighbors.extend(
                self._candidate_time_neighbors(
                    state,
                    search_policy,
                )
            )

            neighbors.extend(
                self._location_neighbors(
                    state,
                    normalized_strings(
                        candidate_locations
                    ),
                    search_policy,
                )
            )

            neighbors.extend(
                self._mode_neighbors(
                    state,
                    normalized_strings(
                        transport_modes
                    ),
                    search_policy,
                )
            )

            neighbors.extend(
                self._existing_event_neighbors(
                    state,
                    evaluation[
                        "blocking_event_ids"
                    ],
                    search_policy,
                )
            )

            for neighbor in neighbors:
                neighbor_identity = (
                    neighbor.identity()
                )

                if neighbor_identity in visited:
                    continue

                counter += 1

                projected = (
                    self._evaluate(
                        neighbor
                    )
                )

                penalty = (
                    evaluation_rank_penalty(
                        projected[
                            "classification"
                        ],
                        search_policy,
                    )
                )

                heapq.heappush(
                    queue,
                    (
                        neighbor.cost
                        + penalty,
                        neighbor.depth,
                        counter,
                        neighbor,
                    ),
                )

        viable = sorted(
            viable,
            key=solution_rank,
        )

        conditional = sorted(
            conditional,
            key=solution_rank,
        )

        unresolved = sorted(
            unresolved,
            key=solution_rank,
        )

        nearest = (
            viable[
                0
            ]
            if viable
            else (
                conditional[
                    0
                ]
                if conditional
                else (
                    unresolved[
                        0
                    ]
                    if unresolved
                    else best_infeasible
                )
            )
        )

        result = {
            "schema":
                schema,

            "kind":
                "inverse-search",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "id":
                stable_id(
                    "carbon-oriel-inverse-search",
                    {
                        "document_digest":
                            source_document_digest,

                        "candidate_digest":
                            source_candidate_digest,

                        "mode":
                            mode,

                        "candidate_locations":
                            list(
                                normalized_strings(
                                    candidate_locations
                                )
                            ),

                        "transport_modes":
                            list(
                                normalized_strings(
                                    transport_modes
                                )
                            ),

                        "policy":
                            search_policy.__dict__,
                    },
                ),

            "desired_event_id":
                candidate_id,

            "source_document_digest":
                source_document_digest,

            "source_candidate_digest":
                source_candidate_digest,

            "search_policy": {
                key:
                    value
                for key, value
                in search_policy.__dict__.items()
            },

            "evaluated_state_count":
                evaluated_count,

            "visited_state_count":
                len(
                    visited
                ),

            "search_exhausted":
                not queue,

            "search_budget_exhausted":
                (
                    evaluated_count
                    >= search_policy.maximum_states
                ),

            "viable_count":
                len(
                    viable
                ),

            "conditional_count":
                len(
                    conditional
                ),

            "unresolved_count":
                len(
                    unresolved
                ),

            "nearest_solution":
                nearest,

            "viable":
                viable,

            "conditional":
                conditional[
                    :search_policy.solution_limit
                ],

            "unresolved":
                unresolved[
                    :search_policy.solution_limit
                ],

            "best_infeasible":
                best_infeasible,

            "historical_anchors_moved":
                False,

            "external_constraints_moved":
                False,

            "source_state_mutated":
                False,

            "canon_effect":
                "none",

            "evidence_admission":
                False,

            "quantum_contract": {
                "output":
                    "counterfactual repair possibilities",

                "selection":
                    False,

                "collapse":
                    False,

                "promotion":
                    False,

                "branch_owner":
                    "carbon",
            },
        }

        result[
            "digest"
        ] = digest(
            result
        )

        return result

    def explain(
        self,
        result: Mapping[str, Any],
    ) -> dict[str, Any]:
        nearest = result.get(
            "nearest_solution"
        )

        if not isinstance(
            nearest,
            Mapping,
        ):
            return {
                "schema":
                    schema,

                "kind":
                    "inverse-explanation",

                "owner":
                    owner,

                "component":
                    component,

                "authority_effect":
                    authority_effect,

                "search_id":
                    result.get(
                        "id"
                    ),

                "outcome":
                    "unresolved",

                "reason":
                    (
                        "no candidate solution "
                        "was produced"
                    ),
            }

        edits = [
            edit
            for edit
            in nearest.get(
                "edits",
                []
            )
            if isinstance(
                edit,
                Mapping,
            )
        ]

        return {
            "schema":
                schema,

            "kind":
                "inverse-explanation",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "search_id":
                result.get(
                    "id"
                ),

            "solution_id":
                nearest.get(
                    "id"
                ),

            "classification":
                nearest.get(
                    "classification"
                ),

            "candidate_only":
                nearest.get(
                    "candidate_only"
                ),

            "minimum_prior_intervention":
                nearest.get(
                    "minimum_prior_intervention"
                ),

            "required_changes":
                clone(
                    edits
                ),

            "required_change_count":
                len(
                    edits
                ),

            "blocking_reason_codes":
                nearest.get(
                    "reason_codes",
                    []
                ),

            "blocking_events":
                nearest.get(
                    "blocking_event_ids",
                    []
                ),

            "historical_anchor_change_required":
                False,

            "source_state_mutated":
                False,

            "canon_effect":
                "none",
        }


engine = OrielInverseEngine()


def capability_manifest() -> dict[str, Any]:
    projection = {
        "modes": [
            "reference",
            "instance",
            "composition",
        ],

        "instanceable":
            True,

        "composable":
            True,

        "maskable":
            True,

        "ownership_transfer":
            False,

        "authority_transfer":
            False,
    }

    return {
        "schema":
            (
                "savant.carbon.oriel-inverse."
                "capabilities.v1"
            ),

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "capabilities": [
            {
                "id":
                    "oriel_inverse_chronology",

                "owner":
                    owner,

                "component":
                    component,

                "kind":
                    "counterfactual-search",

                "purpose":
                    (
                        "Search backward from a desired "
                        "event for the smallest admissible "
                        "spacetime changes that make it "
                        "physically possible."
                    ),

                "version":
                    "1.0.0",

                "status":
                    "active",

                "operations": [
                    "search",
                    "explain",
                ],

                "authority_effect":
                    "none",

                "execution_owner":
                    owner,

                "projection_owner":
                    "filament",

                "transformation_owner":
                    "modus",

                "projection":
                    clone(
                        projection
                    ),
            },
            {
                "id":
                    "oriel_minimum_prior_intervention",

                "owner":
                    owner,

                "component":
                    component,

                "kind":
                    "causal-logistics",

                "purpose":
                    (
                        "Identify the smallest mutable "
                        "earlier chronology intervention "
                        "required to permit a desired "
                        "future event."
                    ),

                "version":
                    "1.0.0",

                "status":
                    "active",

                "operations": [
                    "search",
                ],

                "authority_effect":
                    "none",

                "execution_owner":
                    owner,

                "projection_owner":
                    "filament",

                "transformation_owner":
                    "modus",

                "projection":
                    clone(
                        projection
                    ),
            },
        ],

        "invariants": {
            "historical_anchors_are_immutable":
                True,

            "admitted_evidence_is_immutable":
                True,

            "external_constraints_are_immutable":
                True,

            "search_is_non_mutating":
                True,

            "search_is_not_canon":
                True,

            "search_does_not_admit_evidence":
                True,

            "carbon_owns_counterfactuals":
                True,
        },
    }


def status() -> dict[str, Any]:
    return {
        "schema":
            schema,

        "kind":
            "status",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "carbon_owned":
            True,

        "oriel_role":
            (
                "inverse chronology and "
                "logistics feasibility search"
            ),

        "mutable_source_classes":
            sorted(
                mutable_source_classes
            ),

        "immutable_source_classes":
            sorted(
                immutable_source_classes
            ),

        "historical_anchor_mutation":
            False,

        "external_constraint_mutation":
            False,

        "canon_effect":
            "none",

        "evidence_admission":
            False,

        "enhancement_count":
            len(
                enhancements
            ),

        "enhancements":
            list(
                enhancements
            ),

        "ready":
            True,
    }


def selftest() -> dict[str, Any]:
    document = {
        "locations": [
            {
                "id":
                    "alpha",

                "name":
                    "alpha",

                "latitude":
                    40.0,

                "longitude":
                    -75.0,

                "timezone":
                    "America/New_York",

                "source_class":
                    "verified_external",
            },
            {
                "id":
                    "beta",

                "name":
                    "beta",

                "latitude":
                    41.0,

                "longitude":
                    -74.0,

                "timezone":
                    "America/New_York",

                "source_class":
                    "verified_external",
            },
        ],

        "routes": [
            {
                "source":
                    "alpha",

                "target":
                    "beta",

                "mode":
                    "tour_bus",

                "distance_km":
                    180,

                "minimum_minutes":
                    150,

                "maximum_minutes":
                    210,

                "source_class":
                    "verified_external",
            }
        ],

        "events": [
            {
                "id":
                    "earlier-scene",

                "kind":
                    "scene",

                "entities": [
                    "band"
                ],

                "location_id":
                    "alpha",

                "start":
                    (
                        "2026-01-01"
                        "T15:00:00-05:00"
                    ),

                "duration_minutes":
                    120,

                "teardown_minutes":
                    30,

                "source_class":
                    "simulation",
            }
        ],
    }

    desired = {
        "id":
            "desired-scene",

        "kind":
            "scene",

        "entities": [
            "band"
        ],

        "location_id":
            "beta",

        "start":
            (
                "2026-01-01"
                "T18:00:00-05:00"
            ),

        "duration_minutes":
            60,

        "source_class":
            "simulation",
    }

    result = engine.search(
        document,
        desired,
        mode="tour_bus",
        policy={
            "resolution_minutes":
                30,

            "maximum_candidate_shift_minutes":
                240,

            "maximum_existing_shift_minutes":
                240,

            "maximum_depth":
                3,

            "maximum_states":
                120,

            "solution_limit":
                4,
        },
    )

    nearest = result.get(
        "nearest_solution"
    )

    if not isinstance(
        nearest,
        Mapping,
    ):
        raise oriel_inverse_error(
            (
                "inverse selftest did not "
                "produce a solution"
            )
        )

    if nearest.get(
        "classification"
    ) not in {
        "viable",
        "conditional",
    }:
        raise oriel_inverse_error(
            (
                "inverse selftest did not "
                "find a feasible repair"
            )
        )

    return {
        "schema":
            schema,

        "kind":
            "selftest",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "ok":
            True,

        "evaluated_state_count":
            result[
                "evaluated_state_count"
            ],

        "viable_count":
            result[
                "viable_count"
            ],

        "conditional_count":
            result[
                "conditional_count"
            ],

        "nearest_classification":
            nearest.get(
                "classification"
            ),

        "nearest_edit_count":
            nearest.get(
                "edit_count"
            ),

        "historical_anchors_moved":
            False,

        "source_state_mutated":
            False,

        "canon_effect":
            "none",
    }


__all__ = [
    "OrielInverseEngine",
    "SearchPolicy",
    "capability_manifest",
    "engine",
    "selftest",
    "status",
]

#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import json

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


from counterfactual import (
    deep_delta,
    engine as counterfactual_engine,
)

from oriel import (
    oriel_engine,
    oriel_error,
)

from scenario import (
    Scenario,
    engine as scenario_engine,
)

from simulation import (
    clone,
    digest,
)


owner = "carbon"
component = "oriel-quantum"
authority_effect = "none"

schema = (
    "savant.carbon.oriel-quantum.v1"
)

classifications = (
    "viable",
    "conditional",
    "unresolved",
    "infeasible",
)

enhancements = (
    "oriel-gated quantum superposition",
    "immutable base-scenario preservation",
    "all-possibility retention",
    "infeasible-branch preservation without execution",
    "unknown-preserving branch classification",
    "conditional feasibility classification",
    "deterministic possibility identity",
    "deterministic lattice identity",
    "scenario-native branch creation",
    "scenario provenance inheritance",
    "simulation-event isolation from oriel-event",
    "oriel-event isolation from simulation-event",
    "branch-local state overrides",
    "branch-local parameter overrides",
    "branch-local deterministic seeds",
    "chronometric pressure ranking",
    "constraint failure ranking",
    "advisory burden ranking",
    "branch feasibility receipts",
    "source-document preservation",
    "candidate-document projection",
    "spacetime delta projection",
    "counterfactual packet projection",
    "branch lineage projection",
    "possibility frontier analysis",
    "blocking reason aggregation",
    "conditional reason aggregation",
    "unknown reason aggregation",
    "strict collapse boundary",
    "conditional collapse opt-in",
    "unknown collapse opt-in",
    "infeasible collapse prohibition",
    "collapse without canon effect",
    "collapse without evidence admission",
    "collapse without source mutation",
    "nearest-viable ranking",
    "branch comparison",
    "simulation-versus-logistics separation",
    "quantum-versus-authority separation",
    "replay-compatible scenario packets",
    "filament-projectable branch packets",
    "modus-maskable projection metadata",
)


class oriel_quantum_error(
    RuntimeError
):
    pass


def canonical(
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


def stable_id(
    prefix: str,
    material: Any,
) -> str:
    return (
        prefix
        + ":"
        + hashlib.sha256(
            canonical(
                material
            ).encode(
                "utf-8"
            )
        ).hexdigest()[
            :24
        ]
    )


def normalized_strings(
    values: Sequence[Any] | None,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(
                    value
                ).strip()
                for value
                in (
                    values
                    or []
                )
                if str(
                    value
                ).strip()
            }
        )
    )


def mapping(
    value: Mapping[
        str,
        Any,
    ] | None,
) -> dict[str, Any]:
    return clone(
        dict(
            value
            or {}
        )
    )


@dataclass(
    frozen=True,
    slots=True,
)
class OrielPossibility:
    id: str

    name: str

    oriel_event: Mapping[
        str,
        Any,
    ]

    simulation_event: Any

    state_overrides: Mapping[
        str,
        Any,
    ]

    parameter_overrides: Mapping[
        str,
        Any,
    ]

    seed: int | None

    tags: tuple[str, ...]

    provenance: Mapping[
        str,
        Any,
    ]

    priority: int

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "id":
                self.id,

            "name":
                self.name,

            "oriel_event":
                clone(
                    self.oriel_event
                ),

            "simulation_event":
                clone(
                    self.simulation_event
                ),

            "state_overrides":
                clone(
                    self.state_overrides
                ),

            "parameter_overrides":
                clone(
                    self.parameter_overrides
                ),

            "seed":
                self.seed,

            "tags":
                list(
                    self.tags
                ),

            "provenance":
                clone(
                    self.provenance
                ),

            "priority":
                self.priority,
        }


def define_possibility(
    name: str,
    *,
    oriel_event: Mapping[
        str,
        Any,
    ],
    simulation_event: Any = None,
    state_overrides: Mapping[
        str,
        Any,
    ] | None = None,
    parameter_overrides: Mapping[
        str,
        Any,
    ] | None = None,
    seed: int | None = None,
    tags: Sequence[str] = (),
    provenance: Mapping[
        str,
        Any,
    ] | None = None,
    priority: int = 1000,
) -> OrielPossibility:
    normalized_name = str(
        name
        or ""
    ).strip()

    if not normalized_name:
        raise oriel_quantum_error(
            "possibility name is required"
        )

    if not isinstance(
        oriel_event,
        Mapping,
    ):
        raise oriel_quantum_error(
            (
                "possibility requires an "
                "oriel_event object"
            )
        )

    event_id = str(
        oriel_event.get(
            "id",
            "",
        )
    ).strip()

    if not event_id:
        raise oriel_quantum_error(
            (
                "possibility oriel_event "
                "requires an id"
            )
        )

    material = {
        "name":
            normalized_name,

        "oriel_event":
            clone(
                dict(
                    oriel_event
                )
            ),

        "simulation_event":
            clone(
                simulation_event
            ),

        "state_overrides":
            mapping(
                state_overrides
            ),

        "parameter_overrides":
            mapping(
                parameter_overrides
            ),

        "seed":
            (
                int(
                    seed
                )
                if seed
                is not None
                else None
            ),

        "tags":
            list(
                normalized_strings(
                    tags
                )
            ),

        "provenance":
            mapping(
                provenance
            ),

        "priority":
            int(
                priority
            ),
    }

    return OrielPossibility(
        id=stable_id(
            "carbon-oriel-possibility",
            material,
        ),
        name=normalized_name,
        oriel_event=material[
            "oriel_event"
        ],
        simulation_event=material[
            "simulation_event"
        ],
        state_overrides=material[
            "state_overrides"
        ],
        parameter_overrides=material[
            "parameter_overrides"
        ],
        seed=material[
            "seed"
        ],
        tags=tuple(
            material[
                "tags"
            ]
        ),
        provenance=material[
            "provenance"
        ],
        priority=material[
            "priority"
        ],
    )


def scenario_from_mapping(
    value: Mapping[
        str,
        Any,
    ],
) -> Scenario:
    name = str(
        value.get(
            "name",
            "",
        )
    ).strip()

    if not name:
        raise oriel_quantum_error(
            "scenario name is required"
        )

    return scenario_engine.define(
        name,
        initial_state=(
            value.get(
                "initial_state",
                {}
            )
        ),
        parameters=(
            value.get(
                "parameters",
                {}
            )
        ),
        events=(
            value.get(
                "events",
                []
            )
        ),
        steps=int(
            value.get(
                "steps",
                1,
            )
        ),
        delta_time=float(
            value.get(
                "delta_time",
                1.0,
            )
        ),
        seed=int(
            value.get(
                "seed",
                0,
            )
        ),
        tags=(
            value.get(
                "tags",
                []
            )
        ),
        provenance=(
            value.get(
                "provenance",
                {}
            )
        ),
    )


def possibilities_from_sequence(
    values: Sequence[
        Mapping[
            str,
            Any,
        ]
    ],
) -> list[
    OrielPossibility
]:
    output = []

    for value in values:
        if not isinstance(
            value,
            Mapping,
        ):
            raise oriel_quantum_error(
                (
                    "each possibility must "
                    "be an object"
                )
            )

        output.append(
            define_possibility(
                str(
                    value.get(
                        "name",
                        "",
                    )
                ),
                oriel_event=(
                    value.get(
                        "oriel_event",
                        {}
                    )
                ),
                simulation_event=(
                    value.get(
                        "simulation_event"
                    )
                ),
                state_overrides=(
                    value.get(
                        "state_overrides",
                        {}
                    )
                ),
                parameter_overrides=(
                    value.get(
                        "parameter_overrides",
                        {}
                    )
                ),
                seed=(
                    int(
                        value[
                            "seed"
                        ]
                    )
                    if value.get(
                        "seed"
                    )
                    is not None
                    else None
                ),
                tags=(
                    value.get(
                        "tags",
                        []
                    )
                ),
                provenance=(
                    value.get(
                        "provenance",
                        {}
                    )
                ),
                priority=int(
                    value.get(
                        "priority",
                        1000,
                    )
                ),
            )
        )

    ids = [
        item.id
        for item
        in output
    ]

    if len(
        ids
    ) != len(
        set(
            ids
        )
    ):
        raise oriel_quantum_error(
            (
                "superposition contains "
                "duplicate possibilities"
            )
        )

    return output


def classify(
    evaluation: Mapping[
        str,
        Any,
    ],
) -> str:
    outcome = str(
        evaluation.get(
            "outcome",
            "unknown",
        )
    ).strip().lower()

    if outcome == "pass":
        return "viable"

    if outcome == "advisory":
        return "conditional"

    if outcome == "fail":
        return "infeasible"

    return "unresolved"


def pressure(
    evaluation: Mapping[
        str,
        Any,
    ],
) -> float | None:
    validation = evaluation.get(
        "validation",
        evaluation,
    )

    if not isinstance(
        validation,
        Mapping,
    ):
        return None

    values = []

    for check in validation.get(
        "checks",
        [],
    ):
        if not isinstance(
            check,
            Mapping,
        ):
            continue

        evidence = check.get(
            "evidence"
        )

        if not isinstance(
            evidence,
            Mapping,
        ):
            continue

        candidate = evidence.get(
            "pressure"
        )

        if isinstance(
            candidate,
            (
                int,
                float,
            ),
        ):
            values.append(
                float(
                    candidate
                )
            )

    if not values:
        return None

    return max(
        values
    )


def reason_codes(
    evaluation: Mapping[
        str,
        Any,
    ],
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
                    "reason_code"
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


def branch_rank(
    branch: Mapping[
        str,
        Any,
    ],
) -> tuple[
    int,
    int,
    float,
    int,
    str,
]:
    classification = str(
        branch.get(
            "classification",
            "unresolved",
        )
    )

    classification_rank = {
        "viable":
            0,

        "conditional":
            1,

        "unresolved":
            2,

        "infeasible":
            3,
    }.get(
        classification,
        4,
    )

    evaluation = branch.get(
        "oriel_evaluation",
        {}
    )

    validation = (
        evaluation.get(
            "validation",
            evaluation,
        )
        if isinstance(
            evaluation,
            Mapping,
        )
        else {}
    )

    if not isinstance(
        validation,
        Mapping,
    ):
        validation = {}

    failures = int(
        validation.get(
            "failure_count",
            0,
        )
    )

    advisories = int(
        validation.get(
            "advisory_count",
            0,
        )
    )

    branch_pressure = branch.get(
        "chronometric_pressure"
    )

    if not isinstance(
        branch_pressure,
        (
            int,
            float,
        ),
    ):
        branch_pressure = 0.0

    priority = int(
        branch.get(
            "priority",
            1000,
        )
    )

    return (
        classification_rank,
        failures,
        float(
            branch_pressure
        ),
        advisories,
        (
            f"{priority:09d}:"
            + str(
                branch.get(
                    "possibility_id",
                    "",
                )
            )
        ),
    )


class OrielQuantumEngine:
    def superpose(
        self,
        oriel_document: Mapping[
            str,
            Any,
        ],
        base_scenario: Scenario,
        possibilities: Sequence[
            OrielPossibility
        ],
        *,
        mode: str = "tour_bus",
    ) -> dict[str, Any]:
        if not possibilities:
            raise oriel_quantum_error(
                (
                    "superposition requires "
                    "at least one possibility"
                )
            )

        base_engine = (
            oriel_engine.from_document(
                oriel_document
            )
        )

        base_validation = (
            base_engine.validate(
                mode=mode
            )
        )

        branches = []

        for possibility in possibilities:
            evaluation = (
                base_engine
                .evaluate_candidate(
                    possibility.oriel_event,
                    mode=mode,
                )
            )

            classification = classify(
                evaluation
            )

            candidate_document = clone(
                dict(
                    oriel_document
                )
            )

            candidate_events = list(
                candidate_document.get(
                    "events",
                    []
                )
            )

            candidate_events.append(
                clone(
                    possibility.oriel_event
                )
            )

            candidate_document[
                "events"
            ] = candidate_events

            scenario_events = list(
                base_scenario.events
            )

            if (
                possibility
                .simulation_event
                is not None
            ):
                scenario_events.append(
                    clone(
                        possibility
                        .simulation_event
                    )
                )

            branch = (
                scenario_engine.branch(
                    base_scenario,
                    possibility.name,
                    state=(
                        possibility
                        .state_overrides
                    ),
                    parameters=(
                        possibility
                        .parameter_overrides
                    ),
                    events=
                        scenario_events,
                    seed=(
                        possibility.seed
                    ),
                    tags=(
                        *possibility.tags,
                        "quantum",
                        (
                            "oriel-"
                            + classification
                        ),
                    ),
                    provenance={
                        **clone(
                            possibility
                            .provenance
                        ),

                        "oriel_component":
                            component,

                        "oriel_possibility_id":
                            possibility.id,

                        "oriel_classification":
                            classification,

                        "oriel_candidate_event_id":
                            possibility
                            .oriel_event
                            .get(
                                "id"
                            ),

                        "oriel_candidate_document_digest":
                            digest(
                                candidate_document
                            ),

                        "authority_effect":
                            "none",
                    },
                )
            )

            executable = (
                classification
                in {
                    "viable",
                    "conditional",
                }
            )

            selection_requires_override = (
                classification
                in {
                    "conditional",
                    "unresolved",
                }
            )

            branch_projection = {
                "possibility_id":
                    possibility.id,

                "possibility":
                    possibility
                    .projection(),

                "classification":
                    classification,

                "priority":
                    possibility.priority,

                "executable":
                    executable,

                "selection_requires_override":
                    (
                        selection_requires_override
                    ),

                "chronometric_pressure":
                    pressure(
                        evaluation
                    ),

                "reason_codes":
                    reason_codes(
                        evaluation
                    ),

                "oriel_evaluation":
                    evaluation,

                "scenario":
                    branch.projection(),

                "candidate_oriel_document":
                    candidate_document,

                "candidate_oriel_document_digest":
                    digest(
                        candidate_document
                    ),

                "simulation_event_injected":
                    (
                        possibility
                        .simulation_event
                        is not None
                    ),

                "source_state_mutated":
                    False,

                "canon_effect":
                    "none",

                "evidence_admission":
                    False,
            }

            branch_projection[
                "digest"
            ] = digest(
                branch_projection
            )

            branches.append(
                branch_projection
            )

        ranked = sorted(
            branches,
            key=branch_rank,
        )

        counts = {
            classification:
                sum(
                    1
                    for branch
                    in branches
                    if branch[
                        "classification"
                    ]
                    == classification
                )
            for classification
            in classifications
        }

        lattice_material = {
            "base_scenario_id":
                base_scenario.id,

            "base_oriel_digest":
                digest(
                    oriel_document
                ),

            "mode":
                mode,

            "branch_digests": [
                branch[
                    "digest"
                ]
                for branch
                in ranked
            ],
        }

        result = {
            "schema":
                schema,

            "kind":
                "quantum-superposition",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "id":
                stable_id(
                    "carbon-oriel-lattice",
                    lattice_material,
                ),

            "mode":
                mode,

            "base_scenario":
                base_scenario
                .projection(),

            "base_oriel_document":
                clone(
                    oriel_document
                ),

            "base_oriel_digest":
                digest(
                    oriel_document
                ),

            "base_validation":
                base_validation,

            "possibility_count":
                len(
                    branches
                ),

            "classification_counts":
                counts,

            "branches":
                ranked,

            "nearest_viable":
                next(
                    (
                        branch[
                            "possibility_id"
                        ]
                        for branch
                        in ranked
                        if branch[
                            "classification"
                        ]
                        == "viable"
                    ),
                    None,
                ),

            "selected_branch_id":
                None,

            "collapsed":
                False,

            "all_possibilities_preserved":
                True,

            "source_state_mutated":
                False,

            "authoritative":
                False,

            "canon_effect":
                "none",

            "evidence_admission":
                False,
        }

        result[
            "digest"
        ] = digest(
            result
        )

        return result

    def frontier(
        self,
        lattice: Mapping[
            str,
            Any,
        ],
    ) -> dict[str, Any]:
        branches = lattice.get(
            "branches"
        )

        if not isinstance(
            branches,
            list,
        ):
            raise oriel_quantum_error(
                "invalid quantum lattice"
            )

        blockers = {}
        conditionals = {}
        unresolved = {}

        for branch in branches:
            if not isinstance(
                branch,
                Mapping,
            ):
                continue

            identifier = str(
                branch.get(
                    "possibility_id",
                    "",
                )
            )

            classification = str(
                branch.get(
                    "classification",
                    "unresolved",
                )
            )

            codes = [
                str(
                    value
                )
                for value
                in branch.get(
                    "reason_codes",
                    []
                )
            ]

            if classification == "infeasible":
                blockers[
                    identifier
                ] = codes

            elif classification == "conditional":
                conditionals[
                    identifier
                ] = codes

            elif classification == "unresolved":
                unresolved[
                    identifier
                ] = codes

        frequencies = {}

        for group in (
            blockers,
            conditionals,
            unresolved,
        ):
            for codes in group.values():
                for code in codes:
                    frequencies[
                        code
                    ] = (
                        frequencies.get(
                            code,
                            0,
                        )
                        + 1
                    )

        result = {
            "schema":
                schema,

            "kind":
                "quantum-frontier",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "lattice_id":
                lattice.get(
                    "id"
                ),

            "blockers":
                blockers,

            "conditionals":
                conditionals,

            "unresolved":
                unresolved,

            "reason_frequency":
                dict(
                    sorted(
                        frequencies.items(),
                        key=lambda item: (
                            -item[
                                1
                            ],
                            item[
                                0
                            ],
                        ),
                    )
                ),

            "derived":
                True,

            "non_mutating":
                True,
        }

        result[
            "digest"
        ] = digest(
            result
        )

        return result

    def lineage(
        self,
        lattice: Mapping[
            str,
            Any,
        ],
    ) -> dict[str, Any]:
        base_value = lattice.get(
            "base_scenario"
        )

        branches = lattice.get(
            "branches"
        )

        if (
            not isinstance(
                base_value,
                Mapping,
            )
            or not isinstance(
                branches,
                list,
            )
        ):
            raise oriel_quantum_error(
                "invalid quantum lattice"
            )

        scenarios = [
            scenario_from_mapping(
                base_value
            )
        ]

        for branch in branches:
            if not isinstance(
                branch,
                Mapping,
            ):
                continue

            scenario_value = branch.get(
                "scenario"
            )

            if not isinstance(
                scenario_value,
                Mapping,
            ):
                continue

            scenarios.append(
                scenario_from_mapping(
                    scenario_value
                )
            )

        result = (
            scenario_engine.lineage(
                scenarios
            )
        )

        result[
            "oriel_lattice_id"
        ] = lattice.get(
            "id"
        )

        result[
            "oriel_component"
        ] = component

        result[
            "authority_effect"
        ] = "none"

        result[
            "digest"
        ] = digest(
            result
        )

        return result

    def compare(
        self,
        lattice: Mapping[
            str,
            Any,
        ],
        left_id: str,
        right_id: str,
    ) -> dict[str, Any]:
        branches = lattice.get(
            "branches"
        )

        if not isinstance(
            branches,
            list,
        ):
            raise oriel_quantum_error(
                "invalid quantum lattice"
            )

        index = {
            str(
                branch.get(
                    "possibility_id"
                )
            ):
                branch
            for branch
            in branches
            if isinstance(
                branch,
                Mapping,
            )
        }

        if left_id not in index:
            raise oriel_quantum_error(
                (
                    "unknown left possibility: "
                    + left_id
                )
            )

        if right_id not in index:
            raise oriel_quantum_error(
                (
                    "unknown right possibility: "
                    + right_id
                )
            )

        left = index[
            left_id
        ]

        right = index[
            right_id
        ]

        left_document = left.get(
            "candidate_oriel_document",
            {}
        )

        right_document = right.get(
            "candidate_oriel_document",
            {}
        )

        delta = deep_delta(
            left_document,
            right_document,
        )

        result = {
            "schema":
                schema,

            "kind":
                "quantum-branch-comparison",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "lattice_id":
                lattice.get(
                    "id"
                ),

            "left":
                {
                    "id":
                        left_id,

                    "classification":
                        left.get(
                            "classification"
                        ),

                    "chronometric_pressure":
                        left.get(
                            "chronometric_pressure"
                        ),

                    "reason_codes":
                        left.get(
                            "reason_codes",
                            []
                        ),
                },

            "right":
                {
                    "id":
                        right_id,

                    "classification":
                        right.get(
                            "classification"
                        ),

                    "chronometric_pressure":
                        right.get(
                            "chronometric_pressure"
                        ),

                    "reason_codes":
                        right.get(
                            "reason_codes",
                            []
                        ),
                },

            "spacetime_delta":
                delta,

            "delta_count":
                len(
                    delta
                ),

            "derived":
                True,

            "non_mutating":
                True,

            "causal_claim":
                False,
        }

        result[
            "digest"
        ] = digest(
            result
        )

        return result

    def counterfactual_packet(
        self,
        branch: Mapping[
            str,
            Any,
        ],
        *,
        event_step: int | None = None,
    ) -> dict[str, Any]:
        possibility = branch.get(
            "possibility"
        )

        if not isinstance(
            possibility,
            Mapping,
        ):
            raise oriel_quantum_error(
                (
                    "branch lacks possibility "
                    "projection"
                )
            )

        simulation_event = possibility.get(
            "simulation_event"
        )

        event_overrides = {}

        if (
            simulation_event
            is not None
            and event_step
            is not None
        ):
            step = int(
                event_step
            )

            if step < 0:
                raise oriel_quantum_error(
                    (
                        "event_step may not "
                        "be negative"
                    )
                )

            event_overrides[
                step
            ] = clone(
                simulation_event
            )

        definition = (
            counterfactual_engine.define(
                str(
                    possibility.get(
                        "name",
                        branch.get(
                            "possibility_id",
                            "possibility",
                        ),
                    )
                ),
                state_overrides=(
                    possibility.get(
                        "state_overrides",
                        {}
                    )
                ),
                parameter_overrides=(
                    possibility.get(
                        "parameter_overrides",
                        {}
                    )
                ),
                event_overrides=
                    event_overrides,
                seed=(
                    possibility.get(
                        "seed"
                    )
                ),
            )
        )

        result = {
            "schema":
                schema,

            "kind":
                "counterfactual-packet",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "possibility_id":
                branch.get(
                    "possibility_id"
                ),

            "classification":
                branch.get(
                    "classification"
                ),

            "counterfactual":
                definition
                .projection(),

            "event_step":
                event_step,

            "executable_without_override":
                (
                    branch.get(
                        "classification"
                    )
                    == "viable"
                ),

            "derived":
                True,

            "non_mutating":
                True,

            "canon_effect":
                "none",
        }

        result[
            "digest"
        ] = digest(
            result
        )

        return result

    def collapse(
        self,
        lattice: Mapping[
            str,
            Any,
        ],
        possibility_id: str,
        *,
        allow_conditional:
            bool = False,
        allow_unresolved:
            bool = False,
    ) -> dict[str, Any]:
        branches = lattice.get(
            "branches"
        )

        if not isinstance(
            branches,
            list,
        ):
            raise oriel_quantum_error(
                "invalid quantum lattice"
            )

        branch = next(
            (
                candidate
                for candidate
                in branches
                if (
                    isinstance(
                        candidate,
                        Mapping,
                    )
                    and str(
                        candidate.get(
                            "possibility_id",
                            "",
                        )
                    )
                    == possibility_id
                )
            ),
            None,
        )

        if branch is None:
            raise oriel_quantum_error(
                (
                    "unknown possibility: "
                    + possibility_id
                )
            )

        classification = str(
            branch.get(
                "classification",
                "unresolved",
            )
        )

        if classification == "infeasible":
            raise oriel_quantum_error(
                (
                    "infeasible possibility "
                    "cannot collapse"
                )
            )

        if (
            classification == "conditional"
            and not allow_conditional
        ):
            raise oriel_quantum_error(
                (
                    "conditional possibility "
                    "requires explicit override"
                )
            )

        if (
            classification == "unresolved"
            and not allow_unresolved
        ):
            raise oriel_quantum_error(
                (
                    "unresolved possibility "
                    "requires explicit override"
                )
            )

        selected_scenario = branch.get(
            "scenario"
        )

        selected_document = branch.get(
            "candidate_oriel_document"
        )

        if not isinstance(
            selected_scenario,
            Mapping,
        ):
            raise oriel_quantum_error(
                "selected scenario is missing"
            )

        if not isinstance(
            selected_document,
            Mapping,
        ):
            raise oriel_quantum_error(
                (
                    "selected Oriel document "
                    "is missing"
                )
            )

        receipt_material = {
            "lattice_id":
                lattice.get(
                    "id"
                ),

            "possibility_id":
                possibility_id,

            "classification":
                classification,

            "scenario_id":
                selected_scenario.get(
                    "id"
                ),

            "oriel_document_digest":
                digest(
                    selected_document
                ),

            "allow_conditional":
                bool(
                    allow_conditional
                ),

            "allow_unresolved":
                bool(
                    allow_unresolved
                ),
        }

        result = {
            "schema":
                schema,

            "kind":
                "quantum-collapse",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "id":
                stable_id(
                    "carbon-oriel-collapse",
                    receipt_material,
                ),

            "lattice_id":
                lattice.get(
                    "id"
                ),

            "possibility_id":
                possibility_id,

            "classification":
                classification,

            "collapsed":
                True,

            "selected_scenario":
                clone(
                    selected_scenario
                ),

            "selected_oriel_document":
                clone(
                    selected_document
                ),

            "selection_receipt":
                {
                    **receipt_material,

                    "authority_effect":
                        "none",

                    "canon_effect":
                        "none",

                    "evidence_admission":
                        False,

                    "source_state_mutated":
                        False,
                },

            "simulation_trajectory_selected":
                True,

            "canon_effect":
                "none",

            "evidence_admission":
                False,

            "source_state_mutated":
                False,

            "requires_separate_canon_promotion":
                True,
        }

        result[
            "digest"
        ] = digest(
            result
        )

        return result


engine = OrielQuantumEngine()


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

        "carbon_scenario_owner_preserved":
            True,

        "carbon_counterfactual_owner_preserved":
            True,

        "oriel_role":
            (
                "chronology and logistics "
                "feasibility oracle"
            ),

        "quantum_role":
            (
                "superposition and branch "
                "selection semantics"
            ),

        "classifications":
            list(
                classifications
            ),

        "collapse_requires_feasibility":
            True,

        "conditional_requires_override":
            True,

        "unknown_requires_override":
            True,

        "infeasible_cannot_collapse":
            True,

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
    oriel_document = {
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
                    "show",

                "kind":
                    "show",

                "entities": [
                    "band"
                ],

                "location_id":
                    "alpha",

                "start":
                    (
                        "2026-01-01"
                        "T19:00:00-05:00"
                    ),

                "duration_minutes":
                    120,

                "setup_minutes":
                    60,

                "teardown_minutes":
                    45,

                "source_class":
                    "asserted",
            }
        ],
    }

    base = scenario_engine.define(
        "baseline",
        initial_state={
            "band_state":
                "active"
        },
        parameters={
            "tour":
                "focused-test"
        },
        events=[],
        steps=1,
        delta_time=1.0,
        seed=0,
        tags=[
            "oriel-selftest"
        ],
        provenance={
            "method":
                "focused-test"
        },
    )

    feasible = define_possibility(
        "morning interview",
        oriel_event={
            "id":
                "interview",

            "kind":
                "interview",

            "entities": [
                "band"
            ],

            "location_id":
                "alpha",

            "start":
                (
                    "2026-01-01"
                    "T10:00:00-05:00"
                ),

            "duration_minutes":
                60,

            "source_class":
                "simulation",
        },
        simulation_event={
            "kind":
                "interview"
        },
    )

    impossible = define_possibility(
        "remote conflict",
        oriel_event={
            "id":
                "remote-conflict",

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
                    "T18:30:00-05:00"
                ),

            "duration_minutes":
                120,

            "source_class":
                "simulation",
        },
        simulation_event={
            "kind":
                "remote-conflict"
        },
    )

    lattice = engine.superpose(
        oriel_document,
        base,
        [
            feasible,
            impossible,
        ],
    )

    if (
        lattice[
            "classification_counts"
        ][
            "viable"
        ]
        < 1
    ):
        raise oriel_quantum_error(
            (
                "selftest failed to retain "
                "a viable branch"
            )
        )

    if (
        lattice[
            "classification_counts"
        ][
            "infeasible"
        ]
        < 1
    ):
        raise oriel_quantum_error(
            (
                "selftest failed to reject "
                "an impossible branch"
            )
        )

    collapsed = engine.collapse(
        lattice,
        feasible.id,
    )

    if not collapsed[
        "collapsed"
    ]:
        raise oriel_quantum_error(
            "collapse selftest failed"
        )

    try:
        engine.collapse(
            lattice,
            impossible.id,
        )

    except oriel_quantum_error:
        rejected = True

    else:
        rejected = False

    if not rejected:
        raise oriel_quantum_error(
            (
                "infeasible branch was "
                "incorrectly collapsible"
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

        "lattice_id":
            lattice[
                "id"
            ],

        "classification_counts":
            lattice[
                "classification_counts"
            ],

        "viable_collapse":
            True,

        "infeasible_collapse_rejected":
            True,

        "source_state_mutated":
            False,

        "canon_effect":
            "none",
    }


__all__ = [
    "OrielPossibility",
    "OrielQuantumEngine",
    "define_possibility",
    "engine",
    "possibilities_from_sequence",
    "scenario_from_mapping",
    "selftest",
    "status",
]

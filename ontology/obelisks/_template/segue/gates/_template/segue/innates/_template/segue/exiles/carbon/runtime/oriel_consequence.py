#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping, Sequence

from oriel_causality import engine as causality_engine
from oriel_quantum import engine as quantum_engine
from oriel_simulation import engine as simulation_engine


owner = "carbon"
component = "oriel-consequence"
authority_effect = "none"
schema = "savant.carbon.oriel-consequence.v1"


classification_rank = {
    "viable": 0,
    "conditional": 1,
    "unresolved": 2,
    "infeasible": 3,
}


consequence_rank = {
    "contained": 0,
    "pressured": 1,
    "critical": 2,
    "unresolved": 3,
    "blocked": 4,
    "anchor_breach": 5,
    "infeasible": 6,
}


enhancements = (
    "reality-bound quantum consequence projection",
    "branch-local causal graph construction",
    "baseline-versus-branch graph diff",
    "new causal edge detection",
    "removed causal edge detection",
    "changed causal edge detection",
    "critical-edge delta",
    "pressured-edge delta",
    "blocked-edge delta",
    "unresolved-edge delta",
    "immutable-anchor horizon discovery",
    "candidate-to-anchor inevitability analysis",
    "minimum anchor slack projection",
    "causal-footprint scoring",
    "consequence severity classification",
    "contained-ripple classification",
    "critical-ripple classification",
    "anchor-breach classification",
    "optional intervention propagation",
    "intervention breach reporting",
    "branch causal fingerprinting",
    "deterministic consequence identity",
    "pareto causal frontier",
    "dominated-branch identification",
    "minimum-causal-footprint selection",
    "minimum-anchor-risk selection",
    "branch consequence comparison",
    "classification-aware consequence ranking",
    "immutable reality preservation",
    "quantum collapse boundary preservation",
    "canon-neutral causal projection",
    "evidence-neutral causal projection",
    "filament-projectable consequence packets",
    "modus-maskable consequence metadata",
)


class oriel_consequence_error(
    RuntimeError
):
    pass


def clone(
    value: Any,
) -> Any:
    return copy.deepcopy(
        value
    )


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


def edge_key(
    value: Mapping[
        str,
        Any,
    ],
) -> tuple[
    str,
    str,
]:
    return (
        str(
            value.get(
                "source",
                "",
            )
        ),
        str(
            value.get(
                "target",
                "",
            )
        ),
    )


def normalized_edge(
    value: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    return {
        "source":
            value.get(
                "source"
            ),

        "target":
            value.get(
                "target"
            ),

        "causes":
            sorted(
                [
                    {
                        "kind":
                            str(
                                cause.get(
                                    "kind",
                                    "",
                                )
                            ),

                        "id":
                            str(
                                cause.get(
                                    "id",
                                    "",
                                )
                            ),
                    }
                    for cause
                    in value.get(
                        "causes",
                        [],
                    )
                    if isinstance(
                        cause,
                        Mapping,
                    )
                ],
                key=lambda cause: (
                    cause[
                        "kind"
                    ],
                    cause[
                        "id"
                    ],
                ),
            ),

        "minimum_separation_minutes":
            value.get(
                "minimum_separation_minutes"
            ),

        "maximum_separation_minutes":
            value.get(
                "maximum_separation_minutes"
            ),

        "slack_minutes":
            value.get(
                "slack_minutes"
            ),

        "pressure_state":
            value.get(
                "pressure_state"
            ),
    }


def graph_delta(
    baseline: Mapping[
        str,
        Any,
    ],
    branch: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    baseline_edges = {
        edge_key(
            value
        ):
            normalized_edge(
                value
            )
        for value
        in baseline.get(
            "edges",
            [],
        )
        if isinstance(
            value,
            Mapping,
        )
    }

    branch_edges = {
        edge_key(
            value
        ):
            normalized_edge(
                value
            )
        for value
        in branch.get(
            "edges",
            [],
        )
        if isinstance(
            value,
            Mapping,
        )
    }

    baseline_keys = set(
        baseline_edges
    )

    branch_keys = set(
        branch_edges
    )

    added = [
        branch_edges[
            key
        ]
        for key
        in sorted(
            branch_keys
            - baseline_keys
        )
    ]

    removed = [
        baseline_edges[
            key
        ]
        for key
        in sorted(
            baseline_keys
            - branch_keys
        )
    ]

    changed = []

    for key in sorted(
        baseline_keys
        & branch_keys
    ):
        left = baseline_edges[
            key
        ]

        right = branch_edges[
            key
        ]

        if left == right:
            continue

        changed.append(
            {
                "edge": {
                    "source":
                        key[
                            0
                        ],

                    "target":
                        key[
                            1
                        ],
                },

                "baseline":
                    left,

                "branch":
                    right,
            }
        )

    return {
        "added_edges":
            added,

        "removed_edges":
            removed,

        "changed_edges":
            changed,

        "added_edge_count":
            len(
                added
            ),

        "removed_edge_count":
            len(
                removed
            ),

        "changed_edge_count":
            len(
                changed
            ),

        "causal_footprint":
            (
                len(
                    added
                )
                + len(
                    removed
                )
                + len(
                    changed
                )
            ),
    }


def candidate_event_id(
    branch: Mapping[
        str,
        Any,
    ],
) -> str | None:
    possibility = branch.get(
        "possibility"
    )

    if not isinstance(
        possibility,
        Mapping,
    ):
        return None

    event_value = possibility.get(
        "oriel_event"
    )

    if not isinstance(
        event_value,
        Mapping,
    ):
        return None

    identifier = str(
        event_value.get(
            "id",
            "",
        )
    ).strip()

    return (
        identifier
        if identifier
        else None
    )


def immutable_targets(
    graph: Mapping[
        str,
        Any,
    ],
    source_event: str,
) -> list[str]:
    nodes = [
        value
        for value
        in graph.get(
            "nodes",
            [],
        )
        if isinstance(
            value,
            Mapping,
        )
    ]

    index = {
        str(
            value.get(
                "id",
                "",
            )
        ):
            value
        for value
        in nodes
    }

    source = index.get(
        source_event
    )

    if source is None:
        return []

    source_start = str(
        source.get(
            "scheduled_start",
            "",
        )
    )

    return sorted(
        [
            identifier
            for identifier, value
            in index.items()
            if (
                identifier
                != source_event
                and bool(
                    value.get(
                        "immutable",
                        False,
                    )
                )
                and str(
                    value.get(
                        "scheduled_start",
                        "",
                    )
                )
                >= source_start
            )
        ]
    )


def consequence_class(
    *,
    branch_classification: str,
    graph: Mapping[
        str,
        Any,
    ],
    propagation: Mapping[
        str,
        Any,
    ]
    | None,
) -> str:
    if (
        branch_classification
        == "infeasible"
    ):
        return "infeasible"

    if (
        isinstance(
            propagation,
            Mapping,
        )
        and int(
            propagation.get(
                "immutable_anchor_breach_count",
                0,
            )
        )
        > 0
    ):
        return "anchor_breach"

    if int(
        graph.get(
            "blocked_edge_count",
            0,
        )
    ) > 0:
        return "blocked"

    if int(
        graph.get(
            "unresolved_edge_count",
            0,
        )
    ) > 0:
        return "unresolved"

    if int(
        graph.get(
            "critical_edge_count",
            0,
        )
    ) > 0:
        return "critical"

    if int(
        graph.get(
            "pressured_edge_count",
            0,
        )
    ) > 0:
        return "pressured"

    return "contained"


def minimum_anchor_slack(
    horizons: Sequence[
        Mapping[
            str,
            Any,
        ]
    ],
) -> float | None:
    values = [
        float(
            value[
                "absorbable_delay_minutes"
            ]
        )
        for value
        in horizons
        if (
            value.get(
                "state"
            )
            == "resolved"
            and isinstance(
                value.get(
                    "absorbable_delay_minutes"
                ),
                (
                    int,
                    float,
                ),
            )
        )
    ]

    return (
        min(
            values
        )
        if values
        else None
    )


def branch_rank(
    value: Mapping[
        str,
        Any,
    ],
) -> tuple[
    int,
    int,
    int,
    float,
    int,
    str,
]:
    branch_classification = str(
        value.get(
            "classification",
            "unresolved",
        )
    )

    consequence = str(
        value.get(
            "consequence_class",
            "unresolved",
        )
    )

    anchor_slack = value.get(
        "minimum_anchor_slack_minutes"
    )

    anchor_penalty = (
        float(
            "inf"
        )
        if anchor_slack
        is None
        else -float(
            anchor_slack
        )
    )

    return (
        classification_rank.get(
            branch_classification,
            4,
        ),

        consequence_rank.get(
            consequence,
            7,
        ),

        int(
            value.get(
                "causal_footprint",
                0,
            )
        ),

        anchor_penalty,

        int(
            value.get(
                "priority",
                1000,
            )
        ),

        str(
            value.get(
                "possibility_id",
                "",
            )
        ),
    )


def dominates(
    left: Mapping[
        str,
        Any,
    ],
    right: Mapping[
        str,
        Any,
    ],
) -> bool:
    left_vector = (
        classification_rank.get(
            str(
                left.get(
                    "classification",
                    "unresolved",
                )
            ),
            4,
        ),

        consequence_rank.get(
            str(
                left.get(
                    "consequence_class",
                    "unresolved",
                )
            ),
            7,
        ),

        int(
            left.get(
                "immutable_anchor_breach_count",
                0,
            )
        ),

        int(
            left.get(
                "causal_footprint",
                0,
            )
        ),
    )

    right_vector = (
        classification_rank.get(
            str(
                right.get(
                    "classification",
                    "unresolved",
                )
            ),
            4,
        ),

        consequence_rank.get(
            str(
                right.get(
                    "consequence_class",
                    "unresolved",
                )
            ),
            7,
        ),

        int(
            right.get(
                "immutable_anchor_breach_count",
                0,
            )
        ),

        int(
            right.get(
                "causal_footprint",
                0,
            )
        ),
    )

    no_worse = all(
        left_value
        <= right_value
        for left_value, right_value
        in zip(
            left_vector,
            right_vector,
        )
    )

    strictly_better = any(
        left_value
        < right_value
        for left_value, right_value
        in zip(
            left_vector,
            right_vector,
        )
    )

    return (
        no_worse
        and strictly_better
    )


class OrielConsequenceEngine:
    def superpose(
        self,
        document: Mapping[
            str,
            Any,
        ],
        facts: Sequence[
            Mapping[
                str,
                Any,
            ]
        ],
        scenario_value: Mapping[
            str,
            Any,
        ],
        possibilities_value: Sequence[
            Mapping[
                str,
                Any,
            ]
        ],
        *,
        mode: str = "tour_bus",
        pressure_threshold_minutes:
            float = 60.0,
    ) -> dict[str, Any]:
        simulation = (
            simulation_engine.superpose(
                document,
                facts,
                scenario_value,
                possibilities_value,
                mode=mode,
            )
        )

        world = simulation[
            "world"
        ]

        lattice = simulation[
            "lattice"
        ]

        baseline_graph = (
            causality_engine.graph(
                world[
                    "bound_document"
                ],
                mode=mode,
                pressure_threshold_minutes=
                    pressure_threshold_minutes,
            )
        )

        possibility_by_name = {
            str(
                value.get(
                    "name",
                    "",
                )
            ):
                value
            for value
            in possibilities_value
            if isinstance(
                value,
                Mapping,
            )
        }

        consequence_branches = []

        for branch in lattice.get(
            "branches",
            [],
        ):
            if not isinstance(
                branch,
                Mapping,
            ):
                continue

            candidate_document = (
                branch.get(
                    "candidate_oriel_document"
                )
            )

            if not isinstance(
                candidate_document,
                Mapping,
            ):
                raise oriel_consequence_error(
                    (
                        "quantum branch lacks "
                        "candidate Oriel document"
                    )
                )

            branch_graph = (
                causality_engine.graph(
                    candidate_document,
                    mode=mode,
                    pressure_threshold_minutes=
                        pressure_threshold_minutes,
                )
            )

            delta = graph_delta(
                baseline_graph,
                branch_graph,
            )

            source_event = candidate_event_id(
                branch
            )

            horizons = []

            if source_event:
                for target in immutable_targets(
                    branch_graph,
                    source_event,
                ):
                    horizon = (
                        causality_engine
                        .inevitability_horizon(
                            candidate_document,
                            source_event=
                                source_event,
                            target_event=
                                target,
                            mode=mode,
                        )
                    )

                    if (
                        horizon.get(
                            "state"
                        )
                        != "disconnected"
                    ):
                        horizons.append(
                            horizon
                        )

            possibility = branch.get(
                "possibility",
                {},
            )

            possibility_name = (
                str(
                    possibility.get(
                        "name",
                        "",
                    )
                )
                if isinstance(
                    possibility,
                    Mapping,
                )
                else ""
            )

            original = (
                possibility_by_name.get(
                    possibility_name,
                    {},
                )
            )

            intervention = (
                original.get(
                    "intervention"
                )
                if isinstance(
                    original,
                    Mapping,
                )
                else None
            )

            propagation = None

            if isinstance(
                intervention,
                Mapping,
            ):
                propagation = (
                    causality_engine.propagate(
                        candidate_document,
                        intervention,
                        mode=mode,
                    )
                )

            branch_classification = str(
                branch.get(
                    "classification",
                    "unresolved",
                )
            )

            consequence = consequence_class(
                branch_classification=
                    branch_classification,
                graph=
                    branch_graph,
                propagation=
                    propagation,
            )

            anchor_slack = (
                minimum_anchor_slack(
                    horizons
                )
            )

            packet = {
                "possibility_id":
                    branch.get(
                        "possibility_id"
                    ),

                "priority":
                    branch.get(
                        "priority",
                        1000,
                    ),

                "classification":
                    branch_classification,

                "consequence_class":
                    consequence,

                "candidate_event_id":
                    source_event,

                "causal_footprint":
                    delta[
                        "causal_footprint"
                    ],

                "minimum_anchor_slack_minutes":
                    anchor_slack,

                "immutable_anchor_breach_count":
                    (
                        int(
                            propagation.get(
                                "immutable_anchor_breach_count",
                                0,
                            )
                        )
                        if isinstance(
                            propagation,
                            Mapping,
                        )
                        else 0
                    ),

                "critical_edge_count":
                    branch_graph[
                        "critical_edge_count"
                    ],

                "pressured_edge_count":
                    branch_graph[
                        "pressured_edge_count"
                    ],

                "blocked_edge_count":
                    branch_graph[
                        "blocked_edge_count"
                    ],

                "unresolved_edge_count":
                    branch_graph[
                        "unresolved_edge_count"
                    ],

                "graph_delta":
                    delta,

                "causal_graph":
                    branch_graph,

                "immutable_anchor_horizons":
                    horizons,

                "intervention":
                    clone(
                        intervention
                    ),

                "propagation":
                    clone(
                        propagation
                    ),

                "quantum_branch":
                    clone(
                        branch
                    ),

                "reality_integrity":
                    branch.get(
                        "reality_integrity"
                    ),

                "source_state_mutated":
                    False,

                "canon_effect":
                    "none",

                "evidence_admission":
                    False,

                "causal_claim_is_projection":
                    True,
            }

            packet[
                "id"
            ] = stable_id(
                "carbon-oriel-consequence",
                {
                    key:
                        value
                    for key, value
                    in packet.items()
                    if key
                    not in {
                        "id",
                        "quantum_branch",
                    }
                },
            )

            packet[
                "digest"
            ] = digest(
                packet
            )

            consequence_branches.append(
                packet
            )

        consequence_branches = sorted(
            consequence_branches,
            key=branch_rank,
        )

        result = {
            "schema":
                schema,

            "kind":
                "consequence-lattice",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "id":
                stable_id(
                    (
                        "carbon-oriel-"
                        "consequence-lattice"
                    ),
                    {
                        "world_id":
                            world[
                                "id"
                            ],

                        "quantum_lattice_id":
                            lattice[
                                "id"
                            ],

                        "branch_digests": [
                            value[
                                "digest"
                            ]
                            for value
                            in consequence_branches
                        ],
                    },
                ),

            "world":
                world,

            "quantum_lattice":
                lattice,

            "baseline_causal_graph":
                baseline_graph,

            "branch_count":
                len(
                    consequence_branches
                ),

            "branches":
                consequence_branches,

            "minimum_causal_footprint":
                (
                    consequence_branches[
                        0
                    ][
                        "possibility_id"
                    ]
                    if consequence_branches
                    else None
                ),

            "source_state_mutated":
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
        branches = [
            value
            for value
            in lattice.get(
                "branches",
                [],
            )
            if isinstance(
                value,
                Mapping,
            )
        ]

        frontier = []
        dominated = []

        for candidate in branches:
            dominators = [
                other.get(
                    "possibility_id"
                )
                for other
                in branches
                if (
                    other is not candidate
                    and dominates(
                        other,
                        candidate,
                    )
                )
            ]

            if dominators:
                dominated.append(
                    {
                        "possibility_id":
                            candidate.get(
                                "possibility_id"
                            ),

                        "dominated_by":
                            sorted(
                                str(
                                    value
                                )
                                for value
                                in dominators
                                if value
                                is not None
                            ),
                    }
                )

            else:
                frontier.append(
                    candidate
                )

        frontier = sorted(
            frontier,
            key=branch_rank,
        )

        return {
            "schema":
                schema,

            "kind":
                "causal-pareto-frontier",

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

            "frontier_count":
                len(
                    frontier
                ),

            "frontier": [
                {
                    "possibility_id":
                        value.get(
                            "possibility_id"
                        ),

                    "classification":
                        value.get(
                            "classification"
                        ),

                    "consequence_class":
                        value.get(
                            "consequence_class"
                        ),

                    "causal_footprint":
                        value.get(
                            "causal_footprint"
                        ),

                    "minimum_anchor_slack_minutes":
                        value.get(
                            "minimum_anchor_slack_minutes"
                        ),

                    "immutable_anchor_breach_count":
                        value.get(
                            "immutable_anchor_breach_count"
                        ),
                }
                for value
                in frontier
            ],

            "dominated":
                dominated,

            "derived":
                True,

            "non_mutating":
                True,
        }

    def compare(
        self,
        lattice: Mapping[
            str,
            Any,
        ],
        left_id: str,
        right_id: str,
    ) -> dict[str, Any]:
        index = {
            str(
                value.get(
                    "possibility_id",
                    "",
                )
            ):
                value
            for value
            in lattice.get(
                "branches",
                [],
            )
            if isinstance(
                value,
                Mapping,
            )
        }

        if left_id not in index:
            raise oriel_consequence_error(
                (
                    "unknown left possibility: "
                    + left_id
                )
            )

        if right_id not in index:
            raise oriel_consequence_error(
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

        return {
            "schema":
                schema,

            "kind":
                "consequence-comparison",

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

            "left": {
                "possibility_id":
                    left_id,

                "classification":
                    left.get(
                        "classification"
                    ),

                "consequence_class":
                    left.get(
                        "consequence_class"
                    ),

                "causal_footprint":
                    left.get(
                        "causal_footprint"
                    ),

                "minimum_anchor_slack_minutes":
                    left.get(
                        "minimum_anchor_slack_minutes"
                    ),

                "immutable_anchor_breach_count":
                    left.get(
                        "immutable_anchor_breach_count"
                    ),
            },

            "right": {
                "possibility_id":
                    right_id,

                "classification":
                    right.get(
                        "classification"
                    ),

                "consequence_class":
                    right.get(
                        "consequence_class"
                    ),

                "causal_footprint":
                    right.get(
                        "causal_footprint"
                    ),

                "minimum_anchor_slack_minutes":
                    right.get(
                        "minimum_anchor_slack_minutes"
                    ),

                "immutable_anchor_breach_count":
                    right.get(
                        "immutable_anchor_breach_count"
                    ),
            },

            "preferred_by_causal_rank":
                (
                    left_id
                    if branch_rank(
                        left
                    )
                    < branch_rank(
                        right
                    )
                    else right_id
                ),

            "causal_footprint_delta":
                (
                    int(
                        right.get(
                            "causal_footprint",
                            0,
                        )
                    )
                    - int(
                        left.get(
                            "causal_footprint",
                            0,
                        )
                    )
                ),

            "derived":
                True,

            "non_mutating":
                True,
        }

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
        consequence_branch = next(
            (
                value
                for value
                in lattice.get(
                    "branches",
                    [],
                )
                if (
                    isinstance(
                        value,
                        Mapping,
                    )
                    and str(
                        value.get(
                            "possibility_id",
                            "",
                        )
                    )
                    == possibility_id
                )
            ),
            None,
        )

        if consequence_branch is None:
            raise oriel_consequence_error(
                (
                    "unknown possibility: "
                    + possibility_id
                )
            )

        if consequence_branch.get(
            "consequence_class"
        ) in {
            "infeasible",
            "anchor_breach",
            "blocked",
        }:
            raise oriel_consequence_error(
                (
                    "branch consequence state "
                    "prohibits collapse: "
                    + str(
                        consequence_branch.get(
                            "consequence_class"
                        )
                    )
                )
            )

        quantum_lattice = lattice.get(
            "quantum_lattice"
        )

        if not isinstance(
            quantum_lattice,
            Mapping,
        ):
            raise oriel_consequence_error(
                (
                    "consequence lattice lacks "
                    "quantum lattice"
                )
            )

        collapsed = quantum_engine.collapse(
            quantum_lattice,
            possibility_id,
            allow_conditional=
                allow_conditional,
            allow_unresolved=
                allow_unresolved,
        )

        return {
            "schema":
                schema,

            "kind":
                "consequence-aware-collapse",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "consequence_lattice_id":
                lattice.get(
                    "id"
                ),

            "possibility_id":
                possibility_id,

            "consequence_class":
                consequence_branch.get(
                    "consequence_class"
                ),

            "causal_footprint":
                consequence_branch.get(
                    "causal_footprint"
                ),

            "minimum_anchor_slack_minutes":
                consequence_branch.get(
                    "minimum_anchor_slack_minutes"
                ),

            "collapse":
                collapsed,

            "canon_effect":
                "none",

            "evidence_admission":
                False,

            "source_state_mutated":
                False,
        }


engine = OrielConsequenceEngine()


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

    def capability(
        identifier: str,
        kind: str,
        purpose: str,
        operations: Sequence[str],
    ) -> dict[str, Any]:
        return {
            "id":
                identifier,

            "owner":
                owner,

            "component":
                component,

            "kind":
                kind,

            "purpose":
                purpose,

            "version":
                "1.0.0",

            "status":
                "active",

            "authority_effect":
                "none",

            "execution_owner":
                owner,

            "projection_owner":
                "filament",

            "transformation_owner":
                "modus",

            "operations":
                list(
                    operations
                ),

            "deterministic":
                True,

            "projection":
                clone(
                    projection
                ),
        }

    return {
        "schema":
            (
                "savant.carbon.oriel-consequence."
                "capabilities.v1"
            ),

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "capabilities": [
            capability(
                "oriel_quantum_consequence_lattice",
                "causal-composition",
                (
                    "Attach causal-logistics "
                    "consequence projections to every "
                    "reality-bound quantum branch."
                ),
                [
                    "superpose",
                ],
            ),

            capability(
                "oriel_causal_pareto_frontier",
                "causal-analysis",
                (
                    "Retain non-dominated branches "
                    "across feasibility, consequence "
                    "severity and causal footprint."
                ),
                [
                    "frontier",
                ],
            ),

            capability(
                "oriel_consequence_comparison",
                "causal-analysis",
                (
                    "Compare alternate decisions by "
                    "causal footprint and immutable "
                    "anchor risk."
                ),
                [
                    "compare",
                ],
            ),

            capability(
                "oriel_consequence_aware_collapse",
                "simulation-selection",
                (
                    "Prevent operational collapse of "
                    "branches whose projected causal "
                    "effects breach immutable anchors."
                ),
                [
                    "collapse",
                ],
            ),
        ],

        "invariants": {
            "carbon_owns_quantum":
                True,

            "carbon_owns_causal_simulation":
                True,

            "oriel_projects_logistical_causality":
                True,

            "immutable_reality_is_preserved":
                True,

            "collapse_does_not_promote_canon":
                True,

            "evidence_admission":
                False,
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

        "reality_bound":
            True,

        "quantum_bound":
            True,

        "causality_bound":
            True,

        "collapse_boundary":
            True,

        "consequence_classes":
            sorted(
                consequence_rank,
                key=lambda value:
                    consequence_rank[
                        value
                    ],
            ),

        "enhancement_count":
            len(
                enhancements
            ),

        "enhancements":
            list(
                enhancements
            ),

        "canon_effect":
            "none",

        "evidence_admission":
            False,

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
            {
                "id":
                    "gamma",

                "name":
                    "gamma",

                "latitude":
                    42.0,

                "longitude":
                    -73.0,

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
                    120,

                "maximum_minutes":
                    150,

                "source_class":
                    "verified_external",
            },
            {
                "source":
                    "beta",

                "target":
                    "gamma",

                "mode":
                    "tour_bus",

                "distance_km":
                    260,

                "minimum_minutes":
                    180,

                "maximum_minutes":
                    210,

                "source_class":
                    "verified_external",
            },
        ],

        "events": [
            {
                "id":
                    "show-a",

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
                        "T10:00:00-05:00"
                    ),

                "duration_minutes":
                    60,

                "source_class":
                    "simulation",
            },
            {
                "id":
                    "show-c",

                "kind":
                    "show",

                "entities": [
                    "band"
                ],

                "location_id":
                    "gamma",

                "start":
                    (
                        "2026-01-01"
                        "T20:00:00-05:00"
                    ),

                "duration_minutes":
                    60,

                "source_class":
                    "verified_external",

                "metadata": {
                    "locked":
                        True,
                },
            },
        ],
    }

    facts = [
        {
            "id":
                "beta-open",

            "kind":
                "venue-availability",

            "effect":
                "available",

            "location_id":
                "beta",

            "start":
                (
                    "2026-01-01"
                    "T12:00:00-05:00"
                ),

            "end":
                (
                    "2026-01-01"
                    "T18:00:00-05:00"
                ),

            "source_class":
                "verified_external",

            "verification_state":
                "verified",

            "source_refs": [
                "focused-test:beta-open"
            ],
        },
    ]

    scenario_value = {
        "name":
            "baseline",

        "initial_state": {
            "band":
                "active",
        },

        "parameters":
            {},

        "events":
            [],

        "steps":
            1,

        "delta_time":
            1.0,

        "seed":
            0,

        "tags": [
            "focused-test"
        ],

        "provenance": {
            "method":
                "focused-test"
        },
    }

    possibilities = [
        {
            "name":
                "early-stop",

            "priority":
                10,

            "oriel_event": {
                "id":
                    "stop-early",

                "kind":
                    "show",

                "entities": [
                    "band"
                ],

                "location_id":
                    "beta",

                "start":
                    (
                        "2026-01-01"
                        "T14:00:00-05:00"
                    ),

                "duration_minutes":
                    60,

                "source_class":
                    "simulation",
            },
        },
        {
            "name":
                "late-stop",

            "priority":
                20,

            "oriel_event": {
                "id":
                    "stop-late",

                "kind":
                    "show",

                "entities": [
                    "band"
                ],

                "location_id":
                    "beta",

                "start":
                    (
                        "2026-01-01"
                        "T16:00:00-05:00"
                    ),

                "duration_minutes":
                    60,

                "source_class":
                    "simulation",
            },
        },
    ]

    lattice = engine.superpose(
        document,
        facts,
        scenario_value,
        possibilities,
    )

    if (
        lattice[
            "branch_count"
        ]
        != 2
    ):
        raise oriel_consequence_error(
            (
                "selftest expected "
                "two consequence branches"
            )
        )

    branches = {
        value[
            "quantum_branch"
        ][
            "possibility"
        ][
            "name"
        ]:
            value
        for value
        in lattice[
            "branches"
        ]
    }

    early = branches[
        "early-stop"
    ]

    late = branches[
        "late-stop"
    ]

    if (
        early[
            "minimum_anchor_slack_minutes"
        ]
        is None
    ):
        raise oriel_consequence_error(
            (
                "selftest failed to "
                "calculate early anchor slack"
            )
        )

    if (
        late[
            "minimum_anchor_slack_minutes"
        ]
        is None
    ):
        raise oriel_consequence_error(
            (
                "selftest failed to "
                "calculate late anchor slack"
            )
        )

    if not (
        float(
            early[
                "minimum_anchor_slack_minutes"
            ]
        )
        > float(
            late[
                "minimum_anchor_slack_minutes"
            ]
        )
    ):
        raise oriel_consequence_error(
            (
                "selftest failed to "
                "rank anchor slack"
            )
        )

    frontier = engine.frontier(
        lattice
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

        "branch_count":
            lattice[
                "branch_count"
            ],

        "early_anchor_slack_minutes":
            early[
                "minimum_anchor_slack_minutes"
            ],

        "late_anchor_slack_minutes":
            late[
                "minimum_anchor_slack_minutes"
            ],

        "early_has_more_anchor_slack":
            True,

        "pareto_frontier_count":
            frontier[
                "frontier_count"
            ],

        "immutable_reality_preserved":
            True,

        "source_state_mutated":
            False,

        "canon_effect":
            "none",

        "evidence_admission":
            False,
    }


__all__ = [
    "OrielConsequenceEngine",
    "capability_manifest",
    "engine",
    "graph_delta",
    "selftest",
    "status",
]

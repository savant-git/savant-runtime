#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping, Sequence

from oriel import event as oriel_event
from oriel import oriel_engine
from oriel_inverse import engine as inverse_engine
from oriel_quantum import engine as quantum_engine
from oriel_quantum import possibilities_from_sequence, scenario_from_mapping
from oriel_reality import engine as reality_engine


owner = "carbon"
component = "oriel-simulation"
authority_effect = "none"
schema = "savant.carbon.oriel-simulation.v1"

availability_required_kinds = {
    "concert",
    "performance",
    "show",
}

classification_order = {
    "viable": 0,
    "conditional": 1,
    "unresolved": 2,
    "infeasible": 3,
}

constraint_scopes = {
    "location",
    "entity",
    "resource",
    "intersection",
    "global",
}


class oriel_simulation_error(
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
        separators=(",", ":"),
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
        )[:24]
    )


def location_timezone(
    document: Mapping[str, Any],
    location_id: str,
) -> str | None:
    for value in document.get(
        "locations",
        [],
    ):
        if (
            isinstance(
                value,
                Mapping,
            )
            and str(
                value.get(
                    "id",
                    "",
                )
            )
            == location_id
        ):
            timezone_name = value.get(
                "timezone"
            )

            return (
                str(
                    timezone_name
                )
                if timezone_name
                is not None
                else None
            )

    return None


def requires_availability(
    event_value: Mapping[str, Any],
) -> bool:
    metadata = event_value.get(
        "metadata",
        {},
    )

    if isinstance(
        metadata,
        Mapping,
    ):
        explicit = metadata.get(
            "requires_verified_availability"
        )

        if explicit is not None:
            return bool(
                explicit
            )

        requirements = metadata.get(
            "reality_requirements",
            [],
        )

        if isinstance(
            requirements,
            str,
        ):
            requirements = [
                requirements
            ]

        if isinstance(
            requirements,
            Sequence,
        ):
            normalized = {
                str(
                    item
                ).strip().lower()
                for item
                in requirements
            }

            if (
                "availability"
                in normalized
            ):
                return True

    return (
        str(
            event_value.get(
                "kind",
                "",
            )
        ).strip().lower()
        in availability_required_kinds
    )


def event_window(
    document: Mapping[str, Any],
    event_value: Mapping[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    location_id = str(
        event_value.get(
            "location_id",
            "",
        )
    ).strip()

    parsed = oriel_event.from_mapping(
        event_value,
        location_timezone=
            location_timezone(
                document,
                location_id,
            ),
    )

    return (
        parsed.start.projection(),
        parsed.end.projection(),
    )


def immutable_reality_digest(
    document: Mapping[str, Any],
) -> str:
    return digest(
        {
            "external_constraints":
                document.get(
                    "external_constraints",
                    [],
                ),

            "reality_bindings":
                document.get(
                    "reality_bindings",
                    [],
                ),
        }
    )


def strict_scope_document(
    bound_document: Mapping[str, Any],
) -> dict[str, Any]:
    output = clone(
        dict(
            bound_document
        )
    )

    bindings = {
        str(
            value.get(
                "id",
                "",
            )
        ):
            value
        for value
        in output.get(
            "reality_bindings",
            [],
        )
        if (
            isinstance(
                value,
                Mapping,
            )
            and str(
                value.get(
                    "id",
                    "",
                )
            )
        )
    }

    constraints = []

    for raw in output.get(
        "external_constraints",
        [],
    ):
        if not isinstance(
            raw,
            Mapping,
        ):
            constraints.append(
                clone(
                    raw
                )
            )

            continue

        value = clone(
            dict(
                raw
            )
        )

        metadata = value.get(
            "metadata",
            {},
        )

        metadata = (
            clone(
                dict(
                    metadata
                )
            )
            if isinstance(
                metadata,
                Mapping,
            )
            else {}
        )

        fact = bindings.get(
            str(
                metadata.get(
                    "reality_fact_id",
                    "",
                )
            ).strip()
        )

        if fact is None:
            constraints.append(
                value
            )

            continue

        fact_metadata = fact.get(
            "metadata",
            {},
        )

        fact_metadata = (
            fact_metadata
            if isinstance(
                fact_metadata,
                Mapping,
            )
            else {}
        )

        scope = str(
            fact_metadata.get(
                "scope",
                "",
            )
        ).strip().lower()

        if not scope:
            if fact.get(
                "location_id"
            ):
                scope = "location"

            elif fact.get(
                "entities"
            ):
                scope = "entity"

            elif fact.get(
                "resources"
            ):
                scope = "resource"

            else:
                scope = "global"

        if (
            scope
            not in constraint_scopes
        ):
            raise oriel_simulation_error(
                (
                    "unsupported reality "
                    "constraint scope: "
                    + scope
                )
            )

        metadata[
            "scope"
        ] = scope

        metadata[
            "historical_entities"
        ] = clone(
            value.get(
                "entities",
                [],
            )
        )

        metadata[
            "historical_resources"
        ] = clone(
            value.get(
                "resources",
                [],
            )
        )

        if scope == "location":
            value[
                "entities"
            ] = []

            value[
                "resources"
            ] = []

        elif scope == "entity":
            value[
                "resources"
            ] = []

        elif scope == "resource":
            value[
                "entities"
            ] = []

        elif scope == "global":
            value[
                "location_id"
            ] = None

            value[
                "entities"
            ] = []

            value[
                "resources"
            ] = []

        value[
            "metadata"
        ] = metadata

        constraints.append(
            value
        )

    output[
        "external_constraints"
    ] = constraints

    return output


def merge_classification(
    base: str,
    availability_state: str | None,
) -> str:
    if (
        base == "infeasible"
        or availability_state
        == "verified_conflict"
    ):
        return "infeasible"

    if (
        availability_state
        == "unresolved"
    ):
        return "unresolved"

    return base


def solution_rank(
    value: Mapping[str, Any],
) -> tuple[
    int,
    int,
    float,
    int,
    str,
]:
    return (
        classification_order.get(
            str(
                value.get(
                    "classification",
                    "unresolved",
                )
            ),
            4,
        ),

        int(
            value.get(
                "existing_event_edit_count",
                0,
            )
        ),

        float(
            value.get(
                "cost",
                0.0,
            )
        ),

        int(
            value.get(
                "edit_count",
                0,
            )
        ),

        str(
            value.get(
                "id",
                value.get(
                    "possibility_id",
                    "",
                ),
            )
        ),
    )


class OrielSimulationEngine:
    def compile_world(
        self,
        document: Mapping[str, Any],
        facts: Sequence[
            Mapping[
                str,
                Any,
            ]
        ],
    ) -> dict[str, Any]:
        binding = reality_engine.bind(
            document,
            facts,
        )

        bound_document = (
            strict_scope_document(
                binding[
                    "bound_document"
                ]
            )
        )

        reality_digest = (
            immutable_reality_digest(
                bound_document
            )
        )

        result = {
            "schema":
                schema,

            "kind":
                "compiled-world",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "id":
                stable_id(
                    "carbon-oriel-world",
                    {
                        "source_document_digest":
                            binding[
                                "source_document_digest"
                            ],

                        "facts_digest":
                            digest(
                                facts
                            ),

                        "reality_digest":
                            reality_digest,
                    },
                ),

            "source_document_digest":
                binding[
                    "source_document_digest"
                ],

            "facts_digest":
                digest(
                    facts
                ),

            "bound_document_digest":
                digest(
                    bound_document
                ),

            "immutable_reality_digest":
                reality_digest,

            "fact_count":
                binding[
                    "fact_count"
                ],

            "generated_constraint_count":
                binding[
                    "generated_constraint_count"
                ],

            "bound_document":
                bound_document,

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

    def availability_for_event(
        self,
        document: Mapping[str, Any],
        facts: Sequence[
            Mapping[
                str,
                Any,
            ]
        ],
        event_value: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        if not requires_availability(
            event_value
        ):
            return None

        location_id = str(
            event_value.get(
                "location_id",
                "",
            )
        ).strip()

        if not location_id:
            return {
                "state":
                    "unresolved",

                "reason":
                    (
                        "availability-required "
                        "event has no location_id"
                    ),
            }

        start, end = event_window(
            document,
            event_value,
        )

        return reality_engine.availability(
            document,
            facts,
            location_id=
                location_id,
            start=start,
            end=end,
        )

    def validate_world(
        self,
        document: Mapping[str, Any],
        facts: Sequence[
            Mapping[
                str,
                Any,
            ]
        ],
        *,
        mode: str = "tour_bus",
    ) -> dict[str, Any]:
        world = self.compile_world(
            document,
            facts,
        )

        base = (
            oriel_engine.from_document(
                world[
                    "bound_document"
                ]
            ).validate(
                mode=mode
            )
        )

        checks = []

        for event_value in document.get(
            "events",
            [],
        ):
            if not isinstance(
                event_value,
                Mapping,
            ):
                continue

            availability = (
                self.availability_for_event(
                    document,
                    facts,
                    event_value,
                )
            )

            if availability is None:
                continue

            state = str(
                availability.get(
                    "state",
                    "unresolved",
                )
            )

            if state == "verified_conflict":
                outcome = "fail"

            elif state == "unresolved":
                outcome = "unknown"

            else:
                outcome = "pass"

            checks.append(
                {
                    "event":
                        event_value.get(
                            "id"
                        ),

                    "outcome":
                        outcome,

                    "availability":
                        availability,
                }
            )

        if (
            base[
                "outcome"
            ]
            == "fail"
            or any(
                value[
                    "outcome"
                ]
                == "fail"
                for value
                in checks
            )
        ):
            outcome = "fail"

        elif (
            base[
                "outcome"
            ]
            == "unknown"
            or any(
                value[
                    "outcome"
                ]
                == "unknown"
                for value
                in checks
            )
        ):
            outcome = "unknown"

        elif (
            base[
                "outcome"
            ]
            == "advisory"
        ):
            outcome = "advisory"

        else:
            outcome = "pass"

        return {
            "schema":
                schema,

            "kind":
                "world-validation",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "outcome":
                outcome,

            "world":
                world,

            "oriel_validation":
                base,

            "reality_checks":
                checks,

            "source_state_mutated":
                False,

            "canon_effect":
                "none",

            "evidence_admission":
                False,
        }

    def assert_reality_integrity(
        self,
        document: Mapping[str, Any],
        expected_digest: str,
    ) -> None:
        actual = (
            immutable_reality_digest(
                document
            )
        )

        if actual != expected_digest:
            raise oriel_simulation_error(
                (
                    "branch altered immutable "
                    "reality bindings"
                )
            )

    def superpose(
        self,
        document: Mapping[str, Any],
        facts: Sequence[
            Mapping[
                str,
                Any,
            ]
        ],
        scenario_value: Mapping[str, Any],
        possibilities_value: Sequence[
            Mapping[
                str,
                Any,
            ]
        ],
        *,
        mode: str = "tour_bus",
    ) -> dict[str, Any]:
        world = self.compile_world(
            document,
            facts,
        )

        lattice = quantum_engine.superpose(
            world[
                "bound_document"
            ],
            scenario_from_mapping(
                scenario_value
            ),
            possibilities_from_sequence(
                possibilities_value
            ),
            mode=mode,
        )

        expected = world[
            "immutable_reality_digest"
        ]

        for branch in lattice.get(
            "branches",
            [],
        ):
            if not isinstance(
                branch,
                dict,
            ):
                continue

            candidate_document = branch.get(
                "candidate_oriel_document"
            )

            if not isinstance(
                candidate_document,
                Mapping,
            ):
                raise oriel_simulation_error(
                    (
                        "quantum branch lacks "
                        "candidate Oriel document"
                    )
                )

            self.assert_reality_integrity(
                candidate_document,
                expected,
            )

            possibility = branch.get(
                "possibility",
                {},
            )

            event_value = (
                possibility.get(
                    "oriel_event"
                )
                if isinstance(
                    possibility,
                    Mapping,
                )
                else None
            )

            availability = (
                self.availability_for_event(
                    document,
                    facts,
                    event_value,
                )
                if isinstance(
                    event_value,
                    Mapping,
                )
                else None
            )

            availability_state = (
                str(
                    availability.get(
                        "state",
                        "unresolved",
                    )
                )
                if isinstance(
                    availability,
                    Mapping,
                )
                else None
            )

            branch[
                "reality_availability"
            ] = clone(
                availability
            )

            branch[
                "classification"
            ] = merge_classification(
                str(
                    branch.get(
                        "classification",
                        "unresolved",
                    )
                ),
                availability_state,
            )

            branch[
                "reality_integrity"
            ] = "pass"

            branch[
                "digest"
            ] = digest(
                {
                    key:
                        value
                    for key, value
                    in branch.items()
                    if key
                    != "digest"
                }
            )

        lattice[
            "branches"
        ] = sorted(
            lattice.get(
                "branches",
                [],
            ),
            key=solution_rank,
        )

        lattice[
            "classification_counts"
        ] = {
            label:
                sum(
                    1
                    for branch
                    in lattice[
                        "branches"
                    ]
                    if branch.get(
                        "classification"
                    )
                    == label
                )
            for label
            in (
                "viable",
                "conditional",
                "unresolved",
                "infeasible",
            )
        }

        lattice[
            "nearest_viable"
        ] = next(
            (
                branch.get(
                    "possibility_id"
                )
                for branch
                in lattice[
                    "branches"
                ]
                if branch.get(
                    "classification"
                )
                == "viable"
            ),
            None,
        )

        lattice[
            "world_id"
        ] = world[
            "id"
        ]

        lattice[
            "immutable_reality_digest"
        ] = expected

        lattice[
            "reality_bound"
        ] = True

        lattice[
            "digest"
        ] = digest(
            {
                key:
                    value
                for key, value
                in lattice.items()
                if key
                != "digest"
            }
        )

        return {
            "schema":
                schema,

            "kind":
                "reality-bound-superposition",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "world":
                world,

            "lattice":
                lattice,

            "source_state_mutated":
                False,

            "canon_effect":
                "none",

            "evidence_admission":
                False,
        }

    def inverse(
        self,
        document: Mapping[str, Any],
        facts: Sequence[
            Mapping[
                str,
                Any,
            ]
        ],
        desired_event: Mapping[str, Any],
        *,
        mode: str = "tour_bus",
        candidate_locations:
            Sequence[str] = (),
        transport_modes:
            Sequence[str] = (),
        policy:
            Mapping[
                str,
                Any,
            ]
            | None = None,
    ) -> dict[str, Any]:
        world = self.compile_world(
            document,
            facts,
        )

        result = inverse_engine.search(
            world[
                "bound_document"
            ],
            desired_event,
            mode=mode,
            candidate_locations=
                candidate_locations,
            transport_modes=
                transport_modes,
            policy=policy,
        )

        expected = world[
            "immutable_reality_digest"
        ]

        solutions = []

        for name in (
            "viable",
            "conditional",
            "unresolved",
        ):
            values = result.get(
                name,
                [],
            )

            if isinstance(
                values,
                list,
            ):
                solutions.extend(
                    value
                    for value
                    in values
                    if isinstance(
                        value,
                        dict,
                    )
                )

        best_infeasible = result.get(
            "best_infeasible"
        )

        if isinstance(
            best_infeasible,
            dict,
        ):
            solutions.append(
                best_infeasible
            )

        for solution in solutions:
            candidate_document = (
                solution.get(
                    "candidate_document"
                )
            )

            if isinstance(
                candidate_document,
                Mapping,
            ):
                self.assert_reality_integrity(
                    candidate_document,
                    expected,
                )

            event_value = solution.get(
                "candidate"
            )

            availability = (
                self.availability_for_event(
                    document,
                    facts,
                    event_value,
                )
                if isinstance(
                    event_value,
                    Mapping,
                )
                else None
            )

            availability_state = (
                str(
                    availability.get(
                        "state",
                        "unresolved",
                    )
                )
                if isinstance(
                    availability,
                    Mapping,
                )
                else None
            )

            solution[
                "reality_availability"
            ] = clone(
                availability
            )

            solution[
                "classification"
            ] = merge_classification(
                str(
                    solution.get(
                        "classification",
                        "unresolved",
                    )
                ),
                availability_state,
            )

            solution[
                "reality_integrity"
            ] = "pass"

        ranked = sorted(
            solutions,
            key=solution_rank,
        )

        result[
            "nearest_solution"
        ] = (
            ranked[
                0
            ]
            if ranked
            else None
        )

        result[
            "reality_viable_count"
        ] = sum(
            1
            for value
            in ranked
            if value.get(
                "classification"
            )
            == "viable"
        )

        result[
            "world_id"
        ] = world[
            "id"
        ]

        result[
            "immutable_reality_digest"
        ] = expected

        result[
            "reality_bound"
        ] = True

        result[
            "digest"
        ] = digest(
            {
                key:
                    value
                for key, value
                in result.items()
                if key
                != "digest"
            }
        )

        return {
            "schema":
                schema,

            "kind":
                "reality-bound-inverse-search",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "world":
                world,

            "result":
                result,

            "source_state_mutated":
                False,

            "canon_effect":
                "none",

            "evidence_admission":
                False,
        }

    def position(
        self,
        document: Mapping[str, Any],
        facts: Sequence[
            Mapping[
                str,
                Any,
            ]
        ],
        *,
        entity: str,
        timestamp: Any,
        mode: str = "tour_bus",
    ) -> dict[str, Any]:
        world = self.compile_world(
            document,
            facts,
        )

        value = (
            oriel_engine.from_document(
                world[
                    "bound_document"
                ]
            ).position_at(
                entity,
                timestamp,
                mode=mode,
            )
        )

        value[
            "world_id"
        ] = world[
            "id"
        ]

        value[
            "reality_bound"
        ] = True

        return value

    def availability(
        self,
        document: Mapping[str, Any],
        facts: Sequence[
            Mapping[
                str,
                Any,
            ]
        ],
        *,
        location_id: str,
        start: Any,
        end: Any,
    ) -> dict[str, Any]:
        return reality_engine.availability(
            document,
            facts,
            location_id=
                location_id,
            start=start,
            end=end,
        )

    def encounters(
        self,
        document: Mapping[str, Any],
        facts: Sequence[
            Mapping[
                str,
                Any,
            ]
        ],
        *,
        fictional_entity: str,
        historical_entity: str,
        radius_km: float = 5.0,
    ) -> dict[str, Any]:
        return (
            reality_engine
            .encounter_opportunities(
                document,
                facts,
                fictional_entity=
                    fictional_entity,
                historical_entity=
                    historical_entity,
                radius_km=
                    radius_km,
            )
        )


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
        dependencies: Sequence[str],
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

            "dependencies":
                list(
                    dependencies
                ),

            "deterministic":
                True,

            "side_effects":
                [],

            "projection":
                clone(
                    projection
                ),
        }

    capabilities = [
        capability(
            "oriel_reality_bound_world",
            "composition",
            (
                "Compile one historically "
                "constrained Oriel world used by "
                "chronology, logistics, quantum "
                "and inverse simulation."
            ),
            [
                "compile",
                "validate",
                "position",
            ],
            [
                "oriel_reality_binding",
                "oriel_chronology_validation",
                "oriel_logistics_validation",
            ],
        ),

        capability(
            "oriel_reality_bound_quantum",
            "composition",
            (
                "Gate Carbon superposition through "
                "the same immutable historical "
                "reality envelope used by "
                "Oriel logistics."
            ),
            [
                "superpose"
            ],
            [
                "oriel_quantum_feasibility",
                "oriel_reality_binding",
                "oriel_availability_evidence",
            ],
        ),

        capability(
            "oriel_reality_bound_inverse",
            "composition",
            (
                "Search for minimal chronology "
                "repairs without permitting branches "
                "to alter sourced historical reality."
            ),
            [
                "inverse"
            ],
            [
                "oriel_inverse_chronology",
                "oriel_reality_binding",
                "oriel_availability_evidence",
            ],
        ),

        capability(
            "oriel_reality_interrogation",
            "projection",
            (
                "Expose reality-bound position, "
                "availability and encounter queries "
                "through one Carbon-owned interface."
            ),
            [
                "position",
                "availability",
                "encounters",
            ],
            [
                "oriel_spacetime_position",
                "oriel_historical_snapshot",
                "oriel_encounter_opportunity",
            ],
        ),
    ]

    return {
        "schema":
            (
                "savant.carbon.oriel-simulation."
                "capabilities.v1"
            ),

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "capabilities":
            capabilities,

        "invariants": {
            "carbon_owns_simulation":
                True,

            "oriel_is_contained_by_carbon":
                True,

            "reality_is_immutable_across_branches":
                True,

            "absence_of_evidence_is_not_availability":
                True,

            "canon_effect":
                "none",

            "evidence_admission":
                False,
        },
    }


engine = OrielSimulationEngine()


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
                "reality-bound chronology "
                "and logistics intelligence"
            ),

        "reality_binding":
            True,

        "quantum_binding":
            True,

        "inverse_binding":
            True,

        "strict_constraint_scopes":
            sorted(
                constraint_scopes
            ),

        "availability_required_kinds":
            sorted(
                availability_required_kinds
            ),

        "absence_of_evidence_is_availability":
            False,

        "immutable_reality_can_branch":
            False,

        "source_state_mutated":
            False,

        "canon_effect":
            "none",

        "evidence_admission":
            False,

        "capability_count":
            len(
                capability_manifest()[
                    "capabilities"
                ]
            ),

        "ready":
            True,
    }


def selftest() -> dict[str, Any]:
    document = {
        "locations": [
            {
                "id":
                    "venue-a",

                "name":
                    "venue a",

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
                    "venue-b",

                "name":
                    "venue b",

                "latitude":
                    40.02,

                "longitude":
                    -75.02,

                "timezone":
                    "America/New_York",

                "source_class":
                    "verified_external",
            },
        ],

        "events":
            [],
    }

    facts = [
        {
            "id":
                "real-booking",

            "kind":
                "real-concert",

            "effect":
                "occupy",

            "location_id":
                "venue-a",

            "entities": [
                "real-band"
            ],

            "start":
                (
                    "2017-07-07"
                    "T18:00:00-04:00"
                ),

            "end":
                (
                    "2017-07-07"
                    "T23:00:00-04:00"
                ),

            "constraint_class":
                "hard",

            "source_class":
                "verified_external",

            "verification_state":
                "verified",

            "source_refs": [
                "focused-test:real-booking"
            ],
        },
        {
            "id":
                "venue-b-open",

            "kind":
                "venue-availability",

            "effect":
                "available",

            "location_id":
                "venue-b",

            "start":
                (
                    "2017-07-07"
                    "T17:00:00-04:00"
                ),

            "end":
                (
                    "2017-07-07"
                    "T23:59:00-04:00"
                ),

            "source_class":
                "verified_external",

            "verification_state":
                "verified",

            "source_refs": [
                "focused-test:venue-b"
            ],
        },
    ]

    scenario_value = {
        "name":
            "baseline",

        "initial_state": {
            "band":
                "sgis"
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
                "occupied venue",

            "oriel_event": {
                "id":
                    "fictional-a",

                "kind":
                    "show",

                "entities": [
                    "sgis"
                ],

                "location_id":
                    "venue-a",

                "start":
                    (
                        "2017-07-07"
                        "T19:00:00-04:00"
                    ),

                "duration_minutes":
                    180,

                "source_class":
                    "simulation",
            },
        },
        {
            "name":
                "available venue",

            "oriel_event": {
                "id":
                    "fictional-b",

                "kind":
                    "show",

                "entities": [
                    "sgis"
                ],

                "location_id":
                    "venue-b",

                "start":
                    (
                        "2017-07-07"
                        "T19:00:00-04:00"
                    ),

                "duration_minutes":
                    180,

                "source_class":
                    "simulation",
            },
        },
    ]

    superposition = engine.superpose(
        document,
        facts,
        scenario_value,
        possibilities,
    )

    counts = (
        superposition[
            "lattice"
        ][
            "classification_counts"
        ]
    )

    if (
        counts.get(
            "infeasible",
            0,
        )
        < 1
    ):
        raise oriel_simulation_error(
            (
                "reality-bound quantum test "
                "failed to reject occupied venue"
            )
        )

    if (
        counts.get(
            "viable",
            0,
        )
        < 1
    ):
        raise oriel_simulation_error(
            (
                "reality-bound quantum test "
                "failed to retain available venue"
            )
        )

    inverse = engine.inverse(
        document,
        facts,
        clone(
            possibilities[
                0
            ][
                "oriel_event"
            ]
        ),
        candidate_locations=[
            "venue-b"
        ],
        policy={
            "resolution_minutes":
                30,

            "maximum_candidate_shift_minutes":
                60,

            "maximum_existing_shift_minutes":
                0,

            "maximum_depth":
                2,

            "maximum_states":
                80,

            "solution_limit":
                8,
        },
    )

    nearest = (
        inverse[
            "result"
        ].get(
            "nearest_solution"
        )
    )

    if (
        not isinstance(
            nearest,
            Mapping,
        )
        or nearest.get(
            "classification"
        )
        != "viable"
    ):
        raise oriel_simulation_error(
            (
                "reality-bound inverse test "
                "did not find available venue repair"
            )
        )

    if (
        nearest.get(
            "candidate",
            {},
        ).get(
            "location_id"
        )
        != "venue-b"
    ):
        raise oriel_simulation_error(
            (
                "inverse repair did not select "
                "the verified available location"
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

        "occupied_quantum_branch_rejected":
            True,

        "available_quantum_branch_retained":
            True,

        "inverse_found_reality_valid_repair":
            True,

        "inverse_repair_location":
            nearest.get(
                "candidate",
                {},
            ).get(
                "location_id"
            ),

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
    "OrielSimulationEngine",
    "capability_manifest",
    "engine",
    "selftest",
    "status",
]

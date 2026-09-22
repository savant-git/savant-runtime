#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import json

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Sequence

from oriel import (
    haversine_km,
    oriel_engine,
    parse_datetime,
    possible_overlap,
    temporal_window,
    to_utc,
)


owner = "carbon"
component = "oriel-reality"
authority_effect = "none"
schema = "savant.carbon.oriel-reality.v1"


effects = {
    "block",
    "occupy",
    "available",
    "context",
    "condition",
}


constraint_classes = {
    "hard",
    "soft",
    "informational",
}


source_classes = {
    "admitted_evidence",
    "verified_external",
    "asserted",
    "derived",
    "estimate",
    "simulation",
    "unknown",
}


verification_states = {
    "verified",
    "corroborated",
    "reported",
    "inferred",
    "unknown",
}


availability_states = {
    "verified_conflict",
    "verified_available",
    "no_conflict_found",
    "unresolved",
}


enhancements = (
    "historical reality bindings",
    "real concert occupancy bindings",
    "venue booking bindings",
    "venue closure bindings",
    "hotel existence bindings",
    "hotel closure bindings",
    "weather bindings",
    "road disruption bindings",
    "transport disruption bindings",
    "border disruption bindings",
    "local event bindings",
    "source-class preservation",
    "source-reference preservation",
    "verification-state metadata",
    "fact-level confidence metadata",
    "fact-level retrieval metadata",
    "fact-level publication metadata",
    "coverage-window metadata",
    "complete-source-coverage semantics",
    "verified-conflict classification",
    "verified-availability classification",
    "no-conflict-found classification",
    "unresolved availability classification",
    "absence-of-evidence protection",
    "immutable external fact projection",
    "external constraint generation",
    "duplicate fact coalescence",
    "conflicting fact-id rejection",
    "reality snapshot queries",
    "historical presence queries",
    "real-fictional encounter opportunities",
    "geographic proximity validation",
    "source gap reporting",
    "venue-calendar coverage reporting",
    "historical constraint explanation",
    "reality-aware itinerary validation",
    "source-neutral simulation state",
    "no automatic evidence admission",
    "no automatic canon promotion",
    "quantum-safe external constraints",
    "inverse-search-safe immutable anchors",
    "deterministic reality digests",
    "filament-projectable reality packets",
    "modus-maskable query metadata",
)


class oriel_reality_error(
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


def location_timezone(
    document: Mapping[
        str,
        Any,
    ],
    location_id: str | None,
) -> str | None:
    if not location_id:
        return None

    for value in document.get(
        "locations",
        [],
    ):
        if not isinstance(
            value,
            Mapping,
        ):
            continue

        if str(
            value.get(
                "id",
                "",
            )
        ) != location_id:
            continue

        timezone_name = value.get(
            "timezone"
        )

        if timezone_name is None:
            return None

        return str(
            timezone_name
        )

    return None


def window_covers(
    outer_start: temporal_window,
    outer_end: temporal_window,
    inner_start: temporal_window,
    inner_end: temporal_window,
) -> bool:
    return (
        to_utc(
            outer_start.earliest
        )
        <= to_utc(
            inner_start.earliest
        )
        and to_utc(
            outer_end.latest
        )
        >= to_utc(
            inner_end.latest
        )
    )


@dataclass(
    frozen=True,
    slots=True,
)
class RealityFact:
    id: str
    kind: str
    effect: str
    start: temporal_window
    end: temporal_window
    location_id: str | None
    entities: tuple[str, ...]
    resources: tuple[str, ...]
    constraint_class: str
    source_class: str
    verification_state: str
    source_refs: tuple[str, ...]
    confidence: float | None = None
    retrieved_at: str | None = None
    published_at: str | None = None
    coverage: Mapping[
        str,
        Any,
    ] = field(
        default_factory=dict
    )
    metadata: Mapping[
        str,
        Any,
    ] = field(
        default_factory=dict
    )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[
            str,
            Any,
        ],
        *,
        document: Mapping[
            str,
            Any,
        ],
    ) -> RealityFact:
        identifier = str(
            value.get(
                "id",
                "",
            )
        ).strip()

        if not identifier:
            raise oriel_reality_error(
                "reality fact id is required"
            )

        kind = str(
            value.get(
                "kind",
                "",
            )
        ).strip().lower()

        if not kind:
            raise oriel_reality_error(
                (
                    "reality fact kind is required: "
                    + identifier
                )
            )

        effect = str(
            value.get(
                "effect",
                "context",
            )
        ).strip().lower()

        if effect not in effects:
            raise oriel_reality_error(
                (
                    "unsupported reality effect: "
                    + effect
                )
            )

        location_id = (
            str(
                value.get(
                    "location_id"
                )
            ).strip()
            if value.get(
                "location_id"
            )
            is not None
            else None
        )

        timezone_name = location_timezone(
            document,
            location_id,
        )

        source_class = str(
            value.get(
                "source_class",
                "unknown",
            )
        ).strip().lower()

        if source_class not in source_classes:
            raise oriel_reality_error(
                (
                    "unsupported reality source class: "
                    + source_class
                )
            )

        source_refs = normalized_strings(
            value.get(
                "source_refs"
            )
        )

        if (
            source_class
            in {
                "verified_external",
                "admitted_evidence",
            }
            and not source_refs
        ):
            raise oriel_reality_error(
                (
                    "verified reality fact requires "
                    "source_refs: "
                    + identifier
                )
            )

        verification_state = str(
            value.get(
                "verification_state",
                (
                    "verified"
                    if source_class
                    in {
                        "verified_external",
                        "admitted_evidence",
                    }
                    else "unknown"
                ),
            )
        ).strip().lower()

        if (
            verification_state
            not in verification_states
        ):
            raise oriel_reality_error(
                (
                    "unsupported verification state: "
                    + verification_state
                )
            )

        constraint_class = str(
            value.get(
                "constraint_class",
                (
                    "hard"
                    if effect
                    in {
                        "block",
                        "occupy",
                    }
                    else "informational"
                ),
            )
        ).strip().lower()

        if (
            constraint_class
            not in constraint_classes
        ):
            raise oriel_reality_error(
                (
                    "unsupported constraint class: "
                    + constraint_class
                )
            )

        start = temporal_window.from_value(
            value.get(
                "start"
            ),
            default_timezone=
                timezone_name,
            default_source_class=
                source_class,
        )

        end = temporal_window.from_value(
            value.get(
                "end",
                value.get(
                    "start"
                ),
            ),
            default_timezone=
                timezone_name,
            default_source_class=
                source_class,
        )

        if (
            to_utc(
                end.latest
            )
            < to_utc(
                start.earliest
            )
        ):
            raise oriel_reality_error(
                (
                    "reality fact ends before "
                    "it begins: "
                    + identifier
                )
            )

        confidence = value.get(
            "confidence"
        )

        if confidence is not None:
            confidence = float(
                confidence
            )

            if not (
                0.0
                <= confidence
                <= 1.0
            ):
                raise oriel_reality_error(
                    (
                        "confidence must be "
                        "between zero and one"
                    )
                )

        coverage = value.get(
            "coverage",
            {},
        )

        if not isinstance(
            coverage,
            Mapping,
        ):
            raise oriel_reality_error(
                "coverage must be an object"
            )

        metadata = value.get(
            "metadata",
            {},
        )

        if not isinstance(
            metadata,
            Mapping,
        ):
            raise oriel_reality_error(
                "metadata must be an object"
            )

        return cls(
            id=identifier,
            kind=kind,
            effect=effect,
            start=start,
            end=end,
            location_id=
                location_id,
            entities=
                normalized_strings(
                    value.get(
                        "entities"
                    )
                ),
            resources=
                normalized_strings(
                    value.get(
                        "resources"
                    )
                ),
            constraint_class=
                constraint_class,
            source_class=
                source_class,
            verification_state=
                verification_state,
            source_refs=
                source_refs,
            confidence=
                confidence,
            retrieved_at=(
                str(
                    value.get(
                        "retrieved_at"
                    )
                )
                if value.get(
                    "retrieved_at"
                )
                is not None
                else None
            ),
            published_at=(
                str(
                    value.get(
                        "published_at"
                    )
                )
                if value.get(
                    "published_at"
                )
                is not None
                else None
            ),
            coverage=
                clone(
                    dict(
                        coverage
                    )
                ),
            metadata=
                clone(
                    dict(
                        metadata
                    )
                ),
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        result = {
            "id":
                self.id,

            "kind":
                self.kind,

            "effect":
                self.effect,

            "start":
                self.start.projection(),

            "end":
                self.end.projection(),

            "location_id":
                self.location_id,

            "entities":
                list(
                    self.entities
                ),

            "resources":
                list(
                    self.resources
                ),

            "constraint_class":
                self.constraint_class,

            "source_class":
                self.source_class,

            "verification_state":
                self.verification_state,

            "source_refs":
                list(
                    self.source_refs
                ),

            "confidence":
                self.confidence,

            "retrieved_at":
                self.retrieved_at,

            "published_at":
                self.published_at,

            "coverage":
                clone(
                    dict(
                        self.coverage
                    )
                ),

            "metadata":
                clone(
                    dict(
                        self.metadata
                    )
                ),

            "authority_effect":
                "none",

            "immutable_in_simulation":
                (
                    self.source_class
                    in {
                        "verified_external",
                        "admitted_evidence",
                    }
                ),
        }

        result[
            "digest"
        ] = digest(
            result
        )

        return result


def normalize_facts(
    document: Mapping[
        str,
        Any,
    ],
    values: Sequence[
        Mapping[
            str,
            Any,
        ]
    ],
) -> list[RealityFact]:
    output = []
    seen = {}

    for value in values:
        if not isinstance(
            value,
            Mapping,
        ):
            raise oriel_reality_error(
                (
                    "each reality fact "
                    "must be an object"
                )
            )

        fact = RealityFact.from_mapping(
            value,
            document=document,
        )

        fact_digest = digest(
            fact.projection()
        )

        previous = seen.get(
            fact.id
        )

        if previous is not None:
            if previous != fact_digest:
                raise oriel_reality_error(
                    (
                        "conflicting reality fact id: "
                        + fact.id
                    )
                )

            continue

        seen[
            fact.id
        ] = fact_digest

        output.append(
            fact
        )

    return sorted(
        output,
        key=lambda item: (
            to_utc(
                item.start.earliest
            ),
            item.id,
        ),
    )


def constraint_projection(
    fact: RealityFact,
) -> dict[str, Any] | None:
    if (
        fact.effect
        not in {
            "block",
            "occupy",
        }
    ):
        return None

    return {
        "id":
            (
                "reality:"
                + fact.id
            ),

        "kind":
            fact.kind,

        "start":
            fact.start.projection(),

        "end":
            fact.end.projection(),

        "location_id":
            fact.location_id,

        "entities":
            list(
                fact.entities
            ),

        "resources":
            list(
                fact.resources
            ),

        "constraint_class":
            fact.constraint_class,

        "source_class":
            fact.source_class,

        "source_refs":
            list(
                fact.source_refs
            ),

        "metadata": {
            **clone(
                dict(
                    fact.metadata
                )
            ),

            "reality_fact_id":
                fact.id,

            "verification_state":
                fact.verification_state,

            "confidence":
                fact.confidence,

            "immutable":
                True,
        },
    }


def fact_active_at(
    fact: RealityFact,
    timestamp: datetime,
) -> bool:
    at = to_utc(
        timestamp
    )

    return (
        to_utc(
            fact.start.earliest
        )
        <= at
        <= to_utc(
            fact.end.latest
        )
    )


class OrielRealityEngine:
    def bind(
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
    ) -> dict[str, Any]:
        source_document = clone(
            dict(
                document
            )
        )

        normalized = normalize_facts(
            source_document,
            facts,
        )

        output = clone(
            source_document
        )

        existing_constraints = list(
            output.get(
                "external_constraints",
                [],
            )
        )

        constraint_index = {}

        for value in existing_constraints:
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
            )

            if identifier:
                constraint_index[
                    identifier
                ] = digest(
                    value
                )

        generated = []

        for fact in normalized:
            constraint = constraint_projection(
                fact
            )

            if constraint is None:
                continue

            identifier = str(
                constraint[
                    "id"
                ]
            )

            candidate_digest = digest(
                constraint
            )

            previous = constraint_index.get(
                identifier
            )

            if (
                previous is not None
                and previous
                != candidate_digest
            ):
                raise oriel_reality_error(
                    (
                        "reality binding conflicts "
                        "with existing constraint: "
                        + identifier
                    )
                )

            if previous is None:
                existing_constraints.append(
                    constraint
                )

                constraint_index[
                    identifier
                ] = candidate_digest

                generated.append(
                    identifier
                )

        output[
            "external_constraints"
        ] = existing_constraints

        output[
            "reality_bindings"
        ] = [
            fact.projection()
            for fact
            in normalized
        ]

        return {
            "schema":
                schema,

            "kind":
                "reality-binding",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "source_document_digest":
                digest(
                    source_document
                ),

            "bound_document_digest":
                digest(
                    output
                ),

            "fact_count":
                len(
                    normalized
                ),

            "generated_constraint_count":
                len(
                    generated
                ),

            "generated_constraints":
                generated,

            "bound_document":
                output,

            "source_state_mutated":
                False,

            "evidence_admission":
                False,

            "canon_effect":
                "none",
        }

    def validate(
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
        *,
        mode: str = "tour_bus",
    ) -> dict[str, Any]:
        binding = self.bind(
            document,
            facts,
        )

        validation = (
            oriel_engine.from_document(
                binding[
                    "bound_document"
                ]
            ).validate(
                mode=mode
            )
        )

        return {
            "schema":
                schema,

            "kind":
                "reality-aware-validation",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "outcome":
                validation[
                    "outcome"
                ],

            "binding":
                binding,

            "validation":
                validation,

            "source_state_mutated":
                False,

            "evidence_admission":
                False,

            "canon_effect":
                "none",
        }

    def availability(
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
        *,
        location_id: str,
        start: Any,
        end: Any,
    ) -> dict[str, Any]:
        normalized = normalize_facts(
            document,
            facts,
        )

        timezone_name = location_timezone(
            document,
            location_id,
        )

        requested_start = (
            temporal_window.from_value(
                start,
                default_timezone=
                    timezone_name,
                default_source_class=
                    "simulation",
            )
        )

        requested_end = (
            temporal_window.from_value(
                end,
                default_timezone=
                    timezone_name,
                default_source_class=
                    "simulation",
            )
        )

        relevant = [
            fact
            for fact
            in normalized
            if fact.location_id
            in {
                None,
                location_id,
            }
        ]

        conflicts = []
        explicit_availability = []
        coverage = []

        for fact in relevant:
            overlaps = possible_overlap(
                fact.start,
                fact.end,
                requested_start,
                requested_end,
            )

            if (
                overlaps
                and fact.effect
                in {
                    "block",
                    "occupy",
                }
            ):
                conflicts.append(
                    fact
                )

            if (
                fact.effect
                == "available"
                and window_covers(
                    fact.start,
                    fact.end,
                    requested_start,
                    requested_end,
                )
            ):
                explicit_availability.append(
                    fact
                )

            if (
                fact.coverage.get(
                    "complete",
                    False,
                )
                and window_covers(
                    fact.start,
                    fact.end,
                    requested_start,
                    requested_end,
                )
            ):
                coverage.append(
                    fact
                )

        verified_conflicts = [
            fact
            for fact
            in conflicts
            if (
                fact.verification_state
                in {
                    "verified",
                    "corroborated",
                }
                and fact.source_class
                in {
                    "verified_external",
                    "admitted_evidence",
                }
            )
        ]

        verified_available = [
            fact
            for fact
            in explicit_availability
            if (
                fact.verification_state
                in {
                    "verified",
                    "corroborated",
                }
                and fact.source_class
                in {
                    "verified_external",
                    "admitted_evidence",
                }
            )
        ]

        if verified_conflicts:
            state = "verified_conflict"

        elif verified_available:
            state = "verified_available"

        elif coverage:
            state = "no_conflict_found"

        else:
            state = "unresolved"

        return {
            "schema":
                schema,

            "kind":
                "availability",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "state":
                state,

            "location_id":
                location_id,

            "requested_start":
                requested_start.projection(),

            "requested_end":
                requested_end.projection(),

            "verified_conflicts": [
                fact.projection()
                for fact
                in verified_conflicts
            ],

            "verified_availability": [
                fact.projection()
                for fact
                in verified_available
            ],

            "complete_coverage": [
                fact.projection()
                for fact
                in coverage
            ],

            "absence_of_conflict_is_availability":
                False,

            "source_state_mutated":
                False,
        }

    def snapshot(
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
        *,
        timestamp: Any,
        location_id: str | None = None,
    ) -> dict[str, Any]:
        normalized = normalize_facts(
            document,
            facts,
        )

        timezone_name = location_timezone(
            document,
            location_id,
        )

        at = parse_datetime(
            timestamp,
            timezone_name=
                timezone_name,
        )

        active = [
            fact
            for fact
            in normalized
            if (
                fact_active_at(
                    fact,
                    at,
                )
                and (
                    location_id is None
                    or fact.location_id
                    in {
                        None,
                        location_id,
                    }
                )
            )
        ]

        return {
            "schema":
                schema,

            "kind":
                "historical-snapshot",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "timestamp":
                to_utc(
                    at
                ).isoformat(),

            "location_id":
                location_id,

            "fact_count":
                len(
                    active
                ),

            "facts": [
                fact.projection()
                for fact
                in active
            ],

            "source_state_mutated":
                False,
        }

    def encounter_opportunities(
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
        *,
        fictional_entity: str,
        historical_entity: str,
        radius_km: float = 5.0,
    ) -> dict[str, Any]:
        normalized = normalize_facts(
            document,
            facts,
        )

        engine = oriel_engine.from_document(
            document
        )

        fictional_events = [
            item
            for item
            in engine.events.values()
            if fictional_entity
            in item.entities
        ]

        historical_facts = [
            fact
            for fact
            in normalized
            if historical_entity
            in fact.entities
        ]

        matches = []

        for event_value in fictional_events:
            event_location = (
                engine.locations.get(
                    event_value.location_id
                )
            )

            if event_location is None:
                continue

            for fact in historical_facts:
                if not fact.location_id:
                    continue

                fact_location = (
                    engine.locations.get(
                        fact.location_id
                    )
                )

                if fact_location is None:
                    continue

                if not possible_overlap(
                    event_value.start,
                    event_value.end,
                    fact.start,
                    fact.end,
                ):
                    continue

                distance = haversine_km(
                    event_location.latitude,
                    event_location.longitude,
                    fact_location.latitude,
                    fact_location.longitude,
                )

                if distance > radius_km:
                    continue

                earliest = max(
                    to_utc(
                        event_value.start.earliest
                    ),
                    to_utc(
                        fact.start.earliest
                    ),
                )

                latest = min(
                    to_utc(
                        event_value.end.latest
                    ),
                    to_utc(
                        fact.end.latest
                    ),
                )

                matches.append(
                    {
                        "fictional_event":
                            event_value.id,

                        "historical_fact":
                            fact.id,

                        "fictional_location":
                            event_value.location_id,

                        "historical_location":
                            fact.location_id,

                        "distance_km":
                            round(
                                distance,
                                4,
                            ),

                        "earliest":
                            earliest.isoformat(),

                        "latest":
                            latest.isoformat(),

                        "historical_source_refs":
                            list(
                                fact.source_refs
                            ),

                        "historical_presence_verified":
                            (
                                fact.source_class
                                in {
                                    "verified_external",
                                    "admitted_evidence",
                                }
                                and fact.verification_state
                                in {
                                    "verified",
                                    "corroborated",
                                }
                            ),

                        "interaction_is_historical_fact":
                            False,

                        "interaction_is_simulation_opportunity":
                            True,
                    }
                )

        return {
            "schema":
                schema,

            "kind":
                "encounter-opportunities",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "fictional_entity":
                fictional_entity,

            "historical_entity":
                historical_entity,

            "radius_km":
                radius_km,

            "match_count":
                len(
                    matches
                ),

            "matches":
                sorted(
                    matches,
                    key=lambda item: (
                        item[
                            "earliest"
                        ],
                        item[
                            "distance_km"
                        ],
                    ),
                ),

            "interaction_claimed_as_fact":
                False,

            "source_state_mutated":
                False,
        }

    def coverage_gaps(
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
    ) -> dict[str, Any]:
        normalized = normalize_facts(
            document,
            facts,
        )

        used_locations = sorted(
            {
                str(
                    value.get(
                        "location_id"
                    )
                )
                for value
                in document.get(
                    "events",
                    [],
                )
                if (
                    isinstance(
                        value,
                        Mapping,
                    )
                    and value.get(
                        "location_id"
                    )
                )
            }
        )

        rows = []

        for location_id in used_locations:
            location_facts = [
                fact
                for fact
                in normalized
                if fact.location_id
                == location_id
            ]

            complete_coverage = [
                fact
                for fact
                in location_facts
                if fact.coverage.get(
                    "complete",
                    False,
                )
            ]

            rows.append(
                {
                    "location_id":
                        location_id,

                    "fact_count":
                        len(
                            location_facts
                        ),

                    "complete_coverage_count":
                        len(
                            complete_coverage
                        ),

                    "coverage_state":
                        (
                            "covered"
                            if complete_coverage
                            else (
                                "partial"
                                if location_facts
                                else "unresolved"
                            )
                        ),
                }
            )

        return {
            "schema":
                schema,

            "kind":
                "coverage-gaps",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "location_count":
                len(
                    rows
                ),

            "unresolved_location_count":
                sum(
                    1
                    for row
                    in rows
                    if row[
                        "coverage_state"
                    ]
                    == "unresolved"
                ),

            "partial_location_count":
                sum(
                    1
                    for row
                    in rows
                    if row[
                        "coverage_state"
                    ]
                    == "partial"
                ),

            "locations":
                rows,

            "absence_of_data_is_not_availability":
                True,
        }


engine = OrielRealityEngine()


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

            "projection":
                clone(
                    projection
                ),
        }

    return {
        "schema":
            (
                "savant.carbon.oriel-reality."
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
                "oriel_reality_binding",
                "historical-binding",
                (
                    "Bind sourced historical facts "
                    "into Carbon simulation without "
                    "admitting or promoting them."
                ),
                [
                    "bind",
                    "validate",
                ],
            ),

            capability(
                "oriel_availability_evidence",
                "historical-query",
                (
                    "Distinguish verified conflict, "
                    "verified availability, no "
                    "conflict found and unresolved."
                ),
                [
                    "availability",
                ],
            ),

            capability(
                "oriel_historical_snapshot",
                "historical-query",
                (
                    "Project sourced real-world state "
                    "at a requested timestamp."
                ),
                [
                    "snapshot",
                ],
            ),

            capability(
                "oriel_encounter_opportunity",
                "historical-query",
                (
                    "Find spacetime windows in which "
                    "fictional and historically sourced "
                    "entities could plausibly intersect."
                ),
                [
                    "encounters",
                ],
            ),

            capability(
                "oriel_reality_coverage",
                "epistemic",
                (
                    "Expose historical research gaps "
                    "without converting missing data "
                    "into false availability."
                ),
                [
                    "gaps",
                ],
            ),
        ],

        "invariants": {
            "absence_of_evidence_is_not_availability":
                True,

            "verified_facts_remain_immutable":
                True,

            "no_automatic_evidence_admission":
                True,

            "no_automatic_canon_promotion":
                True,

            "source_references_preserved":
                True,

            "carbon_owns_simulation":
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

        "effects":
            sorted(
                effects
            ),

        "source_classes":
            sorted(
                source_classes
            ),

        "verification_states":
            sorted(
                verification_states
            ),

        "availability_states":
            sorted(
                availability_states
            ),

        "absence_of_evidence_is_availability":
            False,

        "evidence_admission":
            False,

        "canon_effect":
            "none",

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

        "events": [
            {
                "id":
                    "fictional-show",

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
        ],
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

    validation = engine.validate(
        document,
        facts,
    )

    if (
        validation[
            "validation"
        ][
            "failure_count"
        ]
        < 1
    ):
        raise oriel_reality_error(
            (
                "reality selftest failed to "
                "reject occupied venue"
            )
        )

    conflict = engine.availability(
        document,
        facts,
        location_id=
            "venue-a",
        start=(
            "2017-07-07"
            "T19:00:00-04:00"
        ),
        end=(
            "2017-07-07"
            "T22:00:00-04:00"
        ),
    )

    if (
        conflict[
            "state"
        ]
        != "verified_conflict"
    ):
        raise oriel_reality_error(
            (
                "reality selftest failed "
                "verified conflict"
            )
        )

    available = engine.availability(
        document,
        facts,
        location_id=
            "venue-b",
        start=(
            "2017-07-07"
            "T19:00:00-04:00"
        ),
        end=(
            "2017-07-07"
            "T22:00:00-04:00"
        ),
    )

    if (
        available[
            "state"
        ]
        != "verified_available"
    ):
        raise oriel_reality_error(
            (
                "reality selftest failed "
                "verified availability"
            )
        )

    unresolved = engine.availability(
        document,
        [],
        location_id=
            "venue-b",
        start=(
            "2017-07-07"
            "T19:00:00-04:00"
        ),
        end=(
            "2017-07-07"
            "T22:00:00-04:00"
        ),
    )

    if (
        unresolved[
            "state"
        ]
        != "unresolved"
    ):
        raise oriel_reality_error(
            (
                "missing evidence was incorrectly "
                "treated as availability"
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

        "occupied_venue_rejected":
            True,

        "verified_conflict":
            True,

        "verified_availability":
            True,

        "missing_evidence_remains_unresolved":
            True,

        "source_state_mutated":
            False,

        "evidence_admission":
            False,

        "canon_effect":
            "none",
    }


__all__ = [
    "OrielRealityEngine",
    "RealityFact",
    "capability_manifest",
    "engine",
    "normalize_facts",
    "selftest",
    "status",
]

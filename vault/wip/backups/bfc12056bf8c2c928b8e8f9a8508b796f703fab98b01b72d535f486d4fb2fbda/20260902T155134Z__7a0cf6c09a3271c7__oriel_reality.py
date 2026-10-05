#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import json

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Sequence


from oriel import (
    forced_overlap,
    haversine_km,
    oriel_engine,
    oriel_error,
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
    document: Mapping[str, Any],
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
    coverage: Mapping[str, Any] = field(
        default_factory=dict
    )
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
        *,
        document: Mapping[str, Any],
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
                    "unsupported reality "
                    "source class: "
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
                    "verified reality fact "
                    "requires source_refs: "
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
            {}
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
            {}
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
    document: Mapping[str, Any],
    values: Sequence[
        Mapping[str, Any]
    ],
) -> list[RealityFact]:
    output:

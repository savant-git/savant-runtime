#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import (
    datetime,
    timezone,
)
from typing import (
    Any,
    Iterable,
)

from runtime.constitution import (
    ConstitutionalEvent,
    ConstitutionalRegistry,
)
from runtime.memory import (
    CANONICAL_MEMORY_TYPES,
    MemoryEngine,
)

from .instance import (
    ScrybeInstance,
    load_instance,
)


try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None


SCRYBE_PIPELINE = (
    "admission",
    "identity_resolution",
    "authority_resolution",

    "policy_resolution",
    "schema_validation",
    "provenance_resolution",

    "dependency_resolution",
    "temporal_resolution",
    "evidence_resolution",

    "conflict_analysis",
    "supersession_analysis",
    "recall_planning",

    "memory_resolution",
    "context_derivation",
    "relevance_ranking",

    "projection",
    "observability",
    "attestation",
)


SCRYBE_ABILITIES = (
    "episodic_recall",
    "semantic_recall",
    "procedural_recall",

    "reference_recall",
    "conversation_recall",
    "working_context",

    "temporal_recall",
    "validity_resolution",
    "memory_replay",

    "semantic_retrieval",
    "relevance_ranking",
    "context_hydration",

    "relationship_traversal",
    "dependency_traversal",
    "supersession_traversal",

    "memory_feed",
    "explanatory_projection",
    "context_projection",
)


SCRYBE_HEALTH_DIMENSIONS = (
    "canon_binding",
    "authority_integrity",
    "lineage_integrity",

    "provenance_integrity",
    "temporal_integrity",
    "confidence_integrity",

    "reference_integrity",
    "projection_freshness",
    "service_integration",
)


SCRYBE_VALIDATION_DIMENSIONS = (
    "identity",
    "authority",
    "lineage",

    "provenance",
    "validity",
    "confidence",

    "references",
    "supersession",
    "integration",
)


SCRYBE_PROJECTIONS = (
    "memory_record",
    "memory_feed",
    "memory_context",

    "memory_timeline",
    "memory_relationships",
    "memory_dependencies",

    "memory_supersession",
    "memory_explanation",
    "memory_health",
)


class ScrybeError(
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


def normalize_text(
    value: Any,
) -> str:
    text = (
        canonical_json(
            value
        )
        if not isinstance(
            value,
            str,
        )
        else value
    )

    return " ".join(
        re.findall(
            r"[\w]+",
            text.casefold(),
        )
    )


def clamp(
    value: float,
) -> float:
    return max(
        0.0,
        min(
            1.0,
            float(value),
        ),
    )


def parse_time(
    value: Any,
) -> datetime | None:
    if not value:
        return None

    text = str(
        value
    ).strip()

    try:
        if text.endswith(
            "Z"
        ):
            text = (
                text[:-1]
                + "+00:00"
            )

        parsed = (
            datetime
            .fromisoformat(
                text
            )
        )

        if (
            parsed.tzinfo
            is None
        ):
            parsed = (
                parsed.replace(
                    tzinfo=timezone.utc
                )
            )

        return parsed

    except ValueError:
        return None


def lexical_similarity(
    query: Any,
    candidate: Any,
) -> float:
    left = normalize_text(
        query
    )

    right = normalize_text(
        candidate
    )

    if (
        not left
        or not right
    ):
        return 0.0

    if fuzz is not None:
        return clamp(
            fuzz.WRatio(
                left,
                right,
            )
            / 100.0
        )

    left_tokens = set(
        left.split()
    )

    right_tokens = set(
        right.split()
    )

    union = (
        left_tokens
        | right_tokens
    )

    if not union:
        return 0.0

    return clamp(
        len(
            left_tokens
            & right_tokens
        )
        / len(union)
    )


def confidence_score(
    projection:
        dict[str, Any],
) -> float:
    value = projection.get(
        "confidence"
    )

    if value is None:
        return 0.5

    try:
        return clamp(
            float(value)
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0.5


def authority_score(
    projection:
        dict[str, Any],
) -> float:
    authority = (
        projection.get(
            "authority"
        )
    )

    if not isinstance(
        authority,
        dict,
    ):
        return 0.5

    numeric = (
        authority.get(
            "confidence"
        )
        or authority.get(
            "weight"
        )
        or authority.get(
            "score"
        )
    )

    if numeric is not None:
        try:
            return clamp(
                float(numeric)
            )
        except (
            TypeError,
            ValueError,
        ):
            pass

    state = str(
        authority.get(
            "state",
            "",
        )
    ).casefold()

    return {
        "accepted": 1.0,
        "provisional": 0.75,
        "observed": 0.6,
        "proposed": 0.5,
        "superseded": 0.25,
        "rejected": 0.0,
    }.get(
        state,
        0.5,
    )


def recency_score(
    projection:
        dict[str, Any],
) -> float:
    candidates = (
        projection.get(
            "occurred_at"
        ),
        projection.get(
            "updated_at"
        ),
        projection.get(
            "created_at"
        ),
        (
            projection
            .get(
                "validity",
                {},
            )
            .get(
                "from"
            )
            if isinstance(
                projection.get(
                    "validity"
                ),
                dict,
            )
            else None
        ),
    )

    timestamp = next(
        (
            parsed
            for parsed in (
                parse_time(
                    value
                )
                for value
                in candidates
            )
            if parsed
            is not None
        ),
        None,
    )

    if timestamp is None:
        return 0.5

    age_days = max(
        0.0,
        (
            datetime.now(
                timezone.utc
            )
            - timestamp
        ).total_seconds()
        / 86400.0,
    )

    return clamp(
        math.exp(
            -age_days
            / 365.0
        )
    )


class Scrybe:
    schema = (
        "savant://runtime/"
        "scrybe/1.1.0"
    )

    substrate_id = (
        "living:scrybe"
    )

    def __init__(
        self,
        memory:
            MemoryEngine,
        instance:
            ScrybeInstance,
    ) -> None:
        self.memory = memory
        self.registry = (
            memory.registry
        )
        self.instance = (
            instance
        )

    @classmethod
    def install(
        cls,
        registry:
            ConstitutionalRegistry,
        *,
        instance:
            str = "lore",
    ) -> "Scrybe":
        return cls(
            MemoryEngine.install(
                registry
            ),
            load_instance(
                instance
            ),
        )

    @property
    def abilities(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return (
            SCRYBE_ABILITIES
        )

    @property
    def pipeline(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return (
            SCRYBE_PIPELINE
        )

    def memories(
        self,
        memory_type:
            str | None = None,
        *,
        at:
            str | None = None,
        current:
            bool = False,
    ):
        return (
            self.memory
            .memories(
                memory_type,
                at=at,
                current=current,
            )
        )

    def _candidate_projection(
        self,
        value: Any,
    ) -> dict[str, Any]:
        if isinstance(
            value,
            dict,
        ):
            identity = (
                value.get(
                    "identity"
                )
                or value.get(
                    "id"
                )
            )

            if (
                identity
                and identity
                in self.registry.ids
            ):
                try:
                    return dict(
                        self.memory
                        .project(
                            str(
                                identity
                            )
                        )
                    )
                except (
                    KeyError,
                    ValueError,
                ):
                    pass

            return dict(
                value
            )

        identity = getattr(
            value,
            "id",
            None,
        )

        if identity:
            return dict(
                self.memory
                .project(
                    str(identity)
                )
            )

        return {
            "content":
                value
        }

    def _hybrid_score(
        self,
        query: Any,
        projection:
            dict[str, Any],
        semantic_rank:
            int,
        candidate_count:
            int,
    ) -> dict[str, float]:
        config = (
            self.instance
            .retrieval
        )

        if candidate_count <= 1:
            semantic = 1.0
        else:
            semantic = clamp(
                1.0
                - (
                    semantic_rank
                    / candidate_count
                )
            )

        lexical = (
            lexical_similarity(
                query,
                projection,
            )
        )

        confidence = (
            confidence_score(
                projection
            )
        )

        authority = (
            authority_score(
                projection
            )
        )

        recency = (
            recency_score(
                projection
            )
        )

        final = (
            semantic
            * float(
                config[
                    "semantic_weight"
                ]
            )
            + lexical
            * float(
                config[
                    "lexical_weight"
                ]
            )
            + confidence
            * float(
                config[
                    "confidence_weight"
                ]
            )
            + authority
            * float(
                config[
                    "authority_weight"
                ]
            )
            + recency
            * float(
                config[
                    "recency_weight"
                ]
            )
        )

        return {
            "semantic":
                round(
                    semantic,
                    8,
                ),
            "lexical":
                round(
                    lexical,
                    8,
                ),
            "confidence":
                round(
                    confidence,
                    8,
                ),
            "authority":
                round(
                    authority,
                    8,
                ),
            "recency":
                round(
                    recency,
                    8,
                ),
            "final":
                round(
                    clamp(
                        final
                    ),
                    8,
                ),
        }

    def recall(
        self,
        query: Any,
        *,
        limit: int = 9,
        memory_type:
            str | None = None,
        at:
            str | None = None,
    ) -> tuple[
        dict[str, Any],
        ...,
    ]:
        if limit < 0:
            raise ScrybeError(
                "limit must be "
                "non-negative"
            )

        if (
            memory_type
            is not None
            and memory_type
            not in
            CANONICAL_MEMORY_TYPES
        ):
            raise ScrybeError(
                "unknown canonical "
                "memory type: "
                + memory_type
            )

        if limit == 0:
            return ()

        multiplier = int(
            self.instance
            .retrieval[
                "candidate_multiplier"
            ]
        )

        candidate_limit = max(
            limit,
            limit
            * multiplier,
        )

        raw = (
            self.memory
            .retrieve_semantic(
                query,
                limit=(
                    candidate_limit
                ),
                memory_type=(
                    memory_type
                ),
                at=at,
            )
        )

        candidates = [
            self
            ._candidate_projection(
                item
            )
            for item in raw
        ]

        scored: list[
            dict[str, Any]
        ] = []

        seen: set[
            str
        ] = set()

        for index, projection in (
            enumerate(
                candidates
            )
        ):
            identity = str(
                projection.get(
                    "identity",
                    digest(
                        projection
                    ),
                )
            )

            if (
                self.instance
                .retrieval[
                    "deduplicate"
                ]
                and identity
                in seen
            ):
                continue

            seen.add(
                identity
            )

            scores = (
                self._hybrid_score(
                    query,
                    projection,
                    index,
                    max(
                        1,
                        len(
                            candidates
                        ),
                    ),
                )
            )

            if (
                scores["final"]
                < float(
                    self.instance
                    .retrieval[
                        "minimum_score"
                    ]
                )
            ):
                continue

            scored.append(
                {
                    "memory":
                        projection,
                    "score":
                        scores[
                            "final"
                        ],
                    "score_components":
                        scores,
                    "source_rank":
                        index + 1,
                    "instance_id":
                        self.instance
                        .instance_id,
                    "authoritative":
                        False,
                }
            )

        scored.sort(
            key=lambda item: (
                -float(
                    item[
                        "score"
                    ]
                ),
                str(
                    item[
                        "memory"
                    ].get(
                        "identity",
                        "",
                    )
                ),
            )
        )

        result: list[
            dict[str, Any]
        ] = []

        for rank, item in (
            enumerate(
                scored[:limit],
                start=1,
            )
        ):
            value = dict(
                item
            )

            value[
                "rank"
            ] = rank

            value[
                "scrybe_digest"
            ] = digest(
                value
            )

            result.append(
                value
            )

        return tuple(
            result
        )

    def hydrate(
        self,
        query: Any,
        *,
        limit:
            int | None = None,
        at:
            str | None = None,
    ) -> dict[str, Any]:
        effective_limit = (
            int(
                self.instance
                .retrieval[
                    "context_budget"
                ]
            )
            if limit is None
            else limit
        )

        recalled = self.recall(
            query,
            limit=effective_limit,
            at=at,
        )

        type_counts = {
            memory_type: 0
            for memory_type
            in CANONICAL_MEMORY_TYPES
        }

        for item in recalled:
            memory_type = (
                item
                .get(
                    "memory",
                    {},
                )
                .get(
                    "memory_type"
                )
            )

            if (
                memory_type
                in type_counts
            ):
                type_counts[
                    memory_type
                ] += 1

        payload = {
            "schema": (
                "savant://runtime/"
                "scrybe/context/1.1.0"
            ),
            "instance_id": (
                self.instance
                .instance_id
            ),
            "query": query,
            "at": at,
            "limit":
                effective_limit,
            "memory_count":
                len(recalled),
            "memory_types":
                type_counts,
            "memories":
                recalled,
            "authoritative":
                False,
            "rebuildable":
                True,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def remember(
        self,
        identity: str,
    ) -> dict[str, Any]:
        projection = dict(
            self.memory
            .project(
                identity
            )
        )

        result = {
            "schema": (
                "savant://runtime/"
                "scrybe/memory/1.1.0"
            ),
            "instance_id":
                self.instance
                .instance_id,
            "memory":
                projection,
            "authoritative":
                False,
            "rebuildable":
                True,
        }

        result[
            "digest"
        ] = digest(
            result
        )

        return result

    def relationships(
        self,
        identity: str,
        *,
        relationship_type:
            str | None = None,
    ) -> tuple[
        dict[str, Any],
        ...,
    ]:
        objects = (
            self.memory
            .retrieve_relationships(
                identity,
                relationship_type,
            )
        )

        return tuple(
            dict(
                self.memory
                .project(
                    obj.id
                )
            )
            for obj
            in objects
        )

    def authority_recall(
        self,
        authority: Any,
    ) -> tuple[
        dict[str, Any],
        ...,
    ]:
        objects = (
            self.memory
            .retrieve_authority(
                authority
            )
        )

        return tuple(
            dict(
                self.memory
                .project(
                    obj.id
                )
            )
            for obj
            in objects
        )

    def working(
        self,
        *,
        identities:
            Iterable[str] = (),
        events:
            Iterable[
                ConstitutionalEvent
            ] = (),
    ) -> dict[str, Any]:
        projected = dict(
            self.memory
            .working_memory(
                identities=(
                    identities
                ),
                events=events,
            )
        )

        return {
            "schema": (
                "savant://runtime/"
                "scrybe/working/1.1.0"
            ),
            "instance_id":
                self.instance
                .instance_id,
            **projected,
            "authoritative":
                False,
            "persistent":
                False,
        }

    def feed(
        self,
        *,
        memory_type:
            str | None = None,
        at:
            str | None = None,
        limit: int = 18,
    ) -> tuple[
        dict[str, Any],
        ...,
    ]:
        if limit < 0:
            raise ScrybeError(
                "limit must be "
                "non-negative"
            )

        values = list(
            self.memory
            .memories(
                memory_type,
                at=at,
                current=True,
            )
        )

        values.sort(
            key=lambda obj: (
                str(
                    obj.updated_at
                ),
                obj.id,
            ),
            reverse=True,
        )

        return tuple(
            dict(
                self.memory
                .project(
                    obj.id
                )
            )
            for obj
            in values[:limit]
        )

    def explain(
        self,
        query: Any,
        *,
        limit: int = 9,
        at:
            str | None = None,
    ) -> dict[str, Any]:
        results = self.recall(
            query,
            limit=limit,
            at=at,
        )

        payload = {
            "schema": (
                "savant://runtime/"
                "scrybe/explanation/1.1.0"
            ),
            "instance_id":
                self.instance
                .instance_id,
            "query": query,
            "result_count":
                len(results),
            "ranking_policy":
                dict(
                    self.instance
                    .retrieval
                ),
            "rapidfuzz_active":
                fuzz
                is not None,
            "results":
                results,
            "authoritative":
                False,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def health(
        self,
    ) -> dict[str, Any]:
        validation = (
            self.memory
            .validate()
        )

        checks = (
            validation.get(
                "checks",
                {},
            )
        )

        mapping = {
            "canon_binding": (
                "service:fluid-canon"
                in self.registry.ids
            ),
            "authority_integrity": (
                not checks.get(
                    "authority",
                    [],
                )
            ),
            "lineage_integrity": (
                not checks.get(
                    "lineage",
                    [],
                )
            ),
            "provenance_integrity": (
                not checks.get(
                    "provenance",
                    [],
                )
            ),
            "temporal_integrity": (
                not checks.get(
                    "validity",
                    [],
                )
            ),
            "confidence_integrity": (
                not checks.get(
                    "confidence",
                    [],
                )
            ),
            "reference_integrity": (
                not checks.get(
                    "references",
                    [],
                )
            ),
            "projection_freshness":
                True,
            "service_integration": (
                "service:memory"
                in self.registry.ids
            ),
        }

        result = {
            "schema": (
                "savant://runtime/"
                "scrybe/health/1.1.0"
            ),
            "instance_id":
                self.instance
                .instance_id,
            "dimensions": {
                name: {
                    "healthy":
                        bool(
                            mapping[
                                name
                            ]
                        )
                }
                for name
                in (
                    SCRYBE_HEALTH_DIMENSIONS
                )
            },
        }

        result[
            "healthy"
        ] = all(
            value[
                "healthy"
            ]
            for value
            in result[
                "dimensions"
            ].values()
        )

        result[
            "digest"
        ] = digest(
            result
        )

        return result

    def validate(
        self,
    ) -> dict[str, Any]:
        memory_report = (
            self.memory
            .validate()
        )

        positive = {
            "abilities": (
                len(
                    SCRYBE_ABILITIES
                )
                == 18
            ),
            "pipeline": (
                len(
                    SCRYBE_PIPELINE
                )
                == 18
            ),
            "health_dimensions": (
                len(
                    SCRYBE_HEALTH_DIMENSIONS
                )
                == 9
            ),
            "validation_dimensions": (
                len(
                    SCRYBE_VALIDATION_DIMENSIONS
                )
                == 9
            ),
            "projections": (
                len(
                    SCRYBE_PROJECTIONS
                )
                == 9
            ),
            "enhancements": (
                self.instance
                .enhancement_count
                == 27
            ),
            "fluid_canon_bound": (
                "service:fluid-canon"
                in self.registry.ids
            ),
            "memory_service_bound": (
                "service:memory"
                in self.registry.ids
            ),
            "instance_overlay": (
                self.instance
                .instance_id
                .startswith(
                    "scrybe:"
                )
            ),
        }

        invariants = {
            "projection_authoritative":
                False,
            "memory_store_duplicated":
                False,
            "independent_memory_store":
                False,
            "canonical_memory_store":
                "fluid-canon",
        }

        valid = (
            all(
                positive.values()
            )
            and bool(
                memory_report.get(
                    "valid"
                )
            )
            and (
                self.instance
                .projection_authoritative
                is False
            )
            and (
                self.instance
                .independent_memory_store
                is False
            )
        )

        result = {
            "schema": (
                "savant://assurance/"
                "scrybe/1.1.0"
            ),
            "valid": valid,
            "structure":
                positive,
            "invariants":
                invariants,
            "memory":
                memory_report,
            "instance":
                self.instance
                .to_dict(),
            "ability_count": 18,
            "pipeline_stage_count": 18,
            "health_dimension_count": 9,
            "validation_dimension_count": 9,
            "projection_count": 9,
            "enhancement_count": 27,
            "rapidfuzz_active": (
                fuzz
                is not None
            ),
        }

        result[
            "digest"
        ] = digest(
            result
        )

        return result

    def profile(
        self,
    ) -> dict[str, Any]:
        result = {
            "schema":
                self.schema,
            "substrate_id":
                self.substrate_id,
            "name":
                "Scrybe",
            "role":
                "living memory substrate",
            "instance":
                self.instance
                .to_dict(),
            "canonical_memory_store":
                "fluid-canon",
            "independent_memory_store":
                False,
            "abilities":
                list(
                    SCRYBE_ABILITIES
                ),
            "pipeline":
                list(
                    SCRYBE_PIPELINE
                ),
            "health_dimensions":
                list(
                    SCRYBE_HEALTH_DIMENSIONS
                ),
            "validation_dimensions":
                list(
                    SCRYBE_VALIDATION_DIMENSIONS
                ),
            "projections":
                list(
                    SCRYBE_PROJECTIONS
                ),
            "memory_types":
                list(
                    CANONICAL_MEMORY_TYPES
                ),
            "enhancement_count":
                self.instance
                .enhancement_count,
            "rapidfuzz_active":
                fuzz
                is not None,
        }

        result[
            "digest"
        ] = digest(
            result
        )

        return result

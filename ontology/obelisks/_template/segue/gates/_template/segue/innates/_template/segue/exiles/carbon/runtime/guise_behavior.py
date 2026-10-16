#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping, Sequence

from guise import (
    OWNER,
    SCHEMA,
    SPECIALIZATION,
    CharacterGraph,
    digest,
)


CLASSIFICATIONS = {
    "highly_supported",
    "plausible",
    "productive_contradiction",
    "requires_substantiation",
    "continuity_conflict",
}


class CharacterBehaviorEngine:
    def evaluate(
        self,
        graph: CharacterGraph,
        *,
        situation: Mapping[str, Any],
        candidates: Sequence[
            Mapping[str, Any]
        ],
    ) -> dict[str, Any]:
        evaluated = []

        for index, candidate in enumerate(
            candidates
        ):
            item = dict(candidate)

            classification = str(
                item.get(
                    "classification",
                    "requires_substantiation",
                )
            ).strip()

            if classification not in (
                CLASSIFICATIONS
            ):
                classification = (
                    "requires_substantiation"
                )

            evaluated.append(
                {
                    "id": item.get(
                        "id",
                        f"behavior-candidate:{index}",
                    ),
                    "behavior": item.get(
                        "behavior"
                    ),
                    "classification": (
                        classification
                    ),
                    "supporting_refs": list(
                        item.get(
                            "supporting_refs",
                            [],
                        )
                    ),
                    "counter_refs": list(
                        item.get(
                            "counter_refs",
                            [],
                        )
                    ),
                    "state_refs": list(
                        item.get(
                            "state_refs",
                            [],
                        )
                    ),
                    "relationship_refs": list(
                        item.get(
                            "relationship_refs",
                            [],
                        )
                    ),
                    "knowledge_refs": list(
                        item.get(
                            "knowledge_refs",
                            [],
                        )
                    ),
                    "pressure_refs": list(
                        item.get(
                            "pressure_refs",
                            [],
                        )
                    ),
                    "required_conditions": list(
                        item.get(
                            "required_conditions",
                            [],
                        )
                    ),
                    "alternative_explanations": list(
                        item.get(
                            "alternative_explanations",
                            [],
                        )
                    ),
                    "confidence": item.get(
                        "confidence",
                        "unknown",
                    ),
                    "authoritative": False,
                }
            )

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": "behavior_evaluation",
            "character_id": graph.character_id,
            "situation": dict(situation),
            "candidates": evaluated,
            "candidate_count": len(
                evaluated
            ),
            "single_behavior_required": False,
            "behavior_is_deterministic": False,
            "prediction_creates_authority": False,
            "character_mutated": False,
            "authority_effect": "none",
        }

        result["projection_digest"] = digest(
            result
        )

        return result

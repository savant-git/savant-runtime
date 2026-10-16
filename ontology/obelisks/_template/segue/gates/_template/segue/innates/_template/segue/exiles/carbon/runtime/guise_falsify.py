#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping, Sequence

from guise import (
    OWNER,
    SCHEMA,
    SPECIALIZATION,
    CharacterGraph,
    GuiseError,
    digest,
)


class GuiseFalsificationError(
    GuiseError
):
    pass


class CharacterFalsifier:
    def test_category(
        self,
        graph: CharacterGraph,
        *,
        category_id: str,
        challenges: Sequence[
            Mapping[str, Any]
        ] = (),
    ) -> dict[str, Any]:
        category = graph.categories.get(
            category_id
        )

        if category is None:
            raise GuiseFalsificationError(
                f"unknown category: {category_id}"
            )

        evidence = graph.evidence_for(
            category
        )

        normalized_challenges = []

        for challenge in challenges:
            item = dict(challenge)

            item.setdefault(
                "kind",
                "alternative_explanation",
            )
            item.setdefault(
                "supporting_refs",
                [],
            )
            item.setdefault(
                "status",
                "unresolved",
            )

            normalized_challenges.append(
                item
            )

        supporting = evidence.get(
            "supporting",
            [],
        )

        counter = evidence.get(
            "counter",
            [],
        )

        if not supporting:
            status = (
                "insufficient_support"
            )
        elif counter:
            status = (
                "survives_with_counterevidence"
            )
        elif normalized_challenges:
            status = (
                "survives_with_unresolved_challenges"
            )
        else:
            status = (
                "supported_not_proven"
            )

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": (
                "character_falsification"
            ),
            "character_id": (
                graph.character_id
            ),
            "category": (
                category.projection()
            ),
            "supporting_evidence": (
                supporting
            ),
            "counterevidence": counter,
            "challenges": (
                normalized_challenges
            ),
            "status": status,
            "proven": False,
            "automatic_rejection": False,
            "automatic_acceptance": False,
            "character_mutated": False,
            "authority_effect": "none",
        }

        result["projection_digest"] = (
            digest(result)
        )

        return result

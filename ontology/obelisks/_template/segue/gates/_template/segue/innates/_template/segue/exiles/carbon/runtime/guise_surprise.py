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


class SurpriseWithoutBetrayalEngine:
    def evaluate(
        self,
        graph: CharacterGraph,
        *,
        behavior: Mapping[str, Any],
        supporting_refs: Sequence[str] = (),
        contradiction_refs: Sequence[str] = (),
        enabling_conditions: Sequence[str] = (),
        precedent_refs: Sequence[str] = (),
        required_new_facts: Sequence[str] = (),
    ) -> dict[str, Any]:
        support = sorted(
            set(supporting_refs)
        )
        contradictions = sorted(
            set(contradiction_refs)
        )
        conditions = sorted(
            set(enabling_conditions)
        )
        precedents = sorted(
            set(precedent_refs)
        )
        new_facts = sorted(
            set(required_new_facts)
        )

        if new_facts:
            classification = (
                "requires_substantiation"
            )
        elif contradictions and not (
            conditions
            or precedents
            or support
        ):
            classification = (
                "continuity_conflict"
            )
        elif contradictions:
            classification = (
                "productive_contradiction"
            )
        elif support or precedents:
            classification = "plausible"
        else:
            classification = (
                "requires_substantiation"
            )

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": (
                "surprise_without_betrayal"
            ),
            "character_id": (
                graph.character_id
            ),
            "behavior": dict(behavior),
            "supporting_refs": support,
            "contradiction_refs": (
                contradictions
            ),
            "enabling_conditions": (
                conditions
            ),
            "precedent_refs": precedents,
            "required_new_facts": (
                new_facts
            ),
            "classification": (
                classification
            ),
            "surprise_required": False,
            "novelty_creates_authority": False,
            "character_mutated": False,
            "authority_effect": "none",
        }

        result["projection_digest"] = (
            digest(result)
        )
        return result

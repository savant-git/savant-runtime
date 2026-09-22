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


class CharacterBlindSpotEngine:
    def project(
        self,
        graph: CharacterGraph,
        *,
        candidates: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        projected = []

        for index, raw in enumerate(candidates):
            item = dict(raw)

            projected.append(
                {
                    "id": item.get(
                        "id",
                        f"blindspot:{index}",
                    ),
                    "description": item.get("description"),
                    "character_belief_refs": list(
                        item.get("character_belief_refs", [])
                    ),
                    "contradicting_evidence_refs": list(
                        item.get("contradicting_evidence_refs", [])
                    ),
                    "behavior_refs": list(
                        item.get("behavior_refs", [])
                    ),
                    "relationship_refs": list(
                        item.get("relationship_refs", [])
                    ),
                    "alternative_explanations": list(
                        item.get("alternative_explanations", [])
                    ),
                    "classification": item.get(
                        "classification",
                        "requires_substantiation",
                    ),
                    "epistemic_class": item.get(
                        "epistemic_class",
                        "hypothesis",
                    ),
                    "authoritative": False,
                }
            )

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": "blind_spot_projection",
            "character_id": graph.character_id,
            "candidates": projected,
            "candidate_count": len(projected),
            "blind_spot_is_diagnosis": False,
            "automatic_acceptance": False,
            "character_mutated": False,
            "authority_effect": "none",
        }

        result["projection_digest"] = digest(result)
        return result

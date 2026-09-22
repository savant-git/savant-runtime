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


class PredictiveRestraintEngine:
    def evaluate(
        self,
        graph: CharacterGraph,
        *,
        situation: Mapping[str, Any],
        available_evidence_refs: Sequence[str] = (),
        contradiction_refs: Sequence[str] = (),
        unknowns: Sequence[str] = (),
        candidate_behaviors: Sequence[
            Mapping[str, Any]
        ] = (),
    ) -> dict[str, Any]:
        evidence_count = len(
            set(available_evidence_refs)
        )
        contradiction_count = len(
            set(contradiction_refs)
        )
        unknown_count = len(
            set(unknowns)
        )

        if evidence_count == 0:
            recommendation = "abstain"
        elif (
            contradiction_count > 0
            or unknown_count > evidence_count
        ):
            recommendation = "withhold_single_prediction"
        elif len(candidate_behaviors) > 1:
            recommendation = "preserve_alternatives"
        else:
            recommendation = "bounded_projection"

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": "predictive_restraint",
            "character_id": graph.character_id,
            "situation": dict(situation),
            "available_evidence_refs": sorted(
                set(available_evidence_refs)
            ),
            "contradiction_refs": sorted(
                set(contradiction_refs)
            ),
            "unknowns": list(unknowns),
            "candidate_behaviors": [
                dict(candidate)
                for candidate in candidate_behaviors
            ],
            "recommendation": recommendation,
            "prediction_required": False,
            "silence_supported": True,
            "uncertainty_preserved": True,
            "character_mutated": False,
            "authority_effect": "none",
        }

        result["projection_digest"] = digest(result)
        return result

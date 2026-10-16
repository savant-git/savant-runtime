#!/usr/bin/env python3
"""Connect hypothetical character scenarios to existing guise behavior."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from guise import CharacterGraph, digest
from guise_behavior import CharacterBehaviorEngine
from guise_scenario import (
    GuiseScenarioError,
    evaluate,
    normalize_scenario,
)


class GuiseScenarioBehaviorError(ValueError):
    """Invalid scenario-to-behavior composition."""


class GuiseScenarioBehavior:
    """Compose scenario evidence with the existing behavior engine.

    Historical or hypothetical material remains non-authoritative.
    Behavior candidates are supplied explicitly, never invented.
    """

    def __init__(self) -> None:
        self.behavior = CharacterBehaviorEngine()

    def evaluate(
        self,
        graph: CharacterGraph,
        *,
        scenario: Mapping[str, Any],
        evidence_view: Mapping[str, Any],
        candidates: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        if not isinstance(graph, CharacterGraph):
            raise GuiseScenarioBehaviorError(
                "graph must be a character graph"
            )

        if not isinstance(candidates, (list, tuple)):
            raise GuiseScenarioBehaviorError(
                "candidates must be a sequence"
            )

        if any(
            not isinstance(candidate, Mapping)
            for candidate in candidates
        ):
            raise GuiseScenarioBehaviorError(
                "every candidate must be a mapping"
            )

        normalized = normalize_scenario(scenario)

        if normalized["character"] != graph.character_id:
            raise GuiseScenarioBehaviorError(
                "scenario and graph identify different characters"
            )

        if not isinstance(evidence_view, Mapping):
            raise GuiseScenarioBehaviorError(
                "evidence view must be a mapping"
            )

        if evidence_view.get("character") != graph.character_id:
            raise GuiseScenarioBehaviorError(
                "evidence and graph identify different characters"
            )

        if evidence_view.get("authoritative") is not False:
            raise GuiseScenarioBehaviorError(
                "evidence must be a non-authoritative projection"
            )

        try:
            assessment = evaluate(
                normalized,
                evidence_view,
            )
        except GuiseScenarioError as exc:
            raise GuiseScenarioBehaviorError(
                str(exc)
            ) from exc

        situation = {
            "identity": normalized["identity"],
            "description": normalized["situation"],
            "pressures": normalized["pressures"],
            "assessment_digest": assessment["digest"],
            "hypothetical": True,
        }

        behavior = self.behavior.evaluate(
            graph,
            situation=situation,
            candidates=candidates,
        )

        if behavior.get("character_mutated") is not False:
            raise GuiseScenarioBehaviorError(
                "behavior engine reported character mutation"
            )

        if behavior.get("prediction_creates_authority") is not False:
            raise GuiseScenarioBehaviorError(
                "behavior engine reported authority promotion"
            )

        result = {
            "operation": "scenario_behavior_composition",
            "character_id": graph.character_id,
            "scenario": normalized,
            "assessment": assessment,
            "behavior": behavior,
            "authoritative": False,
            "character_mutated": False,
            "authority_effect": "none",
        }

        result["projection_digest"] = digest(result)

        return result

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


class CharacterSceneProjector:
    def project(
        self,
        graph: CharacterGraph,
        *,
        scene: Mapping[str, Any],
        active_state_refs: Sequence[
            str
        ] = (),
        relationship_refs: Sequence[
            str
        ] = (),
        knowledge_refs: Sequence[
            str
        ] = (),
        pressure_refs: Sequence[
            str
        ] = (),
        arc_refs: Sequence[
            str
        ] = (),
        debt_refs: Sequence[
            str
        ] = (),
        behavior_candidates: Sequence[
            Mapping[str, Any]
        ] = (),
    ) -> dict[str, Any]:
        candidates = []

        for index, raw in enumerate(
            behavior_candidates
        ):
            item = dict(raw)

            item.setdefault(
                "id",
                f"scene-behavior:{index}",
            )
            item.setdefault(
                "classification",
                "requires_substantiation",
            )
            item.setdefault(
                "supporting_refs",
                [],
            )
            item.setdefault(
                "counter_refs",
                [],
            )
            item.setdefault(
                "continuity_conflicts",
                [],
            )
            item.setdefault(
                "required_conditions",
                [],
            )

            candidates.append(item)

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": (
                "character_scene_projection"
            ),
            "character_id": (
                graph.character_id
            ),
            "scene": dict(scene),
            "active_state_refs": list(
                active_state_refs
            ),
            "relationship_refs": list(
                relationship_refs
            ),
            "knowledge_refs": list(
                knowledge_refs
            ),
            "pressure_refs": list(
                pressure_refs
            ),
            "arc_refs": list(
                arc_refs
            ),
            "debt_refs": list(
                debt_refs
            ),
            "behavior_candidates": (
                candidates
            ),
            "single_behavior_required": False,
            "scene_prediction_is_fact": False,
            "author_decides": True,
            "character_mutated": False,
            "authority_effect": "none",
        }

        result["projection_digest"] = (
            digest(result)
        )

        return result

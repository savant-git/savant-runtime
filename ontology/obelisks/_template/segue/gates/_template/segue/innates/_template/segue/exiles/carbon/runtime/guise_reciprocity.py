#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from guise import (
    OWNER,
    SCHEMA,
    SPECIALIZATION,
    CharacterGraph,
    digest,
    stable_id,
)


@dataclass(frozen=True)
class ReciprocityLoop:
    character_id: str
    other_ref: str
    left_behavior_ref: str
    right_response_ref: str
    resulting_behavior_ref: str
    evidence_refs: tuple[str, ...] = ()
    temporal_refs: tuple[str, ...] = ()
    epistemic_class: str = "unknown"

    @property
    def id(self) -> str:
        return stable_id(
            "character-reciprocity-loop",
            {
                "character_id": self.character_id,
                "other_ref": self.other_ref,
                "left_behavior_ref": self.left_behavior_ref,
                "right_response_ref": self.right_response_ref,
                "resulting_behavior_ref": self.resulting_behavior_ref,
                "evidence_refs": list(self.evidence_refs),
                "temporal_refs": list(self.temporal_refs),
                "epistemic_class": self.epistemic_class,
            },
        )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": "character_reciprocity_loop",
            "character_id": self.character_id,
            "other_ref": self.other_ref,
            "left_behavior_ref": self.left_behavior_ref,
            "right_response_ref": self.right_response_ref,
            "resulting_behavior_ref": self.resulting_behavior_ref,
            "evidence_refs": list(self.evidence_refs),
            "temporal_refs": list(self.temporal_refs),
            "epistemic_class": self.epistemic_class,
            "authority_effect": "none",
        }


class ReciprocityEngine:
    def __init__(self) -> None:
        self._loops: dict[str, ReciprocityLoop] = {}

    def add(
        self,
        loop: ReciprocityLoop,
    ) -> ReciprocityLoop:
        self._loops[loop.id] = loop
        return loop

    def project(
        self,
        graph: CharacterGraph,
        *,
        other_ref: str | None = None,
    ) -> dict[str, Any]:
        loops = [
            loop
            for loop in self._loops.values()
            if loop.character_id == graph.character_id
            and (
                other_ref is None
                or loop.other_ref == other_ref
            )
        ]

        loops.sort(key=lambda item: item.id)

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": "reciprocity_projection",
            "character_id": graph.character_id,
            "other_ref": other_ref,
            "loops": [
                loop.projection()
                for loop in loops
            ],
            "loop_count": len(loops),
            "causal_determinism_asserted": False,
            "character_mutated": False,
            "authority_effect": "none",
        }

        result["projection_digest"] = digest(result)
        return result

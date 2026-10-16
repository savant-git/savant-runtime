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


class PressureEngine:
    def project(
        self,
        graph: CharacterGraph,
        *,
        pressures: Sequence[
            Mapping[str, Any]
        ],
        candidate_effects: Sequence[
            Mapping[str, Any]
        ],
    ) -> dict[str, Any]:
        normalized_pressures = [
            {
                "id": str(
                    item.get(
                        "id",
                        "",
                    )
                ).strip(),
                "kind": str(
                    item.get(
                        "kind",
                        "unspecified",
                    )
                ).strip(),
                "description": str(
                    item.get(
                        "description",
                        "",
                    )
                ).strip(),
                "source_refs": list(
                    item.get(
                        "source_refs",
                        [],
                    )
                ),
            }
            for item in pressures
        ]

        effects = []

        for effect in candidate_effects:
            item = dict(effect)

            item.setdefault(
                "classification",
                "requires_substantiation",
            )
            item.setdefault(
                "category_refs",
                [],
            )
            item.setdefault(
                "state_refs",
                [],
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
                "relationship_refs",
                [],
            )
            item.setdefault(
                "alternative_explanations",
                [],
            )

            effects.append(item)

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": "pressure_projection",
            "character_id": (
                graph.character_id
            ),
            "pressures": (
                normalized_pressures
            ),
            "candidate_effects": effects,
            "deterministic": False,
            "pressure_reveals_true_self": (
                False
            ),
            "character_mutated": False,
            "authority_effect": "none",
        }

        result["projection_digest"] = (
            digest(result)
        )

        return result

#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping

from guise import (
    OWNER,
    SCHEMA,
    SPECIALIZATION,
    CharacterGraph,
    Guise,
    digest,
)


class CharacterComparator:
    def __init__(
        self,
        guise: Guise,
    ) -> None:
        self.guise = guise

    def compare(
        self,
        left: CharacterGraph,
        right: CharacterGraph,
    ) -> dict[str, Any]:
        domains = sorted(
            self.guise.manifest[
                "domains"
            ]
        )

        comparisons = []

        for domain in domains:
            left_projection = (
                left.domain_projection(
                    domain,
                    self.guise.manifest,
                )
            )

            right_projection = (
                right.domain_projection(
                    domain,
                    self.guise.manifest,
                )
            )

            comparisons.append(
                {
                    "domain": domain,
                    "left": left_projection,
                    "right": right_projection,
                }
            )

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": (
                "character_comparison"
            ),
            "left_character_id": (
                left.character_id
            ),
            "right_character_id": (
                right.character_id
            ),
            "domains": comparisons,
            "numeric_vector_required": False,
            "ranking_required": False,
            "comparison_creates_authority": (
                False
            ),
            "authority_effect": "none",
        }

        result["projection_digest"] = (
            digest(result)
        )

        return result

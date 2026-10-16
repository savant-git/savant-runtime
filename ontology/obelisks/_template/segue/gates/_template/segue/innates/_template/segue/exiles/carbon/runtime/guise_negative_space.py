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


class NegativeSpaceEngine:
    def project(
        self,
        graph: CharacterGraph,
        *,
        expected_refs: Sequence[str] = (),
        observed_refs: Sequence[str] = (),
        absence_candidates: Sequence[
            Mapping[str, Any]
        ] = (),
    ) -> dict[str, Any]:
        expected = set(expected_refs)
        observed = set(observed_refs)

        unobserved = sorted(
            expected - observed
        )

        candidates = []

        for index, candidate in enumerate(
            absence_candidates
        ):
            item = dict(candidate)

            item.setdefault(
                "id",
                f"negative-space:{index}",
            )
            item.setdefault(
                "classification",
                "unknown",
            )
            item.setdefault(
                "evidence_refs",
                [],
            )
            item.setdefault(
                "alternative_explanations",
                [],
            )
            item.setdefault(
                "intentional_absence",
                None,
            )

            candidates.append(item)

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": (
                "negative_space_projection"
            ),
            "character_id": (
                graph.character_id
            ),
            "expected_refs": sorted(
                expected
            ),
            "observed_refs": sorted(
                observed
            ),
            "not_observed_refs": unobserved,
            "absence_candidates": candidates,
            "absence_is_evidence": False,
            "observed_absence_requires_evidence": (
                True
            ),
            "automatic_interpretation": False,
            "authority_effect": "none",
        }

        result["projection_digest"] = (
            digest(result)
        )
        return result

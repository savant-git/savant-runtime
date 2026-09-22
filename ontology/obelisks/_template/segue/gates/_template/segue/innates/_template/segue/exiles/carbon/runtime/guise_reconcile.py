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


class MinimumDifferenceReconciler:
    def reconcile(
        self,
        graph: CharacterGraph,
        *,
        desired_behavior: Mapping[str, Any],
        conflicts: Sequence[
            Mapping[str, Any]
        ],
        candidate_changes: Sequence[
            Mapping[str, Any]
        ],
    ) -> dict[str, Any]:
        normalized_changes = []

        for index, change in enumerate(
            candidate_changes
        ):
            item = dict(change)

            fields = list(
                item.get(
                    "fields",
                    [],
                )
            )

            item.setdefault(
                "id",
                f"reconciliation:{index}",
            )
            item.setdefault(
                "kind",
                "context_change",
            )
            item.setdefault(
                "fields",
                fields,
            )
            item.setdefault(
                "supporting_refs",
                [],
            )
            item.setdefault(
                "new_authority_required",
                False,
            )

            item[
                "difference_size"
            ] = len(fields)

            normalized_changes.append(
                item
            )

        normalized_changes.sort(
            key=lambda item: (
                item["difference_size"],
                str(item["id"]),
            )
        )

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": (
                "minimum_difference_reconciliation"
            ),
            "character_id": (
                graph.character_id
            ),
            "desired_behavior": dict(
                desired_behavior
            ),
            "conflicts": [
                dict(item)
                for item in conflicts
            ],
            "candidate_changes": (
                normalized_changes
            ),
            "preferred": (
                normalized_changes[0]
                if normalized_changes
                else None
            ),
            "preference_rule": (
                "fewest_declared_changed_fields"
            ),
            "automatic_canonization": False,
            "character_mutated": False,
            "authority_effect": "none",
        }

        result["projection_digest"] = (
            digest(result)
        )

        return result

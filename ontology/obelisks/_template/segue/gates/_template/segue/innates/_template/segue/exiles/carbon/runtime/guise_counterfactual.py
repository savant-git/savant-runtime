#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from guise import (
    OWNER,
    SCHEMA,
    SPECIALIZATION,
    CharacterGraph,
    digest,
    stable_id,
)


@dataclass(frozen=True)
class CounterfactualBranch:
    character_id: str
    parent_state_ref: str
    changes: Mapping[str, Any]
    question: str | None = None

    def projection(self) -> dict[str, Any]:
        material = {
            "character_id": (
                self.character_id
            ),
            "parent_state_ref": (
                self.parent_state_ref
            ),
            "changes": dict(
                self.changes
            ),
            "question": self.question,
        }

        return {
            "id": stable_id(
                "character-counterfactual",
                material,
            ),
            "kind": (
                "character_counterfactual_branch"
            ),
            **material,
            "authoritative": False,
            "authority_effect": "none",
        }


class CharacterCounterfactualEngine:
    def branch(
        self,
        graph: CharacterGraph,
        *,
        parent_state_ref: str,
        changes: Mapping[str, Any],
        question: str | None = None,
    ) -> dict[str, Any]:
        branch = CounterfactualBranch(
            character_id=graph.character_id,
            parent_state_ref=(
                parent_state_ref
            ),
            changes=dict(changes),
            question=question,
        )

        projection = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": (
                "character_counterfactual"
            ),
            "character_id": (
                graph.character_id
            ),
            "branch": (
                branch.projection()
            ),
            "parent_mutated": False,
            "character_mutated": False,
            "accepted_character_mutated": (
                False
            ),
            "authoritative": False,
            "authority_effect": "none",
        }

        projection[
            "projection_digest"
        ] = digest(projection)

        return projection

    def compare(
        self,
        *,
        baseline: Mapping[str, Any],
        branch: Mapping[str, Any],
    ) -> dict[str, Any]:
        left = dict(baseline)
        right = dict(branch)

        keys = sorted(
            set(left)
            | set(right)
        )

        differences = []

        for key in keys:
            if left.get(key) == right.get(
                key
            ):
                continue

            differences.append(
                {
                    "field": key,
                    "baseline": (
                        left.get(key)
                    ),
                    "counterfactual": (
                        right.get(key)
                    ),
                }
            )

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": (
                "counterfactual_compare"
            ),
            "differences": differences,
            "difference_count": len(
                differences
            ),
            "authority_effect": "none",
        }

        result["projection_digest"] = (
            digest(result)
        )

        return result

    def alternatives(
        self,
        graph: CharacterGraph,
        *,
        situation: Mapping[str, Any],
        alternatives: Sequence[
            Mapping[str, Any]
        ],
    ) -> dict[str, Any]:
        normalized = []

        for alternative in alternatives:
            item = dict(alternative)

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
                "required_conditions",
                [],
            )
            item.setdefault(
                "conflicts",
                [],
            )

            normalized.append(item)

        return {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": (
                "counterfactual_alternatives"
            ),
            "character_id": (
                graph.character_id
            ),
            "situation": dict(
                situation
            ),
            "alternatives": normalized,
            "single_answer_required": False,
            "character_mutated": False,
            "authority_effect": "none",
        }

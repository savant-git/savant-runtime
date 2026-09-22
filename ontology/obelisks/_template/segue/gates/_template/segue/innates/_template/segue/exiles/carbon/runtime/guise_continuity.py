#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from typing import Any

from guise import (
    OWNER,
    SCHEMA,
    SPECIALIZATION,
    CharacterGraph,
    digest,
)


class GuiseContinuitySentinel:
    def inspect(
        self,
        graph: CharacterGraph,
    ) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []

        knowledge_by_proposition: dict[
            str,
            list[Any],
        ] = defaultdict(list)

        for assertion in graph.knowledge.values():
            knowledge_by_proposition[
                assertion.proposition_ref
            ].append(assertion)

        for proposition_ref, assertions in (
            knowledge_by_proposition.items()
        ):
            states = {
                assertion.knowledge_state
                for assertion in assertions
            }

            if len(states) > 1:
                findings.append(
                    {
                        "kind": "knowledge_state_divergence",
                        "proposition_ref": (
                            proposition_ref
                        ),
                        "assertion_refs": sorted(
                            assertion.id
                            for assertion in assertions
                        ),
                        "states": sorted(states),
                        "severity": "review",
                        "automatic_resolution": False,
                    }
                )

        for contradiction in (
            graph.contradictions.values()
        ):
            findings.append(
                {
                    "kind": "preserved_contradiction",
                    "contradiction_ref": (
                        contradiction.id
                    ),
                    "severity": "review",
                    "automatic_resolution": False,
                }
            )

        categories_by_slot: dict[
            tuple[str, str],
            list[Any],
        ] = defaultdict(list)

        for category in graph.categories.values():
            categories_by_slot[
                (
                    category.domain,
                    category.category,
                )
            ].append(category)

        for (
            domain,
            category_name,
        ), values in categories_by_slot.items():
            formulations = {
                item.formulation
                for item in values
            }

            if len(formulations) > 1:
                findings.append(
                    {
                        "kind": "category_formulation_divergence",
                        "domain": domain,
                        "category": category_name,
                        "category_refs": sorted(
                            item.id
                            for item in values
                        ),
                        "severity": "review",
                        "automatic_resolution": False,
                    }
                )

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": "continuity_inspection",
            "character_id": graph.character_id,
            "findings": findings,
            "finding_count": len(findings),
            "automatic_repair": False,
            "character_mutated": False,
            "authority_effect": "none",
        }

        result["projection_digest"] = digest(
            result
        )

        return result


class KnowledgeLeakDetector:
    def inspect(
        self,
        graph: CharacterGraph,
        *,
        referenced_propositions: list[str],
        at: str | None = None,
    ) -> dict[str, Any]:
        known = set()

        for assertion in graph.knowledge.values():
            if assertion.knowledge_state in {
                "knows",
                "believes",
                "suspects",
                "misremembers",
                "false_belief",
                "refuses_to_believe",
            }:
                known.add(
                    assertion.proposition_ref
                )

        leaks = sorted(
            proposition
            for proposition
            in referenced_propositions
            if proposition not in known
        )

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": "knowledge_leak_detection",
            "character_id": graph.character_id,
            "at": at,
            "referenced_propositions": sorted(
                set(referenced_propositions)
            ),
            "represented_in_character_knowledge": sorted(
                known
            ),
            "potential_leaks": leaks,
            "potential_leak_count": len(
                leaks
            ),
            "automatic_verdict": False,
            "character_mutated": False,
            "authority_effect": "none",
        }

        result["projection_digest"] = digest(
            result
        )

        return result

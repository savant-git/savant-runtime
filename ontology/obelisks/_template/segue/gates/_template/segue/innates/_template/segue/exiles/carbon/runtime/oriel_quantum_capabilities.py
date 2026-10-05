#!/usr/bin/env python3
from __future__ import annotations

import copy
from typing import Any, Sequence

from oriel_quantum import status as quantum_status


owner = "carbon"
component = "oriel-quantum"
authority_effect = "none"
schema = "savant.carbon.oriel-quantum.capabilities.v1"


def clone(
    value: Any,
) -> Any:
    return copy.deepcopy(
        value
    )


def capability_manifest() -> dict[str, Any]:
    projection = {
        "modes": [
            "reference",
            "instance",
            "composition",
        ],
        "instanceable":
            True,
        "composable":
            True,
        "maskable":
            True,
        "ownership_transfer":
            False,
        "authority_transfer":
            False,
    }

    def capability(
        identifier: str,
        kind: str,
        purpose: str,
        operations: Sequence[str],
        dependencies: Sequence[str] = (),
    ) -> dict[str, Any]:
        return {
            "id":
                identifier,
            "owner":
                owner,
            "component":
                component,
            "kind":
                kind,
            "purpose":
                purpose,
            "version":
                "1.0.0",
            "status":
                "active",
            "authority_effect":
                "none",
            "execution_owner":
                owner,
            "projection_owner":
                "filament",
            "transformation_owner":
                "modus",
            "operations":
                list(
                    operations
                ),
            "dependencies":
                list(
                    dependencies
                ),
            "deterministic":
                True,
            "side_effects":
                [],
            "projection":
                clone(
                    projection
                ),
        }

    return {
        "schema":
            schema,
        "owner":
            owner,
        "component":
            component,
        "authority_effect":
            authority_effect,
        "runtime_module":
            "oriel_quantum",
        "capabilities": [
            capability(
                "oriel_quantum_superposition",
                "simulation-branching",
                (
                    "Project multiple Carbon "
                    "possibilities simultaneously "
                    "while retaining Oriel "
                    "chronology and logistics "
                    "feasibility classifications."
                ),
                [
                    "superpose",
                ],
                [
                    "oriel_quantum_feasibility",
                ],
            ),
            capability(
                "oriel_quantum_frontier",
                "simulation-analysis",
                (
                    "Project viable, conditional, "
                    "unresolved and infeasible "
                    "possibility frontiers without "
                    "discarding rejected branches."
                ),
                [
                    "frontier",
                ],
                [
                    "oriel_quantum_superposition",
                ],
            ),
            capability(
                "oriel_quantum_branch_comparison",
                "simulation-analysis",
                (
                    "Compare alternate Oriel "
                    "possibilities and their "
                    "spacetime deltas."
                ),
                [
                    "compare",
                ],
                [
                    "oriel_quantum_superposition",
                ],
            ),
            capability(
                "oriel_quantum_counterfactual_packet",
                "counterfactual-projection",
                (
                    "Project an Oriel possibility "
                    "into Carbon's existing "
                    "counterfactual definition "
                    "surface without executing or "
                    "selecting it."
                ),
                [
                    "counterfactual_packet",
                ],
                [
                    "oriel_quantum_superposition",
                ],
            ),
            capability(
                "oriel_quantum_collapse",
                "simulation-selection",
                (
                    "Select an admissible "
                    "simulation trajectory while "
                    "preserving the boundary "
                    "between simulation selection "
                    "and canon promotion."
                ),
                [
                    "collapse",
                ],
                [
                    "oriel_quantum_superposition",
                ],
            ),
        ],
        "invariants": {
            "carbon_owns_quantum":
                True,
            "oriel_only_gates_feasibility":
                True,
            "all_possibilities_remain_traceable":
                True,
            "infeasible_branch_cannot_collapse":
                True,
            "conditional_collapse_requires_override":
                True,
            "unresolved_collapse_requires_override":
                True,
            "collapse_is_not_canon_promotion":
                True,
            "evidence_admission":
                False,
        },
    }


def status() -> dict[str, Any]:
    runtime = quantum_status()

    return {
        "schema":
            schema,
        "kind":
            "status",
        "owner":
            owner,
        "component":
            component,
        "authority_effect":
            authority_effect,
        "runtime_module":
            "oriel_quantum",
        "runtime_ready":
            bool(
                runtime.get(
                    "ready",
                    False,
                )
            ),
        "capability_count":
            len(
                capability_manifest()[
                    "capabilities"
                ]
            ),
        "authority_transfer":
            False,
        "canon_effect":
            "none",
        "evidence_admission":
            False,
        "ready":
            bool(
                runtime.get(
                    "ready",
                    False,
                )
            ),
    }


__all__ = [
    "capability_manifest",
    "status",
]

#!/usr/bin/env python3

from __future__ import annotations

from runtime.constitution import (
    ConstitutionalObject,
    ConstitutionalRegistry,
)

from runtime.living_governance_constitutional import (
    install as install_living_governance,
    service_id,
)


operator_id = "operator:living-plan"
engine_id = "engine:living-plan"

timestamp_default = "2026-08-30T00:00:00Z"


def operator_assertion(
    timestamp: str = timestamp_default,
) -> ConstitutionalObject:
    return ConstitutionalObject.from_mapping(
        {
            "id":
                operator_id,

            "kind":
                "operator",

            "canonical_name":
                "living-plan",

            "display_name":
                "Living Plan",

            "description":
                (
                    "Provides operational access to the authoritative "
                    "living masterplan stream, including progress, "
                    "readiness, dependency impact, immutable status "
                    "evolution, task addition, history, and deterministic "
                    "export."
                ),

            "authority":
                {},

            "status":
                "active",

            "version":
                "1.0.0",

            "created_at":
                timestamp,

            "updated_at":
                timestamp,

            "lineage":
                {
                    "parent":
                        "domain:operators",

                    "supersedes":
                        [],

                    "superseded_by":
                        [],
                },

            "provenance":
                {
                    "asserted_by":
                        "user",

                    "sources":
                        [
                            "commands/living-plan",
                            "runtime/living_governance.py",
                            "current user directive 2026-08-30",
                        ],

                    "method":
                        "constitutional-extension",
                },

            "relationships":
                [
                    {
                        "type":
                            "implements",

                        "target":
                            service_id,
                    }
                ],

            "dependencies":
                [
                    service_id
                ],

            "metadata":
                {
                    "engine":
                        "living-plan",

                    "implementation_refs":
                        [
                            "commands/living-plan"
                        ],

                    "authority_stream":
                        "masterplan",

                    "capabilities":
                        [
                            "show",
                            "progress",
                            "ready",
                            "impact",
                            "status-evolution",
                            "text-evolution",
                            "task-addition",
                            "history",
                            "export",
                            "dependency-projection",
                            "reverse-dependency-projection",
                        ],

                    "authority_storage":
                        "living-governance-ledger",

                    "duplicate_authority":
                        False,
                },
        }
    )


def install(
    registry: ConstitutionalRegistry,
    timestamp: str = timestamp_default,
) -> ConstitutionalRegistry:
    registry = install_living_governance(
        registry,
        timestamp,
    )

    if operator_id in registry.ids:
        return registry

    contribution = registry.contribute(
        engine_id,
        (
            operator_assertion(
                timestamp
            ),
        ),
    )

    return contribution.registry


__all__ = [
    "engine_id",
    "install",
    "operator_assertion",
    "operator_id",
]

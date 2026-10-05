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


operator_id = "operator:living-governance-guard"
engine_id = "engine:living-governance-guard"

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
                "living-governance-guard",

            "display_name":
                "Living Governance Guard",

            "description":
                (
                    "Deterministically evaluates machine-enforceable "
                    "living governance invariants before mutation."
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
                            "commands/living-guard",
                            "runtime/living_guard.py",
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
                        "living-governance-guard",

                    "implementation_refs":
                        [
                            "runtime/living_guard.py",
                            "commands/living-guard",
                        ],

                    "enforcement_scope":
                        [
                            "absolute-path",
                            "runtime-containment",
                            "lowercase-savant-path",
                            "lowercase-identifier",
                            "canonical-kindred-terminology",
                            "secret-projection",
                            "duplicate-semantic-id",
                        ],

                    "non_claim":
                        (
                            "human-semantic governance rules remain "
                            "outside deterministic enforcement unless "
                            "a specific executable check exists"
                        ),
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

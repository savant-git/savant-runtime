#!/usr/bin/env python3

from __future__ import annotations

from typing import Any

from runtime.constitution import (
    ConstitutionalObject,
    ConstitutionalRegistry,
)


service_id = "service:living-governance"
operator_id = "operator:living-governance-engine"
engine_id = "engine:living-governance"

timestamp_default = "2026-08-30T00:00:00Z"


def service_assertion(
    timestamp: str = timestamp_default,
) -> ConstitutionalObject:
    return ConstitutionalObject.from_mapping(
        {
            "id":
                service_id,

            "kind":
                "service",

            "canonical_name":
                "living-governance",

            "display_name":
                "Living Governance",

            "description":
                (
                    "Projects current rules, permissions, invariants, "
                    "decisions, structure, masterplan, terminology, "
                    "unknowns, compatibility obligations, risks, "
                    "dependencies, and related governance views from "
                    "authoritative living records."
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
                        "domain:services",

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
                            (
                                "current user directive "
                                "2026-08-30"
                            ),
                            (
                                "canon-system/authority/"
                                "living/bootstrap.json"
                            ),
                            (
                                "runtime/"
                                "living_governance.py"
                            ),
                        ],

                    "method":
                        "constitutional-extension",
                },

            "relationships":
                [
                    {
                        "type":
                            "owned_by",

                        "target":
                            "faculty:knowledge",
                    },
                    {
                        "type":
                            "implemented_through",

                        "target":
                            "exile:notary",
                    },
                ],

            "dependencies":
                [
                    "faculty:knowledge",
                    "exile:notary",
                    "service:authority",
                ],

            "metadata":
                {
                    "engine":
                        "living-governance",

                    "implementation_refs":
                        [
                            (
                                "runtime/"
                                "living_governance.py"
                            ),
                            (
                                "canon-system/authority/"
                                "living/bootstrap.json"
                            ),
                        ],

                    "projection_targets":
                        [
                            "runtime",
                            "documentation",
                            "json",
                            "graph",
                            "visualization",
                            "future_tooling",
                        ],

                    "authority_storage":
                        (
                            "constitutional authority "
                            "plus immutable living events"
                        ),

                    "projection_only":
                        [
                            "rules.md",
                            "permissions.md",
                            "invariants.md",
                            "decisions.md",
                            "structure.md",
                            "masterplan.md",
                            "terminology.md",
                            "unknowns.md",
                            "compatibility.md",
                            "risks.md",
                            "enhancements.md",
                            "snapshot.json",
                            "graph.json",
                            "status.json",
                        ],
                },
        }
    )


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
                "living-governance-engine",

            "display_name":
                "Living Governance Engine",

            "description":
                (
                    "Resolves immutable living governance events and "
                    "deterministically regenerates current governance "
                    "projections."
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
                            (
                                "runtime/"
                                "living_governance.py"
                            ),
                            (
                                "current user directive "
                                "2026-08-30"
                            ),
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
                        "living-governance",

                    "implementation_refs":
                        [
                            (
                                "runtime/"
                                "living_governance.py"
                            )
                        ],

                    "projection_targets":
                        [
                            "runtime",
                            "documentation",
                            "json",
                            "graph",
                            "visualization",
                            "future_tooling",
                        ],
                },
        }
    )


def assertions(
    timestamp: str = timestamp_default,
) -> tuple[
    ConstitutionalObject,
    ...,
]:
    return (
        service_assertion(
            timestamp
        ),
        operator_assertion(
            timestamp
        ),
    )


def install(
    registry: ConstitutionalRegistry,
    timestamp: str = timestamp_default,
) -> ConstitutionalRegistry:
    required = {
        service_id,
        operator_id,
    }

    missing = (
        required
        - set(
            registry.ids
        )
    )

    if not missing:
        return registry

    selected = tuple(
        assertion
        for assertion
        in assertions(
            timestamp
        )
        if assertion.id
        in missing
    )

    contribution = (
        registry.contribute(
            engine_id,
            selected,
        )
    )

    return contribution.registry


def describe(
    registry: ConstitutionalRegistry,
) -> dict[
    str,
    Any,
]:
    installed = (
        service_id
        in registry.ids
        and operator_id
        in registry.ids
    )

    return {
        "engine":
            engine_id,

        "service":
            service_id,

        "operator":
            operator_id,

        "installed":
            installed,

        "authority_effect":
            (
                "constitutional-extension"
                if installed
                else "none"
            ),

        "implementation":
            (
                "/root/savant-runtime/runtime/"
                "living_governance.py"
            ),

        "credential_values_exposed":
            False,
    }


__all__ = [
    "assertions",
    "describe",
    "engine_id",
    "install",
    "operator_assertion",
    "operator_id",
    "service_assertion",
    "service_id",
]

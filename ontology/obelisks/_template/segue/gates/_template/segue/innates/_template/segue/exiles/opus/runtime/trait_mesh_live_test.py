#!/usr/bin/env python3
from __future__ import annotations

import json

from .trait_mesh import (
    default_trait_requirements,
    execute_mesh,
)


def main() -> None:
    requirements = (
        default_trait_requirements()[:2]
    )

    result = execute_mesh(
        task=(
            "Determine whether the statement "
            "'all deterministic systems are "
            "predictable in practice' is "
            "necessarily true. Keep the "
            "analysis concise."
        ),
        context={
            "test": (
                "bounded live opus "
                "trait-composition verification"
            ),
            "authority_effect": "none",
        },
        requirements=requirements,
        candidates_per_trait=1,
        maximum_total_calls=4,
    )

    executions = []

    for item in result.get(
        "executions",
        []
    ):
        response = item.get(
            "response"
        )

        lineage = (
            response.get("lineage")
            if isinstance(
                response,
                dict,
            )
            else None
        )

        executions.append(
            {
                "execution_id": item.get(
                    "execution_id"
                ),
                "trait_id": item.get(
                    "trait_id"
                ),
                "provider_id": item.get(
                    "provider_id"
                ),
                "model_id": item.get(
                    "model_id"
                ),
                "status": item.get(
                    "status"
                ),
                "lineage": lineage,
                "error": item.get(
                    "error"
                ),
            }
        )

    projection = {
        "schema": result.get(
            "schema"
        ),
        "owner": result.get(
            "owner"
        ),
        "mesh_id": result.get(
            "mesh_id"
        ),
        "status": result.get(
            "status"
        ),
        "completed_traits": result.get(
            "completed_traits"
        ),
        "missing_traits": result.get(
            "missing_traits"
        ),
        "inference_calls": result.get(
            "inference_calls"
        ),
        "call_budget": result.get(
            "call_budget"
        ),
        "call_budget_exhausted": (
            result.get(
                "call_budget_exhausted"
            )
        ),
        "successful_executions": (
            result.get(
                "successful_executions"
            )
        ),
        "failed_executions": (
            result.get(
                "failed_executions"
            )
        ),
        "contributing_providers": (
            result.get(
                "contributing_providers"
            )
        ),
        "contributing_models": (
            result.get(
                "contributing_models"
            )
        ),
        "executions": executions,
        "projection_digest": result.get(
            "projection_digest"
        ),
        "authority_effect": result.get(
            "authority_effect"
        ),
    }

    print(
        json.dumps(
            projection,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

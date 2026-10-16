from __future__ import annotations

from refuze import project


def main() -> None:
    router_core = {
        "schema": (
            "savant://runtime/opus/"
            "prodigal/router_core/1.0.0"
        ),
        "prodigal": (
            "prodigal:router_core"
        ),
        "authority_effect": "none",
        "projection_only": True,
        "route_id": (
            "text_inference_route"
        ),
        "required_capabilities": [
            "text",
            "tools",
        ],
        "required_layers": [
            "reasoning",
        ],
        "eligible_by_declared_metadata": [
            "alpha",
            "gamma",
        ],
        "digest": "router-digest",
    }

    capex = {
        "schema": (
            "savant://runtime/opus/"
            "prodigal/capex/1.0.0"
        ),
        "prodigal": "prodigal:capex",
        "authority_effect": "none",
        "projection_only": True,
        "provider_count": 3,
        "aperture": {
            "capabilities": [
                "text",
                "tools",
                "vision",
            ],
            "layers": [
                "reasoning",
                "writing",
            ],
            "required_capabilities": [
                "text",
                "tools",
            ],
            "required_layers": [
                "reasoning",
            ],
            "missing_capabilities": [],
            "missing_layers": [],
        },
        "digest": "capex-digest",
    }

    orchid = {
        "schema": (
            "savant://runtime/opus/"
            "prodigal/orchid/1.0.0"
        ),
        "prodigal": "prodigal:orchid",
        "authority_effect": "none",
        "projection_only": True,
        "required_capabilities": [
            "text",
            "tools",
        ],
        "required_layers": [
            "reasoning",
        ],
        "branches": {
            "by_capability": {
                "text": [
                    "alpha",
                    "beta",
                    "gamma",
                ],
                "tools": [
                    "alpha",
                    "gamma",
                ],
            },
            "by_layer": {
                "reasoning": [
                    "alpha",
                    "gamma",
                ],
            },
            "declared_constraint_matches": [
                "alpha",
                "gamma",
            ],
        },
        "digest": "orchid-digest",
    }

    first = project(
        router_core=router_core,
        capex=capex,
        orchid=orchid,
    )

    second = project(
        router_core=dict(
            router_core
        ),
        capex=dict(
            capex
        ),
        orchid=dict(
            orchid
        ),
    )

    assert first == second

    assert first[
        "authority_effect"
    ] == "none"

    assert first[
        "projection_only"
    ] is True

    synthesis = first[
        "synthesis"
    ]

    assert synthesis[
        "route_id"
    ] == "text_inference_route"

    assert synthesis[
        "routing_candidates"
    ] == [
        "alpha",
        "gamma",
    ]

    assert synthesis[
        "consistency"
    ][
        "capability_requirements"
    ] is True

    assert synthesis[
        "consistency"
    ][
        "layer_requirements"
    ] is True

    assert synthesis[
        "consistency"
    ][
        "declared_candidate_projection"
    ] is True

    assert synthesis[
        "conflicts"
    ] == []

    assert synthesis[
        "reconciliation_required"
    ] is False

    divergent = dict(
        orchid
    )

    divergent[
        "required_layers"
    ] = [
        "writing",
    ]

    divergent_result = project(
        router_core=router_core,
        capex=capex,
        orchid=divergent,
    )

    assert divergent_result[
        "synthesis"
    ][
        "reconciliation_required"
    ] is True

    assert (
        "layer_requirements"
        in divergent_result[
            "synthesis"
        ][
            "conflicts"
        ]
    )

    authority_failed = False

    invalid_capex = dict(
        capex
    )

    invalid_capex[
        "authority_effect"
    ] = "mutation"

    try:
        project(
            router_core=router_core,
            capex=invalid_capex,
            orchid=orchid,
        )
    except ValueError:
        authority_failed = True

    assert authority_failed

    assert first[
        "boundaries"
    ][
        "selects_provider"
    ] is False

    assert first[
        "boundaries"
    ][
        "resolves_conflicts"
    ] is False

    assert first[
        "boundaries"
    ][
        "executes_provider"
    ] is False

    print(
        "refuze selftest: ok"
    )


if __name__ == "__main__":
    main()

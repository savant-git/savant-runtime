from __future__ import annotations

from composition import project


def main() -> None:
    route = {
        "id": "text_inference_route",
        "fallback_order": [
            "alpha",
            "beta",
            "gamma",
        ],
        "authority_effect": "none",
    }

    providers = [
        {
            "id": "gamma",
            "capabilities": [
                "text",
                "tools",
            ],
            "cognitive_layers": [
                "reasoning",
            ],
        },
        {
            "id": "alpha",
            "capabilities": [
                "text",
                "tools",
            ],
            "cognitive_layers": [
                "reasoning",
                "writing",
            ],
        },
        {
            "id": "beta",
            "capabilities": [
                "text",
            ],
            "cognitive_layers": [
                "writing",
            ],
        },
    ]

    first = project(
        route=route,
        providers=providers,
        required_capabilities=[
            "text",
            "tools",
        ],
        required_layers=[
            "reasoning",
        ],
    )

    second = project(
        route=dict(
            route
        ),
        providers=reversed(
            providers
        ),
        required_capabilities=[
            "tools",
            "text",
        ],
        required_layers=[
            "reasoning",
        ],
    )

    assert first == second

    assert first[
        "authority_effect"
    ] == "none"

    assert first[
        "projection_only"
    ] is True

    assert first[
        "route_id"
    ] == "text_inference_route"

    assert set(
        first[
            "prodigals"
        ]
    ) == {
        "router_core",
        "capex",
        "orchid",
        "refuze",
    }

    assert first[
        "summary"
    ][
        "provider_count"
    ] == 3

    assert first[
        "summary"
    ][
        "declared_candidates"
    ] == [
        "alpha",
        "gamma",
    ]

    assert first[
        "summary"
    ][
        "reconciliation_required"
    ] is False

    assert first[
        "lineage"
    ][
        "router_core_digest"
    ] == first[
        "prodigals"
    ][
        "router_core"
    ][
        "digest"
    ]

    assert first[
        "lineage"
    ][
        "refuze_digest"
    ] == first[
        "prodigals"
    ][
        "refuze"
    ][
        "digest"
    ]

    assert first[
        "boundaries"
    ][
        "selects_provider"
    ] is False

    assert first[
        "boundaries"
    ][
        "executes_provider"
    ] is False

    assert first[
        "boundaries"
    ][
        "authoritative_router"
    ] == "opus.runtime.router"

    print(
        "opus prodigal composition "
        "selftest: ok"
    )


if __name__ == "__main__":
    main()

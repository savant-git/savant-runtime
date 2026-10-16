from __future__ import annotations

from router_core import project


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
            "tools",
            "text",
        ],
        required_layers=[
            "reasoning",
        ],
    )

    second = project(
        route=route,
        providers=reversed(
            providers
        ),
        required_capabilities=[
            "text",
            "tools",
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
        "eligible_by_declared_metadata"
    ] == [
        "alpha",
        "gamma",
    ]

    rows = {
        row["provider_id"]: row
        for row in first["providers"]
    }

    assert rows["alpha"][
        "fallback_rank"
    ] == 0

    assert rows["beta"][
        "constraints"
    ]["capability_match"] is False

    assert rows["beta"][
        "constraints"
    ]["layer_metadata_match"] is False

    assert first[
        "boundaries"
    ]["selects_provider"] is False

    assert first[
        "boundaries"
    ]["executes_provider"] is False

    assert first[
        "boundaries"
    ]["authoritative_router"] == (
        "opus.runtime.router"
    )

    duplicate_failed = False

    try:
        project(
            route=route,
            providers=[
                {
                    "id": "alpha",
                },
                {
                    "id": "alpha",
                },
            ],
        )
    except ValueError:
        duplicate_failed = True

    assert duplicate_failed

    print(
        "router_core selftest: ok"
    )


if __name__ == "__main__":
    main()

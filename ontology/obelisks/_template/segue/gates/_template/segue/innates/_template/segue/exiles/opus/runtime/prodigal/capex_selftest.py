from __future__ import annotations

from capex import project


def main() -> None:
    providers = [
        {
            "id": "beta",
            "capabilities": [
                "text",
            ],
            "cognitive_layers": [
                "writing",
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
            ],
        },
    ]

    first = project(
        providers=providers,
        required_capabilities=[
            "text",
            "tools",
        ],
        required_layers=[
            "reasoning",
            "writing",
        ],
    )

    second = project(
        providers=reversed(
            providers
        ),
        required_capabilities=[
            "tools",
            "text",
        ],
        required_layers=[
            "writing",
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
        "provider_count"
    ] == 2

    assert first[
        "aperture"
    ][
        "capability_coverage_complete"
    ] is True

    assert first[
        "aperture"
    ][
        "layer_coverage_complete"
    ] is True

    assert first[
        "aperture"
    ][
        "capabilities"
    ] == [
        "text",
        "tools",
    ]

    assert first[
        "aperture"
    ][
        "layers"
    ] == [
        "reasoning",
        "writing",
    ]

    missing = project(
        providers=providers,
        required_capabilities=[
            "vision",
        ],
        required_layers=[
            "code",
        ],
    )

    assert missing[
        "aperture"
    ][
        "missing_capabilities"
    ] == [
        "vision",
    ]

    assert missing[
        "aperture"
    ][
        "missing_layers"
    ] == [
        "code",
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

    duplicate_failed = False

    try:
        project(
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
        "capex selftest: ok"
    )


if __name__ == "__main__":
    main()

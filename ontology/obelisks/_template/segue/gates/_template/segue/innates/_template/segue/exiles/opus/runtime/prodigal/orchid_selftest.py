from __future__ import annotations

from orchid import project


def main() -> None:
    providers = [
        {
            "id": "gamma",
            "capabilities": [
                "text",
                "vision",
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
        providers=providers,
        required_capabilities=[
            "text",
        ],
        required_layers=[
            "reasoning",
        ],
    )

    second = project(
        providers=reversed(
            providers
        ),
        required_capabilities=[
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
        "branches"
    ][
        "by_capability"
    ][
        "text"
    ] == [
        "alpha",
        "beta",
        "gamma",
    ]

    assert first[
        "branches"
    ][
        "by_capability"
    ][
        "tools"
    ] == [
        "alpha",
    ]

    assert first[
        "branches"
    ][
        "by_layer"
    ][
        "reasoning"
    ] == [
        "alpha",
        "gamma",
    ]

    assert first[
        "branches"
    ][
        "declared_constraint_matches"
    ] == [
        "alpha",
        "gamma",
    ]

    assert first[
        "branches"
    ][
        "provider_branch_count"
    ] == 3

    assert first[
        "boundaries"
    ][
        "selects_branch"
    ] is False

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
        "orchid selftest: ok"
    )


if __name__ == "__main__":
    main()

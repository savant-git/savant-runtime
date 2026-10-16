from __future__ import annotations

import sys
from pathlib import Path


RUNTIME = Path(
    __file__
).resolve().parents[1]

OPUS_ROOT = RUNTIME.parent

for path in (
    str(OPUS_ROOT),
    str(RUNTIME),
):
    if path not in sys.path:
        sys.path.insert(
            0,
            path,
        )


from prodigal import project
from router import provider
from router import route


def main() -> None:
    route_data = route(
        "text_inference_route"
    )

    fallback_order = (
        route_data.get(
            "fallback_order"
        )
        or []
    )

    providers = [
        provider(
            provider_id
        )
        for provider_id
        in fallback_order
    ]

    projection = project(
        route=route_data,
        providers=providers,
    )

    assert projection[
        "authority_effect"
    ] == "none"

    assert projection[
        "projection_only"
    ] is True

    assert projection[
        "route_id"
    ] == "text_inference_route"

    assert projection[
        "summary"
    ][
        "provider_count"
    ] == len(
        fallback_order
    )

    assert set(
        projection[
            "prodigals"
        ]
    ) == {
        "router_core",
        "capex",
        "orchid",
        "refuze",
    }

    assert projection[
        "boundaries"
    ][
        "selects_provider"
    ] is False

    assert projection[
        "boundaries"
    ][
        "executes_provider"
    ] is False

    assert projection[
        "boundaries"
    ][
        "authoritative_router"
    ] == "opus.runtime.router"

    print(
        "opus prodigal integration "
        "selftest: ok"
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import sys
from pathlib import Path


PRODIGAL_ROOT = Path(
    __file__
).resolve().parent

RUNTIME_ROOT = (
    PRODIGAL_ROOT.parent
)

OPUS_ROOT = (
    RUNTIME_ROOT.parent
)


if str(
    RUNTIME_ROOT
) not in sys.path:
    sys.path.insert(
        0,
        str(
            RUNTIME_ROOT
        ),
    )


from prodigal import project


def _read_json(
    path: Path,
) -> dict:
    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        value = json.load(
            handle
        )

    if not isinstance(
        value,
        dict,
    ):
        raise TypeError(
            "expected json object: "
            f"{path}"
        )

    return value


def main() -> None:
    route_path = (
        OPUS_ROOT
        / "registry"
        / "routes"
        / "text_inference_route.json"
    )

    provider_root = (
        OPUS_ROOT
        / "registry"
        / "providers"
    )

    route_data = _read_json(
        route_path
    )

    fallback_order = (
        route_data.get(
            "fallback_order"
        )
        or []
    )

    providers = [
        _read_json(
            provider_root
            / f"{provider_id}.json"
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

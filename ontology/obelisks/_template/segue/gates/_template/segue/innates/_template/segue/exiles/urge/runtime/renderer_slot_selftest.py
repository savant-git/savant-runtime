from __future__ import annotations

from .renderer_slot import (
    project,
    renderer_binding,
)


def _renderer(
    request,
):
    candidate = request[
        "candidate"
    ]

    return {
        "schema": (
            "savant://selftest/"
            "renderer-projection/1.0.0"
        ),
        "candidate_digest": request[
            "candidate_digest"
        ],
        "representation": {
            "kind": "vector",
            "primitives": candidate.get(
                "primitives",
                [],
            ),
        },
    }


def main() -> int:
    candidate = {
        "id": "candidate:test",
        "concept": (
            "identity emerges from "
            "one interrupted interval"
        ),
        "primitives": [
            {
                "kind": "interval",
                "start": 0,
                "end": 1,
            }
        ],
        "provenance": [
            "selftest"
        ],
    }

    reserved = project(
        candidate=candidate
    )

    assert (
        reserved["state"]
        == "reserved"
    )

    assert (
        reserved["renderer"][
            "binding"
        ]
        is None
    )

    binding = renderer_binding(
        id=(
            "savant-svg-renderer:"
            "selftest"
        ),
        project=_renderer,
    )

    first = project(
        candidate=candidate,
        binding=binding,
        context={
            "domain": "logo-design",
        },
    )

    second = project(
        candidate=candidate,
        binding=binding,
        context={
            "domain": "logo-design",
        },
    )

    assert (
        first["state"]
        == "projected"
    )

    assert (
        first["digest"]
        == second["digest"]
    )

    assert (
        first["candidate_digest"]
        == reserved[
            "candidate_digest"
        ]
    )

    assert (
        first["boundaries"][
            "owns_renderer"
        ]
        is False
    )

    assert (
        first["boundaries"][
            "mutates_candidate"
        ]
        is False
    )

    print(
        first["digest"]
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

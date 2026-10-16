from __future__ import annotations

from typing import Any

from . import execution_binding
from . import creative_orchestration


class fake_dispatcher:
    def __init__(
        self,
    ) -> None:
        self.routes: dict[
            str,
            Any,
        ] = {}

    def register(
        self,
        capability: str,
        handler: Any,
    ) -> None:
        self.routes[
            capability
        ] = handler

    def dispatch(
        self,
        capability: str,
        payload: dict[
            str,
            Any,
        ],
    ) -> Any:
        return self.routes[
            capability
        ](
            payload
        )


def _candidate(
    name: str,
    mechanism: str,
) -> dict[str, str]:
    return {
        "name": name,
        "concept": (
            f"{name} converts a "
            "constraint into identity"
        ),
        "mechanism": mechanism,
        "rationale": (
            "distinction is structural"
        ),
        "assumption_broken": (
            "identity requires "
            "decoration"
        ),
        "structural_difference": (
            "the mechanism survives "
            "styling removal"
        ),
        "risk": (
            "execution may obscure "
            "the mechanism"
        ),
        "test": (
            "remove styling and "
            "re-evaluate"
        ),
    }


def _fake_opus_text(
    *,
    message: str,
    system: str,
    context: dict[
        str,
        Any,
    ],
    required_capabilities=(),
    required_layers=(),
) -> dict[str, Any]:
    del system
    del context
    del required_capabilities
    del required_layers

    import json

    names = [
        "threshold",
        "counterform",
        "phase",
        "interval",
        "splice",
        "pressure",
    ]

    candidates = [
        _candidate(
            name,
            (
                f"{name} uses one "
                "structural relationship "
                "as the identifying event"
            ),
        )
        for name in names
    ]

    if (
        "adversarial synthesis"
        in message.lower()
    ):
        candidates.reverse()

    return {
        "text": json.dumps(
            {
                "candidates":
                    candidates
            },
            sort_keys=True,
        ),
        "provider":
            "selftest",
        "model":
            "deterministic-fixture",
        "usage": {},
        "lineage": {
            "owner":
                "exile:opus",
            "executor":
                "selftest",
        },
    }


def main() -> int:
    dispatcher = (
        fake_dispatcher()
    )

    registered = (
        execution_binding
        .register(
            dispatcher
        )
    )

    assert (
        registered
        == execution_binding
        .CAPABILITY
    )

    assert (
        execution_binding
        .CAPABILITY
        in dispatcher.routes
    )

    original = (
        creative_orchestration
        ._opus_text
    )

    try:
        creative_orchestration._opus_text = (
            _fake_opus_text
        )

        result = (
            dispatcher.dispatch(
                execution_binding
                .CAPABILITY,
                {
                    "mode":
                        "job",
                    "objective":
                        (
                            "create a "
                            "structurally "
                            "distinct result"
                        ),
                    "constraints": [
                        "remain usable",
                    ],
                    "invariants": [
                        "preserve identity",
                    ],
                    "cliches": [
                        "generic solution",
                    ],
                    "baselines": [
                        "default pattern",
                    ],
                    "context": {
                        "domain":
                            "selftest",
                    },
                    "creative_policy": {
                        "divergence_passes":
                            2,
                        "candidates_per_pass":
                            6,
                        "frontier_size":
                            4,
                        "synthesis_candidates":
                            4,
                    },
                },
            )
        )

    finally:
        creative_orchestration._opus_text = (
            original
        )

    assert (
        result[
            "capability"
        ]
        == execution_binding
        .CAPABILITY
    )

    assert (
        result[
            "owner"
        ]
        == "exile:urge"
    )

    assert (
        result[
            "request"
        ][
            "mode"
        ]
        == "job"
    )

    assert result[
        "creative"
    ]

    assert result[
        "workbench"
    ]

    assert (
        result[
            "boundaries"
        ][
            "owns_provider_routing"
        ]
        is False
    )

    assert (
        result[
            "boundaries"
        ][
            "owns_discrimination"
        ]
        is False
    )

    assert (
        result[
            "boundaries"
        ][
            "owns_renderer"
        ]
        is False
    )

    print(
        execution_binding
        .CAPABILITY
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

from __future__ import annotations

import json

from .praxis import (
    CAPABILITY,
    OWNER,
    execute_step,
    normalize_parameters,
    project_praxis,
)


def _parameters() -> dict:
    return {
        "objective": (
            "Create a proprietary identity "
            "for savant using structural "
            "intelligence rather than "
            "fashionable AI symbolism."
        ),
        "name": "savant",
        "iterations": 3,
        "interval_ms": 250,
        "constraints": [
            "must remain legible",
            "must reproduce at small scale",
        ],
        "invariants": [
            "lowercase identity",
        ],
        "cliches": [
            "generic neural network",
            "sparkle icon",
        ],
        "context": {
            "surface": "splyce",
        },
        "creative_policy": {},
    }


def main() -> int:
    parameters = normalize_parameters(
        _parameters()
    )

    if parameters.name != "savant":
        raise RuntimeError(
            "name normalization failed"
        )

    if parameters.iterations != 3:
        raise RuntimeError(
            "iteration normalization failed"
        )

    if parameters.interval_ms != 250:
        raise RuntimeError(
            "interval normalization failed"
        )

    praxis_a = project_praxis(
        _parameters()
    )

    praxis_b = project_praxis(
        _parameters()
    )

    if praxis_a != praxis_b:
        raise RuntimeError(
            "praxis projection is not "
            "deterministic"
        )

    first = execute_step({
        "parameters":
            _parameters(),
        "index": 1,
    })

    if first["owner"] != OWNER:
        raise RuntimeError(
            "owner mismatch"
        )

    if (
        first["capability"]
        != CAPABILITY
    ):
        raise RuntimeError(
            "capability mismatch"
        )

    if first["index"] != 1:
        raise RuntimeError(
            "iteration index mismatch"
        )

    if first["complete"]:
        raise RuntimeError(
            "first iteration incorrectly "
            "marked complete"
        )

    second = execute_step({
        "parameters":
            _parameters(),
        "index": 2,
        "previous": {
            "index": first["index"],
            "digest": first["digest"],
            "workbench": {
                "digest":
                    first[
                        "workbench"
                    ].get(
                        "digest"
                    ),
            },
        },
    })

    if (
        second[
            "lineage"
        ][
            "previous_digest"
        ]
        != first["digest"]
    ):
        raise RuntimeError(
            "iteration lineage failed"
        )

    third = execute_step({
        "parameters":
            _parameters(),
        "index": 3,
        "previous": {
            "index": second["index"],
            "digest": second["digest"],
            "workbench": {
                "digest":
                    second[
                        "workbench"
                    ].get(
                        "digest"
                    ),
            },
        },
    })

    if not third["complete"]:
        raise RuntimeError(
            "final iteration not complete"
        )

    if (
        third[
            "ownership"
        ][
            "provider_orchestration"
        ]
        != "exile:opus"
    ):
        raise RuntimeError(
            "opus ownership boundary failed"
        )

    output = {
        "ok": True,
        "owner": OWNER,
        "capability": CAPABILITY,
        "schema":
            praxis_a["schema"],
        "step_schema":
            first["schema"],
        "iterations":
            parameters.iterations,
        "interval_ms":
            parameters.interval_ms,
        "client_paced":
            (
                praxis_a[
                    "execution"
                ][
                    "mode"
                ]
                == "client-paced"
            ),
        "live_projection":
            praxis_a[
                "execution"
            ][
                "live_projection"
            ],
        "lineage_preserved":
            (
                second[
                    "lineage"
                ][
                    "previous_digest"
                ]
                == first["digest"]
            ),
        "final_complete":
            third["complete"],
        "provider_owner":
            third[
                "ownership"
            ][
                "provider_orchestration"
            ],
    }

    print(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

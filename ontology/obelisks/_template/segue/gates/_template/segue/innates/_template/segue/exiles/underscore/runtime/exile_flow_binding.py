from __future__ import annotations

from typing import Any

from ...segue.exile_runtime.runtime.execution.exile_flow import (
    prepare_exile,
)


schema = (
    "savant://runtime/underscore/"
    "exile-flow-binding/1.0.1"
)

owner = "exile:underscore"
authority_effect = "none"

accepted_purpose = (
    "structure",
    "hidden support",
    "normalization and alignment",
)

chain_alias = "un"


def preparation() -> dict[str, Any]:
    return prepare_exile(
        exile=owner,
        capabilities=(),
        accepts=(),
        emits=(),
        extensions={
            "purpose":
                accepted_purpose,
            "chain_alias":
                chain_alias,
            "opus_ready":
                True,
            "authority_effect":
                authority_effect,
            "future_slots": (
                "prodigals",
                "quirks",
                "contracts",
                "runtime_hooks",
                "chain_masks",
                "metrics",
                "tests",
            ),
        },
    )


def status() -> dict[str, Any]:
    prepared = preparation()

    return {
        "schema":
            schema,
        "owner":
            owner,
        "authority_effect":
            authority_effect,
        "purpose":
            list(
                accepted_purpose
            ),
        "chain_alias":
            chain_alias,
        "opus_ready":
            True,
        "capabilities":
            list(
                prepared.get(
                    "capabilities",
                    (),
                )
            ),
        "accepted_inputs":
            list(
                prepared.get(
                    "accepts",
                    (),
                )
            ),
        "emitted_outputs":
            list(
                prepared.get(
                    "emits",
                    (),
                )
            ),
        "hooks": [],
        "flow_owner":
            "exile:segue",
        "behavior_fabricated":
            False,
        "creates_authority":
            False,
        "extension_space_reserved":
            bool(
                prepared[
                    "boundaries"
                ][
                    "extension_space_reserved"
                ]
            ),
    }


def selftest() -> dict[str, Any]:
    prepared = preparation()
    projection = status()

    extensions = prepared[
        "extensions"
    ]

    capabilities = tuple(
        prepared.get(
            "capabilities",
            (),
        )
    )

    accepts = tuple(
        prepared.get(
            "accepts",
            (),
        )
    )

    emits = tuple(
        prepared.get(
            "emits",
            (),
        )
    )

    checks = {
        "owner_preserved":
            prepared[
                "exile"
            ]
            == owner,
        "purpose_preserved":
            tuple(
                extensions[
                    "purpose"
                ]
            )
            == accepted_purpose,
        "chain_alias_preserved":
            extensions[
                "chain_alias"
            ]
            == chain_alias,
        "opus_ready_preserved":
            extensions[
                "opus_ready"
            ]
            is True,
        "no_behavior_fabricated":
            projection[
                "behavior_fabricated"
            ]
            is False,
        "no_authority_created":
            projection[
                "creates_authority"
            ]
            is False,
        "extension_space_reserved":
            projection[
                "extension_space_reserved"
            ]
            is True,
        "future_slots_preserved":
            tuple(
                extensions[
                    "future_slots"
                ]
            )
            == (
                "prodigals",
                "quirks",
                "contracts",
                "runtime_hooks",
                "chain_masks",
                "metrics",
                "tests",
            ),
        "capability_projection_exact":
            tuple(
                projection[
                    "capabilities"
                ]
            )
            == capabilities,
        "input_projection_exact":
            tuple(
                projection[
                    "accepted_inputs"
                ]
            )
            == accepts,
        "output_projection_exact":
            tuple(
                projection[
                    "emitted_outputs"
                ]
            )
            == emits,
        "no_runtime_hooks_invented":
            projection[
                "hooks"
            ]
            == [],
    }

    return {
        "schema":
            (
                "savant://runtime/underscore/"
                "exile-flow-binding-selftest/1.0.1"
            ),
        "binding_schema":
            schema,
        "ok":
            all(
                checks.values()
            ),
        "checks":
            checks,
        "prepared_projection": {
            "capabilities":
                list(
                    capabilities
                ),
            "accepts":
                list(
                    accepts
                ),
            "emits":
                list(
                    emits
                ),
        },
    }


__all__ = [
    "accepted_purpose",
    "authority_effect",
    "chain_alias",
    "owner",
    "preparation",
    "schema",
    "selftest",
    "status",
]


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

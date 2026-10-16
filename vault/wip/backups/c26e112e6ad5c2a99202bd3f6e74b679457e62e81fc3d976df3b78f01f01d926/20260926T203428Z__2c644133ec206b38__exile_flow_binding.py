from __future__ import annotations

from typing import Any, Mapping

from .execution_binding import (
    register_execution_bindings,
)

from ...segue.exile_runtime.runtime.execution.exile_flow import (
    prepare_exile,
)


schema = (
    "savant://runtime/urge/"
    "exile-flow-binding/1.0.0"
)

owner = "exile:urge"
execution_owner = "exile:opus"
flow_owner = "exile:segue"
authority_effect = "none"

capability_iterate = "exile:urge:iterate"
capability_praxis_step = "exile:urge:praxis-step"
capability_praxis_rigor = "exile:urge:praxis-rigor"

capabilities = (
    capability_iterate,
    capability_praxis_step,
    capability_praxis_rigor,
)


def preparation() -> dict[str, Any]:
    return prepare_exile(
        exile=owner,
        capabilities=capabilities,
        accepts=(),
        emits=(),
        extensions={
            "execution_owner":
                execution_owner,
            "flow_owner":
                flow_owner,
            "authority_effect":
                authority_effect,
            "terminology": {
                "praxis":
                    "one complete urge session",
                "praxi":
                    "plural of praxis",
                "rigor":
                    "one raw improvement attempt",
                "thrust":
                    (
                        "one rigor accepted by "
                        "qualification"
                    ),
            },
            "qualification": {
                "maximum_improvement_threshold_percent":
                    30,
                "rejected_rigors_become_baselines":
                    False,
                "accepted_rigors_become_thrusts":
                    True,
                "accepted_thrust_becomes_baseline":
                    True,
            },
        },
    )


def bind(
    dispatcher: Any,
) -> dict[str, Any]:
    if dispatcher is None:
        raise ValueError(
            "dispatcher is required"
        )

    register_execution_bindings(
        dispatcher
    )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "execution_owner":
            execution_owner,
        "flow_owner":
            flow_owner,
        "capabilities":
            list(
                capabilities
            ),
        "authority_effect":
            authority_effect,
        "creates_authority":
            False,
    }


def status() -> dict[str, Any]:
    prepared = preparation()

    projected_capabilities = tuple(
        prepared.get(
            "capabilities",
            (),
        )
    )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "execution_owner":
            execution_owner,
        "flow_owner":
            flow_owner,
        "authority_effect":
            authority_effect,
        "capabilities":
            list(
                capabilities
            ),
        "prepared_capabilities":
            list(
                projected_capabilities
            ),
        "praxis_term":
            "praxis",
        "praxis_plural":
            "praxi",
        "attempt_term":
            "rigor",
        "accepted_iteration_term":
            "thrust",
        "maximum_improvement_threshold_percent":
            30,
        "rejected_rigors_become_baselines":
            False,
        "accepted_rigors_become_thrusts":
            True,
        "accepted_thrust_becomes_baseline":
            True,
        "changes_execution_owner":
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

    projected_capabilities = tuple(
        prepared.get(
            "capabilities",
            (),
        )
    )

    checks = {
        "owner_preserved":
            prepared[
                "exile"
            ]
            == owner,
        "execution_owner_preserved":
            projection[
                "execution_owner"
            ]
            == "exile:opus",
        "flow_owner_preserved":
            projection[
                "flow_owner"
            ]
            == "exile:segue",
        "authority_effect_none":
            projection[
                "authority_effect"
            ]
            == "none",
        "three_verified_capabilities":
            capabilities
            == (
                "exile:urge:iterate",
                "exile:urge:praxis-step",
                "exile:urge:praxis-rigor",
            ),
        "capabilities_projected":
            all(
                capability
                in projected_capabilities
                for capability
                in capabilities
            ),
        "praxis_preserved":
            projection[
                "praxis_term"
            ]
            == "praxis",
        "praxi_preserved":
            projection[
                "praxis_plural"
            ]
            == "praxi",
        "rigor_preserved":
            projection[
                "attempt_term"
            ]
            == "rigor",
        "thrust_preserved":
            projection[
                "accepted_iteration_term"
            ]
            == "thrust",
        "threshold_bounded":
            projection[
                "maximum_improvement_threshold_percent"
            ]
            == 30,
        "rejected_rigor_not_baseline":
            projection[
                "rejected_rigors_become_baselines"
            ]
            is False,
        "accepted_rigor_becomes_thrust":
            projection[
                "accepted_rigors_become_thrusts"
            ]
            is True,
        "thrust_becomes_baseline":
            projection[
                "accepted_thrust_becomes_baseline"
            ]
            is True,
        "execution_owner_unchanged":
            projection[
                "changes_execution_owner"
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
    }

    return {
        "schema":
            (
                "savant://runtime/urge/"
                "exile-flow-binding-selftest/1.0.0"
            ),
        "binding_schema":
            schema,
        "ok":
            all(
                checks.values()
            ),
        "checks":
            checks,
    }


__all__ = [
    "bind",
    "capabilities",
    "capability_iterate",
    "capability_praxis_rigor",
    "capability_praxis_step",
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

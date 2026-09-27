#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from hypothesis import given, strategies as st


VEIL_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = VEIL_ROOT / "runtime"
NOCTURNE_ROOT = VEIL_ROOT.parents[1]
CONTRACTS_ROOT = NOCTURNE_ROOT / "contracts"

for path in (
    RUNTIME_ROOT,
    CONTRACTS_ROOT,
):
    if str(path) not in sys.path:
        sys.path.insert(
            0,
            str(path),
        )


from nocturne_contracts import (  # noqa: E402
    ExecutionMode,
    RouteRequest,
)
from veil_runtime import (  # noqa: E402
    build_plan,
    canonical_bytes,
    example_request,
    run,
    simulate_plan,
)


def test_example_request_plans_successfully() -> None:
    request = example_request()
    result = run(request)

    assert result.passed is True
    assert result.plan is not None
    assert result.plan.deterministic is True
    assert result.plan.executable is False
    assert len(result.plan.hops) == request.required_hops


def test_equal_requests_produce_equal_plans() -> None:
    request = example_request()

    first = build_plan(request)
    second = build_plan(request)

    assert canonical_bytes(first) == canonical_bytes(second)
    assert first.plan_digest == second.plan_digest


def test_simulation_is_deterministic() -> None:
    request = example_request().model_copy(
        update={
            "execution_mode": ExecutionMode.SIMULATE,
            "policy": example_request().policy.model_copy(
                update={
                    "execution_mode": ExecutionMode.SIMULATE,
                }
            ),
        }
    )

    plan = build_plan(request)

    first = simulate_plan(
        request,
        plan,
    )
    second = simulate_plan(
        request,
        plan,
    )

    assert canonical_bytes(first) == canonical_bytes(second)


def test_execute_mode_fails_closed_without_live_adapter() -> None:
    request = example_request().model_copy(
        update={
            "destination": "authorized.example.invalid",
            "execution_mode": ExecutionMode.EXECUTE,
            "policy": example_request().policy.model_copy(
                update={
                    "execution_mode": ExecutionMode.EXECUTE,
                    "network_access": True,
                    "allowed_hosts": (
                        "authorized.example.invalid",
                    ),
                }
            ),
        }
    )

    result = run(request)

    assert result.passed is False
    assert result.failure is not None
    assert result.failure.code == "veil.policy.denied"


def test_execute_mode_denies_unauthorized_destination() -> None:
    request = example_request().model_copy(
        update={
            "execution_mode": ExecutionMode.EXECUTE,
            "policy": example_request().policy.model_copy(
                update={
                    "execution_mode": ExecutionMode.EXECUTE,
                    "network_access": True,
                    "allowed_hosts": (
                        "different.example.invalid",
                    ),
                }
            ),
        }
    )

    result = run(request)

    assert result.passed is False
    assert result.failure is not None
    assert result.failure.code == "veil.policy.denied"


def test_insufficient_route_pool_fails_cleanly() -> None:
    request = example_request().model_copy(
        update={
            "required_hops": 12,
        }
    )

    result = run(request)

    assert result.passed is False
    assert result.failure is not None
    assert result.failure.code == "veil.input.invalid"
    assert result.failure.recoverable is True


@given(
    minimum=st.integers(
        min_value=0,
        max_value=5000,
    ),
    maximum=st.integers(
        min_value=0,
        max_value=5000,
    ),
)
def test_jitter_contract_rejects_inverted_ranges(
    minimum: int,
    maximum: int,
) -> None:
    value = {
        **example_request().model_dump(
            mode="json",
        ),
        "timing_jitter_ms": [
            minimum,
            maximum,
        ],
    }

    if minimum <= maximum:
        request = RouteRequest.model_validate(
            value
        )
        assert request.timing_jitter_ms == (
            minimum,
            maximum,
        )
    else:
        with pytest.raises(
            ValueError
        ):
            RouteRequest.model_validate(
                value
            )


@given(
    suffix=st.text(
        alphabet=st.characters(
            whitelist_categories=(
                "Ll",
                "Lu",
                "Nd",
            )
        ),
        min_size=1,
        max_size=24,
    )
)
def test_canonical_serialization_is_stable(
    suffix: str,
) -> None:
    request = example_request().model_copy(
        update={
            "request_id": (
                f"veil-property-{suffix}"
            ),
        }
    )

    first = canonical_bytes(
        request
    )
    decoded = json.loads(
        first
    )
    second = canonical_bytes(
        decoded
    )

    assert first == second

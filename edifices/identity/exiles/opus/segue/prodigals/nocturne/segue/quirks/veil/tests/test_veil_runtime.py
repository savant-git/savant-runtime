#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from hypothesis import (
    given,
    strategies as st,
)


SUBJECT_ROOT = Path(
    __file__
).resolve().parents[1]

RUNTIME_ROOT = (
    SUBJECT_ROOT
    / "runtime"
)

CONTRACTS_ROOT = (
    SUBJECT_ROOT
    / "contracts"
)

for path in (
    RUNTIME_ROOT,
    CONTRACTS_ROOT,
):
    if str(path) not in sys.path:
        sys.path.insert(
            0,
            str(path),
        )


from veil_contracts import (  # noqa: E402
    AuthorityState,
    VeilRequest,
)
from veil_runtime import (  # noqa: E402
    canonical_bytes,
    deterministic_projection,
    example_request,
    run,
)


def test_example_request_succeeds() -> None:
    result = run(
        example_request()
    )

    assert result.passed is True
    assert result.projection is not None
    assert (
        result.projection.subject_id
        == 'quirk.nocturne.veil'
    )


def test_equal_requests_produce_equal_result_digests() -> None:
    request = example_request()

    first = run(request)
    second = run(request)

    assert (
        first.result_digest
        == second.result_digest
    )


def test_result_preserves_provenance() -> None:
    result = run(
        example_request()
    )

    assert result.provenance.generated_by
    assert result.provenance.generated_at
    assert result.provenance.transformations


def test_projection_remains_proposed() -> None:
    result = run(
        example_request()
    )

    assert result.projection is not None
    assert (
        result.projection.authority
        == AuthorityState.PROPOSED
    )


def test_runtime_rejects_undeclared_capability() -> None:
    value = example_request().model_dump(
        mode="json"
    )

    value["policy"][
        "allowed_capabilities"
    ] = [
        "undeclared.capability"
    ]

    try:
        VeilRequest.model_validate(
            value
        )
    except ValueError:
        return

    raise AssertionError(
        "Runtime admitted an undeclared capability."
    )


def test_runtime_rejects_external_authority() -> None:
    value = example_request().model_dump(
        mode="json"
    )

    value["policy"][
        "network_access"
    ] = True

    try:
        VeilRequest.model_validate(
            value
        )
    except ValueError:
        return

    raise AssertionError(
        "Runtime admitted undeclared network authority."
    )


def test_volatile_telemetry_does_not_change_identity() -> None:
    request = example_request()

    first = run(request)
    second = run(request)

    first_value = deterministic_projection(
        first
    )
    second_value = deterministic_projection(
        second
    )

    assert (
        canonical_bytes(first_value)
        == canonical_bytes(second_value)
    )


@given(
    value=st.text(
        alphabet=st.characters(
            blacklist_categories=(
                "Cs",
            )
        ),
        min_size=1,
        max_size=200,
    )
)
def test_canonical_serialization_is_stable(
    value: str,
) -> None:
    payload = {
        "value": value,
    }

    first = canonical_bytes(
        payload
    )

    second = canonical_bytes(
        json.loads(first)
    )

    assert first == second

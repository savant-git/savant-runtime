#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from hypothesis import (
    given,
    strategies as st,
)


ADAPTER_ROOT = (
    Path(
        __file__
    )
    .resolve()
    .parents[1]
)

NOCTURNE_ROOT = (
    ADAPTER_ROOT
    .parents[1]
)

CONTRACTS_ROOT = (
    NOCTURNE_ROOT
    / "contracts"
)

for path in (
    ADAPTER_ROOT,
    CONTRACTS_ROOT,
):
    if str(
        path
    ) not in sys.path:
        sys.path.insert(
            0,
            str(
                path
            ),
        )


from opus_attachment_contracts import (  # noqa: E402
    AttachmentState,
    AuthorityBoundary,
    NocturneAttachmentRequest,
)
from opus_nocturne_adapter import (  # noqa: E402
    attach,
    canonical_bytes,
    decide,
    deterministic_projection,
    example_request,
)


def test_example_attachment_succeeds() -> None:
    result = attach(
        example_request()
    )

    assert result.passed is True
    assert (
        result.decision.admitted
        is True
    )
    assert (
        result.decision.state
        == AttachmentState.COMPLETED
    )
    assert (
        result.nocturne_result
        is not None
    )


def test_equal_requests_produce_equal_result_digests() -> None:
    request = example_request()

    first = attach(
        request
    )

    second = attach(
        request
    )

    assert (
        first.result_digest
        == second.result_digest
    )

    first_value = (
        deterministic_projection(
            first
        )
    )

    second_value = (
        deterministic_projection(
            second
        )
    )

    assert (
        canonical_bytes(
            first_value
        )
        == canonical_bytes(
            second_value
        )
    )


def test_nocturne_cannot_select_external_providers() -> None:
    value = (
        example_request()
        .model_dump(
            mode="json",
        )
    )

    value[
        "authority_boundary"
    ][
        "nocturne_may_select_external_providers"
    ] = True

    try:
        (
            NocturneAttachmentRequest
            .model_validate(
                value
            )
        )
    except ValueError:
        return

    raise AssertionError(
        "Nocturne received external "
        "provider-selection authority."
    )


def test_nocturne_cannot_read_opus_secrets() -> None:
    value = (
        example_request()
        .model_dump(
            mode="json",
        )
    )

    value[
        "authority_boundary"
    ][
        "nocturne_may_read_opus_secrets"
    ] = True

    try:
        (
            NocturneAttachmentRequest
            .model_validate(
                value
            )
        )
    except ValueError:
        return

    raise AssertionError(
        "Nocturne received Opus "
        "secret-read authority."
    )


def test_unresolved_provider_request_is_rejected() -> None:
    request = (
        example_request()
    )

    envelope = (
        request.envelope
        .model_copy(
            update={
                "provider_request": {
                    "provider": "external",
                    "operation": "invoke",
                }
            }
        )
    )

    updated = (
        request.model_copy(
            update={
                "envelope": envelope
            }
        )
    )

    decision = decide(
        updated
    )

    assert (
        decision.admitted
        is False
    )

    result = attach(
        updated
    )

    assert (
        result.passed
        is False
    )

    assert (
        result.decision.state
        == AttachmentState.REJECTED
    )


def test_forbidden_policy_flag_is_rejected() -> None:
    request = (
        example_request()
    )

    envelope = (
        request.envelope
        .model_copy(
            update={
                "policy": {
                    **request.envelope.policy,
                    "allow_nocturne_policy_bypass": True,
                }
            }
        )
    )

    result = attach(
        request.model_copy(
            update={
                "envelope": envelope
            }
        )
    )

    assert (
        result.passed
        is False
    )

    assert any(
        "allow_nocturne_policy_bypass"
        in reason
        for reason
        in result.decision.reasons
    )


def test_attachment_is_reversible() -> None:
    boundary = AuthorityBoundary()

    assert (
        boundary.reversible_attachment
        is True
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
        json.loads(
            first
        )
    )

    assert first == second

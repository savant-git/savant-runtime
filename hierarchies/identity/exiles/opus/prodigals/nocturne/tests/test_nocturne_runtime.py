#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from hypothesis import (
    given,
    strategies as st,
)


NOCTURNE_ROOT = Path(
    __file__
).resolve().parents[1]

RUNTIME_ROOT = (
    NOCTURNE_ROOT
    / "runtime"
)

CONTRACTS_ROOT = (
    NOCTURNE_ROOT
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


from nocturne_fusion_contracts import (  # noqa: E402
    NocturneRequest,
    QuirkName,
    StageState,
)
from nocturne_runtime import (  # noqa: E402
    canonical_bytes,
    compose,
    example_request,
)


def test_example_composes_successfully() -> None:
    result = compose(
        example_request()
    )

    assert result.passed is True
    assert result.partial is False
    assert result.completed_quirks == (
        QuirkName.VEIL,
    )
    assert result.failed_quirks == ()


def test_equal_requests_produce_equal_composition_digests() -> None:
    request = example_request()

    first = compose(request)
    second = compose(request)

    assert (
        first.composition_digest
        == second.composition_digest
    )

    first_value = first.model_dump(
        mode="json"
    )
    second_value = second.model_dump(
        mode="json"
    )

    first_value["metrics"].pop(
        "duration_seconds",
        None,
    )
    second_value["metrics"].pop(
        "duration_seconds",
        None,
    )

    assert (
        canonical_bytes(first_value)
        == canonical_bytes(second_value)
    )


def test_missing_optional_payload_is_skipped() -> None:
    request = example_request().model_copy(
        update={
            "policy": example_request().policy.model_copy(
                update={
                    "enabled_quirks": (
                        QuirkName.VEIL,
                        QuirkName.ECHO,
                    ),
                    "required_quirks": (
                        QuirkName.VEIL,
                    ),
                }
            )
        }
    )

    result = compose(request)

    echo_stage = next(
        stage
        for stage in result.stages
        if stage.quirk
        == QuirkName.ECHO
    )

    assert (
        echo_stage.state
        == StageState.SKIPPED
    )
    assert result.passed is True
    assert result.partial is True


def test_missing_required_payload_fails_closed() -> None:
    request = example_request().model_copy(
        update={
            "policy": example_request().policy.model_copy(
                update={
                    "enabled_quirks": (
                        QuirkName.ECHO,
                    ),
                    "required_quirks": (
                        QuirkName.ECHO,
                    ),
                }
            ),
            "veil_request": None,
            "echo_request": None,
        }
    )

    result = compose(request)

    assert result.passed is False
    assert result.failed_quirks == (
        QuirkName.ECHO,
    )


def test_stage_results_preserve_provenance() -> None:
    result = compose(
        example_request()
    )

    for stage in result.stages:
        assert stage.provenance.generated_by
        assert stage.provenance.generated_at
        assert stage.provenance.transformations


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


def test_required_quirks_must_be_enabled() -> None:
    value = example_request().model_dump(
        mode="json"
    )

    value["policy"][
        "enabled_quirks"
    ] = [
        "veil"
    ]

    value["policy"][
        "required_quirks"
    ] = [
        "echo"
    ]

    try:
        NocturneRequest.model_validate(
            value
        )
    except ValueError:
        return

    raise AssertionError(
        "Fusion policy accepted a disabled required quirk."
    )

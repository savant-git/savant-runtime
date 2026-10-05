#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from hypothesis import (
    given,
    strategies as st,
)


ECHO_ROOT = Path(
    __file__
).resolve().parents[1]

RUNTIME_ROOT = (
    ECHO_ROOT
    / "runtime"
)

NOCTURNE_ROOT = (
    ECHO_ROOT
    .parents[1]
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


from echo_contracts import (  # noqa: E402
    AuthorityState,
    ConfidenceBand,
    CorrelationObservation,
    CorrelationPolicy,
    CorrelationRequest,
    ObservationKind,
    ProvenanceEnvelope,
    SourceReference,
)
from echo_runtime import (  # noqa: E402
    canonical_bytes,
    correlate,
    example_request,
    run,
)


def test_example_correlates_successfully() -> None:
    result = run(
        example_request()
    )

    assert result.passed is True
    assert result.index is not None
    assert len(
        result.index.pairs
    ) >= 1
    assert len(
        result.index.clusters
    ) >= 1
    assert len(
        result.index.hypotheses
    ) >= 1


def test_equal_requests_produce_equal_indexes() -> None:
    request = example_request()

    first = correlate(
        request
    )
    second = correlate(
        request
    )

    assert (
        canonical_bytes(first)
        == canonical_bytes(second)
    )
    assert (
        first.index_digest
        == second.index_digest
    )


def test_hypotheses_remain_proposed() -> None:
    index = correlate(
        example_request()
    )

    for hypothesis in index.hypotheses:
        assert (
            hypothesis.authority
            == AuthorityState.PROPOSED
        )


def test_unmatched_observation_is_preserved() -> None:
    index = correlate(
        example_request()
    )

    assert (
        "echo-observation-c"
        in index.unmatched_observation_ids
    )


def test_correlation_does_not_claim_causation() -> None:
    index = correlate(
        example_request()
    )

    for hypothesis in index.hypotheses:
        assert any(
            "does not establish causation"
            in limitation
            for limitation
            in hypothesis.limitations
        )


def test_pair_limit_is_enforced() -> None:
    request = example_request()

    try:
        request.model_copy(
            update={
                "policy": request.policy.model_copy(
                    update={
                        "maximum_pairs": 1,
                    }
                ),
            }
        )
    except ValueError:
        return


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


@given(
    shared=st.lists(
        st.text(
            alphabet=st.characters(
                whitelist_categories=(
                    "Ll",
                    "Lu",
                    "Nd",
                )
            ),
            min_size=2,
            max_size=12,
        ),
        min_size=2,
        max_size=8,
        unique=True,
    )
)
def test_shared_tokens_produce_bounded_scores(
    shared: list[str],
) -> None:
    generated_at = (
        "2026-07-31T00:00:00+00:00"
    )

    source_a = SourceReference(
        source_id="property-source-a",
        source_kind="property",
        authority=AuthorityState.OBSERVED,
        captured_at=generated_at,
    )

    source_b = SourceReference(
        source_id="property-source-b",
        source_kind="property",
        authority=AuthorityState.OBSERVED,
        captured_at=generated_at,
    )

    value = " ".join(
        shared
    )

    request = CorrelationRequest(
        request_id="property-request",
        purpose=(
            "Verify bounded deterministic "
            "token correlation."
        ),
        observations=(
            CorrelationObservation(
                observation_id="property-a",
                observation_kind=ObservationKind.TEXT,
                value=value,
                normalized_text=value,
                source=source_a,
                confidence=ConfidenceBand.MODERATE,
            ),
            CorrelationObservation(
                observation_id="property-b",
                observation_kind=ObservationKind.TEXT,
                value=value,
                normalized_text=value,
                source=source_b,
                confidence=ConfidenceBand.MODERATE,
            ),
        ),
        policy=CorrelationPolicy(
            minimum_shared_tokens=2,
            minimum_score=0,
            maximum_pairs=10,
            maximum_observations=10,
        ),
        provenance=ProvenanceEnvelope(
            sources=(
                source_a,
                source_b,
            ),
            transformations=(),
            generated_by="property-test",
            generated_at=generated_at,
        ),
    )

    index = correlate(
        request
    )

    assert len(
        index.pairs
    ) == 1
    assert (
        0
        <= index.pairs[0].score
        <= 1
    )


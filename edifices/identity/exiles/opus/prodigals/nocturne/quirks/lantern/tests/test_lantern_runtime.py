#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from hypothesis import given, strategies as st


LANTERN_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = LANTERN_ROOT / "runtime"
NOCTURNE_ROOT = LANTERN_ROOT.parents[1]
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


from lantern_contracts import (  # noqa: E402
    AuthorityState,
    DiscoveryPolicy,
    DiscoveryRecord,
    DiscoveryRequest,
    DiscoverySourceKind,
    ProvenanceEnvelope,
    SourceReference,
)
from lantern_runtime import (  # noqa: E402
    build_index,
    canonical_bytes,
    example_request,
    normalize_records,
    run,
)


def test_example_request_succeeds() -> None:
    request = example_request()
    result = run(request)

    assert result.passed is True
    assert result.index is not None
    assert result.index.accepted_count == 1
    assert result.index.rejected_count == 1
    assert result.index.duplicate_count == 1


def test_equal_requests_produce_equal_indexes() -> None:
    request = example_request()

    first_normalized = normalize_records(
        request
    )
    second_normalized = normalize_records(
        request
    )

    first = build_index(
        request,
        first_normalized,
    )
    second = build_index(
        request,
        second_normalized,
    )

    assert canonical_bytes(first) == canonical_bytes(second)
    assert first.index_digest == second.index_digest


def test_non_onion_location_is_rejected() -> None:
    request = example_request()
    normalized = normalize_records(
        request
    )

    rejected = [
        item
        for item in normalized
        if item.rejection_reasons
    ]

    assert len(rejected) == 1
    assert (
        "non_onion_host_forbidden"
        in rejected[0].rejection_reasons
    )


def test_embedded_credentials_are_rejected() -> None:
    generated_at = "2026-07-31T00:00:00+00:00"

    source = SourceReference(
        source_id="credential-test",
        source_kind=DiscoverySourceKind.MANUAL,
        authority=AuthorityState.OBSERVED,
        captured_at=generated_at,
    )

    host = (
        "b" * 56
        + ".onion"
    )

    request = DiscoveryRequest(
        request_id="credential-test",
        purpose=(
            "Verify rejection of embedded credentials."
        ),
        records=(
            DiscoveryRecord(
                record_id="credential-record",
                location=(
                    f"http://user:pass@{host}/"
                ),
                source=source,
            ),
        ),
        policy=DiscoveryPolicy(
            network_access=False,
            reject_credentials=True,
        ),
        provenance=ProvenanceEnvelope(
            sources=(
                source,
            ),
            transformations=(),
            generated_by="test",
            generated_at=generated_at,
        ),
    )

    result = run(request)

    assert result.passed is True
    assert result.normalized[0].normalized_location is None
    assert (
        "embedded_credentials_forbidden"
        in result.normalized[0].rejection_reasons
    )


def test_network_access_cannot_be_enabled() -> None:
    try:
        DiscoveryPolicy(
            network_access=True,
        )
    except ValueError:
        return

    raise AssertionError(
        "Lantern permitted network access."
    )


@given(
    path_component=st.text(
        alphabet=st.characters(
            whitelist_categories=(
                "Ll",
                "Lu",
                "Nd",
            )
        ),
        min_size=1,
        max_size=32,
    )
)
def test_canonical_serialization_is_stable(
    path_component: str,
) -> None:
    request = example_request()

    first = canonical_bytes(
        request
    )

    decoded = json.loads(
        first
    )

    decoded["purpose"] = (
        f"Stable serialization {path_component}"
    )

    second = canonical_bytes(
        decoded
    )

    third = canonical_bytes(
        json.loads(second)
    )

    assert second == third


@given(
    duplicate_count=st.integers(
        min_value=1,
        max_value=20,
    )
)
def test_duplicate_count_is_deterministic(
    duplicate_count: int,
) -> None:
    generated_at = "2026-07-31T00:00:00+00:00"

    host = (
        "c" * 56
        + ".onion"
    )

    records = []

    for index in range(
        duplicate_count
    ):
        source = SourceReference(
            source_id=(
                f"duplicate-source-{index}"
            ),
            source_kind=DiscoverySourceKind.MANUAL,
            authority=AuthorityState.OBSERVED,
            captured_at=generated_at,
        )

        records.append(
            DiscoveryRecord(
                record_id=(
                    f"duplicate-record-{index}"
                ),
                location=host,
                source=source,
            )
        )

    request = DiscoveryRequest(
        request_id="duplicate-property",
        purpose=(
            "Verify deterministic duplicate aggregation."
        ),
        records=tuple(records),
        policy=DiscoveryPolicy(
            network_access=False,
            deduplicate=True,
        ),
        provenance=ProvenanceEnvelope(
            sources=tuple(
                record.source
                for record in records
            ),
            transformations=(),
            generated_by="test",
            generated_at=generated_at,
        ),
    )

    result = run(request)

    assert result.passed is True
    assert result.index is not None
    assert result.index.accepted_count == 1
    assert (
        result.index.duplicate_count
        == duplicate_count - 1
    )

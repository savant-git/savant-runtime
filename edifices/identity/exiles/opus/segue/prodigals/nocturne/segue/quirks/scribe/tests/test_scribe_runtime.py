#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from hypothesis import given, strategies as st


SCRIBE_ROOT = Path(
    __file__
).resolve().parents[1]

RUNTIME_ROOT = (
    SCRIBE_ROOT
    / "runtime"
)

NOCTURNE_ROOT = (
    SCRIBE_ROOT
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


from scribe_contracts import (  # noqa: E402
    AuthorityState,
    ExtractionPolicy,
    ExtractionRequest,
    ProvenanceEnvelope,
    SourceDocument,
    SourceFormat,
    SourceReference,
)
from scribe_runtime import (  # noqa: E402
    canonical_bytes,
    example_request,
    extract,
    run,
)


def test_example_extracts_successfully() -> None:
    result = run(
        example_request()
    )

    assert result.passed is True
    assert result.index is not None
    assert result.index.source_format == SourceFormat.MARKDOWN
    assert result.index.observation_count >= 3


def test_equal_requests_produce_equal_indexes() -> None:
    request = example_request()

    first = extract(
        request
    )
    second = extract(
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


def test_source_spans_are_bounded() -> None:
    request = example_request()
    index = extract(
        request
    )

    length = len(
        request.document.content
    )

    for item in index.observations:
        assert (
            0
            <= item.source_span.start
            <= item.source_span.end
            <= length
        )


def test_json_scalars_are_extracted() -> None:
    generated_at = (
        "2026-07-31T00:00:00+00:00"
    )
    content = '{"name":"Nocturne","active":true,"count":4}'

    source = SourceReference(
        source_id="json-source",
        source_sha256=__import__(
            "hashlib"
        ).sha256(
            content.encode("utf-8")
        ).hexdigest(),
        authority=AuthorityState.OBSERVED,
        captured_at=generated_at,
    )

    request = ExtractionRequest(
        request_id="json-request",
        purpose=(
            "Verify deterministic JSON scalar extraction."
        ),
        document=SourceDocument(
            document_id="json-document",
            content=content,
            declared_format=SourceFormat.JSON,
            source=source,
        ),
        policy=ExtractionPolicy(),
        provenance=ProvenanceEnvelope(
            sources=(
                source,
            ),
            transformations=(),
            generated_by="test",
            generated_at=generated_at,
        ),
    )

    index = extract(
        request
    )

    assert index.observation_count == 3

    paths = {
        item.metadata["json_path"]
        for item in index.observations
    }

    assert paths == {
        "$.active",
        "$.count",
        "$.name",
    }


def test_disallowed_format_fails_closed() -> None:
    request = example_request().model_copy(
        update={
            "policy": ExtractionPolicy(
                allowed_formats=(
                    SourceFormat.TEXT,
                ),
            )
        }
    )

    result = run(
        request
    )

    assert result.passed is False
    assert result.failure is not None


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
    document = {
        "value": value,
    }

    first = canonical_bytes(
        document
    )
    second = canonical_bytes(
        json.loads(first)
    )

    assert first == second


@given(
    heading=st.text(
        alphabet=st.characters(
            whitelist_categories=(
                "Ll",
                "Lu",
                "Nd",
            )
        ),
        min_size=1,
        max_size=50,
    )
)
def test_heading_extraction_preserves_value(
    heading: str,
) -> None:
    request = example_request()
    content = f"# {heading}\n"

    source = request.document.source.model_copy(
        update={
            "source_sha256": __import__(
                "hashlib"
            ).sha256(
                content.encode("utf-8")
            ).hexdigest(),
        }
    )

    updated = request.model_copy(
        update={
            "document": request.document.model_copy(
                update={
                    "content": content,
                    "source": source,
                }
            ),
        }
    )

    index = extract(
        updated
    )

    headings = [
        item
        for item in index.observations
        if item.observation_kind == "heading"
    ]

    assert len(headings) == 1
    assert headings[0].value == heading

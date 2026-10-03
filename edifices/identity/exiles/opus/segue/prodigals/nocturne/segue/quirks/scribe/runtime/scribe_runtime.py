#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Iterable


NOCTURNE_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_ROOT = NOCTURNE_ROOT / "contracts"

if str(CONTRACTS_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(CONTRACTS_ROOT),
    )

from scribe_contracts import (  # noqa: E402
    AuthorityState,
    ConfidenceBand,
    ExtractedObservation,
    ExtractionIndex,
    ExtractionRequest,
    ExtractionPolicy,
    FailureRecord,
    ProvenanceEnvelope,
    ScribeResult,
    SourceDocument,
    SourceFormat,
    SourceReference,
    SourceSpan,
)


RUNTIME_ID = "quirk.nocturne.scribe.runtime"
RUNTIME_VERSION = "1.0.0"

HEADING_PATTERN = re.compile(
    r"^(#{1,6})[ \t]+(.+?)\s*$"
)

MARKDOWN_LINK_PATTERN = re.compile(
    r"\[([^\]]+)\]\(([^)\s]+)\)"
)

HTML_TAG_PATTERN = re.compile(
    r"<[^>]+>"
)

HTML_LINK_PATTERN = re.compile(
    r"""<a\b[^>]*\bhref=["']([^"']+)["'][^>]*>(.*?)</a>""",
    re.IGNORECASE | re.DOTALL,
)


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def canonical_bytes(
    value: Any,
) -> bytes:
    if hasattr(value, "model_dump"):
        value = value.model_dump(
            mode="json",
        )

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(value)
    ).hexdigest()


def build_provenance(
    request: ExtractionRequest,
    *,
    transformations: Iterable[str] = (),
) -> ProvenanceEnvelope:
    sources = list(
        request.provenance.sources
    )

    if request.document.source not in sources:
        sources.append(
            request.document.source
        )

    return ProvenanceEnvelope(
        sources=tuple(sources),
        transformations=tuple(transformations),
        generated_by=f"{RUNTIME_ID}@{RUNTIME_VERSION}",
        generated_at=request.provenance.generated_at,
    )


def detect_format(
    document: SourceDocument,
) -> SourceFormat:
    if document.declared_format != SourceFormat.UNKNOWN:
        return document.declared_format

    content = document.content.lstrip()

    if content.startswith(
        ("{", "[")
    ):
        try:
            json.loads(content)
            return SourceFormat.JSON
        except json.JSONDecodeError:
            pass

    if re.search(
        r"<(?:html|body|p|h[1-6]|a)\b",
        content,
        re.IGNORECASE,
    ):
        return SourceFormat.HTML

    if any(
        HEADING_PATTERN.match(line)
        for line in content.splitlines()
    ):
        return SourceFormat.MARKDOWN

    return SourceFormat.TEXT


def line_number_at(
    content: str,
    offset: int,
) -> int:
    return content.count(
        "\n",
        0,
        offset,
    ) + 1


def source_span(
    content: str,
    start: int,
    end: int,
) -> SourceSpan:
    return SourceSpan(
        start=start,
        end=end,
        line_start=line_number_at(
            content,
            start,
        ),
        line_end=line_number_at(
            content,
            max(start, end - 1),
        ),
    )


def normalize_text(
    value: str,
    policy: ExtractionPolicy,
) -> str:
    if not policy.normalize_whitespace:
        return value

    return " ".join(
        value.split()
    )


def observation(
    request: ExtractionRequest,
    *,
    kind: str,
    value: Any,
    start: int,
    end: int,
    normalized_text: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ExtractedObservation:
    basis = {
        "request_id": request.request_id,
        "kind": kind,
        "value": value,
        "start": start,
        "end": end,
    }

    return ExtractedObservation(
        observation_id=(
            f"scribe-observation-{digest(basis)[:20]}"
        ),
        observation_kind=kind,
        value=value,
        normalized_text=normalized_text,
        source_span=source_span(
            request.document.content,
            start,
            end,
        ),
        confidence=ConfidenceBand.MODERATE,
        authority=AuthorityState.OBSERVED,
        metadata=metadata or {},
        provenance=build_provenance(
            request,
            transformations=(
                f"extract_{kind}",
                "preserve_source_span",
            ),
        ),
    )


def extract_text(
    request: ExtractionRequest,
) -> list[ExtractedObservation]:
    content = request.document.content
    observations: list[ExtractedObservation] = []

    for match in re.finditer(
        r"\S(?:.*?\S)?(?=\n\s*\n|\Z)",
        content,
        re.DOTALL,
    ):
        raw = match.group(0)

        if not raw.strip():
            continue

        observations.append(
            observation(
                request,
                kind="paragraph",
                value=raw,
                normalized_text=normalize_text(
                    raw,
                    request.policy,
                ),
                start=match.start(),
                end=match.end(),
            )
        )

    return observations


def extract_markdown(
    request: ExtractionRequest,
) -> list[ExtractedObservation]:
    content = request.document.content
    observations = extract_text(
        request
    )

    if request.policy.extract_headings:
        offset = 0

        for line in content.splitlines(
            keepends=True
        ):
            stripped = line.rstrip(
                "\r\n"
            )

            match = HEADING_PATTERN.match(
                stripped
            )

            if match:
                title = match.group(2)
                observations.append(
                    observation(
                        request,
                        kind="heading",
                        value=title,
                        normalized_text=normalize_text(
                            title,
                            request.policy,
                        ),
                        start=offset,
                        end=offset + len(
                            stripped
                        ),
                        metadata={
                            "level": len(
                                match.group(1)
                            ),
                        },
                    )
                )

            offset += len(line)

    if request.policy.extract_links:
        for match in MARKDOWN_LINK_PATTERN.finditer(
            content
        ):
            observations.append(
                observation(
                    request,
                    kind="link",
                    value={
                        "label": match.group(1),
                        "target": match.group(2),
                    },
                    normalized_text=match.group(2),
                    start=match.start(),
                    end=match.end(),
                )
            )

    return observations


def extract_html(
    request: ExtractionRequest,
) -> list[ExtractedObservation]:
    content = request.document.content
    observations: list[ExtractedObservation] = []

    if request.policy.extract_headings:
        for match in re.finditer(
            r"<h([1-6])\b[^>]*>(.*?)</h\1>",
            content,
            re.IGNORECASE | re.DOTALL,
        ):
            raw = HTML_TAG_PATTERN.sub(
                "",
                match.group(2),
            )
            value = html.unescape(
                raw
            )

            observations.append(
                observation(
                    request,
                    kind="heading",
                    value=value,
                    normalized_text=normalize_text(
                        value,
                        request.policy,
                    ),
                    start=match.start(),
                    end=match.end(),
                    metadata={
                        "level": int(
                            match.group(1)
                        ),
                    },
                )
            )

    for match in re.finditer(
        r"<p\b[^>]*>(.*?)</p>",
        content,
        re.IGNORECASE | re.DOTALL,
    ):
        raw = HTML_TAG_PATTERN.sub(
            "",
            match.group(1),
        )
        value = html.unescape(
            raw
        )

        observations.append(
            observation(
                request,
                kind="paragraph",
                value=value,
                normalized_text=normalize_text(
                    value,
                    request.policy,
                ),
                start=match.start(),
                end=match.end(),
            )
        )

    if request.policy.extract_links:
        for match in HTML_LINK_PATTERN.finditer(
            content
        ):
            label = html.unescape(
                HTML_TAG_PATTERN.sub(
                    "",
                    match.group(2),
                )
            )

            observations.append(
                observation(
                    request,
                    kind="link",
                    value={
                        "label": label,
                        "target": match.group(1),
                    },
                    normalized_text=match.group(1),
                    start=match.start(),
                    end=match.end(),
                )
            )

    if not observations:
        plain = html.unescape(
            HTML_TAG_PATTERN.sub(
                " ",
                content,
            )
        )

        observations.append(
            observation(
                request,
                kind="text",
                value=plain,
                normalized_text=normalize_text(
                    plain,
                    request.policy,
                ),
                start=0,
                end=len(content),
            )
        )

    return observations


def iter_json_scalars(
    value: Any,
    path: str = "$",
) -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key in sorted(value):
            yield from iter_json_scalars(
                value[key],
                f"{path}.{key}",
            )

    elif isinstance(value, list):
        for index, child in enumerate(
            value
        ):
            yield from iter_json_scalars(
                child,
                f"{path}[{index}]",
            )

    else:
        yield path, value


def extract_json(
    request: ExtractionRequest,
) -> list[ExtractedObservation]:
    content = request.document.content
    parsed = json.loads(
        content
    )

    observations: list[ExtractedObservation] = []

    if not request.policy.extract_json_scalars:
        return observations

    search_offset = 0

    for path, value in iter_json_scalars(
        parsed
    ):
        encoded = json.dumps(
            value,
            ensure_ascii=False,
        )

        offset = content.find(
            encoded,
            search_offset,
        )

        if offset < 0:
            offset = 0
            end = len(content)
        else:
            end = offset + len(encoded)
            search_offset = end

        observations.append(
            observation(
                request,
                kind="json_scalar",
                value=value,
                normalized_text=(
                    str(value)
                    if value is not None
                    else "null"
                ),
                start=offset,
                end=end,
                metadata={
                    "json_path": path,
                },
            )
        )

    return observations


def extract(
    request: ExtractionRequest,
) -> ExtractionIndex:
    source_format = detect_format(
        request.document
    )

    if source_format not in request.policy.allowed_formats:
        raise ValueError(
            f"Source format is not allowed: {source_format.value}"
        )

    extractors = {
        SourceFormat.TEXT: extract_text,
        SourceFormat.MARKDOWN: extract_markdown,
        SourceFormat.HTML: extract_html,
        SourceFormat.JSON: extract_json,
    }

    extractor = extractors.get(
        source_format
    )

    if extractor is None:
        raise ValueError(
            f"Unsupported source format: {source_format.value}"
        )

    observations = extractor(
        request
    )

    observations = sorted(
        observations,
        key=lambda item: (
            item.source_span.start,
            item.source_span.end,
            item.observation_kind,
            item.observation_id,
        ),
    )

    if (
        len(observations)
        > request.policy.maximum_observations
    ):
        raise ValueError(
            "Extraction exceeded maximum_observations."
        )

    body = {
        "request_id": request.request_id,
        "source_format": source_format.value,
        "observations": [
            item.model_dump(
                mode="json",
            )
            for item in observations
        ],
    }

    index_digest = digest(
        body
    )

    return ExtractionIndex(
        index_id=(
            f"scribe-index-{index_digest[:20]}"
        ),
        request_id=request.request_id,
        source_format=source_format,
        observations=tuple(
            observations
        ),
        observation_count=len(
            observations
        ),
        deterministic=True,
        index_digest=index_digest,
        provenance=build_provenance(
            request,
            transformations=(
                "detect_source_format",
                f"extract_{source_format.value}",
                "sort_observations_by_source_span",
                "build_deterministic_extraction_index",
            ),
        ),
    )


def run(
    request: ExtractionRequest,
) -> ScribeResult:
    started = time.perf_counter()

    try:
        index = extract(
            request
        )

        return ScribeResult(
            operation="extract",
            passed=True,
            request_id=request.request_id,
            index=index,
            metrics={
                "duration_seconds": (
                    time.perf_counter()
                    - started
                ),
                "input_bytes": len(
                    request.document.content.encode(
                        "utf-8"
                    )
                ),
                "observation_count": (
                    index.observation_count
                ),
                "source_format": (
                    index.source_format.value
                ),
                "passed": True,
            },
            provenance=build_provenance(
                request,
                transformations=(
                    "extract_source_document",
                    "emit_contract_valid_result",
                ),
            ),
        )

    except Exception as exc:
        envelope = build_provenance(
            request,
            transformations=(
                "capture_failure",
            ),
        )

        failure = FailureRecord(
            failure_id=(
                "scribe-failure-"
                + digest(
                    [
                        request.request_id,
                        type(exc).__name__,
                        str(exc),
                    ]
                )[:20]
            ),
            code="scribe.runtime.failure",
            message=str(exc),
            recoverable=True,
            retryable=False,
            stage="extract",
            details={
                "exception_type": (
                    type(exc).__name__
                ),
            },
            provenance=envelope,
        )

        return ScribeResult(
            operation="extract",
            passed=False,
            request_id=request.request_id,
            failure=failure,
            metrics={
                "duration_seconds": (
                    time.perf_counter()
                    - started
                ),
                "passed": False,
            },
            provenance=envelope,
        )


def example_request() -> ExtractionRequest:
    generated_at = (
        "2026-07-31T00:00:00+00:00"
    )

    content = """# Nocturne

Nocturne composes Veil, Lantern, Scribe, and Echo.

[Authority](savant://authority/nocturne)
"""

    source = SourceReference(
        source_id="scribe-example-source",
        source_sha256=hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest(),
        authority=AuthorityState.OBSERVED,
        captured_at=generated_at,
    )

    return ExtractionRequest(
        request_id="scribe-example-request",
        purpose=(
            "Demonstrate deterministic Markdown extraction "
            "with exact source-span provenance."
        ),
        document=SourceDocument(
            document_id="scribe-example-document",
            content=content,
            declared_format=SourceFormat.MARKDOWN,
            source=source,
        ),
        policy=ExtractionPolicy(),
        provenance=ProvenanceEnvelope(
            sources=(
                source,
            ),
            transformations=(),
            generated_by="scribe-example",
            generated_at=generated_at,
        ),
    )


def load_request(
    path: Path | None,
) -> ExtractionRequest:
    if path is None:
        raw = sys.stdin.read()
    else:
        raw = path.read_text(
            encoding="utf-8"
        )

    return ExtractionRequest.model_validate_json(
        raw
    )


def write_result(
    result: ScribeResult,
    output: Path | None,
) -> None:
    rendered = json.dumps(
        result.model_dump(
            mode="json",
        ),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"

    if output is None:
        print(
            rendered,
            end="",
        )
        return

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output.write_text(
        rendered,
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Scribe deterministic source extractor."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    run_parser = subparsers.add_parser(
        "run"
    )
    run_parser.add_argument(
        "--input",
        type=Path,
    )
    run_parser.add_argument(
        "--output",
        type=Path,
    )

    example_parser = subparsers.add_parser(
        "example"
    )
    example_parser.add_argument(
        "--output",
        type=Path,
    )

    subparsers.add_parser(
        "schema"
    )

    args = parser.parse_args()

    if args.command == "run":
        result = run(
            load_request(
                args.input
            )
        )
        write_result(
            result,
            args.output,
        )
        return (
            0
            if result.passed
            else 1
        )

    if args.command == "example":
        request = example_request()

        rendered = json.dumps(
            request.model_dump(
                mode="json",
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"

        if args.output is None:
            print(
                rendered,
                end="",
            )
        else:
            args.output.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            args.output.write_text(
                rendered,
                encoding="utf-8",
            )

        return 0

    if args.command == "schema":
        print(
            json.dumps(
                {
                    "extraction_request": (
                        ExtractionRequest
                        .model_json_schema()
                    ),
                    "extraction_index": (
                        ExtractionIndex
                        .model_json_schema()
                    ),
                    "scribe_result": (
                        ScribeResult
                        .model_json_schema()
                    ),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

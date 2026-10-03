#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit


NOCTURNE_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_ROOT = NOCTURNE_ROOT / "contracts"

if str(CONTRACTS_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTRACTS_ROOT))

from lantern_contracts import (  # noqa: E402
    AuthorityState,
    ConfidenceBand,
    DiscoveryPolicy,
    DiscoveryRecord,
    DiscoveryRequest,
    DiscoverySourceKind,
    FailureRecord,
    LanternResult,
    LocationIndex,
    LocationIndexEntry,
    LocationState,
    NormalizedLocation,
    ProvenanceEnvelope,
    SourceReference,
)


RUNTIME_ID = "quirk.nocturne.lantern.runtime"
RUNTIME_VERSION = "1.0.1"

ONION_V3_PATTERN = re.compile(
    r"^[a-z2-7]{56}\.onion$",
    re.IGNORECASE,
)

SCHEME_PATTERN = re.compile(
    r"^[a-z][a-z0-9+.-]*://",
    re.IGNORECASE,
)


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def canonical_bytes(value: Any) -> bytes:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_bytes(value)
    ).hexdigest()


def build_provenance(
    request: DiscoveryRequest,
    *,
    sources: Iterable[SourceReference] = (),
    transformations: Iterable[str] = (),
) -> ProvenanceEnvelope:
    merged: list[SourceReference] = list(
        request.provenance.sources
    )

    for source in sources:
        if source not in merged:
            merged.append(source)

    return ProvenanceEnvelope(
        sources=tuple(merged),
        transformations=tuple(transformations),
        generated_by=f"{RUNTIME_ID}@{RUNTIME_VERSION}",
        generated_at=request.provenance.generated_at,
    )


def prepare_location(value: str) -> str:
    candidate = value.strip()

    if not candidate:
        raise ValueError("Location is empty.")

    if any(character.isspace() for character in candidate):
        raise ValueError("Location contains whitespace.")

    if not SCHEME_PATTERN.match(candidate):
        candidate = f"http://{candidate}"

    return candidate


def normalize_location(
    request: DiscoveryRequest,
    record: DiscoveryRecord,
) -> NormalizedLocation:
    reasons: list[str] = []
    normalized_location: str | None = None
    host: str | None = None
    port: int | None = None
    path = "/"

    try:
        candidate = prepare_location(record.location)
        parsed = urlsplit(candidate)

        if (
            request.policy.reject_credentials
            and (
                parsed.username is not None
                or parsed.password is not None
            )
        ):
            reasons.append(
                "embedded_credentials_forbidden"
            )

        host = (
            parsed.hostname.lower()
            if parsed.hostname
            else None
        )

        if host is None:
            reasons.append("host_missing")

        elif host.endswith(".onion"):
            if not ONION_V3_PATTERN.fullmatch(host):
                reasons.append(
                    "invalid_onion_v3_host"
                )

        elif not request.policy.allow_non_onion_hosts:
            reasons.append(
                "non_onion_host_forbidden"
            )

        try:
            port = parsed.port
        except ValueError:
            reasons.append("invalid_port")

        if (
            parsed.query
            and not request.policy.allow_query_strings
        ):
            reasons.append(
                "query_string_forbidden"
            )

        if (
            parsed.fragment
            and not request.policy.allow_fragments
        ):
            reasons.append(
                "fragment_forbidden"
            )

        path = parsed.path or "/"

        if not path.startswith("/"):
            path = f"/{path}"

        if not reasons and host is not None:
            netloc = host

            if port is not None:
                netloc = f"{host}:{port}"

            normalized_location = urlunsplit(
                (
                    "http",
                    netloc,
                    path,
                    (
                        parsed.query
                        if request.policy.allow_query_strings
                        else ""
                    ),
                    (
                        parsed.fragment
                        if request.policy.allow_fragments
                        else ""
                    ),
                )
            )

    except Exception as exc:
        reasons.append(
            f"parse_failure:{type(exc).__name__}"
        )

    accepted = not reasons

    basis = (
        normalized_location
        or record.location.strip()
        or record.record_id
    )

    return NormalizedLocation(
        location_id=(
            f"lantern-location-{digest(basis)[:20]}"
        ),
        original_location=record.location,
        normalized_location=normalized_location,
        host=host,
        port=port,
        path=path,
        state=(
            LocationState.NORMALIZED
            if accepted
            else LocationState.REJECTED
        ),
        confidence=(
            ConfidenceBand.MODERATE
            if accepted
            else ConfidenceBand.LOW
        ),
        rejection_reasons=tuple(
            sorted(set(reasons))
        ),
        labels=tuple(
            sorted(set(record.labels))
        ),
        source=record.source,
        provenance=build_provenance(
            request,
            sources=(record.source,),
            transformations=(
                "strip_location",
                "apply_default_scheme",
                "parse_location",
                "validate_credentials",
                "validate_host",
                "normalize_location",
            ),
        ),
    )


def normalize_records(
    request: DiscoveryRequest,
) -> tuple[NormalizedLocation, ...]:
    values = [
        normalize_location(request, record)
        for record in request.records
    ]

    return tuple(
        sorted(
            values,
            key=lambda item: (
                item.normalized_location or "",
                item.source.source_id,
                item.original_location,
            ),
        )
    )


def build_index(
    request: DiscoveryRequest,
    normalized: tuple[NormalizedLocation, ...],
) -> LocationIndex:
    groups: dict[
        str,
        list[NormalizedLocation],
    ] = defaultdict(list)

    rejected_count = 0

    for location in normalized:
        if (
            location.state != LocationState.NORMALIZED
            or location.normalized_location is None
            or location.host is None
        ):
            rejected_count += 1
            continue

        groups[
            location.normalized_location
        ].append(location)

    entries: list[LocationIndexEntry] = []
    duplicate_count = 0

    for normalized_location in sorted(groups):
        observations = groups[normalized_location]
        first = observations[0]

        duplicate_count += max(
            0,
            len(observations) - 1,
        )

        labels = tuple(
            sorted(
                {
                    label
                    for observation in observations
                    for label in observation.labels
                }
            )
        )

        source_ids = tuple(
            sorted(
                {
                    observation.source.source_id
                    for observation in observations
                }
            )
        )

        entries.append(
            LocationIndexEntry(
                location_id=first.location_id,
                normalized_location=normalized_location,
                host=first.host,
                port=first.port,
                path=first.path or "/",
                labels=labels,
                source_record_ids=source_ids,
                observation_count=len(observations),
                confidence=(
                    ConfidenceBand.HIGH
                    if len(observations) > 1
                    else ConfidenceBand.MODERATE
                ),
                provenance=build_provenance(
                    request,
                    sources=tuple(
                        observation.source
                        for observation in observations
                    ),
                    transformations=(
                        "group_equal_normalized_locations",
                        "merge_labels",
                        "merge_source_references",
                        "calculate_observation_confidence",
                    ),
                ),
            )
        )

    body = {
        "request_id": request.request_id,
        "entries": [
            entry.model_dump(mode="json")
            for entry in entries
        ],
        "accepted_count": len(entries),
        "rejected_count": rejected_count,
        "duplicate_count": duplicate_count,
    }

    index_digest = digest(body)

    return LocationIndex(
        index_id=(
            f"lantern-index-{index_digest[:20]}"
        ),
        request_id=request.request_id,
        entries=tuple(entries),
        accepted_count=len(entries),
        rejected_count=rejected_count,
        duplicate_count=duplicate_count,
        deterministic=True,
        index_digest=index_digest,
        provenance=build_provenance(
            request,
            transformations=(
                "build_deterministic_location_index",
                "preserve_source_provenance",
            ),
        ),
    )


def failure_result(
    request: DiscoveryRequest,
    exc: Exception,
    started: float,
) -> LanternResult:
    elapsed = time.perf_counter() - started

    envelope = build_provenance(
        request,
        transformations=(
            "capture_failure",
        ),
    )

    failure = FailureRecord(
        failure_id=(
            "lantern-failure-"
            + digest(
                [
                    request.request_id,
                    type(exc).__name__,
                    str(exc),
                ]
            )[:20]
        ),
        code="lantern.runtime.failure",
        message=str(exc),
        recoverable=True,
        retryable=False,
        stage="index",
        details={
            "exception_type": type(exc).__name__,
        },
        provenance=envelope,
    )

    return LanternResult(
        operation="index",
        passed=False,
        request_id=request.request_id,
        failure=failure,
        metrics={
            "duration_seconds": elapsed,
            "passed": False,
        },
        provenance=envelope,
    )


def run(
    request: DiscoveryRequest,
) -> LanternResult:
    started = time.perf_counter()

    try:
        normalized = normalize_records(request)
        index = build_index(
            request,
            normalized,
        )

        return LanternResult(
            operation="index",
            passed=True,
            request_id=request.request_id,
            normalized=normalized,
            index=index,
            metrics={
                "duration_seconds": (
                    time.perf_counter() - started
                ),
                "input_count": len(request.records),
                "accepted_count": index.accepted_count,
                "rejected_count": index.rejected_count,
                "duplicate_count": index.duplicate_count,
                "passed": True,
            },
            provenance=build_provenance(
                request,
                transformations=(
                    "normalize_discovery_records",
                    "build_location_index",
                    "emit_contract_valid_result",
                ),
            ),
        )

    except Exception as exc:
        return failure_result(
            request,
            exc,
            started,
        )


def example_request() -> DiscoveryRequest:
    generated_at = "2026-07-31T00:00:00+00:00"

    source_a = SourceReference(
        source_id="lantern-example-source-a",
        source_kind=DiscoverySourceKind.MANUAL,
        authority=AuthorityState.OBSERVED,
        captured_at=generated_at,
    )

    source_b = SourceReference(
        source_id="lantern-example-source-b",
        source_kind=DiscoverySourceKind.MANUAL,
        authority=AuthorityState.OBSERVED,
        captured_at=generated_at,
    )

    valid_host = f"{'a' * 56}.onion"

    return DiscoveryRequest(
        request_id="lantern-example-request",
        purpose=(
            "Demonstrate deterministic offline "
            "location normalization and indexing."
        ),
        records=(
            DiscoveryRecord(
                record_id="record-a",
                location=valid_host,
                source=source_a,
                title="Example observation",
                labels=(
                    "example",
                    "offline",
                ),
            ),
            DiscoveryRecord(
                record_id="record-b",
                location=f"http://{valid_host}/",
                source=source_b,
                title="Duplicate observation",
                labels=("duplicate",),
            ),
            DiscoveryRecord(
                record_id="record-c",
                location="https://example.com/",
                source=source_a,
                title="Rejected non-onion example",
            ),
        ),
        policy=DiscoveryPolicy(
            network_access=False,
            allow_non_onion_hosts=False,
            allow_query_strings=False,
            allow_fragments=False,
            maximum_records=100,
            reject_credentials=True,
            deduplicate=True,
            preserve_original=True,
            audit_required=True,
        ),
        provenance=ProvenanceEnvelope(
            sources=(
                source_a,
                source_b,
            ),
            transformations=(),
            generated_by="lantern-example",
            generated_at=generated_at,
        ),
    )


def load_request(
    path: Path | None,
) -> DiscoveryRequest:
    if path is None:
        raw = sys.stdin.read()
    else:
        raw = path.read_text(
            encoding="utf-8"
        )

    return DiscoveryRequest.model_validate_json(
        raw
    )


def write_result(
    result: LanternResult,
    output: Path | None,
) -> None:
    rendered = json.dumps(
        result.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"

    if output is None:
        print(rendered, end="")
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
            "Lantern deterministic offline "
            "location normalizer and indexer."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    run_parser = subparsers.add_parser("run")
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

    subparsers.add_parser("schema")

    args = parser.parse_args()

    if args.command == "run":
        result = run(
            load_request(args.input)
        )
        write_result(
            result,
            args.output,
        )
        return 0 if result.passed else 1

    if args.command == "example":
        request = example_request()

        rendered = json.dumps(
            request.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"

        if args.output is None:
            print(rendered, end="")
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
                    "discovery_request": (
                        DiscoveryRequest.model_json_schema()
                    ),
                    "normalized_location": (
                        NormalizedLocation.model_json_schema()
                    ),
                    "location_index": (
                        LocationIndex.model_json_schema()
                    ),
                    "lantern_result": (
                        LanternResult.model_json_schema()
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
    raise SystemExit(main())

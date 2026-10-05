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
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable


NOCTURNE_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_ROOT = NOCTURNE_ROOT / "contracts"

if str(CONTRACTS_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(CONTRACTS_ROOT),
    )

from echo_contracts import (  # noqa: E402
    AuthorityState,
    ConfidenceBand,
    CorrelationCluster,
    CorrelationEvidence,
    CorrelationIndex,
    CorrelationKind,
    CorrelationObservation,
    CorrelationPair,
    CorrelationPolicy,
    CorrelationRequest,
    EchoResult,
    FailureRecord,
    ObservationKind,
    ProvenanceEnvelope,
    SourceReference,
    ThreatHypothesis,
)


RUNTIME_ID = "quirk.nocturne.echo.runtime"
RUNTIME_VERSION = "1.0.0"

TOKEN_PATTERN = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{1,127}"
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
    request: CorrelationRequest,
    *,
    sources: Iterable[SourceReference] = (),
    transformations: Iterable[str] = (),
) -> ProvenanceEnvelope:
    merged = list(
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


def normalized_value(
    observation: CorrelationObservation,
    policy: CorrelationPolicy,
) -> str:
    if observation.normalized_text is not None:
        value = observation.normalized_text
    elif isinstance(observation.value, str):
        value = observation.value
    else:
        value = json.dumps(
            observation.value,
            ensure_ascii=False,
            sort_keys=True,
        )

    value = " ".join(
        value.split()
    )

    if not policy.case_sensitive:
        value = value.lower()

    return value


def tokens(
    observation: CorrelationObservation,
    policy: CorrelationPolicy,
) -> tuple[str, ...]:
    value = normalized_value(
        observation,
        policy,
    )

    found = TOKEN_PATTERN.findall(
        value
    )

    if not policy.case_sensitive:
        found = [
            token.lower()
            for token in found
        ]

    return tuple(
        sorted(set(found))
    )


def normalized_labels(
    observation: CorrelationObservation,
    policy: CorrelationPolicy,
) -> tuple[str, ...]:
    labels = observation.labels

    if not policy.case_sensitive:
        labels = tuple(
            label.lower()
            for label in labels
        )

    return tuple(
        sorted(set(labels))
    )


def jaccard_score(
    left: set[str],
    right: set[str],
) -> float:
    union = left | right

    if not union:
        return 0.0

    return len(
        left & right
    ) / len(union)


def confidence_for_score(
    score: float,
) -> ConfidenceBand:
    if score >= 0.85:
        return ConfidenceBand.HIGH

    if score >= 0.5:
        return ConfidenceBand.MODERATE

    if score > 0:
        return ConfidenceBand.LOW

    return ConfidenceBand.UNKNOWN


def correlate_pair(
    request: CorrelationRequest,
    left: CorrelationObservation,
    right: CorrelationObservation,
) -> CorrelationPair | None:
    evidence: list[CorrelationEvidence] = []
    weighted_scores: list[float] = []

    left_value = normalized_value(
        left,
        request.policy,
    )
    right_value = normalized_value(
        right,
        request.policy,
    )

    if (
        request.policy.include_exact_matches
        and left_value
        and left_value == right_value
    ):
        evidence.append(
            CorrelationEvidence(
                evidence_kind=CorrelationKind.EXACT,
                values=(
                    left_value,
                ),
                weight=1.0,
            )
        )
        weighted_scores.append(
            1.0
        )

    left_tokens = set(
        tokens(
            left,
            request.policy,
        )
    )
    right_tokens = set(
        tokens(
            right,
            request.policy,
        )
    )
    shared_tokens = sorted(
        left_tokens & right_tokens
    )

    if (
        len(shared_tokens)
        >= request.policy.minimum_shared_tokens
    ):
        token_score = jaccard_score(
            left_tokens,
            right_tokens,
        )

        evidence.append(
            CorrelationEvidence(
                evidence_kind=CorrelationKind.TOKEN,
                values=tuple(
                    shared_tokens
                ),
                weight=round(
                    token_score,
                    12,
                ),
            )
        )
        weighted_scores.append(
            token_score
        )

    if request.policy.include_label_matches:
        left_labels = set(
            normalized_labels(
                left,
                request.policy,
            )
        )
        right_labels = set(
            normalized_labels(
                right,
                request.policy,
            )
        )
        shared_labels = sorted(
            left_labels & right_labels
        )

        if shared_labels:
            label_score = jaccard_score(
                left_labels,
                right_labels,
            )

            evidence.append(
                CorrelationEvidence(
                    evidence_kind=CorrelationKind.LABEL,
                    values=tuple(
                        shared_labels
                    ),
                    weight=round(
                        label_score,
                        12,
                    ),
                )
            )
            weighted_scores.append(
                label_score
            )

    if (
        request.policy.include_source_matches
        and left.source.source_id
        == right.source.source_id
    ):
        evidence.append(
            CorrelationEvidence(
                evidence_kind=CorrelationKind.SOURCE,
                values=(
                    left.source.source_id,
                ),
                weight=0.25,
            )
        )
        weighted_scores.append(
            0.25
        )

    if (
        request.policy.include_temporal_matches
        and left.occurred_at
        and right.occurred_at
        and left.occurred_at
        == right.occurred_at
    ):
        evidence.append(
            CorrelationEvidence(
                evidence_kind=CorrelationKind.TEMPORAL,
                values=(
                    left.occurred_at,
                ),
                weight=0.25,
            )
        )
        weighted_scores.append(
            0.25
        )

    if not evidence:
        return None

    score = min(
        1.0,
        sum(weighted_scores)
        / len(weighted_scores),
    )

    if score < request.policy.minimum_score:
        return None

    left_id, right_id = sorted(
        (
            left.observation_id,
            right.observation_id,
        )
    )

    pair_basis = {
        "left": left_id,
        "right": right_id,
        "evidence": [
            item.model_dump(
                mode="json",
            )
            for item in evidence
        ],
        "score": round(
            score,
            12,
        ),
    }

    return CorrelationPair(
        pair_id=(
            f"echo-pair-{digest(pair_basis)[:20]}"
        ),
        left_observation_id=left_id,
        right_observation_id=right_id,
        score=round(
            score,
            12,
        ),
        evidence=tuple(
            sorted(
                evidence,
                key=lambda item: (
                    item.evidence_kind.value,
                    item.values,
                ),
            )
        ),
        confidence=confidence_for_score(
            score
        ),
        authority=AuthorityState.PROPOSED,
        provenance=build_provenance(
            request,
            sources=(
                left.source,
                right.source,
            ),
            transformations=(
                "normalize_observations",
                "compare_observation_pair",
                "calculate_bounded_correlation_score",
                "emit_proposed_correlation",
            ),
        ),
    )


def correlate_pairs(
    request: CorrelationRequest,
) -> tuple[CorrelationPair, ...]:
    observations = sorted(
        request.observations,
        key=lambda item: item.observation_id,
    )

    pairs: list[CorrelationPair] = []

    for left, right in combinations(
        observations,
        2,
    ):
        pair = correlate_pair(
            request,
            left,
            right,
        )

        if pair is not None:
            pairs.append(
                pair
            )

    return tuple(
        sorted(
            pairs,
            key=lambda item: item.pair_id,
        )
    )


def connected_components(
    observations: tuple[
        CorrelationObservation,
        ...,
    ],
    pairs: tuple[
        CorrelationPair,
        ...,
    ],
) -> list[set[str]]:
    adjacency: dict[
        str,
        set[str],
    ] = defaultdict(set)

    for observation in observations:
        adjacency[
            observation.observation_id
        ]

    for pair in pairs:
        adjacency[
            pair.left_observation_id
        ].add(
            pair.right_observation_id
        )
        adjacency[
            pair.right_observation_id
        ].add(
            pair.left_observation_id
        )

    visited: set[str] = set()
    components: list[set[str]] = []

    for identifier in sorted(
        adjacency
    ):
        if identifier in visited:
            continue

        stack = [
            identifier
        ]
        component: set[str] = set()

        while stack:
            current = stack.pop()

            if current in visited:
                continue

            visited.add(
                current
            )
            component.add(
                current
            )

            stack.extend(
                sorted(
                    adjacency[current] - visited,
                    reverse=True,
                )
            )

        components.append(
            component
        )

    return components


def build_clusters(
    request: CorrelationRequest,
    pairs: tuple[
        CorrelationPair,
        ...,
    ],
) -> tuple[
    tuple[CorrelationCluster, ...],
    tuple[str, ...],
]:
    pair_lookup: dict[
        frozenset[str],
        CorrelationPair,
    ] = {}

    for pair in pairs:
        pair_lookup[
            frozenset(
                (
                    pair.left_observation_id,
                    pair.right_observation_id,
                )
            )
        ] = pair

    observation_lookup = {
        item.observation_id: item
        for item in request.observations
    }

    clusters: list[
        CorrelationCluster
    ] = []
    unmatched: list[str] = []

    for component in connected_components(
        request.observations,
        pairs,
    ):
        if len(component) < 2:
            unmatched.extend(
                component
            )
            continue

        component_pairs = [
            pair
            for pair in pairs
            if (
                pair.left_observation_id
                in component
                and pair.right_observation_id
                in component
            )
        ]

        if not component_pairs:
            unmatched.extend(
                component
            )
            continue

        score = sum(
            pair.score
            for pair in component_pairs
        ) / len(component_pairs)

        labels = sorted(
            {
                label
                for identifier in component
                for label in observation_lookup[
                    identifier
                ].labels
            }
        )

        basis = {
            "observation_ids": sorted(
                component
            ),
            "pair_ids": sorted(
                pair.pair_id
                for pair in component_pairs
            ),
            "score": round(
                score,
                12,
            ),
        }

        clusters.append(
            CorrelationCluster(
                cluster_id=(
                    f"echo-cluster-{digest(basis)[:20]}"
                ),
                observation_ids=tuple(
                    sorted(component)
                ),
                pair_ids=tuple(
                    sorted(
                        pair.pair_id
                        for pair in component_pairs
                    )
                ),
                score=round(
                    score,
                    12,
                ),
                confidence=confidence_for_score(
                    score
                ),
                labels=tuple(labels),
                provenance=build_provenance(
                    request,
                    sources=tuple(
                        observation_lookup[
                            identifier
                        ].source
                        for identifier in sorted(
                            component
                        )
                    ),
                    transformations=(
                        "build_connected_component",
                        "aggregate_pair_scores",
                        "emit_correlation_cluster",
                    ),
                ),
            )
        )

    return (
        tuple(
            sorted(
                clusters,
                key=lambda item: item.cluster_id,
            )
        ),
        tuple(
            sorted(
                unmatched
            )
        ),
    )


def build_hypotheses(
    request: CorrelationRequest,
    clusters: tuple[
        CorrelationCluster,
        ...,
    ],
) -> tuple[
    ThreatHypothesis,
    ...,
]:
    hypotheses: list[
        ThreatHypothesis
    ] = []

    for cluster in clusters:
        statement = (
            f"{len(cluster.observation_ids)} observations "
            f"share supported correlation evidence "
            f"with aggregate score {cluster.score:.3f}."
        )

        basis = {
            "cluster_id": cluster.cluster_id,
            "statement": statement,
        }

        hypotheses.append(
            ThreatHypothesis(
                hypothesis_id=(
                    f"echo-hypothesis-{digest(basis)[:20]}"
                ),
                statement=statement,
                supporting_cluster_ids=(
                    cluster.cluster_id,
                ),
                supporting_observation_ids=(
                    cluster.observation_ids
                ),
                confidence=cluster.confidence,
                authority=AuthorityState.PROPOSED,
                limitations=(
                    "Correlation does not establish causation.",
                    "Result is a proposal, not accepted authority.",
                    "Score depends only on declared local evidence and policy.",
                ),
                provenance=cluster.provenance,
            )
        )

    return tuple(
        sorted(
            hypotheses,
            key=lambda item: item.hypothesis_id,
        )
    )


def correlate(
    request: CorrelationRequest,
) -> CorrelationIndex:
    pairs = correlate_pairs(
        request
    )

    clusters, unmatched = build_clusters(
        request,
        pairs,
    )

    hypotheses = build_hypotheses(
        request,
        clusters,
    )

    body = {
        "request_id": request.request_id,
        "pairs": [
            item.model_dump(
                mode="json",
            )
            for item in pairs
        ],
        "clusters": [
            item.model_dump(
                mode="json",
            )
            for item in clusters
        ],
        "hypotheses": [
            item.model_dump(
                mode="json",
            )
            for item in hypotheses
        ],
        "unmatched_observation_ids": unmatched,
    }

    index_digest = digest(
        body
    )

    return CorrelationIndex(
        index_id=(
            f"echo-index-{index_digest[:20]}"
        ),
        request_id=request.request_id,
        pairs=pairs,
        clusters=clusters,
        hypotheses=hypotheses,
        unmatched_observation_ids=unmatched,
        deterministic=True,
        index_digest=index_digest,
        provenance=build_provenance(
            request,
            transformations=(
                "normalize_observations",
                "correlate_observation_pairs",
                "build_correlation_clusters",
                "emit_bounded_hypotheses",
                "build_deterministic_correlation_index",
            ),
        ),
    )


def run(
    request: CorrelationRequest,
) -> EchoResult:
    started = time.perf_counter()

    try:
        index = correlate(
            request
        )

        return EchoResult(
            operation="correlate",
            passed=True,
            request_id=request.request_id,
            index=index,
            metrics={
                "duration_seconds": (
                    time.perf_counter()
                    - started
                ),
                "observation_count": len(
                    request.observations
                ),
                "pair_count": len(
                    index.pairs
                ),
                "cluster_count": len(
                    index.clusters
                ),
                "hypothesis_count": len(
                    index.hypotheses
                ),
                "unmatched_count": len(
                    index.unmatched_observation_ids
                ),
                "passed": True,
            },
            provenance=build_provenance(
                request,
                transformations=(
                    "correlate_observations",
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
                f"echo-failure-"
                f"{digest([request.request_id, type(exc).__name__, str(exc)])[:20]}"
            ),
            code="echo.runtime.failure",
            message=str(exc),
            recoverable=True,
            retryable=False,
            stage="correlate",
            details={
                "exception_type": type(exc).__name__,
            },
            provenance=envelope,
        )

        return EchoResult(
            operation="correlate",
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


def example_request() -> CorrelationRequest:
    generated_at = (
        "2026-07-31T00:00:00+00:00"
    )

    source_a = SourceReference(
        source_id="echo-source-a",
        source_kind="example",
        authority=AuthorityState.OBSERVED,
        captured_at=generated_at,
    )

    source_b = SourceReference(
        source_id="echo-source-b",
        source_kind="example",
        authority=AuthorityState.OBSERVED,
        captured_at=generated_at,
    )

    return CorrelationRequest(
        request_id="echo-example-request",
        purpose=(
            "Demonstrate deterministic bounded "
            "cross-source correlation."
        ),
        observations=(
            CorrelationObservation(
                observation_id="echo-observation-a",
                observation_kind=ObservationKind.TEXT,
                value=(
                    "Nocturne contains Veil Lantern "
                    "Scribe and Echo."
                ),
                normalized_text=(
                    "nocturne contains veil lantern "
                    "scribe and echo"
                ),
                labels=(
                    "nocturne",
                    "opus",
                ),
                source=source_a,
                confidence=ConfidenceBand.MODERATE,
            ),
            CorrelationObservation(
                observation_id="echo-observation-b",
                observation_kind=ObservationKind.CLAIM,
                value=(
                    "Lantern Scribe Echo compose "
                    "inside Nocturne."
                ),
                normalized_text=(
                    "lantern scribe echo compose "
                    "inside nocturne"
                ),
                labels=(
                    "nocturne",
                ),
                source=source_b,
                confidence=ConfidenceBand.MODERATE,
            ),
            CorrelationObservation(
                observation_id="echo-observation-c",
                observation_kind=ObservationKind.TEXT,
                value=(
                    "Unrelated material with no "
                    "shared operational terms."
                ),
                labels=(
                    "unrelated",
                ),
                source=source_a,
                confidence=ConfidenceBand.LOW,
            ),
        ),
        policy=CorrelationPolicy(
            minimum_shared_tokens=2,
            minimum_score=0.2,
            include_exact_matches=True,
            include_label_matches=True,
            include_source_matches=False,
            include_temporal_matches=False,
            maximum_pairs=100,
            maximum_observations=100,
            case_sensitive=False,
            preserve_unmatched=True,
        ),
        provenance=ProvenanceEnvelope(
            sources=(
                source_a,
                source_b,
            ),
            transformations=(),
            generated_by="echo-example",
            generated_at=generated_at,
        ),
    )


def load_request(
    path: Path | None,
) -> CorrelationRequest:
    if path is None:
        raw = sys.stdin.read()
    else:
        raw = path.read_text(
            encoding="utf-8"
        )

    return CorrelationRequest.model_validate_json(
        raw
    )


def write_result(
    result: EchoResult,
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
            "Echo deterministic bounded "
            "correlation runtime."
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
                    "correlation_request": (
                        CorrelationRequest
                        .model_json_schema()
                    ),
                    "correlation_index": (
                        CorrelationIndex
                        .model_json_schema()
                    ),
                    "echo_result": (
                        EchoResult
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

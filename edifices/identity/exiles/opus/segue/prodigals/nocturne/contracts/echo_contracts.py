#!/usr/bin/env python3
from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CONTRACT_VERSION = "1.0.0"


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        validate_default=True,
    )


class AuthorityState(StrEnum):
    PROPOSED = "proposed"
    OBSERVED = "observed"
    ACCEPTED = "accepted"
    AUTHORITATIVE = "authoritative"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class ConfidenceBand(StrEnum):
    UNKNOWN = "unknown"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERIFIED = "verified"


class ObservationKind(StrEnum):
    TEXT = "text"
    LOCATION = "location"
    LINK = "link"
    CLAIM = "claim"
    INDICATOR = "indicator"
    EVENT = "event"
    UNKNOWN = "unknown"


class CorrelationKind(StrEnum):
    EXACT = "exact"
    TOKEN = "token"
    LABEL = "label"
    SOURCE = "source"
    TEMPORAL = "temporal"
    COMPOSITE = "composite"


class SourceReference(StrictModel):
    source_id: str
    source_kind: str
    source_path: str | None = None
    source_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    authority: AuthorityState = AuthorityState.UNKNOWN
    captured_at: str | None = None


class ProvenanceEnvelope(StrictModel):
    sources: tuple[SourceReference, ...] = ()
    transformations: tuple[str, ...] = ()
    generated_by: str
    generated_at: str
    contract_version: str = CONTRACT_VERSION


class CorrelationPolicy(StrictModel):
    minimum_shared_tokens: int = Field(
        default=2,
        ge=1,
        le=100,
    )
    minimum_score: float = Field(
        default=0.25,
        ge=0,
        le=1,
    )
    include_exact_matches: bool = True
    include_label_matches: bool = True
    include_source_matches: bool = False
    include_temporal_matches: bool = False
    maximum_pairs: int = Field(
        default=100000,
        ge=1,
        le=1000000,
    )
    maximum_observations: int = Field(
        default=10000,
        ge=2,
        le=100000,
    )
    case_sensitive: bool = False
    preserve_unmatched: bool = True


class CorrelationObservation(StrictModel):
    observation_id: str
    observation_kind: ObservationKind
    value: Any
    normalized_text: str | None = None
    labels: tuple[str, ...] = ()
    occurred_at: str | None = None
    source: SourceReference
    confidence: ConfidenceBand = ConfidenceBand.UNKNOWN
    authority: AuthorityState = AuthorityState.OBSERVED
    metadata: dict[str, Any] = Field(default_factory=dict)


class CorrelationRequest(StrictModel):
    request_id: str
    purpose: str
    observations: tuple[CorrelationObservation, ...]
    policy: CorrelationPolicy
    provenance: ProvenanceEnvelope

    @model_validator(mode="after")
    def enforce_limits(
        self,
    ) -> "CorrelationRequest":
        if len(self.observations) > self.policy.maximum_observations:
            raise ValueError(
                "Correlation request exceeds maximum_observations."
            )

        pair_count = (
            len(self.observations)
            * (
                len(self.observations) - 1
            )
            // 2
        )

        if pair_count > self.policy.maximum_pairs:
            raise ValueError(
                "Correlation request exceeds maximum_pairs."
            )

        return self


class CorrelationEvidence(StrictModel):
    evidence_kind: CorrelationKind
    values: tuple[str, ...] = ()
    weight: float = Field(
        ge=0,
        le=1,
    )


class CorrelationPair(StrictModel):
    pair_id: str
    left_observation_id: str
    right_observation_id: str
    score: float = Field(
        ge=0,
        le=1,
    )
    evidence: tuple[CorrelationEvidence, ...]
    confidence: ConfidenceBand
    authority: AuthorityState = AuthorityState.PROPOSED
    provenance: ProvenanceEnvelope


class CorrelationCluster(StrictModel):
    cluster_id: str
    observation_ids: tuple[str, ...]
    pair_ids: tuple[str, ...]
    score: float = Field(
        ge=0,
        le=1,
    )
    confidence: ConfidenceBand
    labels: tuple[str, ...] = ()
    provenance: ProvenanceEnvelope


class ThreatHypothesis(StrictModel):
    hypothesis_id: str
    statement: str
    supporting_cluster_ids: tuple[str, ...]
    supporting_observation_ids: tuple[str, ...]
    confidence: ConfidenceBand
    authority: AuthorityState = AuthorityState.PROPOSED
    limitations: tuple[str, ...]
    provenance: ProvenanceEnvelope


class CorrelationIndex(StrictModel):
    index_id: str
    request_id: str
    pairs: tuple[CorrelationPair, ...]
    clusters: tuple[CorrelationCluster, ...]
    hypotheses: tuple[ThreatHypothesis, ...]
    unmatched_observation_ids: tuple[str, ...]
    deterministic: bool = True
    index_digest: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    provenance: ProvenanceEnvelope


class FailureRecord(StrictModel):
    failure_id: str
    code: str
    message: str
    recoverable: bool
    retryable: bool = False
    stage: str
    details: dict[str, Any] = Field(default_factory=dict)
    provenance: ProvenanceEnvelope


class EchoResult(StrictModel):
    operation: Literal[
        "correlate",
        "validate",
    ]
    passed: bool
    request_id: str
    index: CorrelationIndex | None = None
    failure: FailureRecord | None = None
    metrics: dict[str, int | float | str | bool] = Field(
        default_factory=dict,
    )
    provenance: ProvenanceEnvelope

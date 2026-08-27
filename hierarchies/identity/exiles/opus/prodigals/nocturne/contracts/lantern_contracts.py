#!/usr/bin/env python3
from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


CONTRACT_VERSION = "1.0.0"


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
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


class DiscoverySourceKind(StrEnum):
    FILE = "file"
    DOCUMENT = "document"
    EXPORT = "export"
    OBSERVATION = "observation"
    MANUAL = "manual"


class LocationState(StrEnum):
    OBSERVED = "observed"
    NORMALIZED = "normalized"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class SourceReference(StrictModel):
    source_id: str
    source_kind: DiscoverySourceKind
    source_path: str | None = None
    source_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    captured_at: str | None = None
    authority: AuthorityState = AuthorityState.UNKNOWN


class ProvenanceEnvelope(StrictModel):
    sources: tuple[SourceReference, ...] = ()
    transformations: tuple[str, ...] = ()
    generated_by: str
    generated_at: str
    contract_version: str = CONTRACT_VERSION


class DiscoveryPolicy(StrictModel):
    network_access: bool = False
    allow_non_onion_hosts: bool = False
    allow_query_strings: bool = False
    allow_fragments: bool = False
    maximum_records: int = Field(
        default=10000,
        ge=1,
        le=1000000,
    )
    reject_credentials: bool = True
    deduplicate: bool = True
    preserve_original: bool = True
    audit_required: bool = True

    @field_validator("network_access")
    @classmethod
    def network_access_is_not_supported(
        cls,
        value: bool,
    ) -> bool:
        if value:
            raise ValueError(
                "Lantern reference runtime is offline-only and cannot enable network access."
            )

        return value


class DiscoveryRecord(StrictModel):
    record_id: str
    location: str
    source: SourceReference
    title: str | None = None
    description: str | None = None
    labels: tuple[str, ...] = ()
    observed_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DiscoveryRequest(StrictModel):
    request_id: str
    purpose: str
    records: tuple[DiscoveryRecord, ...]
    policy: DiscoveryPolicy
    provenance: ProvenanceEnvelope

    @model_validator(mode="after")
    def enforce_record_limit(
        self,
    ) -> "DiscoveryRequest":
        if len(self.records) > self.policy.maximum_records:
            raise ValueError(
                "Discovery request exceeds maximum_records."
            )

        return self


class NormalizedLocation(StrictModel):
    location_id: str
    original_location: str
    normalized_location: str | None
    host: str | None
    port: int | None = Field(
        default=None,
        ge=1,
        le=65535,
    )
    path: str | None
    state: LocationState
    confidence: ConfidenceBand
    rejection_reasons: tuple[str, ...] = ()
    labels: tuple[str, ...] = ()
    source: SourceReference
    provenance: ProvenanceEnvelope


class LocationIndexEntry(StrictModel):
    location_id: str
    normalized_location: str
    host: str
    port: int | None
    path: str
    labels: tuple[str, ...]
    source_record_ids: tuple[str, ...]
    observation_count: int = Field(
        ge=1,
    )
    confidence: ConfidenceBand
    provenance: ProvenanceEnvelope


class LocationIndex(StrictModel):
    index_id: str
    request_id: str
    entries: tuple[LocationIndexEntry, ...]
    accepted_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    duplicate_count: int = Field(ge=0)
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


class LanternResult(StrictModel):
    operation: Literal[
        "normalize",
        "index",
        "validate",
    ]
    passed: bool
    request_id: str
    normalized: tuple[NormalizedLocation, ...] = ()
    index: LocationIndex | None = None
    failure: FailureRecord | None = None
    metrics: dict[str, int | float | str | bool] = Field(
        default_factory=dict,
    )
    provenance: ProvenanceEnvelope

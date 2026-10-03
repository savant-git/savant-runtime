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


class SourceFormat(StrEnum):
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    UNKNOWN = "unknown"


class SourceReference(StrictModel):
    source_id: str
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


class ExtractionPolicy(StrictModel):
    allowed_formats: tuple[SourceFormat, ...] = (
        SourceFormat.TEXT,
        SourceFormat.MARKDOWN,
        SourceFormat.JSON,
        SourceFormat.HTML,
    )
    preserve_source_spans: bool = True
    normalize_whitespace: bool = True
    extract_headings: bool = True
    extract_links: bool = True
    extract_json_scalars: bool = True
    maximum_input_bytes: int = Field(
        default=10_000_000,
        ge=1,
        le=100_000_000,
    )
    maximum_observations: int = Field(
        default=100_000,
        ge=1,
        le=1_000_000,
    )


class SourceDocument(StrictModel):
    document_id: str
    content: str
    declared_format: SourceFormat = SourceFormat.UNKNOWN
    source: SourceReference
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractionRequest(StrictModel):
    request_id: str
    purpose: str
    document: SourceDocument
    policy: ExtractionPolicy
    provenance: ProvenanceEnvelope

    @model_validator(mode="after")
    def enforce_size(
        self,
    ) -> "ExtractionRequest":
        size = len(
            self.document.content.encode("utf-8")
        )

        if size > self.policy.maximum_input_bytes:
            raise ValueError(
                "Source document exceeds maximum_input_bytes."
            )

        return self


class SourceSpan(StrictModel):
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_span(
        self,
    ) -> "SourceSpan":
        if self.end < self.start:
            raise ValueError(
                "Source span end cannot precede start."
            )

        if self.line_end < self.line_start:
            raise ValueError(
                "Source span line_end cannot precede line_start."
            )

        return self


class ExtractedObservation(StrictModel):
    observation_id: str
    observation_kind: Literal[
        "paragraph",
        "heading",
        "link",
        "json_scalar",
        "text",
    ]
    value: Any
    normalized_text: str | None = None
    source_span: SourceSpan
    confidence: ConfidenceBand = ConfidenceBand.MODERATE
    authority: AuthorityState = AuthorityState.OBSERVED
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: ProvenanceEnvelope


class ExtractionIndex(StrictModel):
    index_id: str
    request_id: str
    source_format: SourceFormat
    observations: tuple[ExtractedObservation, ...]
    observation_count: int = Field(ge=0)
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


class ScribeResult(StrictModel):
    operation: Literal[
        "extract",
        "validate",
    ]
    passed: bool
    request_id: str
    index: ExtractionIndex | None = None
    failure: FailureRecord | None = None
    metrics: dict[str, int | float | str | bool] = Field(
        default_factory=dict,
    )
    provenance: ProvenanceEnvelope

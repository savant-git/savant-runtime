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


class AttachmentMode(StrEnum):
    PLAN = "plan"
    EXECUTE = "execute"
    VALIDATE = "validate"


class AttachmentState(StrEnum):
    ADMITTED = "admitted"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


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


class AuthorityBoundary(StrictModel):
    opus_retains_provider_orchestration: bool = True
    nocturne_retains_internal_composition: bool = True
    nocturne_may_select_external_providers: bool = False
    nocturne_may_read_opus_secrets: bool = False
    nocturne_may_mutate_opus_registry: bool = False
    nocturne_may_bypass_opus_policy: bool = False
    reversible_attachment: bool = True

    @model_validator(mode="after")
    def enforce_boundary(
        self,
    ) -> "AuthorityBoundary":
        violations: list[str] = []

        if not self.opus_retains_provider_orchestration:
            violations.append(
                "Opus must retain provider orchestration authority."
            )

        if not self.nocturne_retains_internal_composition:
            violations.append(
                "Nocturne must retain its internal composition authority."
            )

        if self.nocturne_may_select_external_providers:
            violations.append(
                "Nocturne cannot select external providers directly."
            )

        if self.nocturne_may_read_opus_secrets:
            violations.append(
                "Nocturne cannot read Opus secrets."
            )

        if self.nocturne_may_mutate_opus_registry:
            violations.append(
                "Nocturne cannot mutate the Opus registry."
            )

        if self.nocturne_may_bypass_opus_policy:
            violations.append(
                "Nocturne cannot bypass Opus policy."
            )

        if not self.reversible_attachment:
            violations.append(
                "The attachment must remain reversible."
            )

        if violations:
            raise ValueError(
                " ".join(violations)
            )

        return self


class OpusEnvelope(StrictModel):
    request_id: str
    operation: str
    payload: dict[str, Any]
    provider_request: dict[str, Any] | None = None
    provider_result: dict[str, Any] | None = None
    policy: dict[str, Any] = Field(default_factory=dict)
    provenance: ProvenanceEnvelope


class NocturneAttachmentRequest(StrictModel):
    attachment_id: str
    mode: AttachmentMode
    envelope: OpusEnvelope
    authority_boundary: AuthorityBoundary
    nocturne_request: dict[str, Any]
    provenance: ProvenanceEnvelope


class AttachmentDecision(StrictModel):
    decision_id: str
    state: AttachmentState
    admitted: bool
    reasons: tuple[str, ...]
    authority_boundary_digest: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    request_digest: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    provenance: ProvenanceEnvelope


class NocturneAttachmentResult(StrictModel):
    operation: Literal[
        "attach",
        "validate",
    ]
    passed: bool
    attachment_id: str
    decision: AttachmentDecision
    nocturne_result: dict[str, Any] | None = None
    failure: dict[str, Any] | None = None
    result_digest: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    metrics: dict[str, int | float | str | bool] = Field(
        default_factory=dict,
    )
    provenance: ProvenanceEnvelope

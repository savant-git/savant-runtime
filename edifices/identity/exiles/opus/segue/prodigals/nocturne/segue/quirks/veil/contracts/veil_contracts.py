#!/usr/bin/env python3
from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CONTRACT_VERSION = "1.0.0"
SUBJECT_ID = 'quirk.nocturne.veil'
DECLARED_CAPABILITIES = ('quirk.nocturne.veil.declared_purpose',)


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


class ExecutionMode(StrEnum):
    PLAN = "plan"
    EXECUTE = "execute"
    VALIDATE = "validate"


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


class VeilPolicy(StrictModel):
    execution_mode: ExecutionMode = ExecutionMode.PLAN
    allowed_capabilities: tuple[str, ...] = ()
    fail_closed: bool = True
    deterministic: bool = True
    network_access: bool = False
    filesystem_read: bool = False
    filesystem_write: bool = False
    subprocess_access: bool = False
    secret_access: bool = False

    @model_validator(mode="after")
    def enforce_boundary(
        self,
    ) -> "VeilPolicy":
        undeclared = [
            capability
            for capability in self.allowed_capabilities
            if capability not in DECLARED_CAPABILITIES
        ]

        if undeclared:
            raise ValueError(
                "Undeclared capabilities requested: "
                + ", ".join(
                    sorted(undeclared)
                )
            )

        if (
            self.network_access
            or self.filesystem_read
            or self.filesystem_write
            or self.subprocess_access
            or self.secret_access
        ):
            raise ValueError(
                "The baseline runtime grants no external authority."
            )

        return self


class VeilRequest(StrictModel):
    request_id: str
    purpose: str
    operation: str
    payload: dict[str, Any] = Field(
        default_factory=dict
    )
    policy: VeilPolicy
    authority: AuthorityState = AuthorityState.OBSERVED
    provenance: ProvenanceEnvelope


class FailureRecord(StrictModel):
    failure_id: str
    code: str
    message: str
    stage: str
    recoverable: bool
    details: dict[str, Any] = Field(
        default_factory=dict
    )
    provenance: ProvenanceEnvelope


class VeilProjection(StrictModel):
    projection_id: str
    subject_id: Literal['quirk.nocturne.veil']
    request_id: str
    operation: str
    purpose: str
    payload_digest: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )
    admitted_capabilities: tuple[str, ...]
    authority: AuthorityState = AuthorityState.PROPOSED
    deterministic: bool = True
    provenance: ProvenanceEnvelope


class VeilResult(StrictModel):
    operation: Literal["run", "validate"]
    passed: bool
    request_id: str
    projection: VeilProjection | None = None
    failure: FailureRecord | None = None
    result_digest: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )
    metrics: dict[str, int | float | str | bool] = Field(
        default_factory=dict
    )
    provenance: ProvenanceEnvelope

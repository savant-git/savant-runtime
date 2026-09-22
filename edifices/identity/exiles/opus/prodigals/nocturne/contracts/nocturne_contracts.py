#!/usr/bin/env python3
from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class ExecutionMode(StrEnum):
    PLAN = "plan"
    SIMULATE = "simulate"
    EXECUTE = "execute"


class RiskLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class SourceReference(StrictModel):
    source_id: str
    source_kind: str
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


class SecurityPolicy(StrictModel):
    execution_mode: ExecutionMode = ExecutionMode.PLAN
    network_access: bool = False
    filesystem_read: bool = False
    filesystem_write: bool = False
    subprocess_access: bool = False
    secret_access: bool = False
    allowed_hosts: tuple[str, ...] = ()
    allowed_paths: tuple[str, ...] = ()
    allowed_commands: tuple[str, ...] = ()
    audit_required: bool = True

    @field_validator("network_access")
    @classmethod
    def execution_requires_explicit_network_authority(
        cls,
        value: bool,
        info: Any,
    ) -> bool:
        mode = info.data.get("execution_mode")

        if mode == ExecutionMode.EXECUTE and not value:
            raise ValueError(
                "Execute mode requires explicit network_access=true."
            )

        return value


class RouteHop(StrictModel):
    hop_id: str
    jurisdiction: str | None = None
    provider: str | None = None
    transport: str = "unknown"
    observed_latency_ms: float | None = Field(
        default=None,
        ge=0,
    )
    trust: ConfidenceBand = ConfidenceBand.UNKNOWN
    metadata: dict[str, Any] = Field(default_factory=dict)


class RouteRequest(StrictModel):
    request_id: str
    destination: str
    purpose: str
    execution_mode: ExecutionMode = ExecutionMode.PLAN
    required_hops: int = Field(default=3, ge=1, le=12)
    maximum_latency_ms: float | None = Field(
        default=None,
        gt=0,
    )
    avoid_jurisdictions: tuple[str, ...] = ()
    preferred_transports: tuple[str, ...] = ()
    timing_jitter_ms: tuple[int, int] = (0, 0)
    rotation_interval_seconds: int | None = Field(
        default=None,
        ge=30,
    )
    policy: SecurityPolicy
    provenance: ProvenanceEnvelope

    @field_validator("timing_jitter_ms")
    @classmethod
    def valid_jitter(
        cls,
        value: tuple[int, int],
    ) -> tuple[int, int]:
        minimum, maximum = value

        if minimum < 0 or maximum < 0:
            raise ValueError(
                "Timing jitter cannot be negative."
            )

        if minimum > maximum:
            raise ValueError(
                "Minimum jitter cannot exceed maximum jitter."
            )

        return value


class RoutePlan(StrictModel):
    plan_id: str
    request_id: str
    execution_mode: ExecutionMode
    destination: str
    hops: tuple[RouteHop, ...]
    timing_jitter_ms: tuple[int, int]
    rotation_interval_seconds: int | None
    deterministic: bool
    executable: bool
    policy_digest: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )
    plan_digest: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )
    warnings: tuple[str, ...] = ()
    provenance: ProvenanceEnvelope


class RouteObservation(StrictModel):
    observation_id: str
    request_id: str
    plan_id: str
    authority: AuthorityState = AuthorityState.OBSERVED
    confidence: ConfidenceBand = ConfidenceBand.UNKNOWN
    reachable: bool | None = None
    latency_ms: float | None = Field(
        default=None,
        ge=0,
    )
    failures: tuple[str, ...] = ()
    evidence: tuple[SourceReference, ...] = ()
    provenance: ProvenanceEnvelope


class FailureRecord(StrictModel):
    failure_id: str
    code: str
    message: str
    recoverable: bool
    retryable: bool
    risk: RiskLevel
    stage: str
    details: dict[str, Any] = Field(default_factory=dict)
    provenance: ProvenanceEnvelope


class VeilResult(StrictModel):
    operation: Literal[
        "plan_route",
        "simulate_route",
        "execute_route",
        "validate_policy",
    ]
    passed: bool
    request_id: str
    plan: RoutePlan | None = None
    observation: RouteObservation | None = None
    failure: FailureRecord | None = None
    metrics: dict[str, int | float | str | bool] = Field(
        default_factory=dict
    )
    provenance: ProvenanceEnvelope

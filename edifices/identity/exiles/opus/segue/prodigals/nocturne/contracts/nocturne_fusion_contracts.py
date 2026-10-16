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


class ExecutionMode(StrEnum):
    PLAN = "plan"
    SIMULATE = "simulate"


class QuirkName(StrEnum):
    VEIL = "veil"
    LANTERN = "lantern"
    SCRIBE = "scribe"
    ECHO = "echo"


class StageState(StrEnum):
    PLANNED = "planned"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"


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


class FusionPolicy(StrictModel):
    execution_mode: ExecutionMode = ExecutionMode.PLAN
    enabled_quirks: tuple[QuirkName, ...] = (
        QuirkName.VEIL,
        QuirkName.LANTERN,
        QuirkName.SCRIBE,
        QuirkName.ECHO,
    )
    required_quirks: tuple[QuirkName, ...] = ()
    allow_partial_results: bool = True
    fail_closed: bool = True
    preserve_intermediate_results: bool = True
    maximum_stage_failures: int = Field(
        default=4,
        ge=0,
        le=4,
    )

    @model_validator(mode="after")
    def validate_requirements(
        self,
    ) -> "FusionPolicy":
        enabled = set(self.enabled_quirks)

        missing = [
            quirk
            for quirk in self.required_quirks
            if quirk not in enabled
        ]

        if missing:
            raise ValueError(
                "Required quirks must also be enabled."
            )

        return self


class NocturneRequest(StrictModel):
    request_id: str
    purpose: str
    policy: FusionPolicy
    veil_request: dict[str, Any] | None = None
    lantern_request: dict[str, Any] | None = None
    scribe_request: dict[str, Any] | None = None
    echo_request: dict[str, Any] | None = None
    provenance: ProvenanceEnvelope


class StageResult(StrictModel):
    stage_id: str
    quirk: QuirkName
    state: StageState
    passed: bool
    required: bool
    result: dict[str, Any] | None = None
    failure: dict[str, Any] | None = None
    result_digest: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    provenance: ProvenanceEnvelope


class NocturneResult(StrictModel):
    operation: Literal[
        "compose",
        "validate",
    ]
    passed: bool
    partial: bool
    request_id: str
    stages: tuple[StageResult, ...]
    completed_quirks: tuple[QuirkName, ...]
    failed_quirks: tuple[QuirkName, ...]
    skipped_quirks: tuple[QuirkName, ...]
    composition_digest: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    metrics: dict[str, int | float | str | bool] = Field(
        default_factory=dict,
    )
    provenance: ProvenanceEnvelope

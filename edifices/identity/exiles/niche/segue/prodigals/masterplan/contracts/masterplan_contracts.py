#!/usr/bin/env python3
from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


CONTRACT_VERSION = "1.0.0"
SUBJECT_ID = "prodigal.niche.masterplan"


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        validate_default=True,
    )


class AuthorityState(StrEnum):
    UNKNOWN = "unknown"
    OBSERVED = "observed"
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    AUTHORITATIVE = "authoritative"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class TaskStatus(StrEnum):
    UNKNOWN = "unknown"
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    READY = "ready"
    ACTIVE = "active"
    BLOCKED = "blocked"
    PAUSED = "paused"
    COMPLETED = "completed"
    REOPENED = "reopened"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class TaskKind(StrEnum):
    PROGRAM = "program"
    CAPABILITY = "capability"
    ONUS = "onus"
    TASK = "task"
    SUBTASK = "subtask"
    MICROSTEP = "microstep"
    GATE = "gate"
    MILESTONE = "milestone"
    DECISION = "decision"
    MIGRATION = "migration"
    AUDIT = "audit"
    VERIFICATION = "verification"
    ATTESTATION = "attestation"


class SegueType(StrEnum):
    DEPENDS_ON = "depends_on"
    BLOCKS = "blocks"
    CONTAINS = "contains"
    IMPLEMENTS = "implements"
    VALIDATES = "validates"
    PRODUCES = "produces"
    CONSUMES = "consumes"
    SUPERSEDES = "supersedes"
    RELATES_TO = "relates_to"
    PROMOTES = "promotes"
    MIGRATES = "migrates"
    OBSERVES = "observes"
    ATTESTS = "attests"
    ROLLS_BACK = "rolls_back"
    UNBLOCKS = "unblocks"


class SelectionReason(StrEnum):
    AUTHORITY = "authority"
    PRIORITY = "priority"
    DEPENDENCY = "dependency"
    BLOCKING_IMPACT = "blocking_impact"
    RISK = "risk"
    EXPLICIT_OVERRIDE = "explicit_override"


class SourceReference(StrictModel):
    source_id: str
    source_kind: str
    source_path: str | None = None
    source_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    authority_state: AuthorityState = AuthorityState.UNKNOWN
    captured_at: str | None = None


class AuthorityEnvelope(StrictModel):
    state: AuthorityState
    authority_class: str
    tier: int = Field(
        ge=0,
    )
    source: str
    accepted_by: str | None = None
    accepted_at: str | None = None
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )

    @model_validator(mode="after")
    def validate_acceptance(
        self,
    ) -> "AuthorityEnvelope":
        accepted_states = {
            AuthorityState.ACCEPTED,
            AuthorityState.AUTHORITATIVE,
        }

        if (
            self.state in accepted_states
            and (
                not self.accepted_by
                or not self.accepted_at
            )
        ):
            raise ValueError(
                "Accepted authority requires accepted_by and accepted_at."
            )

        return self


class ProvenanceEnvelope(StrictModel):
    sources: tuple[SourceReference, ...] = ()
    transformations: tuple[str, ...] = ()
    generated_by: str
    generated_at: str
    contract_version: str = CONTRACT_VERSION


class PriorityRecord(StrictModel):
    band: str = Field(
        pattern=r"^P[0-9]+[A-Z]*$",
    )
    ordinal: int = Field(
        ge=0,
    )
    authority_locked: bool = False
    rationale: str = ""


class EvidenceRequirement(StrictModel):
    id: str
    kind: str
    required: bool = True
    acceptance: str


class TaskRecord(StrictModel):
    id: str = Field(
        pattern=r"^SAV-[A-Z0-9][A-Z0-9._-]*$",
    )
    kind: TaskKind
    title: str
    description: str = ""
    priority: PriorityRecord
    status: TaskStatus
    authority: AuthorityEnvelope
    purpose: str
    scope: dict[str, Any] = Field(
        default_factory=dict,
    )
    acceptance: tuple[str, ...] = ()
    evidence_requirements: tuple[
        EvidenceRequirement,
        ...
    ] = ()
    outputs: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    security: dict[str, Any] = Field(
        default_factory=dict,
    )
    lineage: dict[str, Any] = Field(
        default_factory=dict,
    )
    provenance: ProvenanceEnvelope
    extensions: dict[str, Any] = Field(
        default_factory=dict,
    )


class TaskSegue(StrictModel):
    id: str
    type: SegueType
    source: str
    target: str
    authority: AuthorityEnvelope
    provenance: ProvenanceEnvelope
    validity: dict[str, Any] = Field(
        default_factory=dict,
    )
    extensions: dict[str, Any] = Field(
        default_factory=dict,
    )

    @model_validator(mode="after")
    def prevent_self_reference(
        self,
    ) -> "TaskSegue":
        if self.source == self.target:
            raise ValueError(
                "A task segue cannot target its own source."
            )

        return self


class TaskEvent(StrictModel):
    id: str
    task_id: str
    event_type: str
    previous_state: TaskStatus | None = None
    next_state: TaskStatus | None = None
    authority: AuthorityEnvelope
    occurred_at: str
    provenance: ProvenanceEnvelope


class TaskDecision(StrictModel):
    id: str
    subject: str
    decision: str
    authority: AuthorityEnvelope
    rationale: str
    occurred_at: str
    provenance: ProvenanceEnvelope


class TaskEvidence(StrictModel):
    id: str
    task_id: str
    kind: str
    path: str | None = None
    sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    passed: bool | None = None
    authority: AuthorityEnvelope
    provenance: ProvenanceEnvelope


class TaskReceipt(StrictModel):
    id: str
    task_id: str
    operation: str
    passed: bool
    outputs: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    occurred_at: str
    provenance: ProvenanceEnvelope


class CriterionResult(StrictModel):
    criterion: str
    passed: bool
    evidence: tuple[str, ...] = ()
    reason: str = ""


class TaskAttestation(StrictModel):
    id: str
    task_id: str
    passed: bool
    criteria: tuple[CriterionResult, ...]
    evidence: tuple[str, ...] = ()
    digest: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    occurred_at: str
    provenance: ProvenanceEnvelope


class TaskGraph(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    graph_id: Literal["savant.masterplan"] = "savant.masterplan"
    authority: AuthorityEnvelope
    records: tuple[TaskRecord, ...] = ()
    segues: tuple[TaskSegue, ...] = ()
    events: tuple[TaskEvent, ...] = ()
    decisions: tuple[TaskDecision, ...] = ()
    evidence: tuple[TaskEvidence, ...] = ()
    receipts: tuple[TaskReceipt, ...] = ()
    attestations: tuple[TaskAttestation, ...] = ()

    @model_validator(mode="after")
    def validate_graph_uniqueness(
        self,
    ) -> "TaskGraph":
        collections = {
            "records": [
                record.id
                for record in self.records
            ],
            "segues": [
                segue.id
                for segue in self.segues
            ],
            "events": [
                event.id
                for event in self.events
            ],
            "decisions": [
                decision.id
                for decision in self.decisions
            ],
            "evidence": [
                evidence.id
                for evidence in self.evidence
            ],
            "receipts": [
                receipt.id
                for receipt in self.receipts
            ],
            "attestations": [
                attestation.id
                for attestation in self.attestations
            ],
        }

        for collection_name, identifiers in collections.items():
            if len(identifiers) != len(set(identifiers)):
                raise ValueError(
                    f"Duplicate identifiers in {collection_name}."
                )

        task_ids = {
            record.id
            for record in self.records
        }

        for segue in self.segues:
            if (
                segue.source not in task_ids
                or segue.target not in task_ids
            ):
                raise ValueError(
                    f"Segue references an unknown task: {segue.id}"
                )

        for event in self.events:
            if event.task_id not in task_ids:
                raise ValueError(
                    f"Event references an unknown task: {event.id}"
                )

        for evidence in self.evidence:
            if evidence.task_id not in task_ids:
                raise ValueError(
                    f"Evidence references an unknown task: {evidence.id}"
                )

        for receipt in self.receipts:
            if receipt.task_id not in task_ids:
                raise ValueError(
                    f"Receipt references an unknown task: {receipt.id}"
                )

        for attestation in self.attestations:
            if attestation.task_id not in task_ids:
                raise ValueError(
                    f"Attestation references an unknown task: {attestation.id}"
                )

        return self


class TaskQuery(StrictModel):
    include_statuses: tuple[TaskStatus, ...] = ()
    exclude_statuses: tuple[TaskStatus, ...] = ()
    priority_bands: tuple[str, ...] = ()
    task_kinds: tuple[TaskKind, ...] = ()
    authority_states: tuple[AuthorityState, ...] = ()
    executable_only: bool = False
    include_blocked: bool = False
    limit: int = Field(
        default=100,
        ge=1,
        le=10000,
    )


class TaskSelectionCandidate(StrictModel):
    task_id: str
    executable: bool
    score: int
    reasons: tuple[SelectionReason, ...]
    blocked_by: tuple[str, ...] = ()
    unmet_dependencies: tuple[str, ...] = ()


class TaskSelection(StrictModel):
    operation: Literal["select_next"] = "select_next"
    selected_task_id: str | None
    candidates: tuple[
        TaskSelectionCandidate,
        ...
    ]
    graph_digest: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    selection_digest: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    provenance: ProvenanceEnvelope


class TaskProjection(StrictModel):
    operation: Literal[
        "roadmap",
        "queue",
        "dependency_graph",
        "bottlenecks",
        "release",
        "agent_context",
        "audit",
    ]
    graph_id: Literal["savant.masterplan"] = "savant.masterplan"
    graph_digest: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    projection_digest: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    payload: dict[str, Any]
    provenance: ProvenanceEnvelope


class MasterplanRequest(StrictModel):
    request_id: str
    operation: Literal[
        "validate",
        "select_next",
        "query",
        "project",
        "audit",
    ]
    graph: TaskGraph
    query: TaskQuery | None = None
    projection: Literal[
        "roadmap",
        "queue",
        "dependency_graph",
        "bottlenecks",
        "release",
        "agent_context",
        "audit",
    ] | None = None
    authority: AuthorityEnvelope
    provenance: ProvenanceEnvelope

    @model_validator(mode="after")
    def validate_operation_requirements(
        self,
    ) -> "MasterplanRequest":
        if (
            self.operation == "query"
            and self.query is None
        ):
            raise ValueError(
                "Query operation requires query criteria."
            )

        if (
            self.operation == "project"
            and self.projection is None
        ):
            raise ValueError(
                "Project operation requires projection type."
            )

        return self


class FailureRecord(StrictModel):
    failure_id: str
    code: str
    message: str
    stage: str
    recoverable: bool
    details: dict[str, Any] = Field(
        default_factory=dict,
    )
    provenance: ProvenanceEnvelope


class MasterplanResult(StrictModel):
    operation: Literal[
        "validate",
        "select_next",
        "query",
        "project",
        "audit",
    ]
    passed: bool
    request_id: str
    graph_digest: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    result_digest: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    selection: TaskSelection | None = None
    records: tuple[TaskRecord, ...] = ()
    projection: TaskProjection | None = None
    audit: dict[str, Any] | None = None
    failure: FailureRecord | None = None
    metrics: dict[
        str,
        int | float | str | bool,
    ] = Field(
        default_factory=dict,
    )
    provenance: ProvenanceEnvelope


LEGAL_TRANSITIONS: dict[
    TaskStatus,
    frozenset[TaskStatus],
] = {
    TaskStatus.UNKNOWN: frozenset(
        {
            TaskStatus.PROPOSED,
        }
    ),
    TaskStatus.PROPOSED: frozenset(
        {
            TaskStatus.ACCEPTED,
            TaskStatus.REJECTED,
            TaskStatus.SUPERSEDED,
        }
    ),
    TaskStatus.ACCEPTED: frozenset(
        {
            TaskStatus.READY,
            TaskStatus.ACTIVE,
            TaskStatus.BLOCKED,
            TaskStatus.PAUSED,
            TaskStatus.REJECTED,
            TaskStatus.CANCELLED,
            TaskStatus.SUPERSEDED,
        }
    ),
    TaskStatus.READY: frozenset(
        {
            TaskStatus.ACTIVE,
            TaskStatus.BLOCKED,
            TaskStatus.PAUSED,
            TaskStatus.CANCELLED,
            TaskStatus.SUPERSEDED,
        }
    ),
    TaskStatus.ACTIVE: frozenset(
        {
            TaskStatus.BLOCKED,
            TaskStatus.PAUSED,
            TaskStatus.COMPLETED,
            TaskStatus.CANCELLED,
            TaskStatus.SUPERSEDED,
        }
    ),
    TaskStatus.BLOCKED: frozenset(
        {
            TaskStatus.READY,
            TaskStatus.ACTIVE,
            TaskStatus.PAUSED,
            TaskStatus.CANCELLED,
            TaskStatus.SUPERSEDED,
        }
    ),
    TaskStatus.PAUSED: frozenset(
        {
            TaskStatus.READY,
            TaskStatus.ACTIVE,
            TaskStatus.BLOCKED,
            TaskStatus.CANCELLED,
            TaskStatus.SUPERSEDED,
        }
    ),
    TaskStatus.COMPLETED: frozenset(
        {
            TaskStatus.REOPENED,
            TaskStatus.ARCHIVED,
        }
    ),
    TaskStatus.REOPENED: frozenset(
        {
            TaskStatus.READY,
            TaskStatus.ACTIVE,
            TaskStatus.BLOCKED,
            TaskStatus.PAUSED,
            TaskStatus.CANCELLED,
            TaskStatus.SUPERSEDED,
        }
    ),
    TaskStatus.REJECTED: frozenset(
        {
            TaskStatus.ARCHIVED,
        }
    ),
    TaskStatus.CANCELLED: frozenset(
        {
            TaskStatus.REOPENED,
            TaskStatus.ARCHIVED,
        }
    ),
    TaskStatus.SUPERSEDED: frozenset(
        {
            TaskStatus.ARCHIVED,
        }
    ),
    TaskStatus.ARCHIVED: frozenset(),
}


def transition_allowed(
    previous: TaskStatus,
    next_state: TaskStatus,
) -> bool:
    return (
        next_state
        in LEGAL_TRANSITIONS[
            previous
        ]
    )

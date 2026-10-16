#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable, Mapping, Sequence

from runtime.translucent.blot_reconstruction import (
    BlotReconstructionError,
    ExecutionContract,
    OpusWorkUnit,
    ReconstructionPipeline,
    Stage,
    all_stages,
)


name = "blot."
schema = "savant.translucent.blot.opus.v1"
authority_effect = "none"
projection_only = True

max_parallel_work = 8
max_retries_per_method = 3
max_candidate_branches = 16
max_receipts = 8192


class BlotOpusError(BlotReconstructionError):
    pass


class WorkState(str, Enum):
    pending = "pending"
    ready = "ready"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    blocked = "blocked"
    rejected = "rejected"


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(
        _canonical(value).encode("utf-8")
    ).hexdigest()


def _text(value: Any, label: str) -> str:
    result = str(value).strip()

    if not result:
        raise BlotOpusError(
            f"{label} is required"
        )

    return result


def _unique(values: Iterable[Any]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            str(value).strip()
            for value in values
            if str(value).strip()
        )
    )


@dataclass(frozen=True, slots=True)
class TypedSegue:
    segue_id: str
    source_id: str
    target_id: str
    relation: str
    payload_digest: str
    provenance: tuple[str, ...] = ()
    lineage: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        return {
            "schema":
                "savant.segue.v1",

            "segue_id":
                _text(
                    self.segue_id,
                    "segue_id",
                ),

            "source_id":
                _text(
                    self.source_id,
                    "source_id",
                ),

            "target_id":
                _text(
                    self.target_id,
                    "target_id",
                ),

            "relation":
                _text(
                    self.relation,
                    "relation",
                ),

            "payload_digest":
                _text(
                    self.payload_digest,
                    "payload_digest",
                ),

            "provenance":
                list(
                    _unique(
                        self.provenance
                    )
                ),

            "lineage":
                list(
                    _unique(
                        self.lineage
                    )
                ),

            "authority_effect":
                "none",
        }


@dataclass(frozen=True, slots=True)
class WorkReceipt:
    work_id: str
    stage_id: str
    state: WorkState
    attempt: int
    input_digest: str
    output_digest: str | None = None
    provider: str | None = None
    method: str | None = None
    failure_class: str | None = None
    failure_reason: str | None = None
    provenance: tuple[str, ...] = ()
    lineage: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        if self.attempt < 0:
            raise BlotOpusError(
                "attempt cannot be negative"
            )

        return {
            "schema":
                f"{schema}.work-receipt",

            "work_id":
                _text(
                    self.work_id,
                    "work_id",
                ),

            "stage_id":
                _text(
                    self.stage_id,
                    "stage_id",
                ),

            "state":
                self.state.value,

            "attempt":
                self.attempt,

            "input_digest":
                _text(
                    self.input_digest,
                    "input_digest",
                ),

            "output_digest":
                self.output_digest,

            "provider":
                self.provider,

            "method":
                self.method,

            "failure_class":
                self.failure_class,

            "failure_reason":
                self.failure_reason,

            "provenance":
                list(
                    _unique(
                        self.provenance
                    )
                ),

            "lineage":
                list(
                    _unique(
                        self.lineage
                    )
                ),

            "authority_effect":
                "none",

            "mutation_effect":
                "none",
        }


@dataclass(frozen=True, slots=True)
class ProviderCapability:
    provider_id: str
    capabilities: tuple[str, ...]
    deterministic: bool = False
    local: bool = False
    priority: int = 100
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    def supports(
        self,
        capability: str,
    ) -> bool:
        capability = _text(
            capability,
            "capability",
        )

        capabilities = set(
            _unique(
                self.capabilities
            )
        )

        return (
            capability in capabilities
            or "*" in capabilities
        )

    def normalized(self) -> dict[str, Any]:
        return {
            "provider_id":
                _text(
                    self.provider_id,
                    "provider_id",
                ),

            "capabilities":
                list(
                    _unique(
                        self.capabilities
                    )
                ),

            "deterministic":
                bool(
                    self.deterministic
                ),

            "local":
                bool(
                    self.local
                ),

            "priority":
                int(
                    self.priority
                ),

            "metadata":
                dict(
                    self.metadata
                ),
        }


class ProviderRegistry:
    def __init__(
        self,
        providers: Iterable[
            ProviderCapability
        ] = (),
    ) -> None:
        self._providers: dict[
            str,
            ProviderCapability,
        ] = {}

        for provider in providers:
            self.register(
                provider
            )

    def register(
        self,
        provider: ProviderCapability,
    ) -> None:
        provider_id = _text(
            provider.provider_id,
            "provider_id",
        )

        existing = self._providers.get(
            provider_id
        )

        if (
            existing is not None
            and existing.normalized()
            != provider.normalized()
        ):
            raise BlotOpusError(
                "conflicting provider registration: "
                f"{provider_id}"
            )

        self._providers[
            provider_id
        ] = provider

    def resolve(
        self,
        capability: str,
        *,
        preferred: Sequence[str] = (),
        deterministic_required: bool = False,
    ) -> tuple[ProviderCapability, ...]:
        preferred_order = {
            provider_id: index
            for index, provider_id
            in enumerate(
                _unique(
                    preferred
                )
            )
        }

        providers = [
            provider
            for provider
            in self._providers.values()
            if provider.supports(
                capability
            )
            and (
                not deterministic_required
                or provider.deterministic
            )
        ]

        providers.sort(
            key=lambda provider: (
                preferred_order.get(
                    provider.provider_id,
                    len(
                        preferred_order
                    )
                    + 1,
                ),
                provider.priority,
                0
                if provider.local
                else 1,
                provider.provider_id,
            )
        )

        return tuple(
            providers
        )


@dataclass(frozen=True, slots=True)
class StageResult:
    stage_id: str
    work_id: str
    payload: Mapping[str, Any]
    provider: str
    method: str
    confidence: float = 1.0
    provenance: tuple[str, ...] = ()
    lineage: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        confidence = float(
            self.confidence
        )

        if not 0.0 <= confidence <= 1.0:
            raise BlotOpusError(
                "confidence must be between zero and one"
            )

        result = {
            "schema":
                f"{schema}.stage-result",

            "stage_id":
                _text(
                    self.stage_id,
                    "stage_id",
                ),

            "work_id":
                _text(
                    self.work_id,
                    "work_id",
                ),

            "payload":
                dict(
                    self.payload
                ),

            "provider":
                _text(
                    self.provider,
                    "provider",
                ),

            "method":
                _text(
                    self.method,
                    "method",
                ),

            "confidence":
                confidence,

            "provenance":
                list(
                    _unique(
                        self.provenance
                    )
                ),

            "lineage":
                list(
                    _unique(
                        self.lineage
                    )
                ),

            "authority_effect":
                "none",

            "projection_only":
                True,
        }

        result["digest"] = _digest(
            result
        )

        return result


@dataclass(frozen=True, slots=True)
class Counterfactual:
    candidate_id: str
    construction_digest: str
    method: str
    predicted_quality: Mapping[str, float]
    predicted_cost: Mapping[str, float]
    risks: tuple[str, ...] = ()
    violations: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        return {
            "candidate_id":
                _text(
                    self.candidate_id,
                    "candidate_id",
                ),

            "construction_digest":
                _text(
                    self.construction_digest,
                    "construction_digest",
                ),

            "method":
                _text(
                    self.method,
                    "method",
                ),

            "predicted_quality":
                {
                    str(key):
                        float(value)
                    for key, value
                    in self.predicted_quality.items()
                },

            "predicted_cost":
                {
                    str(key):
                        float(value)
                    for key, value
                    in self.predicted_cost.items()
                },

            "risks":
                list(
                    _unique(
                        self.risks
                    )
                ),

            "violations":
                list(
                    _unique(
                        self.violations
                    )
                ),
        }


@dataclass(frozen=True, slots=True)
class SelectionPolicy:
    fidelity_weight: float = 1.0
    structural_weight: float = 1.0
    editability_weight: float = 0.75
    economy_weight: float = 0.75
    compatibility_weight: float = 0.5
    complexity_penalty: float = 0.25
    risk_penalty: float = 0.5

    def score(
        self,
        candidate: Counterfactual,
    ) -> float:
        quality = candidate.predicted_quality
        cost = candidate.predicted_cost

        value = (
            self.fidelity_weight
            * float(
                quality.get(
                    "fidelity",
                    0.0,
                )
            )
            + self.structural_weight
            * float(
                quality.get(
                    "structural",
                    0.0,
                )
            )
            + self.editability_weight
            * float(
                quality.get(
                    "editability",
                    0.0,
                )
            )
            + self.economy_weight
            * float(
                quality.get(
                    "economy",
                    0.0,
                )
            )
            + self.compatibility_weight
            * float(
                quality.get(
                    "compatibility",
                    0.0,
                )
            )
        )

        complexity = sum(
            max(
                0.0,
                float(value),
            )
            for value
            in cost.values()
        )

        value -= (
            self.complexity_penalty
            * complexity
        )

        value -= (
            self.risk_penalty
            * len(
                candidate.risks
            )
        )

        if candidate.violations:
            return float(
                "-inf"
            )

        return value


class CounterfactualSelector:
    def __init__(
        self,
        policy: SelectionPolicy | None = None,
    ) -> None:
        self.policy = (
            policy
            if policy is not None
            else SelectionPolicy()
        )

    def select(
        self,
        candidates: Sequence[
            Counterfactual
        ],
    ) -> Counterfactual:
        if not candidates:
            raise BlotOpusError(
                "no counterfactual candidates supplied"
            )

        if len(candidates) > max_candidate_branches:
            raise BlotOpusError(
                "counterfactual candidate limit exceeded"
            )

        ranked = sorted(
            candidates,
            key=lambda candidate: (
                -self.policy.score(
                    candidate
                ),
                candidate.candidate_id,
            ),
        )

        winner = ranked[0]

        if self.policy.score(
            winner
        ) == float(
            "-inf"
        ):
            raise BlotOpusError(
                "all counterfactual candidates violate constraints"
            )

        return winner


class DependencyGraph:
    def __init__(
        self,
        units: Sequence[OpusWorkUnit],
    ) -> None:
        self.units = {
            unit.work_id:
                unit
            for unit
            in units
        }

        if len(self.units) != len(units):
            raise BlotOpusError(
                "duplicate opus work id"
            )

        for unit in units:
            for dependency in unit.dependencies:
                if dependency not in self.units:
                    raise BlotOpusError(
                        "unknown work dependency: "
                        f"{dependency}"
                    )

        self._assert_acyclic()

    def _assert_acyclic(
        self,
    ) -> None:
        temporary: set[str] = set()
        permanent: set[str] = set()

        def visit(
            work_id: str,
        ) -> None:
            if work_id in permanent:
                return

            if work_id in temporary:
                raise BlotOpusError(
                    "opus work graph contains a cycle"
                )

            temporary.add(
                work_id
            )

            for dependency in self.units[
                work_id
            ].dependencies:
                visit(
                    dependency
                )

            temporary.remove(
                work_id
            )

            permanent.add(
                work_id
            )

        for work_id in sorted(
            self.units
        ):
            visit(
                work_id
            )

    def ready(
        self,
        states: Mapping[str, WorkState],
    ) -> tuple[OpusWorkUnit, ...]:
        ready: list[OpusWorkUnit] = []

        for work_id in sorted(
            self.units
        ):
            state = states.get(
                work_id,
                WorkState.pending,
            )

            if state not in {
                WorkState.pending,
                WorkState.ready,
            }:
                continue

            unit = self.units[
                work_id
            ]

            dependency_states = [
                states.get(
                    dependency,
                    WorkState.pending,
                )
                for dependency
                in unit.dependencies
            ]

            if any(
                state
                in {
                    WorkState.failed,
                    WorkState.blocked,
                    WorkState.rejected,
                }
                for state
                in dependency_states
            ):
                continue

            if all(
                state
                == WorkState.succeeded
                for state
                in dependency_states
            ):
                ready.append(
                    unit
                )

        return tuple(
            ready[
                :max_parallel_work
            ]
        )


class OrchestrationSession:
    def __init__(
        self,
        pipeline: ReconstructionPipeline,
        *,
        provider_registry: ProviderRegistry | None = None,
    ) -> None:
        self.pipeline = pipeline
        self.provider_registry = (
            provider_registry
            if provider_registry is not None
            else ProviderRegistry()
        )

        self._states: dict[
            str,
            WorkState,
        ] = {}

        self._receipts: list[
            WorkReceipt
        ] = []

        self._results: dict[
            str,
            StageResult,
        ] = {}

        self._segues: list[
            TypedSegue
        ] = []

    @property
    def receipts(
        self,
    ) -> tuple[WorkReceipt, ...]:
        return tuple(
            self._receipts
        )

    @property
    def results(
        self,
    ) -> Mapping[str, StageResult]:
        return dict(
            self._results
        )

    @property
    def segues(
        self,
    ) -> tuple[TypedSegue, ...]:
        return tuple(
            self._segues
        )

    def _append_receipt(
        self,
        receipt: WorkReceipt,
    ) -> None:
        if len(self._receipts) >= max_receipts:
            raise BlotOpusError(
                "work receipt limit exceeded"
            )

        self._receipts.append(
            receipt
        )

    def graph(
        self,
        rung: int,
    ) -> DependencyGraph:
        return DependencyGraph(
            self.pipeline.opus_plan(
                rung
            )
        )

    def ready(
        self,
        rung: int,
    ) -> tuple[OpusWorkUnit, ...]:
        return self.graph(
            rung
        ).ready(
            self._states
        )

    def state(
        self,
        work_id: str,
    ) -> WorkState:
        return self._states.get(
            work_id,
            WorkState.pending,
        )

    def begin(
        self,
        unit: OpusWorkUnit,
        *,
        provider: str,
        method: str,
        attempt: int,
    ) -> WorkReceipt:
        if not 1 <= attempt <= max_retries_per_method:
            raise BlotOpusError(
                "attempt outside retry policy"
            )

        current = self.state(
            unit.work_id
        )

        if current not in {
            WorkState.pending,
            WorkState.ready,
            WorkState.failed,
        }:
            raise BlotOpusError(
                "work unit cannot begin from state "
                f"{current.value}"
            )

        input_digest = _digest(
            unit.normalized()
        )

        receipt = WorkReceipt(
            work_id=unit.work_id,
            stage_id=unit.stage_id,
            state=WorkState.running,
            attempt=attempt,
            input_digest=input_digest,
            provider=provider,
            method=method,
            provenance=(
                "orchestrator:opus",
                "requester:blot.",
            ),
        )

        self._states[
            unit.work_id
        ] = WorkState.running

        self._append_receipt(
            receipt
        )

        return receipt

    def succeed(
        self,
        unit: OpusWorkUnit,
        result: StageResult,
        *,
        attempt: int,
    ) -> WorkReceipt:
        if self.state(
            unit.work_id
        ) != WorkState.running:
            raise BlotOpusError(
                "work unit is not running"
            )

        normalized = result.normalized()

        if normalized[
            "work_id"
        ] != unit.work_id:
            raise BlotOpusError(
                "stage result work id mismatch"
            )

        if normalized[
            "stage_id"
        ] != unit.stage_id:
            raise BlotOpusError(
                "stage result stage id mismatch"
            )

        self._results[
            unit.work_id
        ] = result

        self._states[
            unit.work_id
        ] = WorkState.succeeded

        receipt = WorkReceipt(
            work_id=unit.work_id,
            stage_id=unit.stage_id,
            state=WorkState.succeeded,
            attempt=attempt,
            input_digest=_digest(
                unit.normalized()
            ),
            output_digest=normalized[
                "digest"
            ],
            provider=result.provider,
            method=result.method,
            provenance=result.provenance,
            lineage=result.lineage,
        )

        self._append_receipt(
            receipt
        )

        for dependency in unit.dependencies:
            dependency_result = self._results.get(
                dependency
            )

            if dependency_result is None:
                continue

            dependency_digest = (
                dependency_result.normalized()[
                    "digest"
                ]
            )

            segue_substance = {
                "source_id":
                    dependency,

                "target_id":
                    unit.work_id,

                "relation":
                    "feeds",

                "payload_digest":
                    dependency_digest,
            }

            self._segues.append(
                TypedSegue(
                    segue_id=(
                        "segue-"
                        + _digest(
                            segue_substance
                        )[:24]
                    ),
                    source_id=dependency,
                    target_id=unit.work_id,
                    relation="feeds",
                    payload_digest=dependency_digest,
                    provenance=(
                        "orchestrator:opus",
                    ),
                    lineage=(
                        dependency_digest,
                        normalized[
                            "digest"
                        ],
                    ),
                )
            )

        return receipt

    def fail(
        self,
        unit: OpusWorkUnit,
        *,
        attempt: int,
        provider: str,
        method: str,
        failure_class: str,
        failure_reason: str,
    ) -> WorkReceipt:
        if self.state(
            unit.work_id
        ) != WorkState.running:
            raise BlotOpusError(
                "work unit is not running"
            )

        receipt = WorkReceipt(
            work_id=unit.work_id,
            stage_id=unit.stage_id,
            state=WorkState.failed,
            attempt=attempt,
            input_digest=_digest(
                unit.normalized()
            ),
            provider=provider,
            method=method,
            failure_class=_text(
                failure_class,
                "failure_class",
            ),
            failure_reason=_text(
                failure_reason,
                "failure_reason",
            ),
            provenance=(
                "orchestrator:opus",
                "requester:blot.",
            ),
        )

        self._states[
            unit.work_id
        ] = WorkState.failed

        self._append_receipt(
            receipt
        )

        return receipt

    def block(
        self,
        unit: OpusWorkUnit,
        *,
        reason: str,
    ) -> WorkReceipt:
        receipt = WorkReceipt(
            work_id=unit.work_id,
            stage_id=unit.stage_id,
            state=WorkState.blocked,
            attempt=0,
            input_digest=_digest(
                unit.normalized()
            ),
            failure_class="dependency",
            failure_reason=_text(
                reason,
                "reason",
            ),
            provenance=(
                "orchestrator:opus",
                "requester:blot.",
            ),
        )

        self._states[
            unit.work_id
        ] = WorkState.blocked

        self._append_receipt(
            receipt
        )

        return receipt

    def resolve_providers(
        self,
        unit: OpusWorkUnit,
    ) -> tuple[ProviderCapability, ...]:
        return self.provider_registry.resolve(
            unit.capability,
            preferred=unit.preferred_providers,
            deterministic_required=(
                unit.deterministic
            ),
        )

    def execution_packet(
        self,
        contract: ExecutionContract,
    ) -> dict[str, Any]:
        normalized = contract.normalized()

        if not normalized[
            "execution_ready"
        ]:
            raise BlotOpusError(
                "execution contract is blocked"
            )

        result = {
            "schema":
                f"{schema}.execution-packet",

            "owner":
                "opus",

            "requester":
                "blot.",

            "contract":
                normalized,

            "rung":
                3,

            "work":
                [
                    unit.normalized()
                    for unit
                    in self.pipeline.opus_plan(
                        3
                    )
                ],

            "segues":
                [
                    segue.normalized()
                    for segue
                    in self._segues
                ],

            "authority_effect":
                "none",

            "mutation_effect":
                "none",

            "projection_only":
                True,
        }

        result["digest"] = _digest(
            result
        )

        return result

    def replay_manifest(
        self,
    ) -> dict[str, Any]:
        result = {
            "schema":
                f"{schema}.replay",

            "source_digest":
                self.pipeline.source_digest,

            "construction_digest":
                self.pipeline.construction_graph()[
                    "digest"
                ],

            "states":
                {
                    key:
                        self._states[key].value
                    for key
                    in sorted(
                        self._states
                    )
                },

            "receipts":
                [
                    receipt.normalized()
                    for receipt
                    in self._receipts
                ],

            "results":
                [
                    self._results[key].normalized()
                    for key
                    in sorted(
                        self._results
                    )
                ],

            "segues":
                [
                    segue.normalized()
                    for segue
                    in self._segues
                ],

            "authority_effect":
                "none",

            "projection_only":
                True,
        }

        result["digest"] = _digest(
            result
        )

        return result


class OpusAdapter:
    def __init__(
        self,
        dispatch: Callable[
            [Mapping[str, Any]],
            Mapping[str, Any],
        ],
    ) -> None:
        self.dispatch = dispatch

    def execute(
        self,
        unit: OpusWorkUnit,
        *,
        provider: ProviderCapability,
        attempt: int,
    ) -> StageResult:
        request = {
            "schema":
                "savant.opus.request.v1",

            "owner":
                "opus",

            "requester":
                "blot.",

            "provider":
                provider.provider_id,

            "attempt":
                attempt,

            "work":
                unit.normalized(),

            "authority_effect":
                "none",

            "mutation_effect":
                "none",
        }

        response = dict(
            self.dispatch(
                request
            )
        )

        payload = response.get(
            "payload"
        )

        if not isinstance(
            payload,
            Mapping,
        ):
            raise BlotOpusError(
                "opus provider returned invalid payload"
            )

        return StageResult(
            stage_id=unit.stage_id,
            work_id=unit.work_id,
            payload=dict(
                payload
            ),
            provider=provider.provider_id,
            method=str(
                response.get(
                    "method",
                    "provider",
                )
            ),
            confidence=float(
                response.get(
                    "confidence",
                    1.0,
                )
            ),
            provenance=tuple(
                response.get(
                    "provenance",
                    (),
                )
            ),
            lineage=tuple(
                response.get(
                    "lineage",
                    (),
                )
            ),
        )


def stage_index() -> dict[str, Stage]:
    return {
        stage.stage_id:
            stage
        for stage
        in all_stages
    }


def selftest() -> dict[str, Any]:
    pipeline = ReconstructionPipeline(
        source_digest="opus-source-test",
        preferred_providers=(
            "local-deterministic",
        ),
    )

    registry = ProviderRegistry(
        (
            ProviderCapability(
                provider_id="local-deterministic",
                capabilities=("*",),
                deterministic=True,
                local=True,
                priority=1,
            ),
        )
    )

    session = OrchestrationSession(
        pipeline,
        provider_registry=registry,
    )

    ready = session.ready(
        1
    )

    if not ready:
        raise BlotOpusError(
            "rung one produced no ready work"
        )

    first = ready[0]

    providers = session.resolve_providers(
        first
    )

    if not providers:
        raise BlotOpusError(
            "provider resolution failed"
        )

    provider = providers[0]

    session.begin(
        first,
        provider=provider.provider_id,
        method="selftest",
        attempt=1,
    )

    result = StageResult(
        stage_id=first.stage_id,
        work_id=first.work_id,
        payload={
            "ok": True,
        },
        provider=provider.provider_id,
        method="selftest",
        confidence=1.0,
        provenance=(
            "selftest",
        ),
    )

    session.succeed(
        first,
        result,
        attempt=1,
    )

    replay_a = session.replay_manifest()
    replay_b = session.replay_manifest()

    checks = {
        "name_exact":
            name
            == "blot.",

        "authority_none":
            authority_effect
            == "none",

        "projection_only":
            projection_only
            is True,

        "provider_resolved":
            provider.provider_id
            == "local-deterministic",

        "work_succeeded":
            session.state(
                first.work_id
            )
            == WorkState.succeeded,

        "receipt_created":
            len(
                session.receipts
            )
            == 2,

        "result_preserved":
            first.work_id
            in session.results,

        "deterministic_replay":
            replay_a
            == replay_b,

        "all_stages_indexed":
            len(
                stage_index()
            )
            == len(
                all_stages
            ),
    }

    return {
        "schema":
            f"{schema}.selftest",

        "ok":
            all(
                checks.values()
            ),

        "checks":
            checks,

        "replay_digest":
            replay_a[
                "digest"
            ],
    }


__all__ = [
    "BlotOpusError",
    "Counterfactual",
    "CounterfactualSelector",
    "DependencyGraph",
    "OpusAdapter",
    "OrchestrationSession",
    "ProviderCapability",
    "ProviderRegistry",
    "SelectionPolicy",
    "StageResult",
    "TypedSegue",
    "WorkReceipt",
    "WorkState",
    "authority_effect",
    "max_candidate_branches",
    "max_parallel_work",
    "max_retries_per_method",
    "name",
    "projection_only",
    "schema",
    "selftest",
    "stage_index",
]


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )

#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


OWNER = "opus"
SCHEMA = "savant://opus/cognitive-orchestration/1"


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}:{digest(value)[:24]}"


def unique_strings(
    values: Iterable[str] = (),
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(value).strip()
                for value in values
                if str(value).strip()
            }
        )
    )


@dataclass(frozen=True)
class Budget:
    maximum_calls: int = 64
    maximum_parallelism: int = 16
    maximum_rounds: int = 8
    maximum_depth: int = 8
    maximum_cost: float | None = None
    deadline_epoch: float | None = None

    def projection(self) -> dict[str, Any]:
        return {
            "maximum_calls": self.maximum_calls,
            "maximum_parallelism": self.maximum_parallelism,
            "maximum_rounds": self.maximum_rounds,
            "maximum_depth": self.maximum_depth,
            "maximum_cost": self.maximum_cost,
            "deadline_epoch": self.deadline_epoch,
        }


@dataclass(frozen=True)
class EvidenceReference:
    source_ref: str
    claim_ref: str | None = None
    authority_class: str = "unknown"
    supports: tuple[str, ...] = ()
    challenges: tuple[str, ...] = ()

    @property
    def id(self) -> str:
        return stable_id(
            "opus-evidence",
            self.projection(include_id=False),
        )

    def projection(
        self,
        *,
        include_id: bool = True,
    ) -> dict[str, Any]:
        result = {
            "source_ref": self.source_ref,
            "claim_ref": self.claim_ref,
            "authority_class": self.authority_class,
            "supports": list(
                unique_strings(self.supports)
            ),
            "challenges": list(
                unique_strings(self.challenges)
            ),
        }
        if include_id:
            result["id"] = self.id
        return result


@dataclass(frozen=True)
class Hypothesis:
    statement: str
    epistemic_class: str = "hypothesis"
    evidence_refs: tuple[str, ...] = ()
    counterevidence_refs: tuple[str, ...] = ()
    parent_refs: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def id(self) -> str:
        return stable_id(
            "opus-hypothesis",
            self.projection(include_id=False),
        )

    def projection(
        self,
        *,
        include_id: bool = True,
    ) -> dict[str, Any]:
        result = {
            "statement": self.statement,
            "epistemic_class": self.epistemic_class,
            "evidence_refs": list(
                unique_strings(
                    self.evidence_refs
                )
            ),
            "counterevidence_refs": list(
                unique_strings(
                    self.counterevidence_refs
                )
            ),
            "parent_refs": list(
                unique_strings(
                    self.parent_refs
                )
            ),
            "assumptions": list(
                unique_strings(
                    self.assumptions
                )
            ),
            "unresolved": list(
                unique_strings(
                    self.unresolved
                )
            ),
        }
        if include_id:
            result["id"] = self.id
        return result


@dataclass(frozen=True)
class Argument:
    hypothesis_ref: str
    stance: str
    statement: str
    evidence_refs: tuple[str, ...] = ()
    dependency_refs: tuple[str, ...] = ()

    @property
    def id(self) -> str:
        return stable_id(
            "opus-argument",
            self.projection(include_id=False),
        )

    def projection(
        self,
        *,
        include_id: bool = True,
    ) -> dict[str, Any]:
        result = {
            "hypothesis_ref": self.hypothesis_ref,
            "stance": self.stance,
            "statement": self.statement,
            "evidence_refs": list(
                unique_strings(
                    self.evidence_refs
                )
            ),
            "dependency_refs": list(
                unique_strings(
                    self.dependency_refs
                )
            ),
        }
        if include_id:
            result["id"] = self.id
        return result


@dataclass(frozen=True)
class InferenceReceipt:
    task_ref: str
    role: str
    provider: str | None
    model: str | None
    response_digest: str
    lineage_refs: tuple[str, ...] = ()
    failure: str | None = None
    latency_ms: float | None = None
    cost: float | None = None

    @property
    def id(self) -> str:
        return stable_id(
            "opus-receipt",
            self.projection(include_id=False),
        )

    def projection(
        self,
        *,
        include_id: bool = True,
    ) -> dict[str, Any]:
        result = {
            "task_ref": self.task_ref,
            "role": self.role,
            "provider": self.provider,
            "model": self.model,
            "response_digest": (
                self.response_digest
            ),
            "lineage_refs": list(
                unique_strings(
                    self.lineage_refs
                )
            ),
            "failure": self.failure,
            "latency_ms": self.latency_ms,
            "cost": self.cost,
            "authority_effect": "none",
        }
        if include_id:
            result["id"] = self.id
        return result


@dataclass
class CognitiveLedger:
    hypotheses: dict[
        str,
        Hypothesis,
    ] = field(default_factory=dict)
    arguments: dict[
        str,
        Argument,
    ] = field(default_factory=dict)
    evidence: dict[
        str,
        EvidenceReference,
    ] = field(default_factory=dict)
    receipts: dict[
        str,
        InferenceReceipt,
    ] = field(default_factory=dict)
    unresolved: set[str] = field(
        default_factory=set
    )

    def add_hypothesis(
        self,
        value: Hypothesis,
    ) -> Hypothesis:
        self.hypotheses[value.id] = value
        return value

    def add_argument(
        self,
        value: Argument,
    ) -> Argument:
        self.arguments[value.id] = value
        return value

    def add_evidence(
        self,
        value: EvidenceReference,
    ) -> EvidenceReference:
        self.evidence[value.id] = value
        return value

    def add_receipt(
        self,
        value: InferenceReceipt,
    ) -> InferenceReceipt:
        self.receipts[value.id] = value
        return value

    def projection(self) -> dict[str, Any]:
        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "hypotheses": [
                self.hypotheses[key].projection()
                for key in sorted(
                    self.hypotheses
                )
            ],
            "arguments": [
                self.arguments[key].projection()
                for key in sorted(
                    self.arguments
                )
            ],
            "evidence": [
                self.evidence[key].projection()
                for key in sorted(
                    self.evidence
                )
            ],
            "receipts": [
                self.receipts[key].projection()
                for key in sorted(
                    self.receipts
                )
            ],
            "unresolved": sorted(
                self.unresolved
            ),
            "authority_effect": "none",
        }
        result["projection_digest"] = digest(
            result
        )
        return result


@dataclass(frozen=True)
class CognitiveTask:
    instruction: str
    context: Mapping[str, Any] = field(
        default_factory=dict
    )
    required_capabilities: tuple[
        str,
        ...
    ] = ()
    required_layers: tuple[
        str,
        ...
    ] = ()
    parent_ref: str | None = None
    dependency_refs: tuple[str, ...] = ()
    depth: int = 0

    @property
    def id(self) -> str:
        return stable_id(
            "opus-task",
            {
                "instruction": self.instruction,
                "context": dict(
                    self.context
                ),
                "required_capabilities": (
                    list(
                        unique_strings(
                            self.required_capabilities
                        )
                    )
                ),
                "required_layers": list(
                    unique_strings(
                        self.required_layers
                    )
                ),
                "parent_ref": self.parent_ref,
                "dependency_refs": list(
                    unique_strings(
                        self.dependency_refs
                    )
                ),
                "depth": self.depth,
            },
        )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "instruction": self.instruction,
            "context": dict(self.context),
            "required_capabilities": list(
                unique_strings(
                    self.required_capabilities
                )
            ),
            "required_layers": list(
                unique_strings(
                    self.required_layers
                )
            ),
            "parent_ref": self.parent_ref,
            "dependency_refs": list(
                unique_strings(
                    self.dependency_refs
                )
            ),
            "depth": self.depth,
        }

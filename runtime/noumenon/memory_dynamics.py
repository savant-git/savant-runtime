from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/memory-dynamics/1"


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(
    value: Any,
) -> str:
    return sha256(
        _canonical_json(value).encode(
            "utf-8"
        )
    ).hexdigest()


def _unit(
    value: float,
) -> float:
    return max(
        0.0,
        min(
            1.0,
            float(value),
        ),
    )


@dataclass(frozen=True, slots=True)
class MemoryTrace:
    memory_ref: str
    retention: float
    significance: float
    accessibility: float
    residual_effect: float
    reconstruction_uncertainty: float = 0.0
    causal_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.memory_ref:
            raise ValueError(
                "memory_ref is required"
            )

        values = (
            self.retention,
            self.significance,
            self.accessibility,
            self.residual_effect,
            self.reconstruction_uncertainty,
        )

        if any(
            not (
                0.0
                <= float(value)
                <= 1.0
            )
            for value in values
        ):
            raise ValueError(
                "memory dynamics values must "
                "be between 0 and 1"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "memory_ref": self.memory_ref,
            "retention": float(
                self.retention
            ),
            "significance": float(
                self.significance
            ),
            "accessibility": float(
                self.accessibility
            ),
            "residual_effect": float(
                self.residual_effect
            ),
            "reconstruction_uncertainty": (
                float(
                    self
                    .reconstruction_uncertainty
                )
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "authority_effect": "none",
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )

    @property
    def id(self) -> str:
        return (
            "noumenon-memory-trace:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class ForgettingPolicy:
    decay: float
    significance_protection: float
    residual_decay: float

    def __post_init__(self) -> None:
        for value in (
            self.decay,
            self.significance_protection,
            self.residual_decay,
        ):
            if not (
                0.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "forgetting policy values "
                    "must be between 0 and 1"
                )


@dataclass(frozen=True, slots=True)
class Reconstruction:
    memory_ref: str
    source_trace_ref: str
    confidence: float
    uncertainty: float
    causal_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.memory_ref:
            raise ValueError(
                "memory_ref is required"
            )

        if not self.source_trace_ref:
            raise ValueError(
                "source_trace_ref is required"
            )

        if not (
            0.0
            <= float(self.confidence)
            <= 1.0
        ):
            raise ValueError(
                "confidence must be between "
                "0 and 1"
            )

        if not (
            0.0
            <= float(self.uncertainty)
            <= 1.0
        ):
            raise ValueError(
                "uncertainty must be between "
                "0 and 1"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "memory_ref": self.memory_ref,
            "source_trace_ref": (
                self.source_trace_ref
            ),
            "confidence": float(
                self.confidence
            ),
            "uncertainty": float(
                self.uncertainty
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "derived": True,
            "authoritative": False,
        }

        body["digest"] = _digest(
            body
        )

        return body


def forget(
    trace: MemoryTrace,
    *,
    policy: ForgettingPolicy,
) -> MemoryTrace:
    protection = _unit(
        float(trace.significance)
        * float(
            policy.significance_protection
        )
    )

    effective_decay = (
        float(policy.decay)
        * (
            1.0 - protection
        )
    )

    retention = _unit(
        float(trace.retention)
        * (
            1.0 - effective_decay
        )
    )

    accessibility = _unit(
        min(
            float(trace.accessibility),
            retention,
        )
    )

    residual_effect = _unit(
        float(trace.residual_effect)
        * (
            1.0
            - float(
                policy.residual_decay
            )
        )
    )

    uncertainty = _unit(
        max(
            float(
                trace
                .reconstruction_uncertainty
            ),
            1.0 - accessibility,
        )
    )

    return MemoryTrace(
        memory_ref=trace.memory_ref,
        retention=retention,
        significance=trace.significance,
        accessibility=accessibility,
        residual_effect=residual_effect,
        reconstruction_uncertainty=(
            uncertainty
        ),
        causal_refs=tuple(
            dict.fromkeys(
                (
                    *trace.causal_refs,
                    trace.id,
                )
            )
        ),
        evidence_refs=(
            trace.evidence_refs
        ),
    )


def reconstruct(
    trace: MemoryTrace,
    *,
    causal_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
) -> Reconstruction:
    confidence = _unit(
        float(trace.accessibility)
        * (
            1.0
            - float(
                trace
                .reconstruction_uncertainty
            )
        )
    )

    uncertainty = _unit(
        1.0 - confidence
    )

    return Reconstruction(
        memory_ref=trace.memory_ref,
        source_trace_ref=trace.id,
        confidence=confidence,
        uncertainty=uncertainty,
        causal_refs=tuple(
            dict.fromkeys(
                (
                    *trace.causal_refs,
                    trace.id,
                    *(
                        str(value)
                        for value
                        in causal_refs
                    ),
                )
            )
        ),
        evidence_refs=tuple(
            dict.fromkeys(
                (
                    *trace.evidence_refs,
                    *(
                        str(value)
                        for value
                        in evidence_refs
                    ),
                )
            )
        ),
    )


def reconsolidate(
    trace: MemoryTrace,
    reconstruction: Reconstruction,
    *,
    significance: float | None = None,
) -> MemoryTrace:
    if (
        reconstruction.memory_ref
        != trace.memory_ref
    ):
        raise ValueError(
            "reconstruction memory mismatch"
        )

    if (
        reconstruction.source_trace_ref
        != trace.id
    ):
        raise ValueError(
            "reconstruction lineage mismatch"
        )

    next_significance = (
        trace.significance
        if significance is None
        else float(significance)
    )

    if not (
        0.0
        <= next_significance
        <= 1.0
    ):
        raise ValueError(
            "significance must be between "
            "0 and 1"
        )

    return MemoryTrace(
        memory_ref=trace.memory_ref,
        retention=trace.retention,
        significance=next_significance,
        accessibility=trace.accessibility,
        residual_effect=(
            trace.residual_effect
        ),
        reconstruction_uncertainty=(
            max(
                float(
                    trace
                    .reconstruction_uncertainty
                ),
                float(
                    reconstruction.uncertainty
                ),
            )
        ),
        causal_refs=tuple(
            dict.fromkeys(
                (
                    *trace.causal_refs,
                    trace.id,
                    reconstruction
                    .projection()["digest"],
                )
            )
        ),
        evidence_refs=tuple(
            dict.fromkeys(
                (
                    *trace.evidence_refs,
                    *reconstruction
                    .evidence_refs,
                )
            )
        ),
    )


def residual_causality(
    trace: MemoryTrace,
) -> Mapping[str, Any]:
    return {
        "schema": SCHEMA,
        "memory_ref": trace.memory_ref,
        "accessible": (
            not math.isclose(
                trace.accessibility,
                0.0,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ),
        "residual_effect": float(
            trace.residual_effect
        ),
        "causally_active": (
            trace.residual_effect > 0.0
        ),
        "memory_accuracy_inferred": False,
        "interpretation_inferred": False,
        "derived": True,
        "authoritative": False,
    }

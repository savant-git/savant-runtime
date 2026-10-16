#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Sequence


def _normalized_text(value: Any) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .split()
    )


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


def _normalized_strings(
    values: Iterable[Any] | None,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                _normalized_text(value)
                for value in values or ()
                if _normalized_text(value)
            }
        )
    )


@dataclass(frozen=True)
class EvidenceClaim:
    claim_id: str
    text: str
    provider_id: str
    model: str | None = None
    support: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    validation: tuple[str, ...] = ()
    confidence: float | None = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "text": self.text,
            "provider_id": self.provider_id,
            "model": self.model,
            "support": list(self.support),
            "contradictions": list(
                self.contradictions
            ),
            "validation": list(
                self.validation
            ),
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class CognitiveCandidate:
    candidate_id: str
    provider_id: str
    text: str
    model: str | None = None
    role: str = "solver"
    latency_ms: float | None = None
    claims: tuple[EvidenceClaim, ...] = ()
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "provider_id": self.provider_id,
            "model": self.model,
            "role": self.role,
            "text": self.text,
            "latency_ms": self.latency_ms,
            "claims": [
                claim.as_dict()
                for claim in self.claims
            ],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class CognitiveEvidence:
    request_id: str
    strategy: str
    candidates: tuple[CognitiveCandidate, ...]
    agreements: tuple[str, ...] = ()
    disagreements: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()
    validation: tuple[str, ...] = ()
    created_at: float = field(
        default_factory=time.time
    )

    def as_dict(self) -> Dict[str, Any]:
        body = {
            "request_id": self.request_id,
            "strategy": self.strategy,
            "candidates": [
                candidate.as_dict()
                for candidate in self.candidates
            ],
            "agreements": list(
                self.agreements
            ),
            "disagreements": list(
                self.disagreements
            ),
            "unresolved": list(
                self.unresolved
            ),
            "validation": list(
                self.validation
            ),
            "created_at": self.created_at,
        }

        body["evidence_hash"] = _stable_hash(
            body
        )

        return body


def claim(
    text: str,
    *,
    provider_id: str,
    model: str | None = None,
    support: Iterable[str] | None = None,
    contradictions: Iterable[str] | None = None,
    validation: Iterable[str] | None = None,
    confidence: float | None = None,
) -> EvidenceClaim:
    normalized = _normalized_text(text)

    if not normalized:
        raise ValueError(
            "evidence claim requires text"
        )

    provider_value = _normalized_text(
        provider_id
    )

    if not provider_value:
        raise ValueError(
            "evidence claim requires provider_id"
        )

    bounded_confidence = None

    if confidence is not None:
        bounded_confidence = max(
            0.0,
            min(
                1.0,
                float(confidence),
            ),
        )

    identity = {
        "text": normalized,
        "provider_id": provider_value,
        "model": (
            _normalized_text(model)
            if model
            else None
        ),
    }

    return EvidenceClaim(
        claim_id=_stable_hash(identity)[:24],
        text=normalized,
        provider_id=provider_value,
        model=(
            _normalized_text(model)
            if model
            else None
        ),
        support=_normalized_strings(
            support
        ),
        contradictions=_normalized_strings(
            contradictions
        ),
        validation=_normalized_strings(
            validation
        ),
        confidence=bounded_confidence,
    )


def candidate(
    *,
    provider_id: str,
    text: str,
    model: str | None = None,
    role: str = "solver",
    latency_ms: float | None = None,
    claims: Sequence[EvidenceClaim] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> CognitiveCandidate:
    provider_value = _normalized_text(
        provider_id
    )
    text_value = str(
        text or ""
    ).strip()

    if not provider_value:
        raise ValueError(
            "candidate requires provider_id"
        )

    if not text_value:
        raise ValueError(
            "candidate requires text"
        )

    identity = {
        "provider_id": provider_value,
        "model": (
            _normalized_text(model)
            if model
            else None
        ),
        "role": _normalized_text(
            role
        ).lower(),
        "text": text_value,
    }

    return CognitiveCandidate(
        candidate_id=_stable_hash(
            identity
        )[:24],
        provider_id=provider_value,
        model=(
            _normalized_text(model)
            if model
            else None
        ),
        role=(
            _normalized_text(role).lower()
            or "solver"
        ),
        text=text_value,
        latency_ms=(
            float(latency_ms)
            if latency_ms is not None
            else None
        ),
        claims=tuple(
            claims or ()
        ),
        metadata=dict(
            metadata or {}
        ),
    )


def evidence_bundle(
    *,
    request_id: str,
    strategy: str,
    candidates: Sequence[CognitiveCandidate],
    agreements: Iterable[str] | None = None,
    disagreements: Iterable[str] | None = None,
    unresolved: Iterable[str] | None = None,
    validation: Iterable[str] | None = None,
) -> CognitiveEvidence:
    request_value = _normalized_text(
        request_id
    )
    strategy_value = _normalized_text(
        strategy
    ).lower()

    if not request_value:
        raise ValueError(
            "evidence bundle requires request_id"
        )

    if not strategy_value:
        raise ValueError(
            "evidence bundle requires strategy"
        )

    if not candidates:
        raise ValueError(
            "evidence bundle requires candidates"
        )

    return CognitiveEvidence(
        request_id=request_value,
        strategy=strategy_value,
        candidates=tuple(candidates),
        agreements=_normalized_strings(
            agreements
        ),
        disagreements=_normalized_strings(
            disagreements
        ),
        unresolved=_normalized_strings(
            unresolved
        ),
        validation=_normalized_strings(
            validation
        ),
    )

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/identity-drift/1"

DRIFT_CLASSES = frozenset(
    {
        "stable",
        "growth",
        "corruption",
        "state_loss",
        "provider_contamination",
        "ambiguous",
        "unknown",
    }
)


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
class DriftEvidence:
    source_ref: str
    continuity: float
    causal_support: float
    authority_support: float
    unexplained_change: float
    state_integrity: float
    provider_dependence: float
    contradiction: float = 0.0
    evidence_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_ref:
            raise ValueError(
                "source_ref is required"
            )

        for value in (
            self.continuity,
            self.causal_support,
            self.authority_support,
            self.unexplained_change,
            self.state_integrity,
            self.provider_dependence,
            self.contradiction,
        ):
            if not (
                0.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "drift evidence values "
                    "must be between 0 and 1"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "source_ref": self.source_ref,
            "continuity": float(
                self.continuity
            ),
            "causal_support": float(
                self.causal_support
            ),
            "authority_support": float(
                self.authority_support
            ),
            "unexplained_change": float(
                self.unexplained_change
            ),
            "state_integrity": float(
                self.state_integrity
            ),
            "provider_dependence": float(
                self.provider_dependence
            ),
            "contradiction": float(
                self.contradiction
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "authority_refs": list(
                self.authority_refs
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
            "noumenon-drift-evidence:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class DriftDiagnosis:
    drift_class: str
    confidence: float
    scores: Mapping[str, float]
    evidence_refs: tuple[str, ...]
    auto_revert: bool = False

    def __post_init__(self) -> None:
        if self.drift_class not in (
            DRIFT_CLASSES
        ):
            raise ValueError(
                "unsupported drift class"
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

        if self.auto_revert:
            raise ValueError(
                "identity drift diagnosis "
                "cannot authorize auto-revert"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "drift_class": (
                self.drift_class
            ),
            "confidence": float(
                self.confidence
            ),
            "scores": {
                key: float(value)
                for key, value
                in sorted(
                    self.scores.items()
                )
            },
            "evidence_refs": list(
                self.evidence_refs
            ),
            "auto_revert": False,
            "derived": True,
            "authoritative": False,
        }

        body["digest"] = _digest(
            body
        )

        return body


def diagnose_drift(
    evidence: Sequence[
        DriftEvidence
    ],
) -> DriftDiagnosis:
    if not evidence:
        return DriftDiagnosis(
            drift_class="unknown",
            confidence=0.0,
            scores={
                "stable": 0.0,
                "growth": 0.0,
                "corruption": 0.0,
                "state_loss": 0.0,
                "provider_contamination": 0.0,
            },
            evidence_refs=(),
        )

    count = float(
        len(evidence)
    )

    averages = {
        "continuity": (
            sum(
                item.continuity
                for item in evidence
            )
            / count
        ),
        "causal_support": (
            sum(
                item.causal_support
                for item in evidence
            )
            / count
        ),
        "authority_support": (
            sum(
                item.authority_support
                for item in evidence
            )
            / count
        ),
        "unexplained_change": (
            sum(
                item.unexplained_change
                for item in evidence
            )
            / count
        ),
        "state_integrity": (
            sum(
                item.state_integrity
                for item in evidence
            )
            / count
        ),
        "provider_dependence": (
            sum(
                item.provider_dependence
                for item in evidence
            )
            / count
        ),
        "contradiction": (
            sum(
                item.contradiction
                for item in evidence
            )
            / count
        ),
    }

    explained_development = _unit(
        averages["causal_support"]
        * averages["authority_support"]
    )

    scores = {
        "stable": _unit(
            averages["continuity"]
            * averages["state_integrity"]
            * (
                1.0
                - averages[
                    "unexplained_change"
                ]
            )
            * (
                1.0
                - explained_development
            )
        ),
        "growth": _unit(
            averages["continuity"]
            * averages["causal_support"]
            * averages[
                "authority_support"
            ]
            * averages["state_integrity"]
            * (
                1.0
                - averages[
                    "provider_dependence"
                ]
            )
        ),
        "corruption": _unit(
            averages[
                "unexplained_change"
            ]
            * (
                1.0
                - averages[
                    "authority_support"
                ]
            )
            * (
                0.5
                + 0.5
                * averages[
                    "contradiction"
                ]
            )
        ),
        "state_loss": _unit(
            (
                1.0
                - averages[
                    "state_integrity"
                ]
            )
            * (
                1.0
                - averages[
                    "continuity"
                ]
            )
        ),
        "provider_contamination": (
            _unit(
                averages[
                    "provider_dependence"
                ]
                * averages[
                    "unexplained_change"
                ]
                * (
                    1.0
                    - averages[
                        "causal_support"
                    ]
                )
            )
        ),
    }

    ordered = sorted(
        scores.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    )

    best_class, best_score = (
        ordered[0]
    )

    second_score = (
        ordered[1][1]
        if len(ordered) > 1
        else 0.0
    )

    if math.isclose(
        best_score,
        0.0,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        drift_class = "unknown"
        confidence = 0.0

    elif math.isclose(
        best_score,
        second_score,
        rel_tol=1e-12,
        abs_tol=1e-12,
    ):
        drift_class = "ambiguous"
        confidence = best_score

    else:
        drift_class = best_class
        confidence = _unit(
            best_score
            - second_score
        )

    return DriftDiagnosis(
        drift_class=drift_class,
        confidence=confidence,
        scores=scores,
        evidence_refs=tuple(
            item.id
            for item in evidence
        ),
        auto_revert=False,
    )


def drift_projection(
    evidence: Sequence[
        DriftEvidence
    ],
) -> Mapping[str, Any]:
    diagnosis = diagnose_drift(
        evidence
    )

    return {
        "schema": SCHEMA,
        "diagnosis": (
            diagnosis.projection()
        ),
        "evidence": [
            item.projection()
            for item in evidence
        ],
        "diagnosis_is_authority": False,
        "automatic_reversion": False,
        "contradictions_preserved": True,
        "derived": True,
        "authoritative": False,
    }

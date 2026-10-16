
"""reusable novelty and realism preference evaluation.

this module does not create canon, register graph instances, or mutate
simulation state. callers supply evidence and retain ownership of it.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Mapping


class PreferenceError(ValueError):
    """invalid preference or assessment input."""


def _number(value: object, name: str) -> Decimal:
    if isinstance(value, bool):
        raise PreferenceError(f"{name} must be numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise PreferenceError(f"{name} must be numeric") from exc
    if not result.is_finite():
        raise PreferenceError(f"{name} must be finite")
    return result


def _bounded(value: object, name: str) -> Decimal:
    result = _number(value, name)
    if not Decimal("0") <= result <= Decimal("100"):
        raise PreferenceError(f"{name} must be between 0 and 100")
    return result


@dataclass(frozen=True)
class Preference:
    """one reusable evaluation preference, independent of authorship."""

    identifier: str
    value: Decimal

    def __post_init__(self) -> None:
        if self.identifier not in ("novelty", "realism"):
            raise PreferenceError("unsupported preference identifier")
        object.__setattr__(
            self, "value", _bounded(self.value, self.identifier)
        )

    @property
    def normalized(self) -> Decimal:
        return self.value / Decimal("100")


@dataclass(frozen=True)
class CreativePreferences:
    novelty: Preference
    realism: Preference

    def __post_init__(self) -> None:
        if self.novelty.identifier != "novelty":
            raise PreferenceError("novelty preference required")
        if self.realism.identifier != "realism":
            raise PreferenceError("realism preference required")

    @classmethod
    def create(
        cls,
        novelty: object = 50,
        realism: object = 50,
    ) -> CreativePreferences:
        return cls(
            novelty=Preference("novelty", _bounded(novelty, "novelty")),
            realism=Preference("realism", _bounded(realism, "realism")),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "novelty": str(self.novelty.value),
            "realism": str(self.realism.value),
        }


@dataclass(frozen=True)
class Assessment:
    """derived evaluation, never an authoritative story fact."""

    dimension: str
    preference: Decimal
    evidence_score: Decimal | None
    alignment: Decimal | None
    status: str
    evidence_reference: str | None


def assess(
    preference: Preference,
    evidence_score: object | None,
    evidence_reference: str | None = None,
) -> Assessment:
    """evaluate supplied evidence without inventing an assessment.

    evidence_score is a caller-established score from 0 to 100.
    novelty measures distinctiveness, not quality or originality proof.
    realism measures conformity to selected real-world constraints,
    not internal consistency or narrative quality.
    """
    if evidence_score is None:
        return Assessment(
            dimension=preference.identifier,
            preference=preference.value,
            evidence_score=None,
            alignment=None,
            status="insufficient_evidence",
            evidence_reference=evidence_reference,
        )

    score = _bounded(evidence_score, "evidence_score")
    alignment = Decimal("100") - abs(preference.value - score)

    return Assessment(
        dimension=preference.identifier,
        preference=preference.value,
        evidence_score=score,
        alignment=alignment,
        status="assessed",
        evidence_reference=evidence_reference,
    )


def evaluate(
    preferences: CreativePreferences,
    evidence: Mapping[str, object],
    references: Mapping[str, str] | None = None,
) -> dict[str, Assessment]:
    """derive independent evaluations from externally admitted evidence."""
    references = references or {}
    return {
        "novelty": assess(
            preferences.novelty,
            evidence.get("novelty"),
            references.get("novelty"),
        ),
        "realism": assess(
            preferences.realism,
            evidence.get("realism"),
            references.get("realism"),
        ),
    }


def project(assessment: Assessment) -> dict[str, str | None]:
    """serialize a rebuildable evaluation projection."""
    return {
        "dimension": assessment.dimension,
        "preference": str(assessment.preference),
        "evidence_score": (
            str(assessment.evidence_score)
            if assessment.evidence_score is not None
            else None
        ),
        "alignment": (
            str(assessment.alignment)
            if assessment.alignment is not None
            else None
        ),
        "status": assessment.status,
        "evidence_reference": assessment.evidence_reference,
    }

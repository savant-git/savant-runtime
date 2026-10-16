
"""reusable creative controls for carbon and oriel.

novelty and realism are independent preferences. authorship permission,
canon authority, and internal consistency remain outside their control.

this module is an integration adapter, not a graph registration.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping
import hashlib
import json

from creative_preferences import CreativePreferences, evaluate, project
from creative_evidence import novelty, realism


class ControlError(ValueError):
    """invalid creative control input."""


def _bounded(value: object, field: str) -> Decimal:
    if isinstance(value, bool):
        raise ControlError(f"{field} must be numeric")
    try:
        number = Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise ControlError(f"{field} must be numeric") from exc

    if not number.is_finite() or number < 0 or number > 100:
        raise ControlError(f"{field} must be between 0 and 100")
    return number


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class CreativeControls:
    """immutable preferences with no authority to change source content."""

    novelty: Decimal
    realism: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "novelty",
            _bounded(self.novelty, "novelty"),
        )
        object.__setattr__(
            self,
            "realism",
            _bounded(self.realism, "realism"),
        )

    @classmethod
    def create(
        cls,
        novelty: object = 50,
        realism: object = 50,
    ) -> CreativeControls:
        return cls(
            novelty=_bounded(novelty, "novelty"),
            realism=_bounded(realism, "realism"),
        )

    @classmethod
    def from_mapping(
        cls,
        source: Mapping[str, object],
    ) -> CreativeControls:
        if not isinstance(source, Mapping):
            raise ControlError("controls must be a mapping")

        unknown = set(source) - {"novelty", "realism"}
        if unknown:
            raise ControlError("unknown creative control")

        return cls.create(
            novelty=source.get("novelty", 50),
            realism=source.get("realism", 50),
        )

    def project(self) -> dict[str, str]:
        return {
            "novelty": str(self.novelty),
            "realism": str(self.realism),
        }


def assess_candidate(
    candidate: str,
    controls: CreativeControls,
    references: Mapping[str, str],
    constraints: list[Mapping[str, object]],
) -> dict[str, Any]:
    """derive reproducible preference alignment from supplied evidence.

    novelty evidence measures textual distinctiveness only.
    realism evidence comes from explicitly supplied constraint scores.

    neither measure proves originality, quality, or factual correctness.
    """

    if not isinstance(candidate, str):
        raise ControlError("candidate must be text")
    if not isinstance(controls, CreativeControls):
        raise ControlError("controls must be CreativeControls")
    if not isinstance(references, Mapping):
        raise ControlError("references must be a mapping")
    if not isinstance(constraints, list):
        raise ControlError("constraints must be a list")

    novelty_finding = novelty(candidate, references)
    realism_finding = realism(constraints)

    preferences = CreativePreferences.create(
        novelty=controls.novelty,
        realism=controls.realism,
    )

    alignment = evaluate(
        preferences,
        {
            "novelty": novelty_finding.score,
            "realism": realism_finding.score,
        },
        {
            "novelty": novelty_finding.fingerprint,
            "realism": realism_finding.fingerprint,
        },
    )

    result: dict[str, Any] = {
        "schema": 1,
        "kind": "derived_creative_assessment",
        "authoritative": False,
        "controls": controls.project(),
        "evidence": {
            "novelty": novelty_finding.project(),
            "realism": realism_finding.project(),
        },
        "alignment": {
            key: project(value)
            for key, value in sorted(alignment.items())
        },
        "limitations": [
            "textual distinctiveness is not semantic originality",
            "realism requires independently established constraints",
            "internal consistency must be evaluated separately",
            "assessment does not authorize creative additions",
            "assessment does not modify story canon",
        ],
    }

    result["fingerprint"] = _fingerprint(result)
    return result


def compare_candidates(
    candidates: Mapping[str, str],
    controls: CreativeControls,
    references: Mapping[str, str],
    constraints: Mapping[str, list[Mapping[str, object]]],
) -> dict[str, Any]:
    """compare candidate assessments without silently selecting canon.

    results are keyed by caller-owned identifiers.
    no candidate is promoted, accepted, or rejected automatically.
    """

    if not isinstance(candidates, Mapping):
        raise ControlError("candidates must be a mapping")
    if not isinstance(constraints, Mapping):
        raise ControlError("constraints must be a mapping")
    if len(candidates) > 128:
        raise ControlError("too many candidates")

    results: dict[str, Any] = {}

    for identifier in sorted(candidates):
        if not isinstance(identifier, str) or not identifier:
            raise ControlError("candidate identifiers must be text")

        results[identifier] = assess_candidate(
            candidate=candidates[identifier],
            controls=controls,
            references=references,
            constraints=constraints.get(identifier, []),
        )

    projection: dict[str, Any] = {
        "schema": 1,
        "kind": "derived_creative_comparison",
        "authoritative": False,
        "controls": controls.project(),
        "candidates": results,
        "selected_candidate": None,
    }

    projection["fingerprint"] = _fingerprint(projection)
    return projection

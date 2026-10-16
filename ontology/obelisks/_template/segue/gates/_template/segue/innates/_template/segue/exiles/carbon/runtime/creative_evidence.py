
"""reusable evidence analysis for novelty and realism preferences.

non-authoritative, deterministic assessment projections.
no canon mutation, external dependencies, or ai authorship.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from typing import Iterable, Mapping
import hashlib
import json
import re


class EvidenceError(ValueError):
    pass


def _score(value: object, name: str) -> Decimal:
    if isinstance(value, bool):
        raise EvidenceError(f"{name} must be numeric")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise EvidenceError(f"{name} must be numeric") from exc
    if not number.is_finite() or not 0 <= number <= 100:
        raise EvidenceError(f"{name} must be between 0 and 100")
    return number


def _text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise EvidenceError(f"{name} must be text")
    if len(value) > 100_000:
        raise EvidenceError(f"{name} exceeds the size limit")
    return value


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"\w+", value.casefold()))


def _similarity(left: str, right: str) -> Decimal:
    ratio = SequenceMatcher(
        None,
        _normalize(left),
        _normalize(right),
        autojunk=False,
    ).ratio()
    return Decimal(str(ratio * 100))


def _digest(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class Finding:
    dimension: str
    status: str
    score: Decimal | None
    confidence: Decimal
    reasons: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    fingerprint: str

    def project(self) -> dict[str, object]:
        return {
            "dimension": self.dimension,
            "status": self.status,
            "score": str(self.score) if self.score is not None else None,
            "confidence": str(self.confidence),
            "reasons": list(self.reasons),
            "evidence_ids": list(self.evidence_ids),
            "fingerprint": self.fingerprint,
        }


def novelty(
    candidate: str,
    references: Mapping[str, str],
) -> Finding:
    """measure textual distinctiveness against supplied references.

    this is not proof of literary originality or absence of cliches.
    """
    candidate = _text(candidate, "candidate")
    if not isinstance(references, Mapping):
        raise EvidenceError("references must be a mapping")
    if len(references) > 256:
        raise EvidenceError("too many references")

    normalized = _normalize(candidate)
    items: list[tuple[str, str]] = []

    for identifier, passage in references.items():
        if not isinstance(identifier, str) or not identifier:
            raise EvidenceError("reference identifiers must be nonempty")
        items.append((identifier, _text(passage, "reference")))

    items.sort(key=lambda item: item[0])

    fingerprint = _digest({
        "kind": "novelty",
        "candidate": candidate,
        "references": items,
        "version": 1,
    })

    if not normalized or not items:
        return Finding(
            "novelty",
            "insufficient_evidence",
            None,
            Decimal("0"),
            ("no usable candidate or comparison material",),
            tuple(identifier for identifier, _ in items),
            fingerprint,
        )

    comparisons = [
        (identifier, _similarity(candidate, passage))
        for identifier, passage in items
        if _normalize(passage)
    ]

    if not comparisons:
        return Finding(
            "novelty",
            "insufficient_evidence",
            None,
            Decimal("0"),
            ("comparison material contains no usable text",),
            tuple(identifier for identifier, _ in items),
            fingerprint,
        )

    identifier, highest = max(
        comparisons,
        key=lambda item: (item[1], item[0]),
    )

    return Finding(
        "novelty",
        "assessed",
        Decimal("100") - highest,
        Decimal("100"),
        (
            "score measures surface-text distinctiveness only",
            f"closest supplied comparison: {identifier}",
            "plot-level novelty requires separate semantic evidence",
        ),
        tuple(identifier for identifier, _ in comparisons),
        fingerprint,
    )


def realism(
    observations: Iterable[Mapping[str, object]],
) -> Finding:
    """aggregate explicitly supplied constraint assessments.

    each observation contains:
      id: evidence identifier
      score: 0..100 conformity to the stated real-world constraint
      weight: positive relative importance, optional
      reason: explanatory text, optional

    no physical or historical claims are inferred automatically.
    """
    if isinstance(observations, (str, bytes, Mapping)):
        raise EvidenceError("observations must be a sequence")

    entries = list(observations)
    if len(entries) > 256:
        raise EvidenceError("too many observations")

    parsed: list[tuple[str, Decimal, Decimal, str]] = []
    seen: set[str] = set()

    for entry in entries:
        if not isinstance(entry, Mapping):
            raise EvidenceError("observation must be a mapping")

        identifier = entry.get("id")
        if not isinstance(identifier, str) or not identifier:
            raise EvidenceError("observation requires an id")
        if identifier in seen:
            raise EvidenceError("duplicate observation id")
        seen.add(identifier)

        score = _score(entry.get("score"), "score")
        weight = _score(entry.get("weight", 1), "weight")
        if weight == 0:
            raise EvidenceError("weight must be positive")

        reason = _text(entry.get("reason", ""), "reason")
        parsed.append((identifier, score, weight, reason))

    parsed.sort(key=lambda item: item[0])

    fingerprint = _digest({
        "kind": "realism",
        "observations": [
            [identifier, str(score), str(weight), reason]
            for identifier, score, weight, reason in parsed
        ],
        "version": 1,
    })

    if not parsed:
        return Finding(
            "realism",
            "insufficient_evidence",
            None,
            Decimal("0"),
            ("no assessed real-world constraints supplied",),
            (),
            fingerprint,
        )

    total_weight = sum(
        (weight for _, _, weight, _ in parsed),
        Decimal("0"),
    )
    weighted_score = sum(
        (score * weight for _, score, weight, _ in parsed),
        Decimal("0"),
    ) / total_weight

    reasons = tuple(
        f"{identifier}: {reason}"
        for identifier, _, _, reason in parsed
        if reason
    )

    return Finding(
        "realism",
        "assessed",
        weighted_score,
        Decimal("100"),
        reasons or ("weighted assessment of supplied constraints",),
        tuple(identifier for identifier, _, _, _ in parsed),
        fingerprint,
    )


def evaluate(
    candidate: str,
    references: Mapping[str, str],
    constraints: Iterable[Mapping[str, object]],
) -> dict[str, dict[str, object]]:
    """produce independent, reproducible assessment projections."""
    return {
        "novelty": novelty(candidate, references).project(),
        "realism": realism(constraints).project(),
    }

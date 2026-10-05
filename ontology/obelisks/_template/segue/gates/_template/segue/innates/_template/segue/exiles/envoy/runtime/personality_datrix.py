#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "savant.envoy.personality-datrix.v1"
OWNER = "exile:envoy"
AUTHORITY_EFFECT = "none"

STATUS_OBSERVED = "observed"
STATUS_INFERRED = "inferred"
STATUS_ACCEPTED = "accepted"
STATUS_REJECTED = "rejected"
STATUS_CONTRADICTED = "contradicted"

VALID_STATUSES = frozenset(
    {
        STATUS_OBSERVED,
        STATUS_INFERRED,
        STATUS_ACCEPTED,
        STATUS_REJECTED,
        STATUS_CONTRADICTED,
    }
)

SELF_OBSERVED = "observed-self"
SELF_ACCEPTED = "accepted-self"
SELF_ASPIRATIONAL = "aspirational-self"
SELF_IDEAL = "ideal-self"

CANDOR_MIRROR = "mirror"
CANDOR_GENTLE = "gentle"
CANDOR_CANDID = "candid"
CANDOR_CHALLENGE = "challenge"
CANDOR_UNFILTERED = "unfiltered"

PERSONALITY_FACETS = (
    "values",
    "ethics",
    "beliefs",
    "identity",
    "aspirations",
    "goals",
    "motivations",
    "priorities",
    "temperament",
    "emotional_expression",
    "emotional_regulation",
    "empathy",
    "compassion",
    "patience",
    "frustration",
    "anger",
    "fear",
    "optimism",
    "pessimism",
    "confidence",
    "humility",
    "pride",
    "shame",
    "vulnerability",
    "trust",
    "loyalty",
    "forgiveness",
    "resentment",
    "boundaries",
    "attachment",
    "social_energy",
    "privacy",
    "directness",
    "formality",
    "politeness",
    "assertiveness",
    "conflict",
    "negotiation",
    "persuasion",
    "storytelling",
    "verbosity",
    "vocabulary",
    "syntax",
    "rhythm",
    "profanity",
    "humor",
    "sarcasm",
    "irony",
    "deadpan",
    "absurdity",
    "understatement",
    "exaggeration",
    "wordplay",
    "gallows_humor",
    "self_deprecation",
    "teasing",
    "humor_boundaries",
    "curiosity",
    "skepticism",
    "creativity",
    "imagination",
    "intuition",
    "analysis",
    "deliberation",
    "impulsivity",
    "risk",
    "uncertainty",
    "attention",
    "learning",
    "memory_preferences",
    "decision_style",
    "problem_solving",
    "planning",
    "adaptability",
    "novelty",
    "routine",
    "aesthetics",
    "taste",
    "consumer_behavior",
    "financial_behavior",
    "work_behavior",
    "leadership",
    "collaboration",
    "relationship_behavior",
    "family_behavior",
    "friendship_behavior",
    "professional_behavior",
    "public_behavior",
    "private_behavior",
    "online_behavior",
    "moral_reasoning",
    "fairness",
    "authority",
    "rules",
    "tradition",
    "independence",
    "competitiveness",
    "status",
    "recognition",
    "ambition",
    "discipline",
    "persistence",
    "perfectionism",
    "self_awareness",
    "defensiveness",
    "rationalization",
    "bias",
    "regret",
    "growth",
    "idiosyncrasy",
)

CONTEXT_DIMENSIONS = (
    "relationship",
    "role",
    "audience",
    "medium",
    "domain",
    "location",
    "privacy",
    "stakes",
    "urgency",
    "emotional_state",
    "resource_state",
    "social_state",
    "historical_context",
)

EVIDENCE_KINDS = (
    "explicit_statement",
    "conversation",
    "decision",
    "correction",
    "behavior",
    "scenario_response",
    "preference",
    "artifact",
    "outcome",
    "reflection",
    "contradiction",
)

RELATIONSHIP_KINDS = (
    "supports",
    "contradicts",
    "qualifies",
    "contextualizes",
    "causes",
    "inhibits",
    "amplifies",
    "expresses",
    "aspires_from",
    "aspires_to",
    "corrects",
    "resembles",
    "depends_on",
    "applies_with",
)

TRUTH_INVARIANT = (
    "presentation preference never mutates admitted evidence, provenance, "
    "confidence, contradiction, or accepted personality substance"
)

IDEALIZATION_INVARIANT = (
    "ideal-self projection may compensate for a trait only when the user "
    "has accepted the relevant aspiration or correction target"
)

LEARNING_INVARIANT = (
    "observation and inference may propose personality substance but may "
    "not silently promote inference into accepted self or authority"
)


class PersonalityDatrixError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def required_text(value: Any, name: str) -> str:
    result = clean_text(value)
    if not result:
        raise PersonalityDatrixError(f"{name} is required")
    return result


def unit(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise PersonalityDatrixError(f"{name} must be numeric") from exc

    if not math.isfinite(result) or result < 0.0 or result > 1.0:
        raise PersonalityDatrixError(
            f"{name} must be finite and between 0.0 and 1.0"
        )

    return result


def unique_strings(values: Iterable[Any]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        item = clean_text(value)
        if item and item not in seen:
            seen.add(item)
            result.append(item)

    return tuple(result)


@dataclass(frozen=True)
class Context:
    values: tuple[tuple[str, str], ...] = ()

    @classmethod
    def normalize(cls, value: Mapping[str, Any] | None) -> "Context":
        if not value:
            return cls()

        result: list[tuple[str, str]] = []

        for key in sorted(value):
            name = clean_text(key)
            item = clean_text(value[key])

            if name and item:
                result.append((name, item))

        return cls(tuple(result))

    def projection(self) -> dict[str, str]:
        return dict(self.values)


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    kind: str
    content: str
    confidence: float
    source_ref: str
    context: Context = field(default_factory=Context)

    @classmethod
    def normalize(cls, value: Mapping[str, Any]) -> "Evidence":
        kind = required_text(value.get("kind"), "kind")

        if kind not in EVIDENCE_KINDS:
            raise PersonalityDatrixError(
                f"unsupported evidence kind: {kind}"
            )

        return cls(
            evidence_id=required_text(
                value.get("evidence_id"),
                "evidence_id",
            ),
            kind=kind,
            content=required_text(
                value.get("content"),
                "content",
            ),
            confidence=unit(
                value.get("confidence", 1.0),
                "confidence",
            ),
            source_ref=required_text(
                value.get("source_ref"),
                "source_ref",
            ),
            context=Context.normalize(value.get("context")),
        )

    def projection(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "kind": self.kind,
            "content": self.content,
            "confidence": self.confidence,
            "source_ref": self.source_ref,
            "context": self.context.projection(),
        }


@dataclass(frozen=True)
class Trait:
    trait_id: str
    facet: str
    expression: str
    status: str
    confidence: float
    evidence_refs: tuple[str, ...]
    contexts: tuple[Context, ...]
    user_accepted: bool = False
    aspirational: bool = False
    correction_target: bool = False

    @classmethod
    def normalize(cls, value: Mapping[str, Any]) -> "Trait":
        facet = required_text(value.get("facet"), "facet")

        if facet not in PERSONALITY_FACETS:
            raise PersonalityDatrixError(
                f"unsupported personality facet: {facet}"
            )

        status = required_text(
            value.get("status", STATUS_INFERRED),
            "status",
        )

        if status not in VALID_STATUSES:
            raise PersonalityDatrixError(
                f"unsupported trait status: {status}"
            )

        contexts = tuple(
            Context.normalize(item)
            for item in value.get("contexts", ())
        )

        return cls(
            trait_id=required_text(
                value.get("trait_id"),
                "trait_id",
            ),
            facet=facet,
            expression=required_text(
                value.get("expression"),
                "expression",
            ),
            status=status,
            confidence=unit(
                value.get("confidence", 0.0),
                "confidence",
            ),
            evidence_refs=unique_strings(
                value.get("evidence_refs", ())
            ),
            contexts=contexts,
            user_accepted=bool(
                value.get("user_accepted", False)
            ),
            aspirational=bool(
                value.get("aspirational", False)
            ),
            correction_target=bool(
                value.get("correction_target", False)
            ),
        )

    def projection(self) -> dict[str, Any]:
        return {
            "trait_id": self.trait_id,
            "facet": self.facet,
            "expression": self.expression,
            "status": self.status,
            "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs),
            "contexts": [
                item.projection()
                for item in self.contexts
            ],
            "user_accepted": self.user_accepted,
            "aspirational": self.aspirational,
            "correction_target": self.correction_target,
        }


@dataclass(frozen=True)
class Segue:
    segue_id: str
    kind: str
    source_id: str
    target_id: str
    confidence: float
    evidence_refs: tuple[str, ...]

    @classmethod
    def normalize(cls, value: Mapping[str, Any]) -> "Segue":
        kind = required_text(value.get("kind"), "kind")

        if kind not in RELATIONSHIP_KINDS:
            raise PersonalityDatrixError(
                f"unsupported segue kind: {kind}"
            )

        return cls(
            segue_id=required_text(
                value.get("segue_id"),
                "segue_id",
            ),
            kind=kind,
            source_id=required_text(
                value.get("source_id"),
                "source_id",
            ),
            target_id=required_text(
                value.get("target_id"),
                "target_id",
            ),
            confidence=unit(
                value.get("confidence", 1.0),
                "confidence",
            ),
            evidence_refs=unique_strings(
                value.get("evidence_refs", ())
            ),
        )

    def projection(self) -> dict[str, Any]:
        return {
            "segue_id": self.segue_id,
            "kind": self.kind,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class PersonalityDatrix:
    persona_id: str
    evidence: tuple[Evidence, ...]
    traits: tuple[Trait, ...]
    segues: tuple[Segue, ...]

    @classmethod
    def compose(
        cls,
        *,
        persona_id: str,
        evidence: Iterable[Mapping[str, Any]] = (),
        traits: Iterable[Mapping[str, Any]] = (),
        segues: Iterable[Mapping[str, Any]] = (),
    ) -> "PersonalityDatrix":
        normalized_evidence = tuple(
            sorted(
                (
                    Evidence.normalize(item)
                    for item in evidence
                ),
                key=lambda item: item.evidence_id,
            )
        )

        normalized_traits = tuple(
            sorted(
                (
                    Trait.normalize(item)
                    for item in traits
                ),
                key=lambda item: item.trait_id,
            )
        )

        normalized_segues = tuple(
            sorted(
                (
                    Segue.normalize(item)
                    for item in segues
                ),
                key=lambda item: item.segue_id,
            )
        )

        instance_ids = {
            item.evidence_id
            for item in normalized_evidence
        } | {
            item.trait_id
            for item in normalized_traits
        }

        evidence_ids = {
            item.evidence_id
            for item in normalized_evidence
        }

        for trait in normalized_traits:
            missing = set(trait.evidence_refs) - evidence_ids
            if missing:
                raise PersonalityDatrixError(
                    f"{trait.trait_id} references missing evidence: "
                    f"{sorted(missing)}"
                )

        for segue in normalized_segues:
            if segue.source_id not in instance_ids:
                raise PersonalityDatrixError(
                    f"{segue.segue_id} has missing source "
                    f"{segue.source_id}"
                )

            if segue.target_id not in instance_ids:
                raise PersonalityDatrixError(
                    f"{segue.segue_id} has missing target "
                    f"{segue.target_id}"
                )

            missing = set(segue.evidence_refs) - evidence_ids
            if missing:
                raise PersonalityDatrixError(
                    f"{segue.segue_id} references missing evidence: "
                    f"{sorted(missing)}"
                )

        return cls(
            persona_id=required_text(
                persona_id,
                "persona_id",
            ),
            evidence=normalized_evidence,
            traits=normalized_traits,
            segues=normalized_segues,
        )

    def evidence_index(self) -> dict[str, Evidence]:
        return {
            item.evidence_id: item
            for item in self.evidence
        }

    def trait_index(self) -> dict[str, Trait]:
        return {
            item.trait_id: item
            for item in self.traits
        }

    def coverage(self) -> dict[str, Any]:
        facet_traits: dict[str, list[Trait]] = {
            facet: []
            for facet in PERSONALITY_FACETS
        }

        for trait in self.traits:
            facet_traits[trait.facet].append(trait)

        facets: dict[str, Any] = {}

        for facet in PERSONALITY_FACETS:
            items = facet_traits[facet]

            if not items:
                facets[facet] = {
                    "coverage": 0.0,
                    "confidence": 0.0,
                    "accepted": 0,
                    "inferred": 0,
                    "contradicted": 0,
                    "evidence": 0,
                }
                continue

            evidence_refs = {
                ref
                for item in items
                for ref in item.evidence_refs
            }

            confidence = sum(
                item.confidence
                for item in items
            ) / len(items)

            context_count = sum(
                len(item.contexts)
                for item in items
            )

            coverage = min(
                1.0,
                (
                    min(len(items), 5) / 5.0 * 0.35
                    + min(len(evidence_refs), 8) / 8.0 * 0.35
                    + min(context_count, 5) / 5.0 * 0.15
                    + confidence * 0.15
                ),
            )

            facets[facet] = {
                "coverage": round(coverage, 6),
                "confidence": round(confidence, 6),
                "accepted": sum(
                    1
                    for item in items
                    if item.user_accepted
                ),
                "inferred": sum(
                    1
                    for item in items
                    if item.status == STATUS_INFERRED
                ),
                "contradicted": sum(
                    1
                    for item in items
                    if item.status == STATUS_CONTRADICTED
                ),
                "evidence": len(evidence_refs),
            }

        overall = (
            sum(
                item["coverage"]
                for item in facets.values()
            )
            / len(PERSONALITY_FACETS)
        )

        return {
            "overall": round(overall, 6),
            "facets": facets,
        }

    def uncertainty_frontier(
        self,
        *,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        coverage = self.coverage()["facets"]

        ranked = sorted(
            coverage.items(),
            key=lambda item: (
                item[1]["coverage"],
                item[1]["confidence"],
                item[0],
            ),
        )

        result: list[dict[str, Any]] = []

        for facet, state in ranked[: max(0, limit)]:
            result.append(
                {
                    "facet": facet,
                    "coverage": state["coverage"],
                    "confidence": state["confidence"],
                    "contradicted": state["contradicted"],
                    "priority": round(
                        1.0 - state["coverage"],
                        6,
                    ),
                }
            )

        return result

    def contradictions(self) -> list[dict[str, Any]]:
        traits = self.trait_index()
        result: list[dict[str, Any]] = []

        for segue in self.segues:
            if segue.kind != "contradicts":
                continue

            source = traits.get(segue.source_id)
            target = traits.get(segue.target_id)

            if source is None or target is None:
                continue

            result.append(
                {
                    "segue_id": segue.segue_id,
                    "source": source.projection(),
                    "target": target.projection(),
                    "confidence": segue.confidence,
                    "evidence_refs": list(
                        segue.evidence_refs
                    ),
                }
            )

        return result

    def observed_self(self) -> dict[str, Any]:
        selected = [
            item.projection()
            for item in self.traits
            if item.status
            in {
                STATUS_OBSERVED,
                STATUS_INFERRED,
                STATUS_ACCEPTED,
                STATUS_CONTRADICTED,
            }
            and not item.aspirational
        ]

        return self._self_projection(
            SELF_OBSERVED,
            selected,
        )

    def accepted_self(self) -> dict[str, Any]:
        selected = [
            item.projection()
            for item in self.traits
            if item.user_accepted
            and not item.aspirational
        ]

        return self._self_projection(
            SELF_ACCEPTED,
            selected,
        )

    def aspirational_self(self) -> dict[str, Any]:
        selected = [
            item.projection()
            for item in self.traits
            if item.user_accepted
            and item.aspirational
        ]

        return self._self_projection(
            SELF_ASPIRATIONAL,
            selected,
        )

    def ideal_self(self) -> dict[str, Any]:
        accepted = [
            item.projection()
            for item in self.traits
            if item.user_accepted
            and not item.aspirational
        ]

        aspirations = [
            item.projection()
            for item in self.traits
            if item.user_accepted
            and item.aspirational
            and item.correction_target
        ]

        body = {
            "schema": SCHEMA,
            "owner": OWNER,
            "authority_effect": AUTHORITY_EFFECT,
            "persona_id": self.persona_id,
            "projection": SELF_IDEAL,
            "accepted_identity": accepted,
            "accepted_corrections": aspirations,
            "invariant": IDEALIZATION_INVARIANT,
        }

        return {
            **body,
            "digest": digest(body),
        }

    def _self_projection(
        self,
        name: str,
        traits: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        body = {
            "schema": SCHEMA,
            "owner": OWNER,
            "authority_effect": AUTHORITY_EFFECT,
            "persona_id": self.persona_id,
            "projection": name,
            "traits": list(traits),
        }

        return {
            **body,
            "digest": digest(body),
        }

    def projection(self) -> dict[str, Any]:
        coverage = self.coverage()

        body = {
            "schema": SCHEMA,
            "owner": OWNER,
            "authority_effect": AUTHORITY_EFFECT,
            "persona_id": self.persona_id,
            "invariants": {
                "truth": TRUTH_INVARIANT,
                "idealization": IDEALIZATION_INVARIANT,
                "learning": LEARNING_INVARIANT,
            },
            "evidence": [
                item.projection()
                for item in self.evidence
            ],
            "traits": [
                item.projection()
                for item in self.traits
            ],
            "segues": [
                item.projection()
                for item in self.segues
            ],
            "coverage": coverage,
            "uncertainty_frontier": self.uncertainty_frontier(),
            "contradictions": self.contradictions(),
            "observed_self": self.observed_self(),
            "accepted_self": self.accepted_self(),
            "aspirational_self": self.aspirational_self(),
            "ideal_self": self.ideal_self(),
        }

        return {
            **body,
            "digest": digest(body),
        }


def candor_mode(value: Any) -> str:
    level = unit(value, "candor")

    if level < 0.20:
        return CANDOR_MIRROR
    if level < 0.40:
        return CANDOR_GENTLE
    if level < 0.60:
        return CANDOR_CANDID
    if level < 0.80:
        return CANDOR_CHALLENGE
    return CANDOR_UNFILTERED


def candor_projection(
    *,
    value: Any,
    challenge_enabled: bool = True,
    unsolicited_truth_enabled: bool = True,
) -> dict[str, Any]:
    level = unit(value, "candor")

    body = {
        "schema": SCHEMA,
        "owner": OWNER,
        "authority_effect": AUTHORITY_EFFECT,
        "candor": level,
        "mode": candor_mode(level),
        "challenge_enabled": bool(challenge_enabled),
        "unsolicited_truth_enabled": bool(
            unsolicited_truth_enabled
        ),
        "rewrite_truth_for_comfort": False,
        "truth_invariant": TRUTH_INVARIANT,
    }

    return {
        **body,
        "digest": digest(body),
    }


def selftest() -> dict[str, Any]:
    evidence = (
        {
            "evidence_id": "evidence:1",
            "kind": "conversation",
            "content": "uses dry sarcasm with close friends",
            "confidence": 0.94,
            "source_ref": "selftest:conversation:1",
            "context": {
                "relationship": "close-friend",
                "medium": "conversation",
            },
        },
        {
            "evidence_id": "evidence:2",
            "kind": "correction",
            "content": "wants greater restraint when angry",
            "confidence": 1.0,
            "source_ref": "selftest:correction:1",
            "context": {
                "emotional_state": "angry",
            },
        },
        {
            "evidence_id": "evidence:3",
            "kind": "scenario_response",
            "content": "prefers blunt truth over comfortable agreement",
            "confidence": 0.91,
            "source_ref": "selftest:scenario:1",
            "context": {},
        },
    )

    traits = (
        {
            "trait_id": "trait:sarcasm:1",
            "facet": "sarcasm",
            "expression": "dry sarcasm with trusted people",
            "status": "accepted",
            "confidence": 0.94,
            "evidence_refs": ["evidence:1"],
            "contexts": [
                {
                    "relationship": "close-friend",
                }
            ],
            "user_accepted": True,
        },
        {
            "trait_id": "trait:restraint:observed",
            "facet": "emotional_regulation",
            "expression": "can react too quickly when angry",
            "status": "accepted",
            "confidence": 0.90,
            "evidence_refs": ["evidence:2"],
            "contexts": [
                {
                    "emotional_state": "angry",
                }
            ],
            "user_accepted": True,
        },
        {
            "trait_id": "trait:restraint:aspiration",
            "facet": "emotional_regulation",
            "expression": "retain directness with greater restraint",
            "status": "accepted",
            "confidence": 1.0,
            "evidence_refs": ["evidence:2"],
            "contexts": [
                {
                    "emotional_state": "angry",
                }
            ],
            "user_accepted": True,
            "aspirational": True,
            "correction_target": True,
        },
        {
            "trait_id": "trait:candor:1",
            "facet": "directness",
            "expression": "prefers uncomfortable truth over flattery",
            "status": "accepted",
            "confidence": 0.91,
            "evidence_refs": ["evidence:3"],
            "contexts": [],
            "user_accepted": True,
        },
    )

    segues = (
        {
            "segue_id": "segue:restraint:1",
            "kind": "aspires_from",
            "source_id": "trait:restraint:aspiration",
            "target_id": "trait:restraint:observed",
            "confidence": 1.0,
            "evidence_refs": ["evidence:2"],
        },
    )

    datrix = PersonalityDatrix.compose(
        persona_id="persona:selftest",
        evidence=evidence,
        traits=traits,
        segues=segues,
    )

    first = datrix.projection()
    second = datrix.projection()

    assert first == second
    assert first["digest"] == second["digest"]
    assert first["owner"] == OWNER
    assert first["authority_effect"] == "none"

    ideal = first["ideal_self"]
    assert len(ideal["accepted_corrections"]) == 1

    assert (
        ideal["accepted_corrections"][0]["trait_id"]
        == "trait:restraint:aspiration"
    )

    candor_low = candor_projection(value=0.0)
    candor_high = candor_projection(value=1.0)

    assert candor_low["rewrite_truth_for_comfort"] is False
    assert candor_high["rewrite_truth_for_comfort"] is False
    assert candor_low["mode"] == CANDOR_MIRROR
    assert candor_high["mode"] == CANDOR_UNFILTERED

    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "ok": True,
        "deterministic": True,
        "truth_preserved": True,
        "idealization_requires_acceptance": True,
        "facet_count": len(PERSONALITY_FACETS),
        "context_dimension_count": len(CONTEXT_DIMENSIONS),
        "digest": first["digest"],
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] != "--selftest":
        print(
            "usage: personality_datrix.py --selftest",
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

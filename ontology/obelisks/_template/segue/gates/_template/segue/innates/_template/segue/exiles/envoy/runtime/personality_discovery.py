#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "savant.envoy.personality-discovery.v1"
OWNER = "exile:envoy"
AUTHORITY_EFFECT = "none"

MODE_NATURAL = "natural"
MODE_DEEP = "deep"
MODE_SCENARIO = "scenario"
MODE_REFLECTION = "reflection"
MODE_CALIBRATION = "calibration"

VALID_MODES = frozenset(
    {
        MODE_NATURAL,
        MODE_DEEP,
        MODE_SCENARIO,
        MODE_REFLECTION,
        MODE_CALIBRATION,
    }
)

QUESTION_KINDS = (
    "open",
    "contrast",
    "scenario",
    "counterfactual",
    "reflection",
    "correction",
    "boundary",
    "exception",
)

BOUNDARY_INVARIANT = (
    "conversation may optimize information gain but may not work around "
    "a user-declared topic boundary"
)

DISCOVERY_INVARIANT = (
    "the objective is personality fidelity rather than psychological "
    "labeling, diagnosis, persuasion, or maximizing disclosure"
)


class PersonalityDiscoveryError(ValueError):
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


def clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def unit(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise PersonalityDiscoveryError(
            "value must be numeric"
        ) from exc

    if result < 0.0 or result > 1.0:
        raise PersonalityDiscoveryError(
            "value must be between 0.0 and 1.0"
        )

    return result


def unique(values: Iterable[Any]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        item = clean(value)
        if item and item not in seen:
            seen.add(item)
            result.append(item)

    return tuple(result)


@dataclass(frozen=True)
class DiscoveryControls:
    enabled: bool = True
    depth: float = 0.65
    initiative: float = 0.65
    scenario_use: float = 0.50
    contradiction_probe: float = 0.70
    idiosyncrasy_hunt: float = 0.80
    conversational_subtlety: float = 0.85
    direct_question_tolerance: float = 0.50
    topic_boundaries: tuple[str, ...] = ()
    paused_facets: tuple[str, ...] = ()

    @classmethod
    def normalize(
        cls,
        value: Mapping[str, Any] | None,
    ) -> "DiscoveryControls":
        value = value or {}

        return cls(
            enabled=bool(value.get("enabled", True)),
            depth=unit(value.get("depth", 0.65)),
            initiative=unit(
                value.get("initiative", 0.65)
            ),
            scenario_use=unit(
                value.get("scenario_use", 0.50)
            ),
            contradiction_probe=unit(
                value.get(
                    "contradiction_probe",
                    0.70,
                )
            ),
            idiosyncrasy_hunt=unit(
                value.get(
                    "idiosyncrasy_hunt",
                    0.80,
                )
            ),
            conversational_subtlety=unit(
                value.get(
                    "conversational_subtlety",
                    0.85,
                )
            ),
            direct_question_tolerance=unit(
                value.get(
                    "direct_question_tolerance",
                    0.50,
                )
            ),
            topic_boundaries=unique(
                value.get("topic_boundaries", ())
            ),
            paused_facets=unique(
                value.get("paused_facets", ())
            ),
        )

    def projection(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "depth": self.depth,
            "initiative": self.initiative,
            "scenario_use": self.scenario_use,
            "contradiction_probe": self.contradiction_probe,
            "idiosyncrasy_hunt": self.idiosyncrasy_hunt,
            "conversational_subtlety": (
                self.conversational_subtlety
            ),
            "direct_question_tolerance": (
                self.direct_question_tolerance
            ),
            "topic_boundaries": list(
                self.topic_boundaries
            ),
            "paused_facets": list(
                self.paused_facets
            ),
        }


@dataclass(frozen=True)
class DiscoveryTarget:
    facet: str
    coverage: float
    confidence: float
    contradiction_count: int
    relevance: float
    novelty: float
    context_gap: float

    @classmethod
    def normalize(
        cls,
        value: Mapping[str, Any],
    ) -> "DiscoveryTarget":
        facet = clean(value.get("facet"))

        if not facet:
            raise PersonalityDiscoveryError(
                "facet is required"
            )

        return cls(
            facet=facet,
            coverage=unit(
                value.get("coverage", 0.0)
            ),
            confidence=unit(
                value.get("confidence", 0.0)
            ),
            contradiction_count=max(
                0,
                int(
                    value.get(
                        "contradiction_count",
                        0,
                    )
                ),
            ),
            relevance=unit(
                value.get("relevance", 0.5)
            ),
            novelty=unit(
                value.get("novelty", 0.5)
            ),
            context_gap=unit(
                value.get("context_gap", 0.5)
            ),
        )

    def information_value(
        self,
        controls: DiscoveryControls,
    ) -> float:
        uncertainty = 1.0 - (
            self.coverage * 0.60
            + self.confidence * 0.40
        )

        contradiction = min(
            1.0,
            self.contradiction_count / 3.0,
        )

        value = (
            uncertainty * 0.35
            + self.relevance * 0.20
            + self.novelty
            * controls.idiosyncrasy_hunt
            * 0.15
            + self.context_gap * 0.15
            + contradiction
            * controls.contradiction_probe
            * 0.15
        )

        return round(min(1.0, value), 6)


def choose_target(
    *,
    targets: Iterable[Mapping[str, Any]],
    controls: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    control = DiscoveryControls.normalize(controls)

    if not control.enabled:
        return None

    blocked = set(control.paused_facets)

    normalized = [
        DiscoveryTarget.normalize(item)
        for item in targets
        if clean(item.get("facet"))
        not in blocked
    ]

    if not normalized:
        return None

    ranked = sorted(
        normalized,
        key=lambda item: (
            -item.information_value(control),
            item.facet,
        ),
    )

    selected = ranked[0]

    body = {
        "schema": SCHEMA,
        "owner": OWNER,
        "authority_effect": AUTHORITY_EFFECT,
        "facet": selected.facet,
        "information_value": (
            selected.information_value(control)
        ),
        "coverage": selected.coverage,
        "confidence": selected.confidence,
        "contradiction_count": (
            selected.contradiction_count
        ),
        "relevance": selected.relevance,
        "novelty": selected.novelty,
        "context_gap": selected.context_gap,
        "controls": control.projection(),
    }

    return {
        **body,
        "digest": digest(body),
    }


def choose_question_kind(
    *,
    target: Mapping[str, Any],
    controls: Mapping[str, Any] | None = None,
) -> str:
    control = DiscoveryControls.normalize(controls)

    contradictions = int(
        target.get("contradiction_count", 0)
    )

    context_gap = unit(
        target.get("context_gap", 0.5)
    )

    novelty = unit(
        target.get("novelty", 0.5)
    )

    if (
        contradictions > 0
        and control.contradiction_probe >= 0.50
    ):
        return "contrast"

    if (
        context_gap >= 0.70
        and control.scenario_use >= 0.45
    ):
        return "scenario"

    if (
        novelty >= 0.70
        and control.idiosyncrasy_hunt >= 0.60
    ):
        return "exception"

    if control.direct_question_tolerance >= 0.70:
        return "open"

    return "reflection"


def conversation_directive(
    *,
    target: Mapping[str, Any],
    controls: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    control = DiscoveryControls.normalize(controls)
    selected = DiscoveryTarget.normalize(target)

    question_kind = choose_question_kind(
        target=target,
        controls=controls,
    )

    body = {
        "schema": SCHEMA,
        "owner": OWNER,
        "authority_effect": AUTHORITY_EFFECT,
        "target_facet": selected.facet,
        "question_kind": question_kind,
        "objective": (
            "increase predictive personality fidelity "
            "with the smallest natural conversational "
            "intervention"
        ),
        "instructions": [
            (
                "continue the user's actual conversation "
                "rather than abruptly switching into an "
                "interview"
            ),
            (
                "prefer a natural conversational opening "
                "that can reveal the target facet"
            ),
            (
                "treat wording, humor, hesitation, "
                "exceptions, corrections, emotional "
                "texture, and explicit content as "
                "distinct evidence"
            ),
            (
                "distinguish explicit statements from "
                "behavioral inference"
            ),
            (
                "preserve contradictions until evidence "
                "supports contextual resolution"
            ),
            (
                "seek exceptions and context rather than "
                "flattening the user into a trait label"
            ),
            (
                "do not diagnose the user"
            ),
            (
                "do not manipulate the user into "
                "disclosure"
            ),
            (
                "honor topic boundaries immediately"
            ),
            (
                "stop probing when conversational cost "
                "exceeds expected information value"
            ),
        ],
        "controls": control.projection(),
        "invariants": {
            "boundary": BOUNDARY_INVARIANT,
            "discovery": DISCOVERY_INVARIANT,
        },
    }

    return {
        **body,
        "digest": digest(body),
    }


def extract_learning_candidates(
    *,
    turn_ref: str,
    observations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []

    for index, observation in enumerate(
        observations
    ):
        facet = clean(
            observation.get("facet")
        )
        expression = clean(
            observation.get("expression")
        )

        if not facet or not expression:
            continue

        explicit = bool(
            observation.get("explicit", False)
        )

        confidence = unit(
            observation.get(
                "confidence",
                1.0 if explicit else 0.5,
            )
        )

        candidate = {
            "candidate_id": (
                f"candidate:{digest([turn_ref, index, facet, expression])[:24]}"
            ),
            "facet": facet,
            "expression": expression,
            "evidence_kind": (
                "explicit_statement"
                if explicit
                else "conversation"
            ),
            "confidence": confidence,
            "explicit": explicit,
            "context": dict(
                observation.get("context", {})
            ),
            "status": (
                "observed"
                if explicit
                else "inferred"
            ),
            "authority_effect": "none",
        }

        candidates.append(candidate)

    body = {
        "schema": SCHEMA,
        "owner": OWNER,
        "authority_effect": AUTHORITY_EFFECT,
        "turn_ref": clean(turn_ref),
        "candidates": candidates,
        "auto_accept": False,
        "requires_existing_envoy_adjudication": True,
    }

    return {
        **body,
        "digest": digest(body),
    }


def selftest() -> dict[str, Any]:
    controls = {
        "enabled": True,
        "depth": 0.8,
        "initiative": 0.7,
        "scenario_use": 0.8,
        "contradiction_probe": 0.9,
        "idiosyncrasy_hunt": 1.0,
        "conversational_subtlety": 0.9,
        "direct_question_tolerance": 0.4,
        "topic_boundaries": ["private-topic"],
    }

    targets = (
        {
            "facet": "humor",
            "coverage": 0.7,
            "confidence": 0.8,
            "contradiction_count": 0,
            "relevance": 0.8,
            "novelty": 0.8,
            "context_gap": 0.5,
        },
        {
            "facet": "forgiveness",
            "coverage": 0.2,
            "confidence": 0.3,
            "contradiction_count": 2,
            "relevance": 0.8,
            "novelty": 0.7,
            "context_gap": 0.9,
        },
    )

    selected = choose_target(
        targets=targets,
        controls=controls,
    )

    assert selected is not None
    assert selected["facet"] == "forgiveness"

    directive = conversation_directive(
        target=targets[1],
        controls=controls,
    )

    assert directive["question_kind"] == "contrast"

    candidates = extract_learning_candidates(
        turn_ref="conversation:selftest:1",
        observations=(
            {
                "facet": "sarcasm",
                "expression": (
                    "uses sarcasm to soften criticism"
                ),
                "explicit": False,
                "confidence": 0.72,
                "context": {
                    "relationship": "friend",
                },
            },
        ),
    )

    assert candidates["auto_accept"] is False
    assert len(candidates["candidates"]) == 1

    repeated = choose_target(
        targets=targets,
        controls=controls,
    )

    assert repeated == selected

    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "ok": True,
        "deterministic_targeting": True,
        "static_questionnaire": False,
        "boundary_preserving": True,
        "automatic_trait_acceptance": False,
        "digest": digest(
            {
                "selected": selected,
                "directive": directive,
                "candidates": candidates,
            }
        ),
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] != "--selftest":
        print(
            "usage: personality_discovery.py --selftest",
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

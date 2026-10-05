#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from personality_datrix import (
    PersonalityDatrix,
    PersonalityDatrixError,
)


SCHEMA = "savant.envoy.ideal-self-composition.v1"
OWNER = "exile:envoy"
EXECUTION_OWNER = "opus"
AUTHORITY_EFFECT = "none"

SELF_OBSERVED = "observed-self"
SELF_ACCEPTED = "accepted-self"
SELF_ASPIRATIONAL = "aspirational-self"
SELF_IDEAL = "ideal-self"

VALID_SELF_PROJECTIONS = frozenset(
    {
        SELF_OBSERVED,
        SELF_ACCEPTED,
        SELF_ASPIRATIONAL,
        SELF_IDEAL,
    }
)

CANDOR_MODES = (
    "mirror",
    "gentle",
    "candid",
    "challenge",
    "unfiltered",
)

AUGMENTATION_KINDS = (
    "reasoning",
    "verification",
    "research",
    "memory",
    "planning",
    "counterfactual",
    "creativity",
    "skepticism",
    "precision",
    "restraint",
    "uncertainty",
    "communication",
)

TRUTH_INVARIANT = (
    "candor controls disclosure and challenge intensity but never mutates "
    "evidence, provenance, contradiction, confidence, or accepted personality"
)

IDENTITY_INVARIANT = (
    "cognitive augmentation may improve capability but may not silently "
    "replace the user's accepted identity, values, boundaries, or aspirations"
)

IDEALIZATION_INVARIANT = (
    "a personality weakness may be compensated for in ideal-self projection "
    "only when the corresponding aspiration or correction target is accepted "
    "by the user"
)

OPUS_INVARIANT = (
    "envoy may describe required cognitive augmentation but opus retains "
    "execution, provider-selection, and model-selection ownership"
)


class IdealSelfCompositionError(RuntimeError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical(value).encode("utf-8")
    ).hexdigest()


def clean(value: Any) -> str:
    return " ".join(
        str(value or "").strip().split()
    )


def required(value: Any, name: str) -> str:
    result = clean(value)

    if not result:
        raise IdealSelfCompositionError(
            f"{name} is required"
        )

    return result


def unit(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise IdealSelfCompositionError(
            f"{name} must be numeric"
        ) from exc

    if result < 0.0 or result > 1.0:
        raise IdealSelfCompositionError(
            f"{name} must be between 0.0 and 1.0"
        )

    return result


def unique_strings(
    values: Iterable[Any],
) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        item = clean(value)

        if item and item not in seen:
            seen.add(item)
            result.append(item)

    return tuple(result)


@dataclass(frozen=True)
class CandorControls:
    candor: float = 0.75
    challenge: float = 0.70
    unsolicited_truth: bool = True
    soften_delivery: float = 0.25
    preserve_humor: bool = True
    preserve_sarcasm: bool = True
    explain_evidence: bool = True

    @classmethod
    def normalize(
        cls,
        value: Mapping[str, Any] | None,
    ) -> "CandorControls":
        value = value or {}

        return cls(
            candor=unit(
                value.get("candor", 0.75),
                "candor",
            ),
            challenge=unit(
                value.get("challenge", 0.70),
                "challenge",
            ),
            unsolicited_truth=bool(
                value.get(
                    "unsolicited_truth",
                    True,
                )
            ),
            soften_delivery=unit(
                value.get(
                    "soften_delivery",
                    0.25,
                ),
                "soften_delivery",
            ),
            preserve_humor=bool(
                value.get(
                    "preserve_humor",
                    True,
                )
            ),
            preserve_sarcasm=bool(
                value.get(
                    "preserve_sarcasm",
                    True,
                )
            ),
            explain_evidence=bool(
                value.get(
                    "explain_evidence",
                    True,
                )
            ),
        )

    @property
    def mode(self) -> str:
        index = min(
            len(CANDOR_MODES) - 1,
            int(
                self.candor
                * len(CANDOR_MODES)
            ),
        )

        return CANDOR_MODES[index]

    def projection(self) -> dict[str, Any]:
        return {
            "candor": self.candor,
            "challenge": self.challenge,
            "mode": self.mode,
            "unsolicited_truth": (
                self.unsolicited_truth
            ),
            "soften_delivery": (
                self.soften_delivery
            ),
            "preserve_humor": (
                self.preserve_humor
            ),
            "preserve_sarcasm": (
                self.preserve_sarcasm
            ),
            "explain_evidence": (
                self.explain_evidence
            ),
            "rewrite_truth_for_comfort": False,
        }


@dataclass(frozen=True)
class IdealSelfControls:
    enabled: bool = True
    identity_fidelity: float = 1.0
    aspiration_strength: float = 0.80
    cognitive_augmentation: float = 1.0
    preserve_idiosyncrasy: float = 1.0
    preserve_voice: float = 1.0
    preserve_humor: float = 1.0
    preserve_sarcasm: float = 1.0
    preserve_values: float = 1.0
    compensate_accepted_flaws: float = 0.85

    @classmethod
    def normalize(
        cls,
        value: Mapping[str, Any] | None,
    ) -> "IdealSelfControls":
        value = value or {}

        return cls(
            enabled=bool(
                value.get("enabled", True)
            ),
            identity_fidelity=unit(
                value.get(
                    "identity_fidelity",
                    1.0,
                ),
                "identity_fidelity",
            ),
            aspiration_strength=unit(
                value.get(
                    "aspiration_strength",
                    0.80,
                ),
                "aspiration_strength",
            ),
            cognitive_augmentation=unit(
                value.get(
                    "cognitive_augmentation",
                    1.0,
                ),
                "cognitive_augmentation",
            ),
            preserve_idiosyncrasy=unit(
                value.get(
                    "preserve_idiosyncrasy",
                    1.0,
                ),
                "preserve_idiosyncrasy",
            ),
            preserve_voice=unit(
                value.get(
                    "preserve_voice",
                    1.0,
                ),
                "preserve_voice",
            ),
            preserve_humor=unit(
                value.get(
                    "preserve_humor",
                    1.0,
                ),
                "preserve_humor",
            ),
            preserve_sarcasm=unit(
                value.get(
                    "preserve_sarcasm",
                    1.0,
                ),
                "preserve_sarcasm",
            ),
            preserve_values=unit(
                value.get(
                    "preserve_values",
                    1.0,
                ),
                "preserve_values",
            ),
            compensate_accepted_flaws=unit(
                value.get(
                    "compensate_accepted_flaws",
                    0.85,
                ),
                "compensate_accepted_flaws",
            ),
        )

    def projection(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "identity_fidelity": (
                self.identity_fidelity
            ),
            "aspiration_strength": (
                self.aspiration_strength
            ),
            "cognitive_augmentation": (
                self.cognitive_augmentation
            ),
            "preserve_idiosyncrasy": (
                self.preserve_idiosyncrasy
            ),
            "preserve_voice": (
                self.preserve_voice
            ),
            "preserve_humor": (
                self.preserve_humor
            ),
            "preserve_sarcasm": (
                self.preserve_sarcasm
            ),
            "preserve_values": (
                self.preserve_values
            ),
            "compensate_accepted_flaws": (
                self.compensate_accepted_flaws
            ),
        }


@dataclass(frozen=True)
class CognitiveNeed:
    kind: str
    strength: float
    reason: str
    trait_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    @classmethod
    def normalize(
        cls,
        value: Mapping[str, Any],
    ) -> "CognitiveNeed":
        kind = required(
            value.get("kind"),
            "kind",
        )

        if kind not in AUGMENTATION_KINDS:
            raise IdealSelfCompositionError(
                f"unsupported augmentation kind: "
                f"{kind}"
            )

        return cls(
            kind=kind,
            strength=unit(
                value.get("strength", 1.0),
                "strength",
            ),
            reason=required(
                value.get("reason"),
                "reason",
            ),
            trait_refs=unique_strings(
                value.get("trait_refs", ())
            ),
            evidence_refs=unique_strings(
                value.get(
                    "evidence_refs",
                    (),
                )
            ),
        )

    def projection(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "strength": self.strength,
            "reason": self.reason,
            "trait_refs": list(
                self.trait_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
        }


def _trait_id(
    trait: Mapping[str, Any],
) -> str:
    return clean(
        trait.get("trait_id")
        or trait.get("id")
    )


def _trait_facet(
    trait: Mapping[str, Any],
) -> str:
    return clean(
        trait.get("facet")
    )


def _trait_expression(
    trait: Mapping[str, Any],
) -> str:
    return clean(
        trait.get("expression")
    )


def _trait_evidence(
    trait: Mapping[str, Any],
) -> tuple[str, ...]:
    refs = trait.get(
        "evidence_refs",
        (),
    )

    if not isinstance(
        refs,
        (list, tuple),
    ):
        return ()

    return unique_strings(refs)


def _accepted_corrections(
    datrix_projection: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    ideal = datrix_projection.get(
        "ideal_self",
        {},
    )

    if not isinstance(ideal, Mapping):
        return ()

    corrections = ideal.get(
        "accepted_corrections",
        (),
    )

    if not isinstance(
        corrections,
        list,
    ):
        return ()

    return tuple(
        item
        for item in corrections
        if isinstance(item, Mapping)
    )


def _accepted_identity(
    datrix_projection: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    ideal = datrix_projection.get(
        "ideal_self",
        {},
    )

    if not isinstance(ideal, Mapping):
        return ()

    identity = ideal.get(
        "accepted_identity",
        (),
    )

    if not isinstance(
        identity,
        list,
    ):
        return ()

    return tuple(
        item
        for item in identity
        if isinstance(item, Mapping)
    )


def _augmentation_for_facet(
    facet: str,
) -> tuple[str, ...]:
    mapping = {
        "analysis": (
            "reasoning",
            "verification",
        ),
        "bias": (
            "skepticism",
            "verification",
        ),
        "confidence": (
            "uncertainty",
            "verification",
        ),
        "creativity": (
            "creativity",
        ),
        "curiosity": (
            "research",
        ),
        "decision_style": (
            "reasoning",
            "counterfactual",
        ),
        "defensiveness": (
            "skepticism",
            "restraint",
        ),
        "deliberation": (
            "reasoning",
            "counterfactual",
        ),
        "emotional_regulation": (
            "restraint",
        ),
        "impulsivity": (
            "planning",
            "counterfactual",
            "restraint",
        ),
        "intuition": (
            "verification",
            "counterfactual",
        ),
        "learning": (
            "research",
            "memory",
        ),
        "memory_preferences": (
            "memory",
        ),
        "planning": (
            "planning",
        ),
        "problem_solving": (
            "reasoning",
            "counterfactual",
        ),
        "rationalization": (
            "skepticism",
            "verification",
        ),
        "risk": (
            "counterfactual",
            "uncertainty",
        ),
        "self_awareness": (
            "skepticism",
        ),
        "skepticism": (
            "verification",
        ),
        "uncertainty": (
            "uncertainty",
            "verification",
        ),
        "communication": (
            "communication",
        ),
        "directness": (
            "communication",
        ),
        "conflict": (
            "communication",
            "restraint",
        ),
        "persuasion": (
            "communication",
        ),
        "storytelling": (
            "communication",
            "creativity",
        ),
    }

    return mapping.get(
        facet,
        ("reasoning",),
    )


def derive_cognitive_needs(
    datrix_projection: Mapping[str, Any],
    *,
    controls: Mapping[str, Any] | None = None,
) -> tuple[CognitiveNeed, ...]:
    ideal_controls = (
        IdealSelfControls.normalize(
            controls
        )
    )

    if not ideal_controls.enabled:
        return ()

    grouped: dict[
        str,
        dict[str, Any],
    ] = {}

    for trait in _accepted_corrections(
        datrix_projection
    ):
        facet = _trait_facet(trait)
        trait_id = _trait_id(trait)
        expression = _trait_expression(
            trait
        )
        evidence_refs = (
            _trait_evidence(trait)
        )

        if not facet or not trait_id:
            continue

        for kind in _augmentation_for_facet(
            facet
        ):
            state = grouped.setdefault(
                kind,
                {
                    "strength": 0.0,
                    "reasons": [],
                    "trait_refs": set(),
                    "evidence_refs": set(),
                },
            )

            strength = (
                ideal_controls
                .cognitive_augmentation
                * ideal_controls
                .compensate_accepted_flaws
            )

            state["strength"] = max(
                state["strength"],
                strength,
            )

            state["reasons"].append(
                f"{facet}: {expression}"
            )

            state["trait_refs"].add(
                trait_id
            )

            state["evidence_refs"].update(
                evidence_refs
            )

    needs: list[CognitiveNeed] = []

    for kind in sorted(grouped):
        state = grouped[kind]

        needs.append(
            CognitiveNeed(
                kind=kind,
                strength=round(
                    state["strength"],
                    6,
                ),
                reason="; ".join(
                    sorted(
                        set(
                            state["reasons"]
                        )
                    )
                ),
                trait_refs=tuple(
                    sorted(
                        state[
                            "trait_refs"
                        ]
                    )
                ),
                evidence_refs=tuple(
                    sorted(
                        state[
                            "evidence_refs"
                        ]
                    )
                ),
            )
        )

    return tuple(needs)


def build_identity_preservation(
    datrix_projection: Mapping[str, Any],
    *,
    controls: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    ideal_controls = (
        IdealSelfControls.normalize(
            controls
        )
    )

    identity = _accepted_identity(
        datrix_projection
    )

    preserve_facets = {
        "values",
        "ethics",
        "identity",
        "humor",
        "sarcasm",
        "irony",
        "deadpan",
        "absurdity",
        "wordplay",
        "gallows_humor",
        "self_deprecation",
        "teasing",
        "humor_boundaries",
        "vocabulary",
        "syntax",
        "rhythm",
        "profanity",
        "storytelling",
        "idiosyncrasy",
        "directness",
        "aesthetics",
        "taste",
    }

    preserved = [
        dict(trait)
        for trait in identity
        if _trait_facet(trait)
        in preserve_facets
    ]

    body = {
        "schema": SCHEMA,
        "owner": OWNER,
        "authority_effect": (
            AUTHORITY_EFFECT
        ),
        "controls": (
            ideal_controls.projection()
        ),
        "preserved_traits": preserved,
        "preserve_values": True,
        "preserve_voice": True,
        "preserve_humor": True,
        "preserve_sarcasm": True,
        "preserve_idiosyncrasy": True,
        "identity_invariant": (
            IDENTITY_INVARIANT
        ),
    }

    return {
        **body,
        "digest": digest(body),
    }


def build_candor_projection(
    *,
    controls: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candor = CandorControls.normalize(
        controls
    )

    body = {
        "schema": SCHEMA,
        "owner": OWNER,
        "authority_effect": (
            AUTHORITY_EFFECT
        ),
        "controls": candor.projection(),
        "truth_invariant": TRUTH_INVARIANT,
        "behavior": {
            "may_soften_delivery": True,
            "may_withhold_unsolicited_challenge": (
                not candor.unsolicited_truth
            ),
            "may_reduce_challenge_intensity": True,
            "may_rewrite_evidence": False,
            "may_rewrite_accepted_traits": False,
            "may_invent_user_acceptance": False,
        },
    }

    return {
        **body,
        "digest": digest(body),
    }


def build_ideal_self_projection(
    datrix: PersonalityDatrix,
    *,
    ideal_controls: Mapping[str, Any] | None = None,
    candor_controls: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(
        datrix,
        PersonalityDatrix,
    ):
        raise IdealSelfCompositionError(
            "datrix must be PersonalityDatrix"
        )

    source = datrix.projection()

    ideal = IdealSelfControls.normalize(
        ideal_controls
    )

    needs = derive_cognitive_needs(
        source,
        controls=ideal_controls,
    )

    identity = build_identity_preservation(
        source,
        controls=ideal_controls,
    )

    candor = build_candor_projection(
        controls=candor_controls,
    )

    accepted_corrections = [
        dict(item)
        for item in _accepted_corrections(
            source
        )
    ]

    body = {
        "schema": SCHEMA,
        "owner": OWNER,
        "execution_owner": EXECUTION_OWNER,
        "authority_effect": (
            AUTHORITY_EFFECT
        ),
        "projection_only": True,
        "persona_id": datrix.persona_id,
        "personality_datrix_digest": (
            source["digest"]
        ),
        "projection": (
            SELF_IDEAL
            if ideal.enabled
            else SELF_ACCEPTED
        ),
        "ideal_controls": (
            ideal.projection()
        ),
        "candor": candor,
        "identity_preservation": (
            identity
        ),
        "accepted_corrections": (
            accepted_corrections
            if ideal.enabled
            else []
        ),
        "cognitive_needs": [
            item.projection()
            for item in needs
        ],
        "invariants": {
            "truth": TRUTH_INVARIANT,
            "identity": IDENTITY_INVARIANT,
            "idealization": (
                IDEALIZATION_INVARIANT
            ),
            "opus": OPUS_INVARIANT,
        },
        "envoy_may_select_provider": False,
        "envoy_may_select_model": False,
        "envoy_may_access_credentials": False,
    }

    return {
        **body,
        "digest": digest(body),
    }


def opus_augmentation_request(
    ideal_projection: Mapping[str, Any],
    *,
    domains: Iterable[Any] = (),
    signals: Iterable[Any] = (),
) -> dict[str, Any]:
    if ideal_projection.get(
        "schema"
    ) != SCHEMA:
        raise IdealSelfCompositionError(
            "unsupported ideal-self schema"
        )

    if ideal_projection.get(
        "owner"
    ) != OWNER:
        raise IdealSelfCompositionError(
            "ideal-self owner must be envoy"
        )

    if ideal_projection.get(
        "execution_owner"
    ) != EXECUTION_OWNER:
        raise IdealSelfCompositionError(
            "opus execution ownership missing"
        )

    needs = ideal_projection.get(
        "cognitive_needs",
        (),
    )

    if not isinstance(needs, list):
        raise IdealSelfCompositionError(
            "cognitive_needs must be a list"
        )

    normalized_domains = (
        unique_strings(domains)
    )
    normalized_signals = (
        unique_strings(signals)
    )

    body = {
        "schema": (
            "savant.envoy."
            "ideal-self-opus-request.v1"
        ),
        "owner": OWNER,
        "execution_owner": EXECUTION_OWNER,
        "authority_effect": (
            AUTHORITY_EFFECT
        ),
        "projection_only": True,
        "persona_id": ideal_projection[
            "persona_id"
        ],
        "ideal_self_digest": (
            ideal_projection["digest"]
        ),
        "domains": list(
            normalized_domains
        ),
        "signals": list(
            normalized_signals
        ),
        "required_cognitive_traits": [
            {
                "trait": item["kind"],
                "strength": item[
                    "strength"
                ],
                "reason": item["reason"],
                "personality_trait_refs": (
                    item["trait_refs"]
                ),
                "evidence_refs": (
                    item["evidence_refs"]
                ),
            }
            for item in needs
            if isinstance(item, Mapping)
        ],
        "constraints": {
            "preserve_identity": True,
            "preserve_values": True,
            "preserve_voice": True,
            "preserve_humor": True,
            "preserve_sarcasm": True,
            "preserve_idiosyncrasy": True,
            "accepted_corrections_only": True,
            "provider_selection_owner": (
                EXECUTION_OWNER
            ),
            "model_selection_owner": (
                EXECUTION_OWNER
            ),
        },
    }

    return {
        **body,
        "digest": digest(body),
    }


def compose(
    *,
    persona_id: str,
    evidence: Sequence[Mapping[str, Any]],
    traits: Sequence[Mapping[str, Any]],
    segues: Sequence[Mapping[str, Any]],
    ideal_controls: Mapping[str, Any] | None = None,
    candor_controls: Mapping[str, Any] | None = None,
    domains: Iterable[Any] = (),
    signals: Iterable[Any] = (),
) -> dict[str, Any]:
    try:
        datrix = PersonalityDatrix.compose(
            persona_id=persona_id,
            evidence=evidence,
            traits=traits,
            segues=segues,
        )
    except PersonalityDatrixError as exc:
        raise IdealSelfCompositionError(
            str(exc)
        ) from exc

    ideal = build_ideal_self_projection(
        datrix,
        ideal_controls=ideal_controls,
        candor_controls=candor_controls,
    )

    opus = opus_augmentation_request(
        ideal,
        domains=domains,
        signals=signals,
    )

    body = {
        "schema": SCHEMA,
        "owner": OWNER,
        "authority_effect": (
            AUTHORITY_EFFECT
        ),
        "persona_id": persona_id,
        "personality_datrix": (
            datrix.projection()
        ),
        "ideal_self": ideal,
        "opus_request": opus,
    }

    return {
        **body,
        "digest": digest(body),
    }


def selftest() -> dict[str, Any]:
    evidence = (
        {
            "evidence_id": "evidence:humor",
            "kind": "conversation",
            "content": (
                "uses dry sarcasm with trusted people"
            ),
            "confidence": 0.95,
            "source_ref": (
                "selftest:conversation:humor"
            ),
            "context": {
                "relationship": "trusted",
            },
        },
        {
            "evidence_id": "evidence:restraint",
            "kind": "correction",
            "content": (
                "wants greater restraint when angry"
            ),
            "confidence": 1.0,
            "source_ref": (
                "selftest:correction:restraint"
            ),
            "context": {
                "emotional_state": "angry",
            },
        },
    )

    traits = (
        {
            "trait_id": "trait:sarcasm",
            "facet": "sarcasm",
            "expression": (
                "dry sarcasm with trusted people"
            ),
            "status": "accepted",
            "confidence": 0.95,
            "evidence_refs": [
                "evidence:humor",
            ],
            "contexts": [
                {
                    "relationship": "trusted",
                },
            ],
            "user_accepted": True,
        },
        {
            "trait_id": (
                "trait:restraint:observed"
            ),
            "facet": "emotional_regulation",
            "expression": (
                "reacts too quickly when angry"
            ),
            "status": "accepted",
            "confidence": 0.92,
            "evidence_refs": [
                "evidence:restraint",
            ],
            "contexts": [
                {
                    "emotional_state": "angry",
                },
            ],
            "user_accepted": True,
        },
        {
            "trait_id": (
                "trait:restraint:aspiration"
            ),
            "facet": "emotional_regulation",
            "expression": (
                "retain directness with "
                "greater restraint"
            ),
            "status": "accepted",
            "confidence": 1.0,
            "evidence_refs": [
                "evidence:restraint",
            ],
            "contexts": [
                {
                    "emotional_state": "angry",
                },
            ],
            "user_accepted": True,
            "aspirational": True,
            "correction_target": True,
        },
    )

    segues = (
        {
            "segue_id": (
                "segue:restraint:aspiration"
            ),
            "kind": "aspires_from",
            "source_id": (
                "trait:restraint:aspiration"
            ),
            "target_id": (
                "trait:restraint:observed"
            ),
            "confidence": 1.0,
            "evidence_refs": [
                "evidence:restraint",
            ],
        },
    )

    result = compose(
        persona_id="persona:selftest",
        evidence=evidence,
        traits=traits,
        segues=segues,
        ideal_controls={
            "enabled": True,
            "identity_fidelity": 1.0,
            "cognitive_augmentation": 1.0,
            "preserve_humor": 1.0,
            "preserve_sarcasm": 1.0,
        },
        candor_controls={
            "candor": 1.0,
            "challenge": 1.0,
            "unsolicited_truth": True,
            "soften_delivery": 0.0,
        },
        domains=(
            "conversation",
            "analysis",
        ),
        signals=(
            "reason",
            "verify",
        ),
    )

    repeated = compose(
        persona_id="persona:selftest",
        evidence=evidence,
        traits=traits,
        segues=segues,
        ideal_controls={
            "enabled": True,
            "identity_fidelity": 1.0,
            "cognitive_augmentation": 1.0,
            "preserve_humor": 1.0,
            "preserve_sarcasm": 1.0,
        },
        candor_controls={
            "candor": 1.0,
            "challenge": 1.0,
            "unsolicited_truth": True,
            "soften_delivery": 0.0,
        },
        domains=(
            "conversation",
            "analysis",
        ),
        signals=(
            "reason",
            "verify",
        ),
    )

    if result != repeated:
        raise IdealSelfCompositionError(
            "composition is not deterministic"
        )

    ideal = result["ideal_self"]

    if ideal[
        "envoy_may_select_provider"
    ] is not False:
        raise IdealSelfCompositionError(
            "provider authority boundary failed"
        )

    if ideal[
        "envoy_may_select_model"
    ] is not False:
        raise IdealSelfCompositionError(
            "model authority boundary failed"
        )

    if ideal[
        "envoy_may_access_credentials"
    ] is not False:
        raise IdealSelfCompositionError(
            "credential authority boundary failed"
        )

    preserved = ideal[
        "identity_preservation"
    ]["preserved_traits"]

    if not any(
        item.get("facet") == "sarcasm"
        for item in preserved
    ):
        raise IdealSelfCompositionError(
            "sarcasm identity preservation failed"
        )

    corrections = ideal[
        "accepted_corrections"
    ]

    if len(corrections) != 1:
        raise IdealSelfCompositionError(
            "accepted correction projection failed"
        )

    needs = {
        item["kind"]
        for item in ideal[
            "cognitive_needs"
        ]
    }

    if "restraint" not in needs:
        raise IdealSelfCompositionError(
            "accepted weakness did not "
            "produce cognitive augmentation"
        )

    opus = result["opus_request"]

    if opus[
        "execution_owner"
    ] != EXECUTION_OWNER:
        raise IdealSelfCompositionError(
            "opus ownership failed"
        )

    low_candor = build_candor_projection(
        controls={
            "candor": 0.0,
            "challenge": 0.0,
            "unsolicited_truth": False,
        }
    )

    if low_candor[
        "behavior"
    ]["may_rewrite_evidence"]:
        raise IdealSelfCompositionError(
            "low candor corrupted truth"
        )

    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "execution_owner": (
            EXECUTION_OWNER
        ),
        "ok": True,
        "deterministic": True,
        "truth_preserved": True,
        "identity_preserved": True,
        "humor_preserved": True,
        "sarcasm_preserved": True,
        "accepted_corrections_only": True,
        "opus_authority_preserved": True,
        "cognitive_need_count": len(
            ideal["cognitive_needs"]
        ),
        "digest": result["digest"],
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] != "--selftest":
        print(
            "usage: "
            "ideal_self_composition.py "
            "--selftest",
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

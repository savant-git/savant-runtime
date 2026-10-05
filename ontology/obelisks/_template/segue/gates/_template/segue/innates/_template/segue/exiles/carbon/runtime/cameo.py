#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


schema = "savant://carbon/cameo/1.0.0"
owner = "carbon"
specialization = "cameo"
authority_effect = "none"


DIMENSIONS: dict[str, float] = {
    "premise": 0.15,
    "intent": 0.10,
    "character_agency": 0.12,
    "destination": 0.10,
    "transformation": 0.10,
    "causality": 0.09,
    "constraint": 0.06,
    "information_architecture": 0.08,
    "escalation": 0.05,
    "convergence": 0.06,
    "meaning": 0.05,
    "presentation": 0.04,
}

ZONE_A = frozenset(
    {
        "premise",
        "intent",
        "character_agency",
        "destination",
    }
)

ZONE_B = frozenset(
    {
        "transformation",
        "causality",
        "information_architecture",
        "convergence",
        "meaning",
    }
)

ZONE_C = frozenset(
    {
        "constraint",
        "escalation",
        "presentation",
    }
)

PROVENANCE_CREDIT: dict[str, float] = {
    "u0": 1.00,
    "u1": 0.95,
    "u2": 0.80,
    "joint": 0.50,
    "a2": 0.65,
    "a1": 0.35,
    "a0": 0.15,
}

CANON_STATES = frozenset(
    {
        "user_primitive",
        "open_question",
        "ai_candidate",
        "user_selected_candidate",
        "user_transformed_development",
        "accepted_canon",
    }
)

BRAINSTORM_MODES = frozenset(
    {
        "diagnostic",
        "expansion",
        "bridge",
        "convergence",
        "directed_possibility",
        "open_catalyst",
    }
)

TRIVIALITY_CHANNELS = (
    "physical",
    "informational",
    "temporal",
    "spatial",
    "social",
    "psychological",
    "procedural",
    "symbolic",
)

ENHANCEMENTS = (
    "narrative_atom_decomposition",
    "twelve_dimension_sovereignty",
    "zone_a_protection",
    "zone_b_candidate_control",
    "zone_c_assistance_freedom",
    "mixed_provenance_accounting",
    "transformation_depth",
    "dependency_leverage",
    "irreplaceability_weighting",
    "identity_novelty_weighting",
    "constraint_pressure",
    "rejection_as_constraint",
    "causal_distance",
    "identity_drift",
    "counterfactual_ownership",
    "replacement_testing",
    "triviality_transmutation",
    "causal_quality_scoring",
    "multifunctionality",
    "coincidence_debt",
    "information_provenance",
    "character_agency_protection",
    "endogenous_escalation",
    "retrospective_obviousness",
    "candidate_diversity",
    "hard_sovereignty_floors",
    "slider_permission_projection",
    "anchor_enforcement",
    "canon_state_separation",
    "deterministic_projection",
    "content_addressing",
    "opus_orchestration",
    "provider_failure_isolation",
    "ai_output_containment",
    "user_selection_accounting",
    "replay_safe_scoring",
)


def clamp(
    value: float,
    low: float = 0.0,
    high: float = 1.0,
) -> float:
    return max(
        low,
        min(
            high,
            float(value),
        ),
    )


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def smoothstep(
    value: float,
) -> float:
    x = clamp(value)
    return x * x * (3.0 - 2.0 * x)


def involvement_projection(
    involvement: float,
) -> dict[str, Any]:
    raw = max(
        0.0,
        min(
            100.0,
            float(involvement),
        ),
    )

    x = raw / 100.0
    activation = smoothstep(x)

    if raw <= 10:
        label = "editorial"
        maximum_mode = "diagnostic"
    elif raw <= 30:
        label = "conservative"
        maximum_mode = "expansion"
    elif raw <= 55:
        label = "developmental"
        maximum_mode = "bridge"
    elif raw <= 75:
        label = "collaborative"
        maximum_mode = "convergence"
    elif raw <= 90:
        label = "inventive"
        maximum_mode = "directed_possibility"
    else:
        label = "open_ideation"
        maximum_mode = "open_catalyst"

    projection = {
        "slider": raw,
        "normalized": x,
        "activation": activation,
        "label": label,
        "maximum_mode": maximum_mode,
        "canonical_authority_ai": 0.0,
        "canonical_authority_user": 1.0,
        "candidate_breadth": int(
            round(2 + 6 * activation)
        ),
        "causal_distance_limit": int(
            round(1 + 7 * activation)
        ),
        "identity_drift_limit": (
            0.05 + 0.75 * activation
        ),
        "opus_round_budget": int(
            round(1 + 5 * activation)
        ),
        "opus_candidate_budget": int(
            round(2 + 10 * activation)
        ),
        "zone_a_origin_permission": (
            raw >= 91
        ),
        "zone_b_origin_permission": (
            raw >= 36
        ),
        "zone_c_origin_permission": True,
        "user_sovereignty_floor": (
            0.90 - 0.30 * activation
        ),
        "zone_a_user_floor": (
            0.97 - 0.37 * activation
        ),
        "identity_bearing_user_floor": (
            0.90 - 0.35 * activation
        ),
        "requires_user_adoption": True,
        "authority_effect": "none",
    }

    projection["digest"] = digest(projection)
    return projection


@dataclass(frozen=True)
class Transformation:
    result: float = 0.0
    motivation: float = 0.0
    causality: float = 0.0
    dramatic_function: float = 0.0
    thematic_meaning: float = 0.0

    def score(self) -> float:
        values = (
            self.result,
            self.motivation,
            self.causality,
            self.dramatic_function,
            self.thematic_meaning,
        )

        return sum(
            clamp(value)
            for value in values
        ) / len(values)


@dataclass(frozen=True)
class NarrativeAtom:
    atom_id: str
    statement: str
    dimension: str
    provenance: str
    canon_state: str = "open_question"
    dependencies: tuple[str, ...] = ()
    dependent_count: int = 0
    irreplaceability: float = 0.5
    novelty: float = 0.5
    constraint_pressure: float = 0.0
    causal_distance: int = 0
    identity_drift: float = 0.0
    transformation: Transformation = field(
        default_factory=Transformation
    )
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if self.dimension not in DIMENSIONS:
            raise ValueError(
                "unknown cameo dimension: "
                f"{self.dimension}"
            )

        if self.provenance not in PROVENANCE_CREDIT:
            raise ValueError(
                "unknown provenance class: "
                f"{self.provenance}"
            )

        if self.canon_state not in CANON_STATES:
            raise ValueError(
                "unknown canon state: "
                f"{self.canon_state}"
            )

        if self.causal_distance < 0:
            raise ValueError(
                "causal_distance must be nonnegative"
            )

        if self.dependent_count < 0:
            raise ValueError(
                "dependent_count must be nonnegative"
            )

    def zone(self) -> str:
        if self.dimension in ZONE_A:
            return "a"

        if self.dimension in ZONE_B:
            return "b"

        return "c"

    def dependency_leverage(self) -> float:
        return 1.0 + math.log2(
            1.0 + self.dependent_count
        )

    def importance_weight(self) -> float:
        base = DIMENSIONS[self.dimension]

        leverage = self.dependency_leverage()

        irreplaceability = (
            0.6
            + 0.4
            * clamp(self.irreplaceability)
        )

        novelty = (
            0.7
            + 0.3
            * clamp(self.novelty)
        )

        return (
            base
            * leverage
            * irreplaceability
            * novelty
        )

    def user_credit(self) -> float:
        base = PROVENANCE_CREDIT[
            self.provenance
        ]

        transformation = (
            self.transformation.score()
        )

        transformed_credit = (
            base
            + (1.0 - base)
            * 0.35
            * transformation
        )

        constraint_credit = (
            0.10
            * clamp(self.constraint_pressure)
        )

        return clamp(
            transformed_credit
            + constraint_credit
        )

    def projection(self) -> dict[str, Any]:
        result = {
            "atom_id": self.atom_id,
            "statement": self.statement,
            "dimension": self.dimension,
            "zone": self.zone(),
            "provenance": self.provenance,
            "canon_state": self.canon_state,
            "dependencies": list(
                self.dependencies
            ),
            "dependent_count": (
                self.dependent_count
            ),
            "dependency_leverage": (
                self.dependency_leverage()
            ),
            "irreplaceability": clamp(
                self.irreplaceability
            ),
            "novelty": clamp(
                self.novelty
            ),
            "constraint_pressure": clamp(
                self.constraint_pressure
            ),
            "causal_distance": (
                self.causal_distance
            ),
            "identity_drift": clamp(
                self.identity_drift
            ),
            "transformation_depth": (
                self.transformation.score()
            ),
            "importance_weight": (
                self.importance_weight()
            ),
            "user_sovereignty_credit": (
                self.user_credit()
            ),
            "metadata": dict(self.metadata),
            "authority_effect": "none",
        }

        result["digest"] = digest(result)
        return result


def sovereignty(
    atoms: Iterable[NarrativeAtom],
) -> dict[str, Any]:
    values = list(atoms)

    total_weight = sum(
        atom.importance_weight()
        for atom in values
    )

    if total_weight <= 0.0:
        user_score = 1.0
    else:
        user_score = sum(
            atom.importance_weight()
            * atom.user_credit()
            for atom in values
        ) / total_weight

    zone_a = [
        atom
        for atom in values
        if atom.zone() == "a"
    ]

    zone_a_weight = sum(
        atom.importance_weight()
        for atom in zone_a
    )

    if zone_a_weight <= 0.0:
        zone_a_score = 1.0
    else:
        zone_a_score = sum(
            atom.importance_weight()
            * atom.user_credit()
            for atom in zone_a
        ) / zone_a_weight

    identity_atoms = [
        atom
        for atom in values
        if atom.novelty >= 0.75
    ]

    identity_weight = sum(
        atom.importance_weight()
        for atom in identity_atoms
    )

    if identity_weight <= 0.0:
        identity_score = 1.0
    else:
        identity_score = sum(
            atom.importance_weight()
            * atom.user_credit()
            for atom in identity_atoms
        ) / identity_weight

    result = {
        "atom_count": len(values),
        "user_sovereignty": user_score,
        "ai_sovereignty": (
            1.0 - user_score
        ),
        "zone_a_user_sovereignty": (
            zone_a_score
        ),
        "identity_bearing_user_sovereignty": (
            identity_score
        ),
        "canonical_authority_user": 1.0,
        "canonical_authority_ai": 0.0,
        "authority_effect": "none",
    }

    result["digest"] = digest(result)
    return result


def evaluate_permissions(
    atom: NarrativeAtom,
    involvement: float,
) -> dict[str, Any]:
    policy = involvement_projection(
        involvement
    )

    zone = atom.zone()

    if zone == "a":
        origin_permitted = bool(
            policy["zone_a_origin_permission"]
        )
    elif zone == "b":
        origin_permitted = bool(
            policy["zone_b_origin_permission"]
        )
    else:
        origin_permitted = True

    distance_ok = (
        atom.causal_distance
        <= policy["causal_distance_limit"]
    )

    drift_ok = (
        clamp(atom.identity_drift)
        <= policy["identity_drift_limit"]
    )

    permitted = (
        origin_permitted
        and distance_ok
        and drift_ok
    )

    reasons: list[str] = []

    if not origin_permitted:
        reasons.append(
            "zone_origin_protected"
        )

    if not distance_ok:
        reasons.append(
            "causal_distance_exceeded"
        )

    if not drift_ok:
        reasons.append(
            "identity_drift_exceeded"
        )

    return {
        "permitted": permitted,
        "zone": zone,
        "reasons": reasons,
        "requires_user_adoption": True,
        "canonical_authority_ai": 0.0,
        "policy": policy,
        "authority_effect": "none",
    }


def causal_quality(
    *,
    plausibility: float,
    inevitability: float,
    economy: float,
    reinterpretation: float,
    character_consistency: float,
    multifunctionality: float,
    surprise: float,
    thematic_resonance: float,
) -> dict[str, Any]:
    scores = {
        "plausibility": clamp(plausibility),
        "inevitability": clamp(inevitability),
        "economy": clamp(economy),
        "reinterpretation": clamp(
            reinterpretation
        ),
        "character_consistency": clamp(
            character_consistency
        ),
        "multifunctionality": clamp(
            multifunctionality
        ),
        "surprise": clamp(surprise),
        "thematic_resonance": clamp(
            thematic_resonance
        ),
    }

    score = (
        0.20 * scores["plausibility"]
        + 0.15 * scores["inevitability"]
        + 0.15 * scores["economy"]
        + 0.15 * scores["reinterpretation"]
        + 0.10
        * scores["character_consistency"]
        + 0.10
        * scores["multifunctionality"]
        + 0.10 * scores["surprise"]
        + 0.05
        * scores["thematic_resonance"]
    )

    result = {
        "score": score,
        "scores": scores,
        "authority_effect": "none",
    }

    result["digest"] = digest(result)
    return result


def coincidence_debt(
    *,
    improbability: float,
    setup: float,
    character_causation: float,
    procedural_normality: float,
    environmental_inevitability: float,
    prior_constraint: float,
) -> dict[str, Any]:
    debt = clamp(improbability)

    repayment = (
        clamp(setup)
        + clamp(character_causation)
        + clamp(procedural_normality)
        + clamp(environmental_inevitability)
        + clamp(prior_constraint)
    ) / 5.0

    residual = clamp(
        debt * (1.0 - repayment)
    )

    result = {
        "initial_debt": debt,
        "repayment": repayment,
        "residual_debt": residual,
        "authority_effect": "none",
    }

    result["digest"] = digest(result)
    return result


def information_lineage(
    *,
    event: str,
    observation: str,
    interpretation: str,
    belief: str,
    decision: str,
) -> dict[str, Any]:
    result = {
        "event": event,
        "observation": observation,
        "interpretation": interpretation,
        "belief": belief,
        "decision": decision,
        "authority_effect": "none",
    }

    result["digest"] = digest(result)
    return result


def triviality_transmutation(
    trivial_element: str,
    destination: str | None = None,
) -> dict[str, Any]:
    channels = []

    for channel in TRIVIALITY_CHANNELS:
        channels.append(
            {
                "channel": channel,
                "question": (
                    "How can the trivial element "
                    f"change {channel} conditions"
                    + (
                        " on the way to the "
                        "specified destination?"
                        if destination
                        else "?"
                    )
                ),
            }
        )

    result = {
        "trivial_element": trivial_element,
        "destination": destination,
        "channels": channels,
        "preferred_chain_property": (
            "prospectively_unobvious_"
            "retrospectively_inevitable"
        ),
        "authority_effect": "none",
    }

    result["digest"] = digest(result)
    return result


def _opus_runtime_path() -> Path:
    return Path(
        "/root/savant-runtime/"
        "ontology/obelisks/_template/"
        "segue/gates/_template/segue/"
        "innates/_template/segue/"
        "exiles/opus/runtime"
    )


def _extract_text(
    value: Any,
) -> str:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in (
            "text",
            "output_text",
            "content",
            "response",
            "message",
        ):
            candidate = value.get(key)

            if (
                isinstance(candidate, str)
                and candidate.strip()
            ):
                return candidate

        for key in (
            "result",
            "data",
            "output",
        ):
            if key in value:
                candidate = _extract_text(
                    value[key]
                )

                if candidate:
                    return candidate

    if (
        isinstance(value, Sequence)
        and not isinstance(
            value,
            (
                str,
                bytes,
                bytearray,
            ),
        )
    ):
        parts = [
            _extract_text(item)
            for item in value
        ]

        return "\n".join(
            part
            for part in parts
            if part
        )

    return ""


def opus_available() -> bool:
    path = _opus_runtime_path()

    return (
        path.is_dir()
        and (
            path
            / "enterprise_execution.py"
        ).is_file()
    )


def opus_reason(
    *,
    task: str,
    anchors: Sequence[str],
    constraints: Sequence[str] = (),
    destination: str | None = None,
    involvement: float = 50.0,
    mode: str = "bridge",
    context: str = "",
) -> dict[str, Any]:
    if mode not in BRAINSTORM_MODES:
        raise ValueError(
            f"unknown brainstorming mode: {mode}"
        )

    policy = involvement_projection(
        involvement
    )

    ordered_modes = (
        "diagnostic",
        "expansion",
        "bridge",
        "convergence",
        "directed_possibility",
        "open_catalyst",
    )

    if (
        ordered_modes.index(mode)
        > ordered_modes.index(
            str(policy["maximum_mode"])
        )
    ):
        raise ValueError(
            "requested brainstorming mode "
            "exceeds cameo involvement policy"
        )

    if (
        not anchors
        and mode != "open_catalyst"
    ):
        raise ValueError(
            "at least one user-owned anchor "
            "is required outside "
            "open_catalyst mode"
        )

    if not opus_available():
        return {
            "status": "unavailable",
            "reason": (
                "opus enterprise execution "
                "runtime not available"
            ),
            "authority_effect": "none",
        }

    opus_path = str(
        _opus_runtime_path()
    )

    if opus_path not in sys.path:
        sys.path.insert(
            0,
            opus_path,
        )

    try:
        from enterprise_execution import execute
    except Exception as exc:
        return {
            "status": "unavailable",
            "reason": "opus import failure",
            "error_type": type(exc).__name__,
            "authority_effect": "none",
        }

    system_prompt = (
        "You are operating as an Opus reasoning "
        "provider for Carbon Cameo. "
        "Cameo is Savant's user-sovereignty-aware "
        "story plotting specialization. "
        "You possess no canonical authority. "
        "Treat user anchors and constraints as "
        "governing creative primitives. "
        "Do not silently invent accepted canon. "
        "Generate candidate reasoning only. "
        "Distinguish user primitive, observation, "
        "inference, candidate, and unknown. "
        "Optimize causal soundness, character "
        "agency, information provenance, economy, "
        "surprise, retrospective inevitability, "
        "and multifunctionality. "
        "Never disguise a new premise or "
        "motivation as logistics. "
        "Return structured candidate analysis "
        "for user selection."
    )

    request_payload = {
        "task": task,
        "mode": mode,
        "user_owned_anchors": list(anchors),
        "constraints": list(constraints),
        "destination": destination,
        "context": context,
        "cameo_policy": policy,
        "triviality_channels": list(
            TRIVIALITY_CHANNELS
        ),
        "candidate_budget": policy[
            "opus_candidate_budget"
        ],
        "round_budget": policy[
            "opus_round_budget"
        ],
        "required_output": {
            "preserve_anchors": True,
            "candidate_only": True,
            "identify_identity_drift": True,
            "identify_coincidence_debt": True,
            "identify_information_lineage": True,
            "identify_character_agency": True,
            "rank_but_do_not_canonize": True,
        },
    }

    request = {
        "owner": "carbon",
        "request_origin": "carbon.cameo",
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": canonical_json(
                    request_payload
                ),
            },
        ],
        "required_capabilities": [
            "text",
        ],
        "metadata": {
            "carbon_specialization": "cameo",
            "brainstorm_mode": mode,
            "involvement": involvement,
            "authority_effect": "none",
        },
    }

    try:
        raw = execute(request)
    except Exception as exc:
        return {
            "status": "provider_failure",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "authority_effect": "none",
        }

    text = _extract_text(raw)

    result = {
        "status": "ok",
        "mode": mode,
        "policy": policy,
        "candidate_text": text,
        "raw_execution": raw,
        "automatic_canonization": False,
        "requires_user_adoption": True,
        "canonical_authority_ai": 0.0,
        "authority_effect": "none",
        "lineage": {
            "owner": "carbon",
            "specialization": "cameo",
            "executor": "opus",
            "interface": (
                "enterprise_execution.execute"
            ),
            "request_digest": digest(
                request_payload
            ),
        },
    }

    result["digest"] = digest(
        {
            key: value
            for key, value in result.items()
            if key != "raw_execution"
        }
    )

    return result


class CameoRuntime:
    def policy(
        self,
        involvement: float,
    ) -> dict[str, Any]:
        return involvement_projection(
            involvement
        )

    def sovereignty(
        self,
        atoms: Iterable[NarrativeAtom],
    ) -> dict[str, Any]:
        return sovereignty(atoms)

    def evaluate(
        self,
        atom: NarrativeAtom,
        involvement: float,
    ) -> dict[str, Any]:
        return evaluate_permissions(
            atom,
            involvement,
        )

    def reason(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return opus_reason(**kwargs)

    def health(self) -> dict[str, Any]:
        result = {
            "status": "ok",
            "owner": owner,
            "specialization": specialization,
            "schema": schema,
            "dimension_count": len(
                DIMENSIONS
            ),
            "enhancement_count": len(
                ENHANCEMENTS
            ),
            "enhancements": list(
                ENHANCEMENTS
            ),
            "brainstorm_modes": sorted(
                BRAINSTORM_MODES
            ),
            "opus_available": (
                opus_available()
            ),
            "slider_minimum": 0,
            "slider_maximum": 100,
            "automatic_canonization": False,
            "canonical_authority_ai": 0.0,
            "canonical_authority_user": 1.0,
            "authority_effect": "none",
        }

        result["digest"] = digest(result)
        return result

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.noumenon.development import (
    PossibleSelf,
    SelfExplanation,
)
from runtime.noumenon.dynamics import (
    DynamicsProfile,
    derive_profile_projection,
)
from runtime.noumenon.state import (
    NoumenonState,
)


SCHEMA = "savant://noumenon/projection/1"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: Any) -> str:
    return sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def phenomenal_self(
    state: NoumenonState,
    *,
    claimed_dimensions: Mapping[str, float],
    explanation_refs: Sequence[str] = (),
    confidence: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    body = {
        "schema": (
            "savant://noumenon/"
            "phenomenal-self/1"
        ),
        "state_digest": state.state_digest,
        "kind": "phenomenal",
        "dimensions": {
            str(key): float(value)
            for key, value
            in sorted(
                claimed_dimensions.items()
            )
        },
        "explanation_refs": list(
            explanation_refs
        ),
        "confidence": {
            str(key): max(
                0.0,
                min(1.0, float(value)),
            )
            for key, value
            in sorted(
                (confidence or {}).items()
            )
        },
        "authoritative": False,
    }

    body["digest"] = _digest(body)
    return body


def causal_self(
    state: NoumenonState,
    *,
    evidence_refs: Sequence[str] = (),
) -> dict[str, Any]:
    body = {
        "schema": (
            "savant://noumenon/"
            "causal-self/1"
        ),
        "state_digest": state.state_digest,
        "kind": "causal",
        "dimensions": {
            key: float(value)
            for key, value
            in sorted(
                state.dimensions.items()
            )
        },
        "lineage_refs": list(
            state.lineage_refs
        ),
        "evidence_refs": list(
            evidence_refs
        ),
        "authoritative_external_fact": False,
    }

    body["digest"] = _digest(body)
    return body


def historical_self(
    state: NoumenonState,
) -> dict[str, Any]:
    body = {
        "schema": (
            "savant://noumenon/"
            "historical-self/1"
        ),
        "state_digest": state.state_digest,
        "kind": "historical",
        "noumenon_id": state.noumenon_id,
        "predecessor_id": (
            state.predecessor_id
        ),
        "generation": state.generation,
        "succession_status": (
            state.succession_status
        ),
        "lineage_refs": list(
            state.lineage_refs
        ),
        "relationship_refs": list(
            state.relationship_refs
        ),
        "memory_refs": list(
            state.memory_refs
        ),
        "value_refs": list(
            state.value_refs
        ),
    }

    body["digest"] = _digest(body)
    return body


def self_triptych(
    state: NoumenonState,
    *,
    claimed_dimensions: Mapping[str, float],
    explanation_refs: Sequence[str] = (),
    confidence: Mapping[str, float] | None = None,
    evidence_refs: Sequence[str] = (),
) -> dict[str, Any]:
    phenomenal = phenomenal_self(
        state,
        claimed_dimensions=(
            claimed_dimensions
        ),
        explanation_refs=(
            explanation_refs
        ),
        confidence=confidence,
    )

    causal = causal_self(
        state,
        evidence_refs=evidence_refs,
    )

    historical = historical_self(
        state
    )

    body = {
        "schema": (
            "savant://noumenon/"
            "self-triptych/1"
        ),
        "state_digest": state.state_digest,
        "phenomenal": phenomenal,
        "causal": causal,
        "historical": historical,
        "coincident_identity": False,
    }

    body["digest"] = _digest(body)
    return body


def introspective_projection(
    state: NoumenonState,
    explanations: Sequence[
        SelfExplanation
    ],
) -> dict[str, Any]:
    body = {
        "schema": (
            "savant://noumenon/"
            "introspective-projection/1"
        ),
        "state_digest": state.state_digest,
        "explanations": [
            item.projection()
            for item in explanations
        ],
        "self_knowledge_is_fallible": True,
        "direct_chain_of_thought": False,
    }

    body["digest"] = _digest(body)
    return body


def possible_self_ecology(
    state: NoumenonState,
    possible_selves: Sequence[
        PossibleSelf
    ],
) -> dict[str, Any]:
    body = {
        "schema": (
            "savant://noumenon/"
            "possible-self-ecology/1"
        ),
        "state_digest": state.state_digest,
        "possible_selves": [
            item.projection()
            for item in possible_selves
        ],
        "authoritative": False,
    }

    body["digest"] = _digest(body)
    return body


def developmental_projection(
    state: NoumenonState,
    profile: DynamicsProfile,
    *,
    unresolved_refs: Sequence[str] = (),
) -> dict[str, Any]:
    body = {
        "schema": SCHEMA,
        "state": state.projection(),
        "dynamics": (
            derive_profile_projection(
                profile
            )
        ),
        "unresolved_refs": list(
            unresolved_refs
        ),
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body

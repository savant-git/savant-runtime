from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.noumenon.integrant import (
    IntegrantEnvelope,
    request,
)
from runtime.noumenon.state import NoumenonState


SCHEMA = "savant://noumenon/cognition/1"

REQUEST_TYPES = frozenset(
    {
        "appraise",
        "reflect",
        "recall",
        "reinterpret",
        "relationship",
        "counterlife",
        "self_model",
        "conflict",
        "repair",
        "curiosity",
        "taste",
        "continuity",
    }
)


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


@dataclass(frozen=True, slots=True)
class CognitiveContract:
    request_type: str
    state_digest: str
    subject_refs: tuple[str, ...]
    context_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    constraints: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.request_type not in REQUEST_TYPES:
            raise ValueError(
                "unsupported cognitive request type"
            )

        if not self.state_digest:
            raise ValueError(
                "state_digest is required"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "request_type": self.request_type,
            "state_digest": (
                self.state_digest
            ),
            "subject_refs": list(
                self.subject_refs
            ),
            "context_refs": list(
                self.context_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "constraints": dict(
                self.constraints
            ),
            "candidate_only": True,
            "authority_effect": "none",
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )


def opus_request(
    state: NoumenonState,
    request_type: str,
    *,
    subject_refs: Sequence[str] = (),
    context_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    constraints: Mapping[str, Any] | None = None,
) -> IntegrantEnvelope:
    contract = CognitiveContract(
        request_type=request_type,
        state_digest=state.state_digest,
        subject_refs=tuple(subject_refs),
        context_refs=tuple(context_refs),
        evidence_refs=tuple(evidence_refs),
        constraints=dict(
            constraints or {}
        ),
    )

    return request(
        "opus",
        f"noumenon.{request_type}",
        contract.projection(),
        evidence_refs=evidence_refs,
        lineage_refs=(
            state.lineage_refs
            + (state.noumenon_id,)
        ),
    )


def underscore_request(
    state: NoumenonState,
    *,
    problem_ref: str,
    candidate_refs: Sequence[str],
    evidence_refs: Sequence[str] = (),
) -> IntegrantEnvelope:
    if not problem_ref:
        raise ValueError(
            "problem_ref is required"
        )

    return request(
        "underscore",
        "noumenon.divergence",
        {
            "schema": (
                "savant://noumenon/"
                "divergence-request/1"
            ),
            "state_digest": state.state_digest,
            "problem_ref": problem_ref,
            "candidate_refs": list(
                candidate_refs
            ),
            "requirements": {
                "preserve_evidence": True,
                "preserve_authority": True,
                "preserve_uncertainty": True,
                "preserve_dissent": True,
                "avoid_cliche_attractors": True,
                "avoid_premature_convergence": True,
                "novelty_is_authority": False,
            },
        },
        evidence_refs=evidence_refs,
        lineage_refs=(
            state.lineage_refs
            + (state.noumenon_id,)
        ),
    )


def candidate_integrity(
    envelope: IntegrantEnvelope,
    *,
    expected_state_digest: str,
    allowed_sources: Sequence[str],
) -> dict[str, Any]:
    failures: list[str] = []

    if envelope.source not in set(
        allowed_sources
    ):
        failures.append(
            "unexpected_source"
        )

    supplied_state_digest = (
        envelope.payload.get(
            "state_digest"
        )
    )

    if (
        supplied_state_digest
        is not None
        and supplied_state_digest
        != expected_state_digest
    ):
        failures.append(
            "state_digest_mismatch"
        )

    if (
        envelope.target
        != "noumenon"
    ):
        failures.append(
            "wrong_target"
        )

    if (
        envelope.direction
        != "candidate"
    ):
        failures.append(
            "not_candidate"
        )

    return {
        "schema": (
            "savant://noumenon/"
            "cognitive-candidate-integrity/1"
        ),
        "accepted": not failures,
        "failures": failures,
        "envelope_id": envelope.id,
    }

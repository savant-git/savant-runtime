from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.noumenon.integrant import IntegrantEnvelope
from runtime.noumenon.state import (
    NoumenonState,
    TransitionCandidate,
    continuity_receipt,
)


SCHEMA = "savant://noumenon/admission/1"


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
class AdmissionDecision:
    admitted: bool
    reason: str
    predecessor_digest: str
    candidate_digest: str
    authority_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    admission_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.reason:
            raise ValueError("reason is required")

        if not self.predecessor_digest:
            raise ValueError(
                "predecessor_digest is required"
            )

        if not self.candidate_digest:
            raise ValueError(
                "candidate_digest is required"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "admitted": self.admitted,
            "reason": self.reason,
            "predecessor_digest": (
                self.predecessor_digest
            ),
            "candidate_digest": (
                self.candidate_digest
            ),
            "authority_refs": list(
                self.authority_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "admission_refs": list(
                self.admission_refs
            ),
        }

    @property
    def digest(self) -> str:
        return _digest(self.projection())

    @property
    def id(self) -> str:
        return f"noumenon-admission:{self.digest}"


@dataclass(frozen=True, slots=True)
class AdmittedTransition:
    predecessor: NoumenonState
    successor: NoumenonState
    decision: AdmissionDecision
    receipt: Mapping[str, Any]


def candidate_digest(
    candidate: TransitionCandidate,
) -> str:
    return _digest(
        {
            "predecessor": (
                candidate.predecessor.state_digest
            ),
            "experience": (
                candidate.experience.projection()
            ),
            "significance": (
                candidate.significance.projection()
            ),
            "consequences": [
                consequence.projection()
                for consequence
                in candidate.consequences
            ],
        }
    )


def evaluate_admission(
    candidate: TransitionCandidate,
    *,
    notary_envelope: IntegrantEnvelope | None,
    coda_envelope: IntegrantEnvelope | None = None,
) -> AdmissionDecision:
    digest = candidate_digest(candidate)

    if notary_envelope is None:
        return AdmissionDecision(
            admitted=False,
            reason="missing_notary_admission",
            predecessor_digest=(
                candidate.predecessor.state_digest
            ),
            candidate_digest=digest,
            authority_refs=(),
            evidence_refs=(),
        )

    if notary_envelope.source != "notary":
        return AdmissionDecision(
            admitted=False,
            reason="invalid_notary_source",
            predecessor_digest=(
                candidate.predecessor.state_digest
            ),
            candidate_digest=digest,
            authority_refs=(
                notary_envelope.authority_refs
            ),
            evidence_refs=(
                notary_envelope.evidence_refs
            ),
        )

    if (
        notary_envelope.target != "noumenon"
        or notary_envelope.direction
        != "candidate"
    ):
        return AdmissionDecision(
            admitted=False,
            reason="invalid_notary_envelope",
            predecessor_digest=(
                candidate.predecessor.state_digest
            ),
            candidate_digest=digest,
            authority_refs=(
                notary_envelope.authority_refs
            ),
            evidence_refs=(
                notary_envelope.evidence_refs
            ),
        )

    admitted = notary_envelope.payload.get(
        "admitted"
    )

    admitted_candidate_digest = (
        notary_envelope.payload.get(
            "candidate_digest"
        )
    )

    if admitted is not True:
        return AdmissionDecision(
            admitted=False,
            reason="notary_rejected",
            predecessor_digest=(
                candidate.predecessor.state_digest
            ),
            candidate_digest=digest,
            authority_refs=(
                notary_envelope.authority_refs
            ),
            evidence_refs=(
                notary_envelope.evidence_refs
            ),
            admission_refs=(
                notary_envelope.id,
            ),
        )

    if admitted_candidate_digest != digest:
        return AdmissionDecision(
            admitted=False,
            reason="candidate_digest_mismatch",
            predecessor_digest=(
                candidate.predecessor.state_digest
            ),
            candidate_digest=digest,
            authority_refs=(
                notary_envelope.authority_refs
            ),
            evidence_refs=(
                notary_envelope.evidence_refs
            ),
            admission_refs=(
                notary_envelope.id,
            ),
        )

    admission_refs = [
        notary_envelope.id,
    ]

    authority_refs = list(
        notary_envelope.authority_refs
    )

    evidence_refs = list(
        notary_envelope.evidence_refs
    )

    if coda_envelope is not None:
        if coda_envelope.source != "coda":
            return AdmissionDecision(
                admitted=False,
                reason="invalid_coda_source",
                predecessor_digest=(
                    candidate.predecessor.state_digest
                ),
                candidate_digest=digest,
                authority_refs=tuple(
                    authority_refs
                ),
                evidence_refs=tuple(
                    evidence_refs
                ),
                admission_refs=tuple(
                    admission_refs
                ),
            )

        if (
            coda_envelope.target != "noumenon"
            or coda_envelope.direction
            != "candidate"
        ):
            return AdmissionDecision(
                admitted=False,
                reason="invalid_coda_envelope",
                predecessor_digest=(
                    candidate.predecessor.state_digest
                ),
                candidate_digest=digest,
                authority_refs=tuple(
                    authority_refs
                ),
                evidence_refs=tuple(
                    evidence_refs
                ),
                admission_refs=tuple(
                    admission_refs
                ),
            )

        admission_refs.append(
            coda_envelope.id
        )

        authority_refs.extend(
            coda_envelope.authority_refs
        )

        evidence_refs.extend(
            coda_envelope.evidence_refs
        )

    return AdmissionDecision(
        admitted=True,
        reason="admitted",
        predecessor_digest=(
            candidate.predecessor.state_digest
        ),
        candidate_digest=digest,
        authority_refs=tuple(
            dict.fromkeys(authority_refs)
        ),
        evidence_refs=tuple(
            dict.fromkeys(evidence_refs)
        ),
        admission_refs=tuple(
            admission_refs
        ),
    )


def admit_transition(
    candidate: TransitionCandidate,
    decision: AdmissionDecision,
) -> AdmittedTransition:
    if not decision.admitted:
        raise ValueError(
            "transition cannot be applied without admission"
        )

    digest = candidate_digest(candidate)

    if digest != decision.candidate_digest:
        raise ValueError(
            "admission does not match transition candidate"
        )

    if (
        candidate.predecessor.state_digest
        != decision.predecessor_digest
    ):
        raise ValueError(
            "admission predecessor mismatch"
        )

    successor = candidate.successor()

    receipt = continuity_receipt(
        candidate.predecessor,
        successor,
        transition_refs=(
            successor.lineage_refs
        ),
        authority_refs=(
            decision.authority_refs
        ),
        evidence_refs=(
            decision.evidence_refs
        ),
    )

    return AdmittedTransition(
        predecessor=candidate.predecessor,
        successor=successor,
        decision=decision,
        receipt=receipt,
    )


def notary_admission_payload(
    candidate: TransitionCandidate,
    *,
    admitted: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "schema": (
            "savant://noumenon/"
            "notary-admission-candidate/1"
        ),
        "admitted": admitted,
        "reason": reason,
        "candidate_digest": (
            candidate_digest(candidate)
        ),
        "predecessor_digest": (
            candidate.predecessor.state_digest
        ),
    }


def coda_mutation_payload(
    candidate: TransitionCandidate,
    *,
    durable_dimensions: Sequence[str],
) -> dict[str, Any]:
    durable = frozenset(
        str(value)
        for value in durable_dimensions
    )

    return {
        "schema": (
            "savant://noumenon/"
            "coda-mutation-candidate/1"
        ),
        "candidate_digest": (
            candidate_digest(candidate)
        ),
        "predecessor_digest": (
            candidate.predecessor.state_digest
        ),
        "durable_consequences": [
            consequence.projection()
            for consequence
            in candidate.consequences
            if consequence.dimension in durable
        ],
    }

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.noumenon.development import (
    continuity_challenge,
)
from runtime.noumenon.state import (
    NoumenonState,
)


SCHEMA = "savant://noumenon/recovery/2"

CONTINUITY_DOMAINS = (
    "lineage",
    "autobiography",
    "relationships",
    "commitments",
    "significance_history",
    "identity_ancestry",
    "integrity_receipts",
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
class ContinuityEvidence:
    kind: str
    ref: str
    digest: str | None = None
    weight: float = 1.0

    def __post_init__(self) -> None:
        if self.kind not in CONTINUITY_DOMAINS:
            raise ValueError(
                "unsupported continuity "
                "evidence kind"
            )

        if not self.ref:
            raise ValueError(
                "continuity evidence ref "
                "is required"
            )

        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(
                "weight must be between "
                "0 and 1"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "ref": self.ref,
            "digest": self.digest,
            "weight": self.weight,
        }


@dataclass(frozen=True, slots=True)
class ContinuityQuorum:
    evidence: tuple[
        ContinuityEvidence,
        ...,
    ] = ()

    def projection(self) -> dict[str, Any]:
        grouped: dict[
            str,
            list[dict[str, Any]],
        ] = {
            domain: []
            for domain
            in CONTINUITY_DOMAINS
        }

        for item in self.evidence:
            grouped[
                item.kind
            ].append(
                item.projection()
            )

        return {
            "schema": (
                "savant://noumenon/"
                "continuity-quorum/2"
            ),
            "domains": grouped,
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )


@dataclass(frozen=True, slots=True)
class RecoveryDecision:
    status: str
    score: float
    agreeing_domains: tuple[str, ...]
    missing_domains: tuple[str, ...]
    conflicting_domains: tuple[str, ...]
    predecessor_id: str
    candidate_id: str
    candidate_state_digest: str
    evidence_digest: str

    def __post_init__(self) -> None:
        if self.status not in {
            "continuous",
            "restored",
            "reconstructed",
            "disputed",
            "unknown",
        }:
            raise ValueError(
                "unsupported recovery status"
            )

        if not 0.0 <= self.score <= 1.0:
            raise ValueError(
                "score must be between "
                "0 and 1"
            )

        if not self.predecessor_id:
            raise ValueError(
                "predecessor_id is required"
            )

        if not self.candidate_id:
            raise ValueError(
                "candidate_id is required"
            )

        if not self.candidate_state_digest:
            raise ValueError(
                "candidate_state_digest "
                "is required"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "status": self.status,
            "score": self.score,
            "agreeing_domains": list(
                self.agreeing_domains
            ),
            "missing_domains": list(
                self.missing_domains
            ),
            "conflicting_domains": list(
                self.conflicting_domains
            ),
            "predecessor_id": (
                self.predecessor_id
            ),
            "candidate_id": (
                self.candidate_id
            ),
            "candidate_state_digest": (
                self.candidate_state_digest
            ),
            "evidence_digest": (
                self.evidence_digest
            ),
            "authority_effect": "none",
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )


def _domain_score(
    quorum: ContinuityQuorum,
) -> tuple[
    float,
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    grouped: dict[
        str,
        list[ContinuityEvidence],
    ] = {
        domain: []
        for domain
        in CONTINUITY_DOMAINS
    }

    for item in quorum.evidence:
        grouped[
            item.kind
        ].append(item)

    agreeing: list[str] = []
    missing: list[str] = []
    conflicting: list[str] = []

    total = 0.0

    for domain in CONTINUITY_DOMAINS:
        items = grouped[domain]

        if not items:
            missing.append(domain)
            continue

        digests = {
            item.digest
            for item in items
            if item.digest is not None
        }

        if len(digests) > 1:
            conflicting.append(domain)
            continue

        weight = max(
            item.weight
            for item in items
        )

        if weight <= 0.0:
            missing.append(domain)
            continue

        agreeing.append(domain)
        total += weight

    score = total / float(
        len(CONTINUITY_DOMAINS)
    )

    return (
        score,
        tuple(agreeing),
        tuple(missing),
        tuple(conflicting),
    )


def evaluate_quorum(
    predecessor: NoumenonState,
    candidate: NoumenonState,
    quorum: ContinuityQuorum,
) -> RecoveryDecision:
    (
        score,
        agreeing,
        missing,
        conflicting,
    ) = _domain_score(
        quorum
    )

    challenge = continuity_challenge(
        predecessor,
        candidate,
    )

    if conflicting:
        status = "disputed"

    elif challenge["continuous"]:
        status = "continuous"

    elif score >= 0.75:
        status = "restored"

    elif score >= 0.5:
        status = "reconstructed"

    else:
        status = "unknown"

    return RecoveryDecision(
        status=status,
        score=score,
        agreeing_domains=agreeing,
        missing_domains=missing,
        conflicting_domains=conflicting,
        predecessor_id=(
            predecessor.state_digest
        ),
        candidate_id=(
            candidate.noumenon_id
        ),
        candidate_state_digest=(
            candidate.state_digest
        ),
        evidence_digest=(
            quorum.digest
        ),
    )


def fork_classification(
    states: Sequence[NoumenonState],
) -> Mapping[str, Any]:
    children: dict[
        str,
        set[str],
    ] = {}

    for state in states:
        if state.predecessor_id is None:
            continue

        children.setdefault(
            state.predecessor_id,
            set(),
        ).add(
            state.state_digest
        )

    forks = []

    for predecessor, successors in sorted(
        children.items()
    ):
        if len(successors) < 2:
            continue

        forks.append(
            {
                "predecessor_state_digest": (
                    predecessor
                ),
                "successor_state_digests": (
                    sorted(successors)
                ),
                "classification": "branch",
            }
        )

    body: dict[str, Any] = {
        "schema": (
            "savant://noumenon/"
            "fork-classification/2"
        ),
        "forks": forks,
        "derived": True,
        "authoritative": False,
    }

    body["digest"] = _digest(body)
    return body


def recovery_receipt(
    decision: RecoveryDecision,
    *,
    authority_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema": (
            "savant://noumenon/"
            "recovery-receipt/2"
        ),
        "decision_digest": (
            decision.digest
        ),
        "status": decision.status,
        "predecessor_id": (
            decision.predecessor_id
        ),
        "candidate_id": (
            decision.candidate_id
        ),
        "candidate_state_digest": (
            decision.candidate_state_digest
        ),
        "evidence_digest": (
            decision.evidence_digest
        ),
        "authority_refs": list(
            authority_refs
        ),
        "evidence_refs": list(
            evidence_refs
        ),
        "authority_effect": "none",
    }

    body["integrity_digest"] = _digest(
        body
    )

    return body

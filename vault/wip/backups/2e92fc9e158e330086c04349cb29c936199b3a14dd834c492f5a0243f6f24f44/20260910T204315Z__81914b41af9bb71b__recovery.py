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


SCHEMA = "savant://noumenon/recovery/1"


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
        if not self.kind:
            raise ValueError("kind is required")

        if not self.ref:
            raise ValueError("ref is required")

        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(
                "weight must be between 0 and 1"
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
    lineage: tuple[ContinuityEvidence, ...] = ()
    autobiography: tuple[ContinuityEvidence, ...] = ()
    relationships: tuple[ContinuityEvidence, ...] = ()
    commitments: tuple[ContinuityEvidence, ...] = ()
    significance_history: tuple[
        ContinuityEvidence, ...
    ] = ()
    identity_ancestry: tuple[
        ContinuityEvidence, ...
    ] = ()
    integrity_receipts: tuple[
        ContinuityEvidence, ...
    ] = ()

    def projection(self) -> dict[str, Any]:
        return {
            "schema": (
                "savant://noumenon/"
                "continuity-quorum/1"
            ),
            "lineage": [
                item.projection()
                for item in self.lineage
            ],
            "autobiography": [
                item.projection()
                for item in self.autobiography
            ],
            "relationships": [
                item.projection()
                for item in self.relationships
            ],
            "commitments": [
                item.projection()
                for item in self.commitments
            ],
            "significance_history": [
                item.projection()
                for item
                in self.significance_history
            ],
            "identity_ancestry": [
                item.projection()
                for item in self.identity_ancestry
            ],
            "integrity_receipts": [
                item.projection()
                for item in self.integrity_receipts
            ],
        }

    @property
    def digest(self) -> str:
        return _digest(self.projection())


@dataclass(frozen=True, slots=True)
class RecoveryDecision:
    status: str
    score: float
    agreeing_domains: tuple[str, ...]
    missing_domains: tuple[str, ...]
    conflicting_domains: tuple[str, ...]
    predecessor_id: str | None
    candidate_id: str
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
                "score must be between 0 and 1"
            )

        if not self.candidate_id:
            raise ValueError(
                "candidate_id is required"
            )

        if not self.evidence_digest:
            raise ValueError(
                "evidence_digest is required"
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
            "predecessor_id": self.predecessor_id,
            "candidate_id": self.candidate_id,
            "evidence_digest": (
                self.evidence_digest
            ),
        }

    @property
    def digest(self) -> str:
        return _digest(self.projection())


def _domain_score(
    evidence: Sequence[ContinuityEvidence],
) -> tuple[float, bool]:
    if not evidence:
        return 0.0, False

    total_weight = sum(
        item.weight
        for item in evidence
    )

    if total_weight == 0.0:
        return 0.0, True

    return (
        min(
            1.0,
            total_weight / len(evidence),
        ),
        True,
    )


def evaluate_quorum(
    quorum: ContinuityQuorum,
    *,
    predecessor: NoumenonState | None,
    candidate: NoumenonState,
    minimum_domains: int = 3,
    minimum_score: float = 0.5,
) -> RecoveryDecision:
    domains = {
        "lineage": quorum.lineage,
        "autobiography": quorum.autobiography,
        "relationships": quorum.relationships,
        "commitments": quorum.commitments,
        "significance_history": (
            quorum.significance_history
        ),
        "identity_ancestry": (
            quorum.identity_ancestry
        ),
        "integrity_receipts": (
            quorum.integrity_receipts
        ),
    }

    agreeing: list[str] = []
    missing: list[str] = []
    conflicting: list[str] = []
    scores: list[float] = []

    for name, evidence in domains.items():
        score, present = _domain_score(
            evidence
        )

        if not present:
            missing.append(name)
            continue

        scores.append(score)

        if score > 0.0:
            agreeing.append(name)
        else:
            conflicting.append(name)

    structural_continuity = True

    if predecessor is not None:
        challenge = continuity_challenge(
            predecessor,
            candidate,
        )

        structural_continuity = bool(
            challenge["continuous"]
        )

        if not structural_continuity:
            conflicting.append(
                "structural_continuity"
            )

    score = (
        sum(scores) / len(scores)
        if scores
        else 0.0
    )

    enough_domains = (
        len(agreeing) >= minimum_domains
    )

    enough_score = (
        score >= minimum_score
    )

    if (
        predecessor is not None
        and structural_continuity
        and enough_domains
        and enough_score
    ):
        status = "continuous"
    elif (
        predecessor is not None
        and enough_domains
        and enough_score
        and not structural_continuity
    ):
        status = "disputed"
    elif (
        predecessor is None
        and enough_domains
        and score >= 0.75
    ):
        status = "restored"
    elif (
        predecessor is None
        and enough_domains
        and enough_score
    ):
        status = "reconstructed"
    else:
        status = "unknown"

    return RecoveryDecision(
        status=status,
        score=score,
        agreeing_domains=tuple(
            sorted(set(agreeing))
        ),
        missing_domains=tuple(
            sorted(set(missing))
        ),
        conflicting_domains=tuple(
            sorted(set(conflicting))
        ),
        predecessor_id=(
            predecessor.noumenon_id
            if predecessor is not None
            else None
        ),
        candidate_id=candidate.noumenon_id,
        evidence_digest=quorum.digest,
    )


def fork_classification(
    states: Sequence[NoumenonState],
) -> dict[str, Any]:
    by_predecessor: dict[
        str,
        list[NoumenonState],
    ] = {}

    for state in states:
        if state.predecessor_id is None:
            continue

        by_predecessor.setdefault(
            state.predecessor_id,
            [],
        ).append(state)

    forks = []

    for predecessor_id, children in sorted(
        by_predecessor.items()
    ):
        unique_children = {
            child.noumenon_id
            for child in children
        }

        if len(unique_children) < 2:
            continue

        forks.append(
            {
                "predecessor_id": (
                    predecessor_id
                ),
                "successor_ids": sorted(
                    unique_children
                ),
                "status": "branched",
            }
        )

    body = {
        "schema": (
            "savant://noumenon/"
            "fork-classification/1"
        ),
        "forks": forks,
    }

    body["digest"] = _digest(body)
    return body


def recovery_receipt(
    decision: RecoveryDecision,
    *,
    authority_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
) -> dict[str, Any]:
    body = {
        "schema": (
            "savant://noumenon/"
            "recovery-receipt/1"
        ),
        "decision": decision.projection(),
        "authority_refs": list(
            authority_refs
        ),
        "evidence_refs": list(
            evidence_refs
        ),
    }

    body["integrity_digest"] = _digest(body)
    return body

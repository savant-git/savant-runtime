


from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/commitment/1"

STATUSES = frozenset(
    {
        "active",
        "fulfilled",
        "broken",
        "released",
        "superseded",
    }
)


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(
    value: Any,
) -> str:
    return sha256(
        _canonical_json(value).encode(
            "utf-8"
        )
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class Commitment:
    subject_ref: str
    statement: str
    gravity: float
    status: str = "active"
    predecessor_ref: str | None = None
    causal_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()
    resolution_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.subject_ref:
            raise ValueError(
                "subject_ref is required"
            )

        if not self.statement:
            raise ValueError(
                "statement is required"
            )

        if self.status not in STATUSES:
            raise ValueError(
                "unsupported commitment status"
            )

        if not (
            0.0
            <= float(self.gravity)
            <= 1.0
        ):
            raise ValueError(
                "gravity must be between "
                "0 and 1"
            )

        if (
            self.status != "active"
            and not self.resolution_refs
        ):
            raise ValueError(
                "resolved commitment requires "
                "resolution_refs"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "subject_ref": self.subject_ref,
            "statement": self.statement,
            "gravity": float(
                self.gravity
            ),
            "status": self.status,
            "predecessor_ref": (
                self.predecessor_ref
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "authority_refs": list(
                self.authority_refs
            ),
            "resolution_refs": list(
                self.resolution_refs
            ),
            "authority_effect": "none",
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )

    @property
    def id(self) -> str:
        return (
            "noumenon-commitment:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class CommitmentLedger:
    noumenon_id: str
    commitments: tuple[
        Commitment,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not self.noumenon_id:
            raise ValueError(
                "noumenon_id is required"
            )

        identifiers = [
            commitment.id
            for commitment
            in self.commitments
        ]

        if (
            len(identifiers)
            != len(set(identifiers))
        ):
            raise ValueError(
                "duplicate commitment"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "noumenon_id": (
                self.noumenon_id
            ),
            "commitments": [
                commitment.projection()
                for commitment
                in self.commitments
            ],
            "active_refs": [
                commitment.id
                for commitment
                in self.commitments
                if commitment.status
                == "active"
            ],
            "derived": True,
            "authoritative": False,
        }

        body["digest"] = _digest(
            body
        )

        return body


def empty_ledger(
    noumenon_id: str,
) -> CommitmentLedger:
    return CommitmentLedger(
        noumenon_id=noumenon_id
    )


def create_commitment(
    ledger: CommitmentLedger,
    *,
    subject_ref: str,
    statement: str,
    gravity: float,
    causal_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    authority_refs: Sequence[str] = (),
) -> CommitmentLedger:
    commitment = Commitment(
        subject_ref=subject_ref,
        statement=statement,
        gravity=gravity,
        causal_refs=tuple(
            dict.fromkeys(
                str(value)
                for value in causal_refs
            )
        ),
        evidence_refs=tuple(
            dict.fromkeys(
                str(value)
                for value in evidence_refs
            )
        ),
        authority_refs=tuple(
            dict.fromkeys(
                str(value)
                for value in authority_refs
            )
        ),
    )

    return CommitmentLedger(
        noumenon_id=ledger.noumenon_id,
        commitments=(
            *ledger.commitments,
            commitment,
        ),
    )


def resolve_commitment(
    ledger: CommitmentLedger,
    commitment_id: str,
    *,
    status: str,
    resolution_refs: Sequence[str],
) -> CommitmentLedger:
    if status == "active":
        raise ValueError(
            "resolution status cannot be "
            "active"
        )

    if status not in STATUSES:
        raise ValueError(
            "unsupported commitment status"
        )

    refs = tuple(
        dict.fromkeys(
            str(value)
            for value in resolution_refs
        )
    )

    if not refs:
        raise ValueError(
            "resolution_refs are required"
        )

    found = False
    commitments: list[
        Commitment
    ] = []

    for commitment in (
        ledger.commitments
    ):
        if commitment.id != commitment_id:
            commitments.append(
                commitment
            )
            continue

        found = True

        if commitment.status != "active":
            raise ValueError(
                "commitment is already "
                "resolved"
            )

        commitments.append(
            Commitment(
                subject_ref=(
                    commitment.subject_ref
                ),
                statement=(
                    commitment.statement
                ),
                gravity=(
                    commitment.gravity
                ),
                status=status,
                predecessor_ref=(
                    commitment.id
                ),
                causal_refs=tuple(
                    dict.fromkeys(
                        (
                            *commitment
                            .causal_refs,
                            commitment.id,
                            *refs,
                        )
                    )
                ),
                evidence_refs=(
                    commitment.evidence_refs
                ),
                authority_refs=(
                    commitment.authority_refs
                ),
                resolution_refs=refs,
            )
        )

    if not found:
        raise KeyError(
            commitment_id
        )

    return CommitmentLedger(
        noumenon_id=ledger.noumenon_id,
        commitments=tuple(
            commitments
        ),
    )


def active_commitments(
    ledger: CommitmentLedger,
) -> tuple[Commitment, ...]:
    return tuple(
        commitment
        for commitment
        in ledger.commitments
        if commitment.status == "active"
    )


def commitment_gravity(
    ledger: CommitmentLedger,
) -> float:
    active = active_commitments(
        ledger
    )

    if not active:
        return 0.0

    remaining = 1.0

    for commitment in active:
        remaining *= (
            1.0
            - float(
                commitment.gravity
            )
        )

    return (
        1.0 - remaining
    )


def commitment_projection(
    ledger: CommitmentLedger,
) -> Mapping[str, Any]:
    active = active_commitments(
        ledger
    )

    return {
        "schema": SCHEMA,
        "noumenon_id": (
            ledger.noumenon_id
        ),
        "active_count": len(
            active
        ),
        "resolved_count": (
            len(ledger.commitments)
            - len(active)
        ),
        "gravity": (
            commitment_gravity(
                ledger
            )
        ),
        "active_refs": [
            commitment.id
            for commitment in active
        ],
        "derived": True,
        "authoritative": False,
    }

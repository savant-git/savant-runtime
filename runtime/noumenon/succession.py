from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.noumenon.state import NoumenonState


SCHEMA = "savant://noumenon/succession/1"

SUCCESSION_KINDS = frozenset(
    {
        "continuous",
        "branched",
        "copied",
        "restored",
        "reconstructed",
        "disputed",
        "unknown",
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
class SuccessionEdge:
    predecessor_state_digest: str
    successor_state_digest: str
    noumenon_id: str
    kind: str
    evidence_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()
    lineage_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.predecessor_state_digest:
            raise ValueError(
                "predecessor_state_digest is required"
            )

        if not self.successor_state_digest:
            raise ValueError(
                "successor_state_digest is required"
            )

        if not self.noumenon_id:
            raise ValueError(
                "noumenon_id is required"
            )

        if self.kind not in SUCCESSION_KINDS:
            raise ValueError(
                "unsupported succession kind"
            )

        if (
            self.predecessor_state_digest
            == self.successor_state_digest
        ):
            raise ValueError(
                "succession edge cannot self-reference"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "predecessor_state_digest": (
                self.predecessor_state_digest
            ),
            "successor_state_digest": (
                self.successor_state_digest
            ),
            "noumenon_id": self.noumenon_id,
            "kind": self.kind,
            "evidence_refs": list(
                self.evidence_refs
            ),
            "authority_refs": list(
                self.authority_refs
            ),
            "lineage_refs": list(
                self.lineage_refs
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
            "noumenon-succession:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class ForkProjection:
    predecessor_state_digest: str
    successor_state_digests: tuple[str, ...]
    noumenon_id: str
    classification: str

    def __post_init__(self) -> None:
        if not self.predecessor_state_digest:
            raise ValueError(
                "predecessor_state_digest is required"
            )

        if not self.noumenon_id:
            raise ValueError(
                "noumenon_id is required"
            )

        if self.classification not in {
            "none",
            "branch",
        }:
            raise ValueError(
                "unsupported fork classification"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": (
                "savant://noumenon/"
                "fork-projection/1"
            ),
            "predecessor_state_digest": (
                self.predecessor_state_digest
            ),
            "successor_state_digests": list(
                self.successor_state_digests
            ),
            "noumenon_id": self.noumenon_id,
            "classification": (
                self.classification
            ),
            "derived": True,
            "authoritative": False,
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )


def succession_edge(
    predecessor: NoumenonState,
    successor: NoumenonState,
    *,
    kind: str | None = None,
    evidence_refs: Sequence[str] = (),
    authority_refs: Sequence[str] = (),
    lineage_refs: Sequence[str] = (),
) -> SuccessionEdge:
    if (
        successor.predecessor_id
        != predecessor.state_digest
    ):
        raise ValueError(
            "successor does not descend from "
            "the supplied predecessor state"
        )

    resolved_kind = (
        kind
        if kind is not None
        else successor.succession_status
    )

    if (
        resolved_kind == "continuous"
        and successor.noumenon_id
        != predecessor.noumenon_id
    ):
        raise ValueError(
            "continuous succession cannot "
            "change noumenon identity"
        )

    return SuccessionEdge(
        predecessor_state_digest=(
            predecessor.state_digest
        ),
        successor_state_digest=(
            successor.state_digest
        ),
        noumenon_id=(
            successor.noumenon_id
        ),
        kind=resolved_kind,
        evidence_refs=tuple(
            evidence_refs
        ),
        authority_refs=tuple(
            authority_refs
        ),
        lineage_refs=tuple(
            lineage_refs
        ),
    )


def classify_fork(
    predecessor: NoumenonState,
    successors: Sequence[NoumenonState],
) -> ForkProjection:
    valid: dict[
        str,
        NoumenonState,
    ] = {}

    for successor in successors:
        if (
            successor.predecessor_id
            != predecessor.state_digest
        ):
            continue

        valid[
            successor.state_digest
        ] = successor

    successor_digests = tuple(
        sorted(valid)
    )

    return ForkProjection(
        predecessor_state_digest=(
            predecessor.state_digest
        ),
        successor_state_digests=(
            successor_digests
        ),
        noumenon_id=(
            predecessor.noumenon_id
        ),
        classification=(
            "branch"
            if len(successor_digests) > 1
            else "none"
        ),
    )


def ancestry_projection(
    states: Sequence[NoumenonState],
) -> dict[str, Any]:
    by_digest = {
        state.state_digest: state
        for state in states
    }

    edges: list[
        dict[str, str]
    ] = []

    roots: list[str] = []

    for digest, state in sorted(
        by_digest.items()
    ):
        predecessor = state.predecessor_id

        if predecessor is None:
            roots.append(digest)
            continue

        edges.append(
            {
                "predecessor_state_digest": (
                    predecessor
                ),
                "successor_state_digest": (
                    digest
                ),
            }
        )

    body: dict[str, Any] = {
        "schema": (
            "savant://noumenon/"
            "ancestry-projection/1"
        ),
        "state_digests": sorted(
            by_digest
        ),
        "roots": sorted(
            roots
        ),
        "edges": edges,
        "derived": True,
        "authoritative": False,
    }

    body["digest"] = _digest(body)
    return body


def validate_linear_continuity(
    states: Sequence[NoumenonState],
) -> Mapping[str, Any]:
    ordered = tuple(
        sorted(
            states,
            key=lambda state: (
                state.generation,
                state.state_digest,
            ),
        )
    )

    failures: list[str] = []

    if not ordered:
        return {
            "continuous": True,
            "failures": [],
            "state_digests": [],
        }

    identity = ordered[0].noumenon_id

    for index, state in enumerate(
        ordered
    ):
        if state.noumenon_id != identity:
            failures.append(
                "noumenon_identity_mismatch"
            )

        if index == 0:
            continue

        predecessor = ordered[
            index - 1
        ]

        if (
            state.predecessor_id
            != predecessor.state_digest
        ):
            failures.append(
                "predecessor_state_mismatch"
            )

        if (
            state.generation
            != predecessor.generation + 1
        ):
            failures.append(
                "generation_discontinuity"
            )

    return {
        "schema": (
            "savant://noumenon/"
            "linear-continuity/1"
        ),
        "continuous": not failures,
        "failures": list(
            dict.fromkeys(failures)
        ),
        "noumenon_id": identity,
        "state_digests": [
            state.state_digest
            for state in ordered
        ],
    }

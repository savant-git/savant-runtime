from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/state/1"

SUCCESSION_STATUSES = frozenset(
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
class EvidenceRef:
    ref: str
    authority: str = "none"

    def __post_init__(self) -> None:
        if not self.ref:
            raise ValueError(
                "evidence ref is required"
            )

    def projection(self) -> dict[str, str]:
        return {
            "ref": self.ref,
            "authority": self.authority,
        }


@dataclass(frozen=True, slots=True)
class Experience:
    id: str
    observed: bool = False
    owned: bool = False
    believed: bool = False
    remembered: bool = False
    evidence: tuple[EvidenceRef, ...] = ()
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError(
                "experience id is required"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "observed": self.observed,
            "owned": self.owned,
            "believed": self.believed,
            "remembered": self.remembered,
            "evidence": [
                item.projection()
                for item in self.evidence
            ],
            "metadata": dict(
                self.metadata
            ),
        }


@dataclass(frozen=True, slots=True)
class Significance:
    dimensions: Mapping[str, float] = field(
        default_factory=dict
    )
    interpretation_refs: tuple[str, ...] = ()
    uncertainty: Mapping[str, float] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        for value in self.dimensions.values():
            if not -1.0 <= float(value) <= 1.0:
                raise ValueError(
                    "significance dimensions "
                    "must be between -1 and 1"
                )

        for value in self.uncertainty.values():
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(
                    "uncertainty must be "
                    "between 0 and 1"
                )

    def projection(self) -> dict[str, Any]:
        return {
            "dimensions": {
                str(key): float(value)
                for key, value
                in sorted(
                    self.dimensions.items()
                )
            },
            "interpretation_refs": list(
                self.interpretation_refs
            ),
            "uncertainty": {
                str(key): float(value)
                for key, value
                in sorted(
                    self.uncertainty.items()
                )
            },
        }


@dataclass(frozen=True, slots=True)
class DevelopmentalConsequence:
    dimension: str
    delta: float
    causal_refs: tuple[str, ...]
    dormant: bool = False
    unresolved: bool = False

    def __post_init__(self) -> None:
        if not self.dimension:
            raise ValueError(
                "dimension is required"
            )

        if not self.causal_refs:
            raise ValueError(
                "developmental consequence "
                "requires causal refs"
            )

        if not -1.0 <= float(self.delta) <= 1.0:
            raise ValueError(
                "delta must be between -1 and 1"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "delta": float(self.delta),
            "causal_refs": list(
                self.causal_refs
            ),
            "dormant": self.dormant,
            "unresolved": self.unresolved,
        }


@dataclass(frozen=True, slots=True)
class NoumenonState:
    noumenon_id: str
    predecessor_id: str | None = None
    succession_status: str = "unknown"
    generation: int = 0
    dimensions: Mapping[str, float] = field(
        default_factory=dict
    )
    unresolved: tuple[str, ...] = ()
    lineage_refs: tuple[str, ...] = ()
    relationship_refs: tuple[str, ...] = ()
    memory_refs: tuple[str, ...] = ()
    value_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.noumenon_id:
            raise ValueError(
                "noumenon_id is required"
            )

        if (
            self.succession_status
            not in SUCCESSION_STATUSES
        ):
            raise ValueError(
                "unsupported succession status"
            )

        if self.generation < 0:
            raise ValueError(
                "generation cannot be negative"
            )

        for value in self.dimensions.values():
            if not -1.0 <= float(value) <= 1.0:
                raise ValueError(
                    "state dimensions must be "
                    "between -1 and 1"
                )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "noumenon_id": self.noumenon_id,
            "predecessor_id": (
                self.predecessor_id
            ),
            "succession_status": (
                self.succession_status
            ),
            "generation": self.generation,
            "dimensions": {
                str(key): float(value)
                for key, value
                in sorted(
                    self.dimensions.items()
                )
            },
            "unresolved": list(
                self.unresolved
            ),
            "lineage_refs": list(
                self.lineage_refs
            ),
            "relationship_refs": list(
                self.relationship_refs
            ),
            "memory_refs": list(
                self.memory_refs
            ),
            "value_refs": list(
                self.value_refs
            ),
        }

    @property
    def state_digest(self) -> str:
        return _digest(
            self.projection()
        )


@dataclass(frozen=True, slots=True)
class TransitionCandidate:
    predecessor: NoumenonState
    experience: Experience
    significance: Significance
    consequences: tuple[
        DevelopmentalConsequence, ...
    ]

    def __post_init__(self) -> None:
        for consequence in self.consequences:
            if not consequence.causal_refs:
                raise ValueError(
                    "developmental conservation "
                    "requires causal lineage"
                )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": (
                "savant://noumenon/"
                "transition-candidate/1"
            ),
            "predecessor_digest": (
                self.predecessor.state_digest
            ),
            "experience": (
                self.experience.projection()
            ),
            "significance": (
                self.significance.projection()
            ),
            "consequences": [
                item.projection()
                for item in self.consequences
            ],
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )

    def successor(self) -> NoumenonState:
        dimensions = {
            str(key): float(value)
            for key, value
            in self.predecessor.dimensions.items()
        }

        unresolved = list(
            self.predecessor.unresolved
        )

        causal_refs: list[str] = []

        for consequence in self.consequences:
            current = float(
                dimensions.get(
                    consequence.dimension,
                    0.0,
                )
            )

            dimensions[
                consequence.dimension
            ] = max(
                -1.0,
                min(
                    1.0,
                    current
                    + float(
                        consequence.delta
                    ),
                ),
            )

            causal_refs.extend(
                consequence.causal_refs
            )

            if consequence.unresolved:
                unresolved.append(
                    consequence.dimension
                )

        transition_ref = (
            "noumenon-transition:"
            + self.digest
        )

        lineage_refs = (
            self.predecessor.lineage_refs
            + (
                self.predecessor.state_digest,
                transition_ref,
            )
        )

        return NoumenonState(
            noumenon_id=(
                self.predecessor.noumenon_id
            ),
            predecessor_id=(
                self.predecessor.state_digest
            ),
            succession_status="continuous",
            generation=(
                self.predecessor.generation
                + 1
            ),
            dimensions=dimensions,
            unresolved=tuple(
                dict.fromkeys(unresolved)
            ),
            lineage_refs=tuple(
                dict.fromkeys(
                    lineage_refs
                    + tuple(causal_refs)
                )
            ),
            relationship_refs=(
                self.predecessor.relationship_refs
            ),
            memory_refs=(
                self.predecessor.memory_refs
            ),
            value_refs=(
                self.predecessor.value_refs
            ),
        )


def empty_state(
    seed_id: str,
) -> NoumenonState:
    if not seed_id:
        raise ValueError(
            "seed_id is required"
        )

    return NoumenonState(
        noumenon_id=(
            "noumenon:" + seed_id
        ),
        predecessor_id=None,
        succession_status="unknown",
        generation=0,
    )


def continuity_receipt(
    predecessor: NoumenonState,
    successor: NoumenonState,
    *,
    transition_ref: str,
    authority_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
) -> dict[str, Any]:
    if (
        successor.noumenon_id
        != predecessor.noumenon_id
    ):
        raise ValueError(
            "continuous succession cannot "
            "change noumenon identity"
        )

    if (
        successor.predecessor_id
        != predecessor.state_digest
    ):
        raise ValueError(
            "successor predecessor digest "
            "does not match predecessor"
        )

    if (
        successor.generation
        != predecessor.generation + 1
    ):
        raise ValueError(
            "successor generation is not "
            "continuous"
        )

    body = {
        "schema": (
            "savant://noumenon/"
            "continuity-receipt/1"
        ),
        "noumenon_id": (
            predecessor.noumenon_id
        ),
        "predecessor_id": (
            predecessor.state_digest
        ),
        "successor_id": (
            successor.state_digest
        ),
        "transition_ref": transition_ref,
        "authority_refs": list(
            authority_refs
        ),
        "evidence_refs": list(
            evidence_refs
        ),
    }

    body["integrity_digest"] = _digest(
        body
    )

    return body

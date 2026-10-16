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
    id: str
    authority: str
    confidence: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("evidence id is required")
        if not self.authority:
            raise ValueError(
                "evidence authority is required"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "authority": self.authority,
            "confidence": self.confidence,
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
            raise ValueError("experience id is required")

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
            "metadata": dict(self.metadata),
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
        for name, value in self.dimensions.items():
            if not name:
                raise ValueError(
                    "significance dimension name is required"
                )
            if not -1.0 <= float(value) <= 1.0:
                raise ValueError(
                    "significance dimensions must be "
                    "between -1 and 1"
                )

        for name, value in self.uncertainty.items():
            if not name:
                raise ValueError(
                    "uncertainty dimension name is required"
                )
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(
                    "uncertainty must be between 0 and 1"
                )

    def projection(self) -> dict[str, Any]:
        return {
            "dimensions": {
                key: float(value)
                for key, value
                in sorted(self.dimensions.items())
            },
            "interpretation_refs": list(
                self.interpretation_refs
            ),
            "uncertainty": {
                key: float(value)
                for key, value
                in sorted(self.uncertainty.items())
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
                "consequence dimension is required"
            )
        if not self.causal_refs:
            raise ValueError(
                "developmental consequence requires "
                "causal lineage"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "delta": float(self.delta),
            "causal_refs": list(self.causal_refs),
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

        if self.succession_status not in (
            SUCCESSION_STATUSES
        ):
            raise ValueError(
                "invalid succession_status"
            )

        if self.generation < 0:
            raise ValueError(
                "generation cannot be negative"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "noumenon_id": self.noumenon_id,
            "predecessor_id": self.predecessor_id,
            "succession_status": (
                self.succession_status
            ),
            "generation": self.generation,
            "dimensions": {
                key: float(value)
                for key, value
                in sorted(self.dimensions.items())
            },
            "unresolved": list(self.unresolved),
            "lineage_refs": list(self.lineage_refs),
            "relationship_refs": list(
                self.relationship_refs
            ),
            "memory_refs": list(self.memory_refs),
            "value_refs": list(self.value_refs),
        }

    @property
    def state_digest(self) -> str:
        return _digest(self.projection())


@dataclass(frozen=True, slots=True)
class TransitionCandidate:
    predecessor: NoumenonState
    experience: Experience
    significance: Significance
    consequences: tuple[
        DevelopmentalConsequence, ...
    ]

    def validate_conservation(self) -> None:
        for consequence in self.consequences:
            if (
                abs(consequence.delta) > 0.0
                and not consequence.causal_refs
            ):
                raise ValueError(
                    "developmental change requires "
                    "causal lineage"
                )

    def successor(self) -> NoumenonState:
        self.validate_conservation()

        dimensions = dict(
            self.predecessor.dimensions
        )

        for consequence in self.consequences:
            dimensions[consequence.dimension] = (
                dimensions.get(
                    consequence.dimension,
                    0.0,
                )
                + consequence.delta
            )

        transition_id = _digest(
            {
                "predecessor": (
                    self.predecessor.state_digest
                ),
                "experience": (
                    self.experience.projection()
                ),
                "significance": (
                    self.significance.projection()
                ),
                "consequences": [
                    consequence.projection()
                    for consequence
                    in self.consequences
                ],
            }
        )

        successor_id = (
            "noumenon:"
            + _digest(
                {
                    "root": (
                        self.predecessor.noumenon_id
                    ),
                    "transition": transition_id,
                }
            )
        )

        unresolved = list(
            self.predecessor.unresolved
        )

        for consequence in self.consequences:
            if consequence.unresolved:
                unresolved.append(
                    consequence.dimension
                )

        return NoumenonState(
            noumenon_id=successor_id,
            predecessor_id=(
                self.predecessor.noumenon_id
            ),
            succession_status="continuous",
            generation=(
                self.predecessor.generation + 1
            ),
            dimensions=dimensions,
            unresolved=tuple(
                dict.fromkeys(unresolved)
            ),
            lineage_refs=(
                self.predecessor.lineage_refs
                + (
                    self.experience.id,
                    transition_id,
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


def empty_state(seed_id: str) -> NoumenonState:
    if not seed_id:
        raise ValueError("seed_id is required")

    return NoumenonState(
        noumenon_id=(
            "noumenon:"
            + _digest(
                {
                    "schema": SCHEMA,
                    "seed": seed_id,
                }
            )
        ),
        succession_status="unknown",
    )


def continuity_receipt(
    predecessor: NoumenonState,
    successor: NoumenonState,
    *,
    transition_refs: Sequence[str] = (),
    authority_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    projection_version: str = SCHEMA,
) -> dict[str, Any]:
    body = {
        "schema": "savant://noumenon/continuity-receipt/1",
        "noumenon_id": successor.noumenon_id,
        "predecessor_id": predecessor.noumenon_id,
        "successor_id": successor.noumenon_id,
        "succession_status": (
            successor.succession_status
        ),
        "transition_refs": list(transition_refs),
        "authority_refs": list(authority_refs),
        "evidence_refs": list(evidence_refs),
        "projection_version": projection_version,
        "lineage_digest": _digest(
            successor.lineage_refs
        ),
        "state_digest": successor.state_digest,
        "unresolved_discontinuities": list(
            successor.unresolved
        ),
    }

    body["integrity_digest"] = _digest(body)
    return body

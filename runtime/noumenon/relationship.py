from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/relationship/1"


RELATIONSHIP_DIMENSIONS = (
    "familiarity",
    "trust",
    "affection",
    "respect",
    "admiration",
    "dependence",
    "vulnerability",
    "safety",
    "predictability",
    "reciprocity",
    "intimacy",
    "grievance",
    "unresolvedness",
    "indebtedness",
    "loyalty",
    "rivalry",
    "authority_asymmetry",
    "power_asymmetry",
    "expectation",
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


def _signed(value: float) -> float:
    return max(
        -1.0,
        min(1.0, float(value)),
    )


@dataclass(frozen=True, slots=True)
class RelationshipProjection:
    subject_id: str
    object_id: str
    dimensions: Mapping[str, float] = field(
        default_factory=dict
    )
    boundary_refs: tuple[str, ...] = ()
    repair_refs: tuple[str, ...] = ()
    shared_history_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    uncertainty: Mapping[str, float] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not self.subject_id:
            raise ValueError(
                "subject_id is required"
            )

        if not self.object_id:
            raise ValueError(
                "object_id is required"
            )

        if self.subject_id == self.object_id:
            raise ValueError(
                "relationship endpoints "
                "must be distinct"
            )

        unsupported = (
            set(self.dimensions)
            - set(
                RELATIONSHIP_DIMENSIONS
            )
        )

        if unsupported:
            raise ValueError(
                "unsupported relationship "
                "dimensions: "
                + ", ".join(
                    sorted(unsupported)
                )
            )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "subject_id": self.subject_id,
            "object_id": self.object_id,
            "directional": True,
            "dimensions": {
                key: _signed(value)
                for key, value
                in sorted(
                    self.dimensions.items()
                )
            },
            "boundary_refs": list(
                self.boundary_refs
            ),
            "repair_refs": list(
                self.repair_refs
            ),
            "shared_history_refs": list(
                self.shared_history_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "uncertainty": {
                key: max(
                    0.0,
                    min(1.0, float(value)),
                )
                for key, value
                in sorted(
                    self.uncertainty.items()
                )
            },
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )

    @property
    def id(self) -> str:
        return (
            "relationship-projection:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class RelationshipConsequence:
    relationship_ref: str
    dimension: str
    delta: float
    causal_refs: tuple[str, ...]
    repair: bool = False

    def __post_init__(self) -> None:
        if not self.relationship_ref:
            raise ValueError(
                "relationship_ref is required"
            )

        if (
            self.dimension
            not in RELATIONSHIP_DIMENSIONS
        ):
            raise ValueError(
                "unsupported relationship dimension"
            )

        if not self.causal_refs:
            raise ValueError(
                "causal_refs are required"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "relationship_ref": (
                self.relationship_ref
            ),
            "dimension": self.dimension,
            "delta": _signed(self.delta),
            "causal_refs": list(
                self.causal_refs
            ),
            "repair": self.repair,
        }


def consequence_candidate(
    relationship: RelationshipProjection,
    *,
    deltas: Mapping[str, float],
    causal_refs: Sequence[str],
    repair: bool = False,
) -> dict[str, Any]:
    consequences = tuple(
        RelationshipConsequence(
            relationship_ref=(
                relationship.id
            ),
            dimension=dimension,
            delta=float(delta),
            causal_refs=tuple(
                causal_refs
            ),
            repair=repair,
        )
        for dimension, delta
        in sorted(deltas.items())
        if float(delta) != 0.0
    )

    body = {
        "schema": (
            "savant://noumenon/"
            "relationship-consequence-candidate/1"
        ),
        "relationship_ref": (
            relationship.id
        ),
        "subject_id": (
            relationship.subject_id
        ),
        "object_id": (
            relationship.object_id
        ),
        "consequences": [
            item.projection()
            for item in consequences
        ],
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body

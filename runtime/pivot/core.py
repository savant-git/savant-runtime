from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence


SCHEMA = "savant://pivot/core/1"


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


def _finite(value: float) -> float:
    result = float(value)

    if not math.isfinite(result):
        raise ValueError(
            "pivot force must be finite"
        )

    return result


@dataclass(frozen=True, slots=True)
class PivotForce:
    source_ref: str
    dimension: str
    magnitude: float
    provenance_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_ref:
            raise ValueError(
                "source_ref is required"
            )

        if not self.dimension:
            raise ValueError(
                "dimension is required"
            )

        _finite(self.magnitude)

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "source_ref": self.source_ref,
            "dimension": self.dimension,
            "magnitude": float(
                self.magnitude
            ),
            "provenance_refs": list(
                self.provenance_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "authority_refs": list(
                self.authority_refs
            ),
            "force_is_input": True,
            "source_mutated": False,
            "authority_transferred": False,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)
        return body

    @property
    def digest(self) -> str:
        return str(
            self.projection()["digest"]
        )

    @property
    def id(self) -> str:
        return "pivot-force:" + self.digest


@dataclass(frozen=True, slots=True)
class PivotVector:
    dimensions: tuple[
        tuple[str, float],
        ...
    ]
    source_refs: tuple[str, ...]

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "dimensions": [
                {
                    "dimension": dimension,
                    "magnitude": magnitude,
                }
                for dimension, magnitude
                in self.dimensions
            ],
            "source_refs": list(
                self.source_refs
            ),
            "orientation_only": True,
            "reasoning_claimed": False,
            "text_mutated": False,
            "source_mutated": False,
            "authority_transferred": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)
        return body

    @property
    def digest(self) -> str:
        return str(
            self.projection()["digest"]
        )

    @property
    def id(self) -> str:
        return "pivot-vector:" + self.digest


def compose_vector(
    forces: Sequence[PivotForce],
) -> PivotVector:
    ordered = tuple(
        sorted(
            forces,
            key=lambda force: (
                force.dimension,
                force.source_ref,
                force.id,
            ),
        )
    )

    totals: dict[str, float] = {}

    for force in ordered:
        totals[force.dimension] = (
            totals.get(
                force.dimension,
                0.0,
            )
            + _finite(force.magnitude)
        )

    dimensions = tuple(
        (
            dimension,
            totals[dimension],
        )
        for dimension
        in sorted(totals)
    )

    return PivotVector(
        dimensions=dimensions,
        source_refs=tuple(
            force.id
            for force in ordered
        ),
    )


def pivot_projection(
    forces: Sequence[PivotForce],
) -> Mapping[str, Any]:
    vector = compose_vector(forces)

    body = vector.projection()

    projection = dict(body)
    projection.update(
        {
            "model_independent": True,
            "provider_independent": True,
            "deterministic": True,
            "automatic_action": False,
            "automatic_reconciliation": False,
        }
    )

    projection.pop("digest", None)
    projection["digest"] = _digest(
        projection
    )

    return projection

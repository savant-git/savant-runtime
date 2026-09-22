from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/developmental-resonance/1"


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


def _unit(
    value: float,
) -> float:
    return max(
        0.0,
        min(
            1.0,
            float(value),
        ),
    )


@dataclass(frozen=True, slots=True)
class ResonanceSource:
    source_ref: str
    dimensions: Mapping[str, float]
    significance: float
    recency: float
    unresolved: float = 0.0
    relational: float = 0.0
    causal_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_ref:
            raise ValueError(
                "source_ref is required"
            )

        if not self.dimensions:
            raise ValueError(
                "dimensions are required"
            )

        for dimension, value in (
            self.dimensions.items()
        ):
            if not dimension:
                raise ValueError(
                    "dimension is required"
                )

            if not (
                -1.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "dimension values must be "
                    "between -1 and 1"
                )

        for value in (
            self.significance,
            self.recency,
            self.unresolved,
            self.relational,
        ):
            if not (
                0.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "resonance values must be "
                    "between 0 and 1"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "source_ref": self.source_ref,
            "dimensions": {
                key: float(value)
                for key, value
                in sorted(
                    self.dimensions.items()
                )
            },
            "significance": float(
                self.significance
            ),
            "recency": float(
                self.recency
            ),
            "unresolved": float(
                self.unresolved
            ),
            "relational": float(
                self.relational
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
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
            "noumenon-resonance-source:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class Resonance:
    source_a_ref: str
    source_b_ref: str
    overlap: float
    directional_alignment: float
    developmental_resonance: float
    shared_dimensions: tuple[str, ...]
    causal_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.source_a_ref:
            raise ValueError(
                "source_a_ref is required"
            )

        if not self.source_b_ref:
            raise ValueError(
                "source_b_ref is required"
            )

        for value in (
            self.overlap,
            self.directional_alignment,
            self.developmental_resonance,
        ):
            if not (
                0.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "resonance scores must be "
                    "between 0 and 1"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "source_a_ref": (
                self.source_a_ref
            ),
            "source_b_ref": (
                self.source_b_ref
            ),
            "overlap": float(
                self.overlap
            ),
            "directional_alignment": (
                float(
                    self
                    .directional_alignment
                )
            ),
            "developmental_resonance": (
                float(
                    self
                    .developmental_resonance
                )
            ),
            "shared_dimensions": list(
                self.shared_dimensions
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "derived": True,
            "authoritative": False,
        }

        body["digest"] = _digest(
            body
        )

        return body


def resonate(
    source_a: ResonanceSource,
    source_b: ResonanceSource,
) -> Resonance:
    shared = tuple(
        sorted(
            set(source_a.dimensions)
            & set(source_b.dimensions)
        )
    )

    if not shared:
        return Resonance(
            source_a_ref=source_a.id,
            source_b_ref=source_b.id,
            overlap=0.0,
            directional_alignment=0.0,
            developmental_resonance=0.0,
            shared_dimensions=(),
            causal_refs=tuple(
                dict.fromkeys(
                    (
                        source_a.id,
                        source_b.id,
                        *source_a.causal_refs,
                        *source_b.causal_refs,
                    )
                )
            ),
        )

    overlap_values: list[float] = []
    alignment_values: list[float] = []

    for dimension in shared:
        left = float(
            source_a.dimensions[
                dimension
            ]
        )

        right = float(
            source_b.dimensions[
                dimension
            ]
        )

        overlap_values.append(
            min(
                abs(left),
                abs(right),
            )
        )

        if (
            left == 0.0
            or right == 0.0
        ):
            alignment_values.append(
                0.0
            )
        elif (
            left > 0.0
            and right > 0.0
        ) or (
            left < 0.0
            and right < 0.0
        ):
            alignment_values.append(
                1.0
            )
        else:
            alignment_values.append(
                0.0
            )

    overlap = (
        sum(overlap_values)
        / len(overlap_values)
    )

    alignment = (
        sum(alignment_values)
        / len(alignment_values)
    )

    significance = (
        float(source_a.significance)
        + float(source_b.significance)
    ) / 2.0

    recency = (
        float(source_a.recency)
        + float(source_b.recency)
    ) / 2.0

    unresolved = (
        float(source_a.unresolved)
        + float(source_b.unresolved)
    ) / 2.0

    relational = (
        float(source_a.relational)
        + float(source_b.relational)
    ) / 2.0

    activation = (
        significance
        + recency
        + unresolved
        + relational
    ) / 4.0

    developmental_resonance = (
        _unit(
            overlap
            * (
                0.5
                + 0.5 * alignment
            )
            * activation
        )
    )

    return Resonance(
        source_a_ref=source_a.id,
        source_b_ref=source_b.id,
        overlap=overlap,
        directional_alignment=alignment,
        developmental_resonance=(
            developmental_resonance
        ),
        shared_dimensions=shared,
        causal_refs=tuple(
            dict.fromkeys(
                (
                    source_a.id,
                    source_b.id,
                    *source_a.causal_refs,
                    *source_b.causal_refs,
                )
            )
        ),
    )


def resonance_field(
    focal: ResonanceSource,
    history: Sequence[
        ResonanceSource
    ],
) -> tuple[Resonance, ...]:
    resonances = tuple(
        resonate(
            focal,
            source,
        )
        for source in history
        if source.id != focal.id
    )

    return tuple(
        sorted(
            resonances,
            key=lambda item: (
                -item
                .developmental_resonance,
                item.source_b_ref,
            ),
        )
    )


def resonance_projection(
    focal: ResonanceSource,
    history: Sequence[
        ResonanceSource
    ],
) -> Mapping[str, Any]:
    field = resonance_field(
        focal,
        history,
    )

    return {
        "schema": SCHEMA,
        "focal_ref": focal.id,
        "resonances": [
            item.projection()
            for item in field
        ],
        "strongest_ref": (
            field[0].source_b_ref
            if field
            else None
        ),
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

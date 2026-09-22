from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/path-dependence/1"


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
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _signed(
    value: float,
) -> float:
    return max(
        -1.0,
        min(1.0, float(value)),
    )


def _unit(
    value: float,
) -> float:
    return max(
        0.0,
        min(1.0, float(value)),
    )


@dataclass(frozen=True, slots=True)
class PathEvent:
    event_ref: str
    dimensions: Mapping[str, float]
    significance: float
    persistence: float
    sequence: int
    causal_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.event_ref:
            raise ValueError(
                "event_ref is required"
            )

        if self.sequence < 0:
            raise ValueError(
                "sequence cannot be negative"
            )

        if not self.dimensions:
            raise ValueError(
                "dimensions are required"
            )

        if not self.causal_refs:
            raise ValueError(
                "path event requires causal refs"
            )

        for dimension, value in (
            self.dimensions.items()
        ):
            if not dimension:
                raise ValueError(
                    "dimension is required"
                )

            if not (
                -1.0 <= float(value) <= 1.0
            ):
                raise ValueError(
                    "dimension values must be "
                    "between -1 and 1"
                )

        for value in (
            self.significance,
            self.persistence,
        ):
            if not (
                0.0 <= float(value) <= 1.0
            ):
                raise ValueError(
                    "significance and persistence "
                    "must be between 0 and 1"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "event_ref": self.event_ref,
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
            "persistence": float(
                self.persistence
            ),
            "sequence": self.sequence,
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
            "noumenon-path-event:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class PathState:
    dimensions: Mapping[str, float]
    hysteresis: Mapping[str, float]
    event_refs: tuple[str, ...]
    causal_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for mapping in (
            self.dimensions,
            self.hysteresis,
        ):
            for value in mapping.values():
                if not (
                    -1.0
                    <= float(value)
                    <= 1.0
                ):
                    raise ValueError(
                        "path state values must "
                        "be between -1 and 1"
                    )

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "dimensions": {
                key: float(value)
                for key, value
                in sorted(
                    self.dimensions.items()
                )
            },
            "hysteresis": {
                key: float(value)
                for key, value
                in sorted(
                    self.hysteresis.items()
                )
            },
            "event_refs": list(
                self.event_refs
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)

        return body


def derive_path_state(
    events: Sequence[PathEvent],
    *,
    hysteresis_retention: float,
) -> PathState:
    if not (
        0.0
        <= float(hysteresis_retention)
        <= 1.0
    ):
        raise ValueError(
            "hysteresis_retention must be "
            "between 0 and 1"
        )

    ordered = tuple(
        sorted(
            events,
            key=lambda item: (
                item.sequence,
                item.event_ref,
                item.id,
            ),
        )
    )

    sequences = [
        item.sequence
        for item in ordered
    ]

    if len(sequences) != len(
        set(sequences)
    ):
        raise ValueError(
            "path event sequences must be unique"
        )

    dimensions: dict[str, float] = {}
    hysteresis: dict[str, float] = {}
    causal_refs: list[str] = []

    for event in ordered:
        for dimension in (
            set(dimensions)
            | set(event.dimensions)
        ):
            previous = float(
                dimensions.get(
                    dimension,
                    0.0,
                )
            )

            residue = float(
                hysteresis.get(
                    dimension,
                    0.0,
                )
            )

            incoming = float(
                event.dimensions.get(
                    dimension,
                    0.0,
                )
            )

            effective = (
                incoming
                * float(event.significance)
            )

            resistance = _unit(
                abs(residue)
                * float(
                    hysteresis_retention
                )
            )

            if (
                previous != 0.0
                and effective != 0.0
                and (
                    previous > 0.0
                ) != (
                    effective > 0.0
                )
            ):
                effective *= (
                    1.0 - resistance
                )

            updated = _signed(
                previous
                + (
                    effective
                    * (
                        1.0
                        - (
                            0.5
                            * abs(previous)
                        )
                    )
                )
            )

            dimensions[dimension] = updated

            hysteresis[dimension] = (
                _signed(
                    (
                        residue
                        * float(
                            hysteresis_retention
                        )
                    )
                    + (
                        updated
                        * float(
                            event.persistence
                        )
                        * (
                            1.0
                            - float(
                                hysteresis_retention
                            )
                        )
                    )
                )
            )

        causal_refs.extend(
            (
                event.id,
                *event.causal_refs,
            )
        )

    return PathState(
        dimensions={
            key: dimensions[key]
            for key in sorted(dimensions)
        },
        hysteresis={
            key: hysteresis[key]
            for key in sorted(hysteresis)
        },
        event_refs=tuple(
            item.id
            for item in ordered
        ),
        causal_refs=tuple(
            dict.fromkeys(
                causal_refs
            )
        ),
    )


def compare_paths(
    left: PathState,
    right: PathState,
) -> Mapping[str, float]:
    dimensions = (
        set(left.dimensions)
        | set(right.dimensions)
    )

    return {
        dimension: _signed(
            float(
                left.dimensions.get(
                    dimension,
                    0.0,
                )
            )
            - float(
                right.dimensions.get(
                    dimension,
                    0.0,
                )
            )
        )
        for dimension
        in sorted(dimensions)
    }


def transformative_thresholds(
    predecessor: PathState,
    successor: PathState,
    *,
    threshold: float,
) -> tuple[str, ...]:
    if not (
        0.0 < float(threshold) <= 1.0
    ):
        raise ValueError(
            "threshold must be greater than "
            "0 and at most 1"
        )

    dimensions = (
        set(predecessor.dimensions)
        | set(successor.dimensions)
    )

    crossed = []

    for dimension in sorted(
        dimensions
    ):
        before = float(
            predecessor.dimensions.get(
                dimension,
                0.0,
            )
        )

        after = float(
            successor.dimensions.get(
                dimension,
                0.0,
            )
        )

        if (
            abs(after - before)
            >= float(threshold)
        ):
            crossed.append(dimension)

    return tuple(crossed)


def path_projection(
    events: Sequence[PathEvent],
    *,
    hysteresis_retention: float,
) -> Mapping[str, Any]:
    state = derive_path_state(
        events,
        hysteresis_retention=(
            hysteresis_retention
        ),
    )

    return {
        "schema": SCHEMA,
        "state": state.projection(),
        "path_order_matters": True,
        "hysteresis_preserved": True,
        "history_is_authority": False,
        "automatic_identity_mutation": False,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

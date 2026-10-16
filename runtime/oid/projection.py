from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.oid.constraint import (
    TemporalConstraint,
    detect_constraint_conflicts,
    relation_from_constraints,
)
from runtime.oid.core import (
    TemporalRecord,
    detect_conflicts,
    replay_order,
)


SCHEMA = "savant://oid/projection/1"


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
class TemporalLayer:
    index: int
    record_refs: tuple[str, ...]

    def projection(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "record_refs": list(
                self.record_refs
            ),
            "internally_totally_ordered": False,
        }


def _strict_edges(
    records: Sequence[TemporalRecord],
    constraints: Sequence[
        TemporalConstraint
    ],
) -> dict[str, set[str]]:
    record_ids = {
        record.id
        for record in records
    }

    edges: dict[str, set[str]] = {
        record_id: set()
        for record_id in record_ids
    }

    for record in records:
        for predecessor in (
            record.predecessor_refs
        ):
            if predecessor in record_ids:
                edges[
                    predecessor
                ].add(record.id)

    ordered_ids = sorted(record_ids)

    for index, left in enumerate(
        ordered_ids
    ):
        for right in ordered_ids[
            index + 1:
        ]:
            relation = (
                relation_from_constraints(
                    left,
                    right,
                    constraints,
                )
            )

            if relation == "before":
                edges[left].add(right)

            elif relation == "after":
                edges[right].add(left)

    return edges


def topological_layers(
    records: Sequence[TemporalRecord],
    constraints: Sequence[
        TemporalConstraint
    ] = (),
) -> tuple[TemporalLayer, ...]:
    edges = _strict_edges(
        records,
        constraints,
    )

    incoming: dict[str, set[str]] = {
        ref: set()
        for ref in edges
    }

    for source, targets in edges.items():
        for target in targets:
            incoming.setdefault(
                target,
                set(),
            ).add(source)

    remaining = set(incoming)
    layers: list[TemporalLayer] = []
    index = 0

    while remaining:
        available = tuple(
            sorted(
                ref
                for ref in remaining
                if not (
                    incoming[ref]
                    & remaining
                )
            )
        )

        if not available:
            break

        layers.append(
            TemporalLayer(
                index=index,
                record_refs=available,
            )
        )

        remaining.difference_update(
            available
        )
        index += 1

    if remaining:
        layers.append(
            TemporalLayer(
                index=index,
                record_refs=tuple(
                    sorted(remaining)
                ),
            )
        )

    return tuple(layers)


def deterministic_replay(
    records: Sequence[TemporalRecord],
    constraints: Sequence[
        TemporalConstraint
    ] = (),
) -> tuple[TemporalRecord, ...]:
    by_id = {
        record.id: record
        for record in records
    }

    fallback = {
        record.id: index
        for index, record in enumerate(
            replay_order(records)
        )
    }

    result: list[TemporalRecord] = []

    for layer in topological_layers(
        records,
        constraints,
    ):
        ordered_refs = sorted(
            layer.record_refs,
            key=lambda ref: (
                fallback.get(ref, 0),
                ref,
            ),
        )

        result.extend(
            by_id[ref]
            for ref in ordered_refs
        )

    return tuple(result)


def temporal_snapshot(
    records: Sequence[TemporalRecord],
    constraints: Sequence[
        TemporalConstraint
    ] = (),
) -> Mapping[str, Any]:
    ordered = deterministic_replay(
        records,
        constraints,
    )

    layers = topological_layers(
        records,
        constraints,
    )

    temporal_conflicts = detect_conflicts(
        records
    )

    constraint_conflicts = (
        detect_constraint_conflicts(
            constraints
        )
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "record_refs": [
            record.id
            for record in ordered
        ],
        "layers": [
            layer.projection()
            for layer in layers
        ],
        "temporal_conflicts": [
            conflict.projection()
            for conflict in temporal_conflicts
        ],
        "constraint_conflicts": [
            conflict.projection()
            for conflict
            in constraint_conflicts
        ],
        "record_count": len(records),
        "layer_count": len(layers),
        "temporal_conflict_count": len(
            temporal_conflicts
        ),
        "constraint_conflict_count": len(
            constraint_conflicts
        ),
        "single_present_projection": True,
        "single_present_is_external_fact": False,
        "replay_is_external_chronology": False,
        "partial_order_preserved": True,
        "concurrency_preserved": True,
        "unknown_order_preserved": True,
        "conflicts_preserved": True,
        "authority_transferred": False,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body

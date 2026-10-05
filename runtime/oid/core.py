from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://oid/core/1"

RELATIONS = frozenset(
    {
        "before",
        "after",
        "equal",
        "overlaps",
        "contains",
        "contained_by",
        "concurrent",
        "conflicting",
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


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError(
            "oid timestamps require timezone information"
        )

    return value.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None

    return (
        _utc(value)
        .isoformat()
        .replace("+00:00", "Z")
    )


@dataclass(frozen=True, slots=True)
class TemporalInterval:
    start: datetime | None = None
    end: datetime | None = None
    uncertainty_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.start is not None:
            _utc(self.start)

        if self.end is not None:
            _utc(self.end)

        if (
            self.start is not None
            and self.end is not None
            and _utc(self.end) < _utc(self.start)
        ):
            raise ValueError(
                "temporal interval ends before it starts"
            )

        if self.uncertainty_seconds < 0.0:
            raise ValueError(
                "uncertainty cannot be negative"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "start": _iso(self.start),
            "end": _iso(self.end),
            "uncertainty_seconds": float(
                self.uncertainty_seconds
            ),
        }


@dataclass(frozen=True, slots=True)
class TemporalRecord:
    record_ref: str
    frame_ref: str
    source_clock_ref: str
    logical_sequence: int
    event_interval: TemporalInterval
    observation_time: datetime
    original_timestamp: str | None = None
    predecessor_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.record_ref:
            raise ValueError("record_ref is required")

        if not self.frame_ref:
            raise ValueError("frame_ref is required")

        if not self.source_clock_ref:
            raise ValueError(
                "source_clock_ref is required"
            )

        if self.logical_sequence < 0:
            raise ValueError(
                "logical_sequence cannot be negative"
            )

        _utc(self.observation_time)

        if len(self.metadata) > 64:
            raise ValueError(
                "oid metadata is bounded to 64 entries"
            )

        keys = [key for key, _ in self.metadata]

        if len(keys) != len(set(keys)):
            raise ValueError(
                "duplicate metadata key"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "record_ref": self.record_ref,
            "frame_ref": self.frame_ref,
            "source_clock_ref": (
                self.source_clock_ref
            ),
            "logical_sequence": (
                self.logical_sequence
            ),
            "event_interval": (
                self.event_interval.projection()
            ),
            "observation_time": _iso(
                self.observation_time
            ),
            "original_timestamp": (
                self.original_timestamp
            ),
            "predecessor_refs": list(
                self.predecessor_refs
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
            "metadata": {
                key: value
                for key, value in self.metadata
            },
            "authority_effect": "none",
        }

    @property
    def digest(self) -> str:
        return _digest(self.projection())

    @property
    def id(self) -> str:
        return "oid-record:" + self.digest


@dataclass(frozen=True, slots=True)
class TemporalRelation:
    left_ref: str
    right_ref: str
    relation: str
    causal: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.relation not in RELATIONS:
            raise ValueError(
                "unsupported temporal relation"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "left_ref": self.left_ref,
            "right_ref": self.right_ref,
            "relation": self.relation,
            "causal": self.causal,
            "reasons": list(self.reasons),
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }


@dataclass(frozen=True, slots=True)
class ClockObservation:
    source_clock_ref: str
    observed_offset_seconds: float
    uncertainty_seconds: float
    observation_ref: str

    def __post_init__(self) -> None:
        if not self.source_clock_ref:
            raise ValueError(
                "source_clock_ref is required"
            )

        if self.uncertainty_seconds < 0.0:
            raise ValueError(
                "uncertainty cannot be negative"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "source_clock_ref": (
                self.source_clock_ref
            ),
            "observed_offset_seconds": float(
                self.observed_offset_seconds
            ),
            "uncertainty_seconds": float(
                self.uncertainty_seconds
            ),
            "observation_ref": (
                self.observation_ref
            ),
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }


@dataclass(frozen=True, slots=True)
class TemporalConflict:
    record_refs: tuple[str, ...]
    reason: str
    evidence_refs: tuple[str, ...]

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "record_refs": list(
                self.record_refs
            ),
            "reason": self.reason,
            "evidence_refs": list(
                self.evidence_refs
            ),
            "automatically_resolved": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }


def interval_relation(
    left: TemporalInterval,
    right: TemporalInterval,
) -> str:
    if (
        left.start is None
        or left.end is None
        or right.start is None
        or right.end is None
    ):
        return "unknown"

    ls = _utc(left.start)
    le = _utc(left.end)
    rs = _utc(right.start)
    re = _utc(right.end)

    if le < rs:
        return "before"

    if ls > re:
        return "after"

    if ls == rs and le == re:
        return "equal"

    if ls <= rs and le >= re:
        return "contains"

    if rs <= ls and re >= le:
        return "contained_by"

    return "overlaps"


def relate(
    left: TemporalRecord,
    right: TemporalRecord,
) -> TemporalRelation:
    if left.id == right.id:
        return TemporalRelation(
            left_ref=left.id,
            right_ref=right.id,
            relation="equal",
            causal=False,
            reasons=("same_record",),
        )

    if left.id in right.predecessor_refs:
        return TemporalRelation(
            left_ref=left.id,
            right_ref=right.id,
            relation="before",
            causal=True,
            reasons=("explicit_predecessor",),
        )

    if right.id in left.predecessor_refs:
        return TemporalRelation(
            left_ref=left.id,
            right_ref=right.id,
            relation="after",
            causal=True,
            reasons=("explicit_predecessor",),
        )

    relation = interval_relation(
        left.event_interval,
        right.event_interval,
    )

    if relation == "unknown":
        if (
            left.frame_ref == right.frame_ref
            and left.logical_sequence
            != right.logical_sequence
        ):
            return TemporalRelation(
                left_ref=left.id,
                right_ref=right.id,
                relation="concurrent",
                causal=False,
                reasons=(
                    "logical_order_without_causal_order",
                ),
            )

        return TemporalRelation(
            left_ref=left.id,
            right_ref=right.id,
            relation="unknown",
            causal=False,
            reasons=(
                "insufficient_temporal_evidence",
            ),
        )

    return TemporalRelation(
        left_ref=left.id,
        right_ref=right.id,
        relation=relation,
        causal=False,
        reasons=("event_interval",),
    )


def detect_conflicts(
    records: Sequence[TemporalRecord],
) -> tuple[TemporalConflict, ...]:
    by_ref: dict[str, list[TemporalRecord]] = {}

    for record in records:
        by_ref.setdefault(
            record.record_ref,
            [],
        ).append(record)

    conflicts: list[TemporalConflict] = []

    for record_ref, variants in sorted(
        by_ref.items()
    ):
        digests = {
            item.digest
            for item in variants
        }

        if len(digests) <= 1:
            continue

        intervals = {
            _canonical_json(
                item.event_interval.projection()
            )
            for item in variants
        }

        if len(intervals) > 1:
            conflicts.append(
                TemporalConflict(
                    record_refs=tuple(
                        sorted(
                            item.id
                            for item in variants
                        )
                    ),
                    reason=(
                        "incompatible_temporal_assertions:"
                        + record_ref
                    ),
                    evidence_refs=tuple(
                        sorted(
                            {
                                ref
                                for item in variants
                                for ref in (
                                    *item.evidence_refs,
                                    *item.provenance_refs,
                                )
                            }
                        )
                    ),
                )
            )

    return tuple(conflicts)


def replay_order(
    records: Sequence[TemporalRecord],
) -> tuple[TemporalRecord, ...]:
    return tuple(
        sorted(
            records,
            key=lambda item: (
                item.logical_sequence,
                _iso(item.observation_time),
                item.id,
            ),
        )
    )


def next_logical_sequence(
    records: Sequence[TemporalRecord],
) -> int:
    if not records:
        return 0

    return max(
        record.logical_sequence
        for record in records
    ) + 1


def temporal_receipt(
    records: Sequence[TemporalRecord],
) -> Mapping[str, Any]:
    ordered = replay_order(records)
    conflicts = detect_conflicts(records)

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "record_refs": [
            record.id
            for record in ordered
        ],
        "logical_sequences": [
            record.logical_sequence
            for record in ordered
        ],
        "conflicts": [
            conflict.projection()
            for conflict in conflicts
        ],
        "conflict_count": len(conflicts),
        "replay_is_external_chronology": False,
        "concurrency_may_be_preserved": True,
        "unknown_may_be_preserved": True,
        "authority_transferred": False,
        "model_independent": True,
        "provider_independent": True,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body

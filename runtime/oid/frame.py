from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.oid.core import (
    TemporalConflict,
    TemporalRecord,
    detect_conflicts,
    replay_order,
    temporal_receipt,
)


SCHEMA = "savant://oid/frame/1"


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
class OidFrame:
    frame_ref: str
    generation: int
    records: tuple[TemporalRecord, ...]
    predecessor_ref: str | None = None
    causal_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.frame_ref:
            raise ValueError(
                "frame_ref is required"
            )

        if self.generation < 0:
            raise ValueError(
                "generation cannot be negative"
            )

        if self.generation == 0:
            if self.predecessor_ref is not None:
                raise ValueError(
                    "genesis frame cannot have predecessor"
                )
        elif not self.predecessor_ref:
            raise ValueError(
                "successor frame requires predecessor"
            )

        record_ids = [
            record.id
            for record in self.records
        ]

        if len(record_ids) != len(set(record_ids)):
            raise ValueError(
                "duplicate oid record"
            )

        for record in self.records:
            if record.frame_ref != self.frame_ref:
                raise ValueError(
                    "record belongs to another oid frame"
                )

    def projection(self) -> dict[str, Any]:
        ordered = replay_order(self.records)
        conflicts = detect_conflicts(self.records)

        body: dict[str, Any] = {
            "schema": SCHEMA,
            "frame_ref": self.frame_ref,
            "generation": self.generation,
            "predecessor_ref": self.predecessor_ref,
            "records": [
                record.projection()
                for record in ordered
            ],
            "record_refs": [
                record.id
                for record in ordered
            ],
            "conflicts": [
                conflict.projection()
                for conflict in conflicts
            ],
            "causal_refs": list(
                self.causal_refs
            ),
            "single_present_claimed": False,
            "partial_order_preserved": True,
            "conflicts_preserved": True,
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
        return "oid-frame:" + self.digest


@dataclass(frozen=True, slots=True)
class FrameTransition:
    predecessor_ref: str
    successor_ref: str
    frame_ref: str
    predecessor_generation: int
    successor_generation: int
    added_record_refs: tuple[str, ...]
    retained_record_refs: tuple[str, ...]
    removed_record_refs: tuple[str, ...]
    conflict_refs: tuple[str, ...]
    causal_refs: tuple[str, ...]

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "predecessor_ref": (
                self.predecessor_ref
            ),
            "successor_ref": (
                self.successor_ref
            ),
            "frame_ref": self.frame_ref,
            "predecessor_generation": (
                self.predecessor_generation
            ),
            "successor_generation": (
                self.successor_generation
            ),
            "added_record_refs": list(
                self.added_record_refs
            ),
            "retained_record_refs": list(
                self.retained_record_refs
            ),
            "removed_record_refs": list(
                self.removed_record_refs
            ),
            "conflict_refs": list(
                self.conflict_refs
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "destructive_reconciliation": False,
            "authority_transferred": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)
        return body


def establish_frame(
    frame_ref: str,
    records: Sequence[TemporalRecord] = (),
    *,
    causal_refs: Sequence[str] = (),
) -> OidFrame:
    return OidFrame(
        frame_ref=frame_ref,
        generation=0,
        records=tuple(records),
        predecessor_ref=None,
        causal_refs=tuple(
            dict.fromkeys(causal_refs)
        ),
    )


def advance_frame(
    predecessor: OidFrame,
    records: Sequence[TemporalRecord],
    *,
    causal_refs: Sequence[str] = (),
) -> tuple[OidFrame, FrameTransition]:
    predecessor_ids = frozenset(
        record.id
        for record in predecessor.records
    )

    successor_records = tuple(records)

    successor_ids = frozenset(
        record.id
        for record in successor_records
    )

    successor = OidFrame(
        frame_ref=predecessor.frame_ref,
        generation=predecessor.generation + 1,
        records=successor_records,
        predecessor_ref=predecessor.id,
        causal_refs=tuple(
            dict.fromkeys(
                (
                    predecessor.id,
                    *causal_refs,
                )
            )
        ),
    )

    conflicts = detect_conflicts(
        successor_records
    )

    conflict_refs = tuple(
        _digest(
            conflict.projection()
        )
        for conflict in conflicts
    )

    transition = FrameTransition(
        predecessor_ref=predecessor.id,
        successor_ref=successor.id,
        frame_ref=predecessor.frame_ref,
        predecessor_generation=(
            predecessor.generation
        ),
        successor_generation=(
            successor.generation
        ),
        added_record_refs=tuple(
            sorted(
                successor_ids
                - predecessor_ids
            )
        ),
        retained_record_refs=tuple(
            sorted(
                successor_ids
                & predecessor_ids
            )
        ),
        removed_record_refs=tuple(
            sorted(
                predecessor_ids
                - successor_ids
            )
        ),
        conflict_refs=conflict_refs,
        causal_refs=tuple(
            dict.fromkeys(
                (
                    predecessor.id,
                    successor.id,
                    *causal_refs,
                )
            )
        ),
    )

    return successor, transition


def frame_receipt(
    frame: OidFrame,
) -> Mapping[str, Any]:
    temporal = temporal_receipt(
        frame.records
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "frame_ref": frame.frame_ref,
        "frame_id": frame.id,
        "generation": frame.generation,
        "predecessor_ref": (
            frame.predecessor_ref
        ),
        "temporal_receipt_ref": (
            temporal["digest"]
        ),
        "record_count": len(frame.records),
        "conflict_count": (
            temporal["conflict_count"]
        ),
        "causal_refs": list(
            frame.causal_refs
        ),
        "replay_is_external_chronology": False,
        "conflicts_are_automatically_resolved": False,
        "authority_transferred": False,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body


def validate_transition(
    predecessor: OidFrame,
    successor: OidFrame,
    transition: FrameTransition,
) -> bool:
    if predecessor.frame_ref != successor.frame_ref:
        return False

    if (
        successor.generation
        != predecessor.generation + 1
    ):
        return False

    if successor.predecessor_ref != predecessor.id:
        return False

    if transition.predecessor_ref != predecessor.id:
        return False

    if transition.successor_ref != successor.id:
        return False

    if transition.frame_ref != successor.frame_ref:
        return False

    if predecessor.id not in transition.causal_refs:
        return False

    if successor.id not in transition.causal_refs:
        return False

    return True

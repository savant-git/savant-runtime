from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.oid.bridge import (
    TemporalBridge,
    bridge_projection,
)
from runtime.oid.constraint import (
    TemporalConstraint,
    constraint_projection,
)
from runtime.oid.core import (
    ClockObservation,
    TemporalRecord,
    temporal_receipt,
)
from runtime.oid.frame import (
    OidFrame,
    frame_receipt,
)
from runtime.oid.projection import (
    temporal_snapshot,
)


SCHEMA = "savant://oid/integrity/1"


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
class IntegrityFinding:
    code: str
    subject_ref: str
    severity: str
    details: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.severity not in {
            "information",
            "warning",
            "conflict",
        }:
            raise ValueError(
                "unsupported integrity severity"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "code": self.code,
            "subject_ref": self.subject_ref,
            "severity": self.severity,
            "details": list(self.details),
            "automatic_mutation": False,
            "authority_effect": "none",
        }


def inspect_frame(
    frame: OidFrame,
    *,
    constraints: Sequence[
        TemporalConstraint
    ] = (),
    bridges: Sequence[
        TemporalBridge
    ] = (),
) -> tuple[IntegrityFinding, ...]:
    findings: list[IntegrityFinding] = []

    record_ids = {
        record.id
        for record in frame.records
    }

    sequence_owners: dict[
        int,
        list[str],
    ] = {}

    for record in frame.records:
        sequence_owners.setdefault(
            record.logical_sequence,
            [],
        ).append(record.id)

        for predecessor_ref in (
            record.predecessor_refs
        ):
            if predecessor_ref not in record_ids:
                findings.append(
                    IntegrityFinding(
                        code=(
                            "orphan_predecessor"
                        ),
                        subject_ref=record.id,
                        severity="warning",
                        details=(
                            predecessor_ref,
                        ),
                    )
                )

    for sequence, owners in sorted(
        sequence_owners.items()
    ):
        if len(owners) > 1:
            findings.append(
                IntegrityFinding(
                    code=(
                        "logical_sequence_collision"
                    ),
                    subject_ref=frame.id,
                    severity="information",
                    details=(
                        str(sequence),
                        *sorted(owners),
                    ),
                )
            )

    for constraint in constraints:
        missing = tuple(
            ref
            for ref in (
                constraint.left_ref,
                constraint.right_ref,
            )
            if ref not in record_ids
        )

        if missing:
            findings.append(
                IntegrityFinding(
                    code=(
                        "constraint_endpoint_absent"
                    ),
                    subject_ref=constraint.id,
                    severity="warning",
                    details=missing,
                )
            )

    for bridge in bridges:
        frame_participates = (
            bridge.left_frame_ref
            == frame.frame_ref
            or bridge.right_frame_ref
            == frame.frame_ref
        )

        if not frame_participates:
            continue

        local_refs: list[str] = []

        if (
            bridge.left_frame_ref
            == frame.frame_ref
        ):
            local_refs.append(
                bridge.left_record_ref
            )

        if (
            bridge.right_frame_ref
            == frame.frame_ref
        ):
            local_refs.append(
                bridge.right_record_ref
            )

        missing = tuple(
            ref
            for ref in local_refs
            if ref not in record_ids
        )

        if missing:
            findings.append(
                IntegrityFinding(
                    code=(
                        "bridge_endpoint_absent"
                    ),
                    subject_ref=bridge.id,
                    severity="warning",
                    details=missing,
                )
            )

    return tuple(
        sorted(
            findings,
            key=lambda item: (
                item.severity,
                item.code,
                item.subject_ref,
                item.details,
            ),
        )
    )


def integrity_receipt(
    frame: OidFrame,
    *,
    constraints: Sequence[
        TemporalConstraint
    ] = (),
    bridges: Sequence[
        TemporalBridge
    ] = (),
    clock_observations: Sequence[
        ClockObservation
    ] = (),
) -> Mapping[str, Any]:
    findings = inspect_frame(
        frame,
        constraints=constraints,
        bridges=bridges,
    )

    temporal = temporal_receipt(
        frame.records
    )

    frame_state = frame_receipt(frame)

    constraints_state = (
        constraint_projection(
            constraints
        )
    )

    bridges_state = bridge_projection(
        bridges
    )

    snapshot = temporal_snapshot(
        frame.records,
        constraints,
    )

    clock_refs = tuple(
        sorted(
            {
                observation.source_clock_ref
                for observation
                in clock_observations
            }
        )
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "frame_ref": frame.frame_ref,
        "frame_id": frame.id,
        "generation": frame.generation,
        "frame_receipt_ref": (
            frame_state["digest"]
        ),
        "temporal_receipt_ref": (
            temporal["digest"]
        ),
        "constraint_receipt_ref": (
            constraints_state["digest"]
        ),
        "bridge_receipt_ref": (
            bridges_state["digest"]
        ),
        "snapshot_receipt_ref": (
            snapshot["digest"]
        ),
        "clock_refs": list(clock_refs),
        "finding_count": len(findings),
        "findings": [
            finding.projection()
            for finding in findings
        ],
        "record_count": len(
            frame.records
        ),
        "constraint_count": len(
            constraints
        ),
        "bridge_count": len(bridges),
        "clock_observation_count": len(
            clock_observations
        ),
        "logical_sequence_is_causal_fact": False,
        "integrity_is_external_truth": False,
        "automatic_reconciliation": False,
        "historical_evidence_mutated": False,
        "authority_transferred": False,
        "model_independent": True,
        "provider_independent": True,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body

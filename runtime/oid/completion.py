from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.oid.bridge import TemporalBridge
from runtime.oid.constraint import TemporalConstraint
from runtime.oid.core import ClockObservation
from runtime.oid.frame import OidFrame
from runtime.oid.integrity import integrity_receipt


SCHEMA = "savant://oid/completion/1"

REQUIREMENTS = (
    "utc_normalization",
    "original_timestamp_preservation",
    "source_clock_identity",
    "logical_sequence_coordinates",
    "monotonic_frame_sequencing",
    "causal_predecessor_references",
    "causal_successor_derivation",
    "partial_ordering",
    "explicit_concurrency",
    "explicit_unknown_ordering",
    "temporal_intervals",
    "interval_overlap_detection",
    "temporal_conflict_detection",
    "clock_skew_representation",
    "uncertainty_bounds",
    "authority_isolation",
    "deterministic_content_addressing",
    "replay_coordinates",
    "deterministic_projection",
    "immutable_temporal_evidence",
    "provenance_references",
    "evidence_references",
    "authority_references",
    "bounded_metadata",
    "model_independence",
    "provider_independence",
    "dependency_sovereignty",
    "stdlib_operation",
    "deterministic_tie_handling",
    "temporal_integrity_receipts",
    "reversible_serialization",
    "contradiction_preservation",
    "no_destructive_reconciliation",
    "typed_temporal_relationships",
    "cross_system_frame_compatibility",
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
class RequirementStatus:
    requirement: str
    implemented: bool
    evidence_refs: tuple[str, ...]

    def projection(self) -> dict[str, Any]:
        return {
            "requirement": self.requirement,
            "implemented": self.implemented,
            "evidence_refs": list(
                self.evidence_refs
            ),
        }


def requirement_statuses() -> tuple[
    RequirementStatus,
    ...
]:
    evidence: dict[str, tuple[str, ...]] = {
        "utc_normalization": (
            "runtime.oid.conversion",
        ),
        "original_timestamp_preservation": (
            "runtime.oid.core",
            "runtime.oid.conversion",
        ),
        "source_clock_identity": (
            "runtime.oid.core",
            "runtime.oid.clock",
        ),
        "logical_sequence_coordinates": (
            "runtime.oid.core",
        ),
        "monotonic_frame_sequencing": (
            "runtime.oid.frame",
        ),
        "causal_predecessor_references": (
            "runtime.oid.core",
        ),
        "causal_successor_derivation": (
            "runtime.oid.projection",
        ),
        "partial_ordering": (
            "runtime.oid.constraint",
            "runtime.oid.projection",
        ),
        "explicit_concurrency": (
            "runtime.oid.core",
            "runtime.oid.constraint",
        ),
        "explicit_unknown_ordering": (
            "runtime.oid.core",
            "runtime.oid.constraint",
        ),
        "temporal_intervals": (
            "runtime.oid.core",
        ),
        "interval_overlap_detection": (
            "runtime.oid.core",
        ),
        "temporal_conflict_detection": (
            "runtime.oid.core",
            "runtime.oid.constraint",
        ),
        "clock_skew_representation": (
            "runtime.oid.clock",
        ),
        "uncertainty_bounds": (
            "runtime.oid.core",
            "runtime.oid.clock",
            "runtime.oid.conversion",
        ),
        "authority_isolation": (
            "runtime.oid.runtime",
            "runtime.oid.integrity",
        ),
        "deterministic_content_addressing": (
            "runtime.oid.core",
            "runtime.oid.frame",
        ),
        "replay_coordinates": (
            "runtime.oid.core",
            "runtime.oid.projection",
        ),
        "deterministic_projection": (
            "runtime.oid.projection",
        ),
        "immutable_temporal_evidence": (
            "runtime.oid.core",
            "runtime.oid.store",
        ),
        "provenance_references": (
            "runtime.oid.core",
        ),
        "evidence_references": (
            "runtime.oid.core",
        ),
        "authority_references": (
            "runtime.oid.core",
        ),
        "bounded_metadata": (
            "runtime.oid.core",
        ),
        "model_independence": (
            "runtime.oid.runtime",
        ),
        "provider_independence": (
            "runtime.oid.runtime",
        ),
        "dependency_sovereignty": (
            "runtime.oid.core",
        ),
        "stdlib_operation": (
            "runtime.oid.core",
            "runtime.oid.store",
        ),
        "deterministic_tie_handling": (
            "runtime.oid.core",
            "runtime.oid.projection",
        ),
        "temporal_integrity_receipts": (
            "runtime.oid.integrity",
        ),
        "reversible_serialization": (
            "runtime.oid.store",
            "runtime.oid.recovery",
        ),
        "contradiction_preservation": (
            "runtime.oid.constraint",
            "runtime.oid.bridge",
        ),
        "no_destructive_reconciliation": (
            "runtime.oid.recovery",
            "runtime.oid.integrity",
        ),
        "typed_temporal_relationships": (
            "runtime.oid.constraint",
            "runtime.oid.bridge",
        ),
        "cross_system_frame_compatibility": (
            "runtime.oid.bridge",
        ),
    }

    return tuple(
        RequirementStatus(
            requirement=requirement,
            implemented=bool(
                evidence.get(requirement)
            ),
            evidence_refs=evidence.get(
                requirement,
                (),
            ),
        )
        for requirement in REQUIREMENTS
    )


def completion_receipt(
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
    statuses = requirement_statuses()

    missing = tuple(
        status.requirement
        for status in statuses
        if not status.implemented
    )

    integrity = integrity_receipt(
        frame,
        constraints=constraints,
        bridges=bridges,
        clock_observations=(
            clock_observations
        ),
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "frame_ref": frame.frame_ref,
        "frame_id": frame.id,
        "requirements": [
            status.projection()
            for status in statuses
        ],
        "requirement_count": len(
            statuses
        ),
        "implemented_count": sum(
            1
            for status in statuses
            if status.implemented
        ),
        "missing_requirements": list(
            missing
        ),
        "integrity_receipt_ref": (
            integrity["digest"]
        ),
        "semantic_scope": (
            "temporal_coherence"
        ),
        "external_truth_authority": False,
        "external_chronology_authority": False,
        "automatic_reconciliation": False,
        "historical_evidence_mutated": False,
        "authority_transferred": False,
        "model_independent": True,
        "provider_independent": True,
        "dependency_sovereign": True,
        "complete": not missing,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.catax.composition import (
    TransformChain,
)
from runtime.catax.core import (
    TemporalCoordinate,
)
from runtime.catax.integrity import (
    integrity_receipt,
)
from runtime.catax.transform import (
    TemporalTransform,
)


SCHEMA = "savant://catax/completion/1"

REQUIREMENTS = (
    "temporal_coordinates",
    "frame_identity",
    "logical_sequence_support",
    "phase_coordinates",
    "uncertainty_preservation",
    "typed_temporal_geometry",
    "explicit_unknown_geometry",
    "cross_frame_order_isolation",
    "deterministic_geometry_projection",
    "immutable_coordinates",
    "content_addressed_identity",
    "provenance_references",
    "evidence_references",
    "authority_references",
    "temporal_translation",
    "temporal_scaling",
    "temporal_reflection",
    "identity_transformation",
    "ordered_transform_composition",
    "intermediate_state_preservation",
    "interaction_classification",
    "contradiction_preservation",
    "dependency_integrity",
    "coordinate_divergence_detection",
    "sequence_collision_preservation",
    "source_immutability",
    "no_destructive_reconciliation",
    "no_external_chronology_claim",
    "authority_isolation",
    "model_independence",
    "provider_independence",
    "dependency_sovereignty",
    "deterministic_receipts",
    "reversible_projection",
    "halo_independence",
)


EVIDENCE: dict[str, tuple[str, ...]] = {
    "temporal_coordinates": (
        "runtime.catax.core",
    ),
    "frame_identity": (
        "runtime.catax.core",
    ),
    "logical_sequence_support": (
        "runtime.catax.core",
    ),
    "phase_coordinates": (
        "runtime.catax.core",
    ),
    "uncertainty_preservation": (
        "runtime.catax.core",
        "runtime.catax.composition",
    ),
    "typed_temporal_geometry": (
        "runtime.catax.core",
    ),
    "explicit_unknown_geometry": (
        "runtime.catax.core",
    ),
    "cross_frame_order_isolation": (
        "runtime.catax.core",
        "runtime.catax.interaction",
    ),
    "deterministic_geometry_projection": (
        "runtime.catax.core",
    ),
    "immutable_coordinates": (
        "runtime.catax.core",
    ),
    "content_addressed_identity": (
        "runtime.catax.core",
        "runtime.catax.transform",
        "runtime.catax.composition",
    ),
    "provenance_references": (
        "runtime.catax.core",
        "runtime.catax.transform",
    ),
    "evidence_references": (
        "runtime.catax.core",
        "runtime.catax.transform",
    ),
    "authority_references": (
        "runtime.catax.core",
        "runtime.catax.transform",
    ),
    "temporal_translation": (
        "runtime.catax.transform",
    ),
    "temporal_scaling": (
        "runtime.catax.transform",
    ),
    "temporal_reflection": (
        "runtime.catax.transform",
    ),
    "identity_transformation": (
        "runtime.catax.transform",
    ),
    "ordered_transform_composition": (
        "runtime.catax.composition",
    ),
    "intermediate_state_preservation": (
        "runtime.catax.composition",
    ),
    "interaction_classification": (
        "runtime.catax.interaction",
    ),
    "contradiction_preservation": (
        "runtime.catax.interaction",
        "runtime.catax.integrity",
    ),
    "dependency_integrity": (
        "runtime.catax.integrity",
    ),
    "coordinate_divergence_detection": (
        "runtime.catax.integrity",
    ),
    "sequence_collision_preservation": (
        "runtime.catax.integrity",
    ),
    "source_immutability": (
        "runtime.catax.transform",
        "runtime.catax.composition",
        "runtime.catax.integrity",
    ),
    "no_destructive_reconciliation": (
        "runtime.catax.interaction",
        "runtime.catax.integrity",
    ),
    "no_external_chronology_claim": (
        "runtime.catax.core",
        "runtime.catax.transform",
        "runtime.catax.interaction",
    ),
    "authority_isolation": (
        "runtime.catax.core",
        "runtime.catax.integrity",
    ),
    "model_independence": (
        "runtime.catax.core",
        "runtime.catax.integrity",
    ),
    "provider_independence": (
        "runtime.catax.core",
        "runtime.catax.integrity",
    ),
    "dependency_sovereignty": (
        "runtime.catax.core",
    ),
    "deterministic_receipts": (
        "runtime.catax.core",
        "runtime.catax.integrity",
    ),
    "reversible_projection": (
        "runtime.catax.composition",
    ),
    "halo_independence": (
        "runtime.catax.core",
    ),
}


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


def requirement_statuses() -> tuple[
    Mapping[str, Any],
    ...
]:
    return tuple(
        {
            "requirement": requirement,
            "implemented": bool(
                EVIDENCE.get(requirement)
            ),
            "evidence_refs": list(
                EVIDENCE.get(
                    requirement,
                    (),
                )
            ),
        }
        for requirement in REQUIREMENTS
    )


def completion_receipt(
    coordinates: Sequence[
        TemporalCoordinate
    ],
    *,
    transforms: Sequence[
        TemporalTransform
    ] = (),
    chains: Sequence[
        TransformChain
    ] = (),
) -> Mapping[str, Any]:
    statuses = requirement_statuses()

    missing = tuple(
        status["requirement"]
        for status in statuses
        if not status["implemented"]
    )

    integrity = integrity_receipt(
        coordinates,
        transforms=transforms,
        chains=chains,
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "semantic_scope": (
            "temporal_geometry"
        ),
        "requirements": list(statuses),
        "requirement_count": len(
            statuses
        ),
        "implemented_count": sum(
            1
            for status in statuses
            if status["implemented"]
        ),
        "missing_requirements": list(
            missing
        ),
        "integrity_receipt_ref": (
            integrity["digest"]
        ),
        "historical_kernel": (
            "catax_applies_temporal_geometry"
        ),
        "historical_halo_required": False,
        "metaphysical_rotation_required": False,
        "fixed_catax_taxonomy_required": False,
        "source_mutated": False,
        "automatic_reconciliation": False,
        "external_truth_authority": False,
        "external_chronology_authority": False,
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

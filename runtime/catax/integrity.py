from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.catax.composition import (
    TransformChain,
)
from runtime.catax.core import (
    TemporalCoordinate,
)
from runtime.catax.interaction import (
    interaction_projection,
)
from runtime.catax.transform import (
    TemporalTransform,
)


SCHEMA = "savant://catax/integrity/1"


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


def inspect_integrity(
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
) -> tuple[IntegrityFinding, ...]:
    findings: list[IntegrityFinding] = []

    coordinate_refs: dict[
        str,
        list[str],
    ] = {}

    for coordinate in coordinates:
        coordinate_refs.setdefault(
            coordinate.coordinate_ref,
            [],
        ).append(coordinate.id)

    for coordinate_ref, ids in sorted(
        coordinate_refs.items()
    ):
        if len(set(ids)) > 1:
            findings.append(
                IntegrityFinding(
                    code=(
                        "coordinate_assertion_divergence"
                    ),
                    subject_ref=coordinate_ref,
                    severity="conflict",
                    details=tuple(
                        sorted(set(ids))
                    ),
                )
            )

    transform_ids = {
        transform.id
        for transform in transforms
    }

    for chain in chains:
        for transform in chain.transforms:
            if (
                transforms
                and transform.id
                not in transform_ids
            ):
                findings.append(
                    IntegrityFinding(
                        code=(
                            "chain_transform_absent"
                        ),
                        subject_ref=chain.id,
                        severity="warning",
                        details=(
                            transform.id,
                        ),
                    )
                )

    frame_sequences: dict[
        tuple[str, int],
        list[str],
    ] = {}

    for coordinate in coordinates:
        if coordinate.sequence is None:
            continue

        key = (
            coordinate.frame_ref,
            coordinate.sequence,
        )

        frame_sequences.setdefault(
            key,
            [],
        ).append(coordinate.id)

    for (
        frame_ref,
        sequence,
    ), ids in sorted(
        frame_sequences.items()
    ):
        if len(ids) > 1:
            findings.append(
                IntegrityFinding(
                    code=(
                        "shared_sequence_coordinate"
                    ),
                    subject_ref=frame_ref,
                    severity="information",
                    details=(
                        str(sequence),
                        *sorted(ids),
                    ),
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
    findings = inspect_integrity(
        coordinates,
        transforms=transforms,
        chains=chains,
    )

    interactions = interaction_projection(
        coordinates
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "coordinate_count": len(
            coordinates
        ),
        "transform_count": len(
            transforms
        ),
        "chain_count": len(chains),
        "finding_count": len(findings),
        "findings": [
            finding.projection()
            for finding in findings
        ],
        "interaction_receipt_ref": (
            interactions["digest"]
        ),
        "temporal_geometry_is_external_truth": False,
        "sequence_collision_is_causal_fact": False,
        "contradictions_preserved": True,
        "unknowns_preserved": True,
        "source_mutated": False,
        "automatic_reconciliation": False,
        "external_chronology_claimed": False,
        "authority_transferred": False,
        "model_independent": True,
        "provider_independent": True,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body

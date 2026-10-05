import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.catax.completion import (
    REQUIREMENTS,
    completion_receipt,
    requirement_statuses,
)
from runtime.catax.composition import (
    TransformChain,
)
from runtime.catax.core import (
    TemporalCoordinate,
)
from runtime.catax.transform import (
    TemporalTransform,
)


def main() -> int:
    coordinate = TemporalCoordinate(
        coordinate_ref="event:completion",
        frame_ref="frame:completion",
        sequence=0,
        phase=0.0,
        uncertainty=0.1,
        provenance_refs=(
            "source:test",
        ),
        evidence_refs=(
            "evidence:test",
        ),
        authority_refs=(
            "authority:test",
        ),
    )

    transform = TemporalTransform(
        transform_ref="transform:test",
        kind="translate",
        offset=1.0,
    )

    chain = TransformChain(
        chain_ref="chain:test",
        transforms=(transform,),
    )

    statuses = requirement_statuses()

    assert len(REQUIREMENTS) == 35
    assert len(statuses) == 35

    assert all(
        status["implemented"]
        for status in statuses
    )

    assert all(
        status["evidence_refs"]
        for status in statuses
    )

    receipt = completion_receipt(
        (coordinate,),
        transforms=(transform,),
        chains=(chain,),
    )

    assert (
        receipt["requirement_count"]
        == 35
    )

    assert (
        receipt["implemented_count"]
        == 35
    )

    assert (
        receipt["missing_requirements"]
        == []
    )

    assert receipt["complete"] is True

    assert (
        receipt["semantic_scope"]
        == "temporal_geometry"
    )

    assert (
        receipt["historical_kernel"]
        == "catax_applies_temporal_geometry"
    )

    assert (
        receipt[
            "historical_halo_required"
        ]
        is False
    )

    assert (
        receipt[
            "metaphysical_rotation_required"
        ]
        is False
    )

    assert (
        receipt[
            "fixed_catax_taxonomy_required"
        ]
        is False
    )

    assert (
        receipt["source_mutated"]
        is False
    )

    assert (
        receipt[
            "automatic_reconciliation"
        ]
        is False
    )

    assert (
        receipt[
            "external_truth_authority"
        ]
        is False
    )

    assert (
        receipt[
            "external_chronology_authority"
        ]
        is False
    )

    assert (
        receipt[
            "authority_transferred"
        ]
        is False
    )

    assert (
        receipt["model_independent"]
        is True
    )

    assert (
        receipt["provider_independent"]
        is True
    )

    assert (
        receipt["dependency_sovereign"]
        is True
    )

    assert (
        receipt["authoritative"]
        is False
    )

    assert (
        receipt["authority_effect"]
        == "none"
    )

    assert len(receipt["digest"]) == 64

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

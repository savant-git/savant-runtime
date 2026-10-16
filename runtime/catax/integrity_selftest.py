import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.catax.composition import (
    TransformChain,
)
from runtime.catax.core import (
    TemporalCoordinate,
)
from runtime.catax.integrity import (
    inspect_integrity,
    integrity_receipt,
)
from runtime.catax.transform import (
    TemporalTransform,
)


def main() -> int:
    first = TemporalCoordinate(
        coordinate_ref="event:a",
        frame_ref="frame:test",
        sequence=1,
        phase=1.0,
    )

    divergent = TemporalCoordinate(
        coordinate_ref="event:a",
        frame_ref="frame:test",
        sequence=2,
        phase=2.0,
    )

    concurrent = TemporalCoordinate(
        coordinate_ref="event:b",
        frame_ref="frame:test",
        sequence=1,
        phase=1.0,
    )

    registered = TemporalTransform(
        transform_ref="transform:a",
        kind="translate",
        offset=1.0,
    )

    absent = TemporalTransform(
        transform_ref="transform:b",
        kind="scale",
        factor=2.0,
    )

    chain = TransformChain(
        chain_ref="chain:test",
        transforms=(
            registered,
            absent,
        ),
    )

    findings = inspect_integrity(
        (
            first,
            divergent,
            concurrent,
        ),
        transforms=(
            registered,
        ),
        chains=(chain,),
    )

    codes = {
        finding.code
        for finding in findings
    }

    assert (
        "coordinate_assertion_divergence"
        in codes
    )

    assert (
        "chain_transform_absent"
        in codes
    )

    assert (
        "shared_sequence_coordinate"
        in codes
    )

    receipt = integrity_receipt(
        (
            first,
            divergent,
            concurrent,
        ),
        transforms=(
            registered,
        ),
        chains=(chain,),
    )

    assert receipt["finding_count"] == 3

    assert (
        receipt[
            "temporal_geometry_is_external_truth"
        ]
        is False
    )

    assert (
        receipt[
            "sequence_collision_is_causal_fact"
        ]
        is False
    )

    assert (
        receipt[
            "contradictions_preserved"
        ]
        is True
    )

    assert (
        receipt["unknowns_preserved"]
        is True
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
            "external_chronology_claimed"
        ]
        is False
    )

    assert (
        receipt["authority_transferred"]
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
        receipt["authoritative"]
        is False
    )

    assert (
        receipt["authority_effect"]
        == "none"
    )

    assert len(receipt["digest"]) == 64

    assert all(
        finding.projection()[
            "automatic_mutation"
        ]
        is False
        for finding in findings
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

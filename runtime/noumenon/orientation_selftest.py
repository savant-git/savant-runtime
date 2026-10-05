import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.orientation import (
    OrientationInfluence,
    derive_orientation,
    orientation_projection,
)


def main() -> int:
    trust_gain = OrientationInfluence(
        significance_ref="significance:a",
        dimension="trust",
        magnitude=0.75,
        weight=1.0,
        provenance_refs=(
            "provenance:a",
        ),
    )

    trust_loss = OrientationInfluence(
        significance_ref="significance:b",
        dimension="trust",
        magnitude=-0.25,
        weight=2.0,
    )

    autonomy = OrientationInfluence(
        significance_ref="significance:c",
        dimension="autonomy",
        magnitude=0.5,
        weight=1.0,
    )

    dimensions = derive_orientation(
        (
            trust_gain,
            autonomy,
            trust_loss,
        )
    )

    assert tuple(
        item.dimension
        for item in dimensions
    ) == (
        "autonomy",
        "trust",
    )

    values = {
        item.dimension: item.magnitude
        for item in dimensions
    }

    assert values["autonomy"] == 0.5
    assert values["trust"] == 0.25

    projection = orientation_projection(
        (
            trust_gain,
            trust_loss,
            autonomy,
        )
    )

    assert (
        projection[
            "orientation_is_derived"
        ]
        is True
    )

    assert (
        projection[
            "orientation_is_authority"
        ]
        is False
    )

    assert (
        projection[
            "orientation_is_external_truth"
        ]
        is False
    )

    assert (
        projection[
            "significance_authority_replaced"
        ]
        is False
    )

    assert (
        projection[
            "becoming_authority_replaced"
        ]
        is False
    )

    assert (
        projection["automatic_action"]
        is False
    )

    assert (
        projection[
            "automatic_reconciliation"
        ]
        is False
    )

    assert (
        projection["source_mutated"]
        is False
    )

    assert (
        projection["authority_transferred"]
        is False
    )

    assert (
        projection["model_independent"]
        is True
    )

    assert (
        projection["provider_independent"]
        is True
    )

    assert (
        projection["deterministic"]
        is True
    )

    assert (
        projection[
            "historical_pivot_kernel"
        ]
        == "directional orientation"
    )

    assert (
        projection[
            "historical_pivot_authority"
        ]
        is False
    )

    assert (
        projection[
            "historical_pivot_runtime_required"
        ]
        is False
    )

    assert (
        projection["authoritative"]
        is False
    )

    assert (
        projection["authority_effect"]
        == "none"
    )

    repeated = orientation_projection(
        (
            autonomy,
            trust_loss,
            trust_gain,
        )
    )

    assert (
        repeated["digest"]
        == projection["digest"]
    )

    assert len(projection["digest"]) == 64

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

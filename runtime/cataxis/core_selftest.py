import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.cataxis.core import (
    Catalyst,
    catalyst_registry,
)


def main() -> int:
    dormant = Catalyst(
        catalyst_ref="catalyst:a",
        pressure=0.25,
        threshold=0.5,
        polarity=-0.25,
        surge_limit=1.0,
        provenance_refs=(
            "source:a",
        ),
    )

    active = Catalyst(
        catalyst_ref="catalyst:b",
        pressure=1.5,
        threshold=1.0,
        polarity=0.75,
        surge_limit=0.25,
        evidence_refs=(
            "evidence:b",
        ),
    )

    assert dormant.activated is False
    assert dormant.excess_pressure == 0.0
    assert dormant.bounded_surge == 0.0

    assert active.activated is True
    assert active.excess_pressure == 0.5
    assert active.bounded_surge == 0.25

    projection = active.projection()

    assert (
        projection[
            "automatic_activation_side_effect"
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

    registry = catalyst_registry(
        (
            active,
            dormant,
        )
    )

    assert (
        registry["catalyst_count"]
        == 2
    )

    assert (
        registry["activated_count"]
        == 1
    )

    assert registry["duplicate_refs"] == []

    assert (
        registry["conflicts_preserved"]
        is True
    )

    assert (
        registry[
            "automatic_reconciliation"
        ]
        is False
    )

    assert (
        registry["source_mutated"]
        is False
    )

    assert (
        registry["authority_transferred"]
        is False
    )

    assert (
        registry["model_independent"]
        is True
    )

    assert (
        registry["provider_independent"]
        is True
    )

    assert (
        registry["authoritative"]
        is False
    )

    assert (
        registry["authority_effect"]
        == "none"
    )

    repeated = catalyst_registry(
        (
            dormant,
            active,
        )
    )

    assert (
        repeated["digest"]
        == registry["digest"]
    )

    assert len(registry["digest"]) == 64

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

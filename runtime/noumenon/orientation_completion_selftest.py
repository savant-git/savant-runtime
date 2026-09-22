import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.orientation_completion import (
    REQUIREMENTS,
    completion_receipt,
    requirement_statuses,
)


def main() -> int:
    statuses = requirement_statuses()

    assert len(REQUIREMENTS) == 22
    assert len(statuses) == 22

    assert all(
        status["satisfied"]
        for status in statuses
    )

    receipt = completion_receipt()

    assert (
        receipt["concept"]
        == "noumenon-orientation"
    )

    assert (
        receipt["requirement_count"]
        == 22
    )

    assert (
        receipt["satisfied_count"]
        == 22
    )

    assert receipt["complete"] is True

    assert (
        receipt["historical_source_concept"]
        == "pivot"
    )

    assert (
        receipt["historical_kernel_preserved"]
        == "directional orientation"
    )

    assert (
        receipt["pivot_independent_substrate"]
        is False
    )

    assert (
        receipt["pivot_authority_created"]
        is False
    )

    assert (
        receipt["pivot_reasoning_owner"]
        is False
    )

    assert (
        receipt["pivot_text_transformer"]
        is False
    )

    assert (
        receipt[
            "obsolete_shard_tables_required"
        ]
        is False
    )

    assert (
        receipt["persona_coupling_required"]
        is False
    )

    assert (
        receipt["noumenon_authority_expanded"]
        is False
    )

    assert (
        receipt[
            "significance_authority_replaced"
        ]
        is False
    )

    assert (
        receipt[
            "becoming_authority_replaced"
        ]
        is False
    )

    assert (
        receipt["external_authority_claimed"]
        is False
    )

    assert (
        receipt["source_mutated"]
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

    assert receipt["deterministic"] is True

    assert (
        receipt["authoritative"]
        is False
    )

    assert (
        receipt["authority_effect"]
        == "none"
    )

    repeated = completion_receipt()

    assert (
        repeated["digest"]
        == receipt["digest"]
    )

    assert len(receipt["digest"]) == 64

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

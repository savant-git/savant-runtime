import math
import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.commitment import (
    active_commitments,
    commitment_gravity,
    commitment_projection,
    create_commitment,
    empty_ledger,
    resolve_commitment,
)


def main() -> int:
    ledger = empty_ledger(
        "noumenon:commitment-selftest"
    )

    ledger = create_commitment(
        ledger,
        subject_ref="self",
        statement="preserve continuity",
        gravity=0.8,
        causal_refs=(
            "experience:commitment-a",
        ),
    )

    first = (
        active_commitments(
            ledger
        )[0]
    )

    ledger = create_commitment(
        ledger,
        subject_ref="relationship:alpha",
        statement="repair rupture",
        gravity=0.5,
        causal_refs=(
            "experience:commitment-b",
        ),
    )

    assert len(
        active_commitments(
            ledger
        )
    ) == 2

    assert math.isclose(
        commitment_gravity(
            ledger
        ),
        0.9,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    ledger = resolve_commitment(
        ledger,
        first.id,
        status="fulfilled",
        resolution_refs=(
            "experience:fulfillment",
        ),
    )

    active = active_commitments(
        ledger
    )

    assert len(active) == 1

    assert (
        active[0].subject_ref
        == "relationship:alpha"
    )

    resolved = tuple(
        commitment
        for commitment
        in ledger.commitments
        if commitment.status
        == "fulfilled"
    )

    assert len(resolved) == 1

    assert (
        resolved[0].predecessor_ref
        == first.id
    )

    assert (
        first.id
        in resolved[0].causal_refs
    )

    assert math.isclose(
        commitment_gravity(
            ledger
        ),
        0.5,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    projection = (
        commitment_projection(
            ledger
        )
    )

    assert (
        projection[
            "active_count"
        ]
        == 1
    )

    assert (
        projection[
            "resolved_count"
        ]
        == 1
    )

    assert (
        projection[
            "authoritative"
        ]
        is False
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

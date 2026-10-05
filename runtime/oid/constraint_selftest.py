import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.oid.constraint import (
    TemporalConstraint,
    constraint_projection,
    detect_constraint_conflicts,
    relation_from_constraints,
)


def main() -> int:
    ab = TemporalConstraint(
        left_ref="event:a",
        right_ref="event:b",
        relation="before",
        evidence_refs=("evidence:ab",),
    )

    bc = TemporalConstraint(
        left_ref="event:b",
        right_ref="event:c",
        relation="before",
        evidence_refs=("evidence:bc",),
    )

    assert (
        relation_from_constraints(
            "event:a",
            "event:c",
            (ab, bc),
        )
        == "before"
    )

    assert (
        relation_from_constraints(
            "event:c",
            "event:a",
            (ab, bc),
        )
        == "after"
    )

    assert (
        relation_from_constraints(
            "event:a",
            "event:d",
            (ab, bc),
        )
        == "unknown"
    )

    concurrent = TemporalConstraint(
        left_ref="event:x",
        right_ref="event:y",
        relation="concurrent",
    )

    assert (
        relation_from_constraints(
            "event:x",
            "event:y",
            (concurrent,),
        )
        == "concurrent"
    )

    ba = TemporalConstraint(
        left_ref="event:b",
        right_ref="event:a",
        relation="before",
        evidence_refs=("evidence:ba",),
    )

    conflicts = (
        detect_constraint_conflicts(
            (ab, ba)
        )
    )

    assert conflicts

    assert any(
        conflict.reason
        == "incompatible_temporal_constraints"
        for conflict in conflicts
    )

    cycle_ca = TemporalConstraint(
        left_ref="event:c",
        right_ref="event:a",
        relation="before",
        evidence_refs=("evidence:ca",),
    )

    cycle_conflicts = (
        detect_constraint_conflicts(
            (
                ab,
                bc,
                cycle_ca,
            )
        )
    )

    assert any(
        conflict.reason
        == "strict_order_cycle"
        for conflict in cycle_conflicts
    )

    projection = constraint_projection(
        (
            ab,
            bc,
            concurrent,
        )
    )

    assert (
        projection[
            "partial_order_preserved"
        ]
        is True
    )

    assert (
        projection[
            "unknown_order_preserved"
        ]
        is True
    )

    assert (
        projection[
            "concurrency_preserved"
        ]
        is True
    )

    assert (
        projection[
            "automatic_reconciliation"
        ]
        is False
    )

    assert (
        projection[
            "authority_transferred"
        ]
        is False
    )

    assert projection["authoritative"] is False

    assert (
        projection["authority_effect"]
        == "none"
    )

    assert len(projection["digest"]) == 64

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

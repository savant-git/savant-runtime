import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.residue import (
    active_residue,
    add_residue,
    empty_ledger,
    residue_pressure,
    residue_projection,
    resolve_residue,
)


def main() -> int:
    ledger = empty_ledger(
        "noumenon:residue-selftest"
    )

    ledger = add_residue(
        ledger,
        kind="relational",
        dimension="trust",
        magnitude=0.6,
        causal_refs=(
            "experience:rupture",
        ),
        evidence_refs=(
            "evidence:rupture",
        ),
    )

    ledger = add_residue(
        ledger,
        kind="gratitude",
        dimension="trust",
        magnitude=0.3,
        causal_refs=(
            "experience:repair",
        ),
    )

    assert len(
        active_residue(ledger)
    ) == 2

    assert (
        residue_pressure(
            ledger,
            dimension="trust",
        )
        == 0.9
    )

    relational = (
        active_residue(
            ledger,
            kind="relational",
        )[0]
    )

    original_id = (
        relational.id
    )

    ledger = resolve_residue(
        ledger,
        original_id,
        resolution_refs=(
            "experience:repair",
        ),
    )

    assert len(
        active_residue(
            ledger,
            kind="relational",
        )
    ) == 0

    assert len(
        active_residue(
            ledger,
            kind="gratitude",
        )
    ) == 1

    assert (
        residue_pressure(
            ledger,
            dimension="trust",
        )
        == 0.3
    )

    assert len(
        ledger.entries
    ) == 2

    resolved = tuple(
        entry
        for entry in ledger.entries
        if entry.resolved
    )

    assert len(resolved) == 1

    assert (
        resolved[0].causal_refs
        == relational.causal_refs
    )

    assert (
        resolved[0]
        .resolution_refs
        == (
            "experience:repair",
        )
    )

    projection = (
        residue_projection(
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

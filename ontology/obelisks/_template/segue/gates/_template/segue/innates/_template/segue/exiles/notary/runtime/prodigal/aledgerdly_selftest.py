#!/usr/bin/env python3

from __future__ import annotations

import sys


ROOT = "/root/savant-runtime"

if ROOT not in sys.path:
    sys.path.insert(
        0,
        ROOT,
    )


from ontology.obelisks._template.segue.gates._template.segue.innates._template.segue.exiles.notary.runtime.prodigal.aledgerdly import (
    AledgerdlyError,
    append_projection,
    entry_from_earmark,
    status,
)
from ontology.obelisks._template.segue.gates._template.segue.innates._template.segue.exiles.notary.runtime.prodigal.earmarkd import (
    from_scrible,
)
from ontology.obelisks._template.segue.gates._template.segue.innates._template.segue.exiles.notary.runtime.prodigal.scrible import (
    shape_atom,
)


def make_earmark(
    subject: str,
    value: int,
) -> dict:
    atom = shape_atom(
        subject=subject,
        material={
            "value": value,
        },
        provenance={
            "source": "selftest",
        },
        lineage={
            "parent": "test:root",
        },
        dependencies=(
            "test:dependency",
        ),
        tags=(
            "test",
        ),
    ).projection()

    return from_scrible(
        atom,
        indices=(
            f"subject:{subject}",
        ),
        metadata={
            "value": value,
        },
        semantic_lattice={
            "kind": "test",
        },
    ).projection()


def main() -> int:
    first_earmark = make_earmark(
        "test:first",
        1,
    )

    second_earmark = make_earmark(
        "test:second",
        2,
    )

    first = entry_from_earmark(
        first_earmark,
        sequence=0,
    )

    second = entry_from_earmark(
        second_earmark,
        sequence=1,
        predecessor_ref=(
            first.entry_id
        ),
    )

    first_projection = (
        first.projection()
    )

    assert first_projection[
        "sequence"
    ] == 0

    assert first_projection[
        "immutable_entry"
    ] is True

    assert first_projection[
        "history_preserved"
    ] is True

    assert first_projection[
        "persistent_append"
    ] is False

    assert first_projection[
        "ledger_mutated"
    ] is False

    assert first_projection[
        "canon_mutated"
    ] is False

    assert first_projection[
        "authority_effect"
    ] == "none"

    ledger = append_projection(
        (
            second,
            first,
        )
    )

    assert ledger[
        "entry_count"
    ] == 2

    assert [
        entry["sequence"]
        for entry in ledger[
            "entries"
        ]
    ] == [
        0,
        1,
    ]

    assert ledger[
        "append_only"
    ] is True

    assert ledger[
        "immutable_history"
    ] is True

    assert ledger[
        "persistent_append"
    ] is False

    assert ledger[
        "ledger_mutated"
    ] is False

    assert ledger[
        "authority_effect"
    ] == "none"

    repeated = append_projection(
        (
            first,
            second,
        )
    )

    assert (
        repeated["digest"]
        == ledger["digest"]
    )

    duplicate = entry_from_earmark(
        second_earmark,
        sequence=0,
    )

    try:
        append_projection(
            (
                first,
                duplicate,
            )
        )
    except AledgerdlyError:
        pass
    else:
        raise AssertionError(
            "duplicate sequence accepted"
        )

    state = status()

    assert state[
        "prodigal"
    ] == "prodigal:aledgerdly"

    assert state[
        "can_verify"
    ] is False

    assert state[
        "can_admit_evidence"
    ] is False

    assert state[
        "can_persist_ledger"
    ] is False

    assert state[
        "can_mutate_ledger"
    ] is False

    assert state[
        "can_mutate_canon"
    ] is False

    assert state[
        "authority_effect"
    ] == "none"

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

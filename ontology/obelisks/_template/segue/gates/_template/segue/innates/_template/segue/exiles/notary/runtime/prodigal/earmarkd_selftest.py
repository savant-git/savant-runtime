#!/usr/bin/env python3

from __future__ import annotations

import sys


ROOT = "/root/savant-runtime"

if ROOT not in sys.path:
    sys.path.insert(
        0,
        ROOT,
    )


from ontology.obelisks._template.segue.gates._template.segue.innates._template.segue.exiles.notary.runtime.prodigal.earmarkd import (
    from_scrible,
    status,
)
from ontology.obelisks._template.segue.gates._template.segue.innates._template.segue.exiles.notary.runtime.prodigal.scrible import (
    shape_atom,
)


def main() -> int:
    atom = shape_atom(
        subject="test:evidence",
        material={
            "claim": "alpha",
            "value": 7,
        },
        provenance={
            "source": "selftest",
        },
        lineage={
            "parent": "test:source",
        },
        dependencies=(
            "beta",
            "alpha",
        ),
        tags=(
            "claim",
            "test",
        ),
    ).projection()

    result = from_scrible(
        atom,
        indices=(
            "subject:test:evidence",
            "kind:claim",
        ),
        metadata={
            "format": "mapping",
            "version": 1,
        },
        semantic_lattice={
            "kind": "claim",
            "domain": "test",
        },
    ).projection()

    assert result[
        "subject"
    ] == "test:evidence"

    assert result[
        "tags"
    ] == [
        "claim",
        "test",
    ]

    assert result[
        "indices"
    ] == [
        "kind:claim",
        "subject:test:evidence",
    ]

    assert result[
        "metadata_extracted"
    ] is True

    assert result[
        "hash_state_condensed"
    ] is True

    assert result[
        "semantic_lattice_extracted"
    ] is True

    assert result[
        "hash_reference_derived"
    ] is True

    assert result[
        "snapshot_derived"
    ] is True

    assert result[
        "verification_decision"
    ] is None

    assert result[
        "evidence_admitted"
    ] is False

    assert result[
        "canon_mutated"
    ] is False

    assert result[
        "ledger_mutated"
    ] is False

    assert result[
        "authority_effect"
    ] == "none"

    repeated = from_scrible(
        atom,
        indices=(
            "kind:claim",
            "subject:test:evidence",
        ),
        metadata={
            "version": 1,
            "format": "mapping",
        },
        semantic_lattice={
            "domain": "test",
            "kind": "claim",
        },
    ).projection()

    assert (
        result["digest"]
        == repeated["digest"]
    )

    assert (
        result["earmark_id"]
        == repeated["earmark_id"]
    )

    assert (
        result[
            "immutable_state_digest"
        ]
        == repeated[
            "immutable_state_digest"
        ]
    )

    state = status()

    assert state[
        "prodigal"
    ] == "prodigal:earmarkd"

    assert state[
        "can_verify"
    ] is False

    assert state[
        "can_admit_evidence"
    ] is False

    assert state[
        "can_mutate_canon"
    ] is False

    assert state[
        "can_mutate_ledger"
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

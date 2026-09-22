#!/usr/bin/env python3

from __future__ import annotations

import sys


ROOT = "/root/savant-runtime"

if ROOT not in sys.path:
    sys.path.insert(
        0,
        ROOT,
    )


from ontology.obelisks._template.segue.gates._template.segue.innates._template.segue.exiles.notary.runtime.prodigal.scrible import (
    normalize_delta,
    shape_atom,
    status,
)


def main() -> int:
    atom = shape_atom(
        subject="test:artifact",
        material={
            "value": 7,
        },
        provenance={
            "source": "selftest",
        },
        lineage={
            "parent": "test:parent",
        },
        dependencies=(
            "beta",
            "alpha",
            "beta",
        ),
        tags=(
            "test",
            "atom",
            "test",
        ),
        metadata={
            "z": 2,
            "a": 1,
        },
    )

    projection = atom.projection()

    assert projection[
        "subject"
    ] == "test:artifact"

    assert projection[
        "dependencies"
    ] == [
        "alpha",
        "beta",
    ]

    assert projection[
        "tags"
    ] == [
        "atom",
        "test",
    ]

    assert projection[
        "complete"
    ] is True

    assert projection[
        "recordable"
    ] is True

    assert projection[
        "held_incomplete"
    ] is False

    assert projection[
        "verification_decision"
    ] is None

    assert projection[
        "evidence_admitted"
    ] is False

    assert projection[
        "canon_mutated"
    ] is False

    assert projection[
        "ledger_mutated"
    ] is False

    assert projection[
        "authority_effect"
    ] == "none"

    repeated = shape_atom(
        subject="test:artifact",
        material={
            "value": 7,
        },
        provenance={
            "source": "selftest",
        },
        lineage={
            "parent": "test:parent",
        },
        dependencies=(
            "alpha",
            "beta",
        ),
        tags=(
            "atom",
            "test",
        ),
        metadata={
            "a": 1,
            "z": 2,
        },
    ).projection()

    assert (
        repeated["digest"]
        == projection["digest"]
    )

    incomplete = shape_atom(
        subject="test:incomplete",
        material=None,
    ).projection()

    assert incomplete[
        "complete"
    ] is False

    assert incomplete[
        "recordable"
    ] is False

    assert incomplete[
        "held_incomplete"
    ] is True

    delta = normalize_delta(
        {
            "z": 2,
            "a": 1,
        }
    )

    assert list(
        delta["delta"]
    ) == [
        "a",
        "z",
    ]

    state = status()

    assert state[
        "prodigal"
    ] == "prodigal:scrible"

    assert state[
        "can_verify"
    ] is False

    assert state[
        "can_admit_evidence"
    ] is False

    assert state[
        "can_attest"
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

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
    entry_from_earmark,
)
from ontology.obelisks._template.segue.gates._template.segue.innates._template.segue.exiles.notary.runtime.prodigal.dogmixa import (
    inspect_pipeline,
    status,
)
from ontology.obelisks._template.segue.gates._template.segue.innates._template.segue.exiles.notary.runtime.prodigal.earmarkd import (
    from_scrible,
)
from ontology.obelisks._template.segue.gates._template.segue.innates._template.segue.exiles.notary.runtime.prodigal.scrible import (
    shape_atom,
)


def build_pipeline() -> tuple[
    dict,
    dict,
    dict,
]:
    scrible = shape_atom(
        subject="test:dogmixa",
        material={
            "value": 11,
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

    earmarkd = from_scrible(
        scrible,
        indices=(
            "kind:test",
        ),
        metadata={
            "version": 1,
        },
        semantic_lattice={
            "domain": "test",
        },
    ).projection()

    aledgerdly = (
        entry_from_earmark(
            earmarkd,
            sequence=0,
        ).projection()
    )

    return (
        scrible,
        earmarkd,
        aledgerdly,
    )


def main() -> int:
    (
        scrible,
        earmarkd,
        aledgerdly,
    ) = build_pipeline()

    result = inspect_pipeline(
        scrible_projection=scrible,
        earmarkd_projection=earmarkd,
        aledgerdly_projection=(
            aledgerdly
        ),
    )

    assert result[
        "consistent"
    ] is True

    assert result[
        "finding_count"
    ] == 0

    assert result[
        "conflict_count"
    ] == 0

    assert result[
        "hold_count"
    ] == 0

    assert result[
        "reconciliation_required"
    ] is False

    assert result[
        "reconciliation_performed"
    ] is False

    assert result[
        "canonical_output_generated"
    ] is False

    assert result[
        "verification_decision"
    ] is None

    assert result[
        "evidence_admitted"
    ] is False

    assert result[
        "automatic_reconciliation"
    ] is False

    assert result[
        "authority_effect"
    ] == "none"

    repeated = inspect_pipeline(
        scrible_projection=scrible,
        earmarkd_projection=earmarkd,
        aledgerdly_projection=(
            aledgerdly
        ),
    )

    assert (
        repeated["digest"]
        == result["digest"]
    )

    divergent_ledger = dict(
        aledgerdly
    )

    divergent_ledger[
        "source_digest"
    ] = "wrong-digest"

    divergent = inspect_pipeline(
        scrible_projection=scrible,
        earmarkd_projection=earmarkd,
        aledgerdly_projection=(
            divergent_ledger
        ),
    )

    assert divergent[
        "consistent"
    ] is False

    assert divergent[
        "conflict_count"
    ] == 1

    assert divergent[
        "reconciliation_required"
    ] is True

    assert divergent[
        "reconciliation_performed"
    ] is False

    assert divergent[
        "canonical_output_generated"
    ] is False

    assert divergent[
        "automatic_conflict_resolution"
    ] is False

    state = status()

    assert state[
        "prodigal"
    ] == "prodigal:dogmixa"

    assert state[
        "can_verify"
    ] is False

    assert state[
        "can_admit_evidence"
    ] is False

    assert state[
        "can_reconcile"
    ] is False

    assert state[
        "can_resolve_conflicts"
    ] is False

    assert state[
        "can_generate_canonical_output"
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

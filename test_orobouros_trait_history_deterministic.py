#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(
    "/root/savant-runtime"
)

ENVOY_RUNTIME = (
    ROOT
    / "ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/"
    "segue/exiles/envoy/runtime"
)


def load_module(
    name: str,
    path: Path,
):
    specification = (
        importlib.util
        .spec_from_file_location(
            name,
            path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise RuntimeError(
            f"cannot load {path}"
        )

    module = (
        importlib.util
        .module_from_spec(
            specification
        )
    )

    sys.modules[
        name
    ] = module

    specification.loader.exec_module(
        module
    )

    return module


def candidate(
    adjudication,
    candidate_id: str,
    correctness: float,
):
    return (
        adjudication
        .AdjudicationCandidate(
            candidate_id=candidate_id,
            trait_id=(
                "analytical_rigor"
            ),
            measurements=(
                (
                    "correctness",
                    correctness,
                ),
            ),
            evidence_ids=(
                "notary-evidence:"
                + candidate_id,
            ),
            verified=True,
            evidence_admitted=True,
            lineage=(
                "experiment:test:history",
            ),
        )
    )


def main() -> int:
    adjudication = load_module(
        "orobouros_history_adjudication",
        ENVOY_RUNTIME
        / "trait_adjudication.py",
    )

    history = load_module(
        "orobouros_trait_history",
        ENVOY_RUNTIME
        / "trait_history.py",
    )

    policy = (
        adjudication
        .AdjudicationPolicy(
            policy_id=(
                "orobouros_trait_default"
            ),
            weights=(
                (
                    "correctness",
                    1.0,
                ),
            ),
            minimum_margin=0.03,
            minimum_dimensions=1,
        )
    )

    candidate_a = candidate(
        adjudication,
        "candidate:a",
        0.90,
    )

    candidate_b = candidate(
        adjudication,
        "candidate:b",
        0.97,
    )

    candidate_c = candidate(
        adjudication,
        "candidate:c",
        0.965,
    )

    establish = (
        adjudication.adjudicate(
            (
                candidate_a,
                candidate_b,
            ),
            policy,
            previous_champion_id=None,
        )
    )

    if (
        establish.decision
        != "establish_champion"
    ):
        raise RuntimeError(
            "expected initial champion"
        )

    if (
        establish.winner_candidate_id
        != "candidate:b"
    ):
        raise RuntimeError(
            "wrong initial champion"
        )

    records = history.append_record(
        (),
        establish.projection(),
    )

    tie_or_insufficient = (
        adjudication.adjudicate(
            (
                candidate_b,
                candidate_c,
            ),
            policy,
            previous_champion_id=(
                "candidate:b"
            ),
        )
    )

    if (
        tie_or_insufficient.decision
        != "no_decision"
    ):
        raise RuntimeError(
            "expected no_decision"
        )

    records = history.append_record(
        records,
        tie_or_insufficient.projection(),
    )

    champions = (
        history.current_champions(
            records
        )
    )

    if (
        champions.get(
            "analytical_rigor"
        )
        != "candidate:b"
    ):
        raise RuntimeError(
            "no_decision changed champion"
        )

    catalog = {
        "candidate:a": {
            "trait_id": (
                "analytical_rigor"
            ),
            "description": (
                "candidate A"
            ),
            "domains": [
                "analysis",
            ],
            "signals": [
                "analyze",
            ],
            "priority": 100,
            "conflicts": [],
        },
        "candidate:b": {
            "trait_id": (
                "analytical_rigor"
            ),
            "description": (
                "candidate B"
            ),
            "domains": [
                "analysis",
                "engineering",
            ],
            "signals": [
                "analyze",
                "evaluate",
            ],
            "priority": 100,
            "conflicts": [],
        },
        "candidate:c": {
            "trait_id": (
                "analytical_rigor"
            ),
            "description": (
                "candidate C"
            ),
            "domains": [
                "analysis",
            ],
            "signals": [
                "evaluate",
            ],
            "priority": 100,
            "conflicts": [],
        },
    }

    projection_a = (
        history
        .accepted_trait_projection(
            records,
            catalog,
        )
    )

    projection_b = (
        history
        .accepted_trait_projection(
            records,
            catalog,
        )
    )

    if projection_a != projection_b:
        raise RuntimeError(
            "accepted trait projection "
            "is not deterministic"
        )

    if (
        projection_a[
            "champions"
        ][
            "analytical_rigor"
        ]
        != "candidate:b"
    ):
        raise RuntimeError(
            "accepted projection selected "
            "wrong champion"
        )

    if (
        len(
            projection_a[
                "accepted_traits"
            ]
        )
        != 1
    ):
        raise RuntimeError(
            "accepted projection count "
            "is incorrect"
        )

    accepted = (
        projection_a[
            "accepted_traits"
        ][0]
    )

    if (
        accepted[
            "candidate_id"
        ]
        != "candidate:b"
    ):
        raise RuntimeError(
            "candidate substance did not "
            "follow champion reference"
        )

    if (
        projection_a[
            "baseline_mutated"
        ]
        is not False
    ):
        raise RuntimeError(
            "baseline mutation detected"
        )

    if (
        projection_a[
            "trait_pool_mutated"
        ]
        is not False
    ):
        raise RuntimeError(
            "trait pool mutation detected"
        )

    if (
        projection_a[
            "persistent_state"
        ]
        is not False
    ):
        raise RuntimeError(
            "Envoy improperly owns "
            "persistence"
        )

    try:
        history.append_record(
            records,
            establish.projection(),
        )
    except history.TraitHistoryError:
        pass
    else:
        raise RuntimeError(
            "decision replay was accepted"
        )

    status = history.status()

    if (
        status[
            "persistence_owner_required"
        ]
        != "coda"
    ):
        raise RuntimeError(
            "Coda persistence ownership "
            "was not preserved"
        )

    print(
        "OROBOUROS TRAIT HISTORY "
        "DETERMINISM: PASS"
    )

    print(
        "history_records="
        + str(
            len(
                records
            )
        )
    )

    print(
        "champion=andidate:b".replace(
            "andidate",
            "candidate",
        )
    )

    print(
        "no_decision_preserved_champion=true"
    )

    print(
        "decision_replay_rejected=true"
    )

    print(
        "accepted_projection_deterministic=true"
    )

    print(
        "baseline_mutated=false"
    )

    print(
        "trait_pool_mutated=false"
    )

    print(
        "persistent_state=false"
    )

    print(
        "persistence_owner_required=coda"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

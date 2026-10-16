#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/ontology/obelisks/"
    "_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/envoy/"
    "runtime/trait_adjudication.py"
)


def load_module():
    specification = (
        importlib.util
        .spec_from_file_location(
            "envoy_trait_adjudication",
            MODULE_PATH,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise RuntimeError(
            "cannot load "
            "trait_adjudication.py"
        )

    module = (
        importlib.util
        .module_from_spec(
            specification
        )
    )

    sys.modules[
        specification.name
    ] = module

    specification.loader.exec_module(
        module
    )

    return module


def candidate(
    module,
    candidate_id: str,
    correctness: float,
    consistency: float,
):
    return module.AdjudicationCandidate(
        candidate_id=candidate_id,
        trait_id="analytical_rigor",
        measurements=(
            (
                "correctness",
                correctness,
            ),
            (
                "internal_consistency",
                consistency,
            ),
        ),
        evidence_ids=(
            "evidence:"
            + candidate_id,
        ),
        verified=True,
        evidence_admitted=True,
        lineage=(
            "experiment:001",
        ),
    )


def main() -> int:
    module = load_module()

    policy = module.AdjudicationPolicy(
        policy_id=(
            "orobouros_trait_default"
        ),
        weights=(
            (
                "correctness",
                1.0,
            ),
            (
                "internal_consistency",
                1.0,
            ),
        ),
        minimum_margin=0.03,
        minimum_dimensions=2,
    )

    champion = candidate(
        module,
        "candidate:a",
        0.90,
        0.90,
    )

    challenger = candidate(
        module,
        "candidate:b",
        0.98,
        0.96,
    )

    decision_a = module.adjudicate(
        (
            champion,
            challenger,
        ),
        policy,
        previous_champion_id=(
            "candidate:a"
        ),
    )

    decision_b = module.adjudicate(
        (
            challenger,
            champion,
        ),
        policy,
        previous_champion_id=(
            "candidate:a"
        ),
    )

    if (
        decision_a.projection()
        != decision_b.projection()
    ):
        raise RuntimeError(
            "adjudication changed "
            "under equivalent ordering"
        )

    if (
        decision_a.decision
        != "challenge_wins"
    ):
        raise RuntimeError(
            "expected challenger win"
        )

    if (
        decision_a
        .winner_candidate_id
        != "candidate:b"
    ):
        raise RuntimeError(
            "incorrect winner"
        )

    tied_a = candidate(
        module,
        "candidate:c",
        0.90,
        0.90,
    )

    tied_b = candidate(
        module,
        "candidate:d",
        0.90,
        0.90,
    )

    tie_decision = (
        module.adjudicate(
            (
                tied_a,
                tied_b,
            ),
            policy,
        )
    )

    if (
        tie_decision.decision
        != "no_decision"
    ):
        raise RuntimeError(
            "tie improperly selected "
            "a champion"
        )

    if (
        tie_decision
        .winner_candidate_id
        is not None
    ):
        raise RuntimeError(
            "tie produced winner"
        )

    try:
        module.AdjudicationCandidate(
            candidate_id=(
                "candidate:invalid"
            ),
            trait_id=(
                "analytical_rigor"
            ),
            measurements=(
                (
                    "correctness",
                    0.9,
                ),
            ),
            evidence_ids=(
                "evidence:invalid",
            ),
            verified=False,
            evidence_admitted=True,
        )
    except module.TraitAdjudicationError:
        pass
    else:
        raise RuntimeError(
            "unverified evidence "
            "entered adjudication"
        )

    status = module.status()

    required = {
        "verification_owner": (
            "exile:notary"
        ),
        "verified_evidence_required": (
            True
        ),
        "admitted_evidence_required": (
            True
        ),
        "deterministic_scoring": True,
        "explicit_no_decision": True,
        "automatic_supersession": (
            False
        ),
        "baseline_mutation": False,
        "crown_mutation": False,
        "authoritative": False,
    }

    for key, expected in (
        required.items()
    ):
        if (
            status.get(
                key
            )
            != expected
        ):
            raise RuntimeError(
                "status mismatch: "
                + key
            )

    print(
        "OROBOUROS TRAIT "
        "ADJUDICATION DETERMINISM: PASS"
    )

    print(
        "winner="
        + str(
            decision_a
            .winner_candidate_id
        )
    )

    print(
        "decision="
        + decision_a.decision
    )

    print(
        "tie_decision="
        + tie_decision.decision
    )

    print(
        "automatic_supersession=false"
    )

    print(
        "verification_owner=exile:notary"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

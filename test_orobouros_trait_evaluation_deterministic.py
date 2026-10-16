#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/ontology/obelisks/"
    "_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/envoy/"
    "runtime/trait_evaluation.py"
)


def load_module():
    specification = (
        importlib.util
        .spec_from_file_location(
            "envoy_trait_evaluation",
            MODULE_PATH,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise RuntimeError(
            "cannot load "
            "trait_evaluation.py"
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


def evaluation(
    module,
    packet_id: str,
    evaluator_id: str,
    correctness: float,
    consistency: float,
):
    return module.BlindEvaluation(
        packet_id=packet_id,
        blind_id="participant:test",
        evaluator_id=evaluator_id,
        scores=(
            (
                "internal_consistency",
                consistency,
            ),
            (
                "correctness",
                correctness,
            ),
        ),
        target_traits=(
            "analytical_rigor",
        ),
        evidence_refs=(
            packet_id,
        ),
    )


def main() -> int:
    module = load_module()

    rows_a = (
        evaluation(
            module,
            "packet:1",
            "evaluator:a",
            0.90,
            0.80,
        ),
        evaluation(
            module,
            "packet:2",
            "evaluator:b",
            0.70,
            1.00,
        ),
    )

    rows_b = tuple(
        reversed(
            rows_a
        )
    )

    aggregates_a = (
        module.aggregate_evaluations(
            rows_a
        )
    )

    aggregates_b = (
        module.aggregate_evaluations(
            rows_b
        )
    )

    if (
        len(
            aggregates_a
        )
        != 1
    ):
        raise RuntimeError(
            "incorrect aggregate count"
        )

    if (
        aggregates_a[
            0
        ].projection()
        != aggregates_b[
            0
        ].projection()
    ):
        raise RuntimeError(
            "aggregation changed "
            "under equivalent ordering"
        )

    aggregate = (
        aggregates_a[
            0
        ]
    )

    measurements = (
        aggregate.measurements()
    )

    if (
        measurements[
            "correctness"
        ][
            "mean"
        ]
        != 0.8
    ):
        raise RuntimeError(
            "correctness mean "
            "is incorrect"
        )

    if (
        measurements[
            "internal_consistency"
        ][
            "mean"
        ]
        != 0.9
    ):
        raise RuntimeError(
            "consistency mean "
            "is incorrect"
        )

    if (
        aggregate.overall_mean()
        != 0.85
    ):
        raise RuntimeError(
            "overall mean "
            "is incorrect"
        )

    trait = (
        module.trait_measurements(
            aggregate,
            "analytical-rigor",
        )
    )

    if (
        trait[
            "trait_id"
        ]
        != "analytical_rigor"
    ):
        raise RuntimeError(
            "trait normalization "
            "failed"
        )

    if (
        trait[
            "provider_identity_exposed"
        ]
        is not False
    ):
        raise RuntimeError(
            "provider identity leaked"
        )

    if (
        trait[
            "evidence_admitted"
        ]
        is not False
    ):
        raise RuntimeError(
            "evidence admitted "
            "without Notary"
        )

    if (
        trait[
            "champion_selected"
        ]
        is not False
    ):
        raise RuntimeError(
            "champion selected "
            "prematurely"
        )

    status = module.status()

    if (
        status[
            "verification_owner"
        ]
        != "exile:notary"
    ):
        raise RuntimeError(
            "verification ownership "
            "mismatch"
        )

    if (
        status[
            "baseline_mutation"
        ]
        or status[
            "crown_mutation"
        ]
    ):
        raise RuntimeError(
            "Orobouros mutation "
            "unexpectedly enabled"
        )

    print(
        "OROBOUROS TRAIT EVALUATION "
        "DETERMINISM: PASS"
    )

    print(
        "aggregate_id="
        + aggregate.aggregate_id
    )

    print(
        "evaluation_count="
        + str(
            len(
                aggregate.evaluations
            )
        )
    )

    print(
        "correctness_mean=0.8"
    )

    print(
        "internal_consistency_mean=0.9"
    )

    print(
        "overall_mean=0.85"
    )

    print(
        "provider_identity_exposed=false"
    )

    print(
        "verification_owner=exile:notary"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

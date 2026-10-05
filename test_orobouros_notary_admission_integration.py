#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(
    "/root/savant-runtime"
)

NOTARY_RUNTIME = (
    ROOT
    / "ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/"
    "segue/exiles/notary/runtime"
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


def main() -> int:
    if str(ROOT) not in sys.path:
        sys.path.insert(
            0,
            str(ROOT),
        )

    notary_assurance = load_module(
        "orobouros_notary_assurance",
        NOTARY_RUNTIME
        / "thryce_assurance.py",
    )

    admission = load_module(
        "orobouros_notary_admission",
        NOTARY_RUNTIME
        / "evidence_admission.py",
    )

    adjudication = load_module(
        "orobouros_trait_adjudication",
        ENVOY_RUNTIME
        / "trait_adjudication.py",
    )

    assurance_instance = (
        notary_assurance
        .NotaryThryceAssurance(
            validators={
                "syntax": (
                    lambda value: {
                        "passed": (
                            isinstance(
                                value,
                                dict,
                            )
                            and bool(
                                value.get(
                                    "candidate_id"
                                )
                            )
                            and bool(
                                value.get(
                                    "trait_id"
                                )
                            )
                            and isinstance(
                                value.get(
                                    "measurements"
                                ),
                                dict,
                            )
                        )
                    }
                )
            }
        )
    )

    candidate_payload = {
        "candidate_id": (
            "candidate:analytical:a"
        ),
        "trait_id": (
            "analytical_rigor"
        ),
        "measurements": {
            "correctness": 0.90,
            "internal_consistency": (
                0.91
            ),
        },
    }

    verification_candidate = (
        assurance_instance.candidate(
            subject=(
                "orobouros-trait:"
                "analytical_rigor"
            ),
            payload=candidate_payload,
            provenance={
                "experiment_id": (
                    "experiment:test:001"
                )
            },
            lineage=[
                "aggregate:test:001",
            ],
            dependencies=[
                "opus:text_inference_route",
            ],
        )
    )

    assurance_projection = (
        assurance_instance.projection(
            verification_candidate,
            validation_layers=(
                "syntax",
            ),
        )
    )

    if (
        assurance_projection[
            "assurance_passed"
        ]
        is not True
    ):
        raise RuntimeError(
            "Notary assurance failed"
        )

    if (
        assurance_projection[
            "verification_decision"
        ]
        is not None
    ):
        raise RuntimeError(
            "Thryce assurance crossed "
            "verification boundary"
        )

    if (
        assurance_projection[
            "evidence_admitted"
        ]
        is not False
    ):
        raise RuntimeError(
            "Thryce assurance crossed "
            "evidence admission boundary"
        )

    admitted_a = (
        admission.admit_assured_candidate(
            assurance_projection,
            evidence_ids=(
                "aggregate:test:001",
            ),
        )
    )

    admitted_b = (
        admission.admit_assured_candidate(
            assurance_projection,
            evidence_ids=(
                "aggregate:test:001",
            ),
        )
    )

    projection_a = (
        admitted_a.projection()
    )

    projection_b = (
        admitted_b.projection()
    )

    if (
        projection_a
        != projection_b
    ):
        raise RuntimeError(
            "admission is not deterministic"
        )

    if (
        projection_a[
            "verified"
        ]
        is not True
    ):
        raise RuntimeError(
            "admitted evidence is not "
            "verified"
        )

    if (
        projection_a[
            "evidence_admitted"
        ]
        is not True
    ):
        raise RuntimeError(
            "Notary did not admit evidence"
        )

    if (
        projection_a[
            "owner"
        ]
        != "exile:notary"
    ):
        raise RuntimeError(
            "admission ownership leaked"
        )

    envoy_candidate = (
        adjudication
        .AdjudicationCandidate(
            candidate_id=(
                candidate_payload[
                    "candidate_id"
                ]
            ),
            trait_id=(
                candidate_payload[
                    "trait_id"
                ]
            ),
            measurements=tuple(
                candidate_payload[
                    "measurements"
                ].items()
            ),
            evidence_ids=(
                projection_a[
                    "evidence_id"
                ],
            ),
            verified=(
                projection_a[
                    "verified"
                ]
            ),
            evidence_admitted=(
                projection_a[
                    "evidence_admitted"
                ]
            ),
            lineage=(
                "aggregate:test:001",
            ),
        )
    )

    if (
        envoy_candidate.verified
        is not True
    ):
        raise RuntimeError(
            "verification state did not "
            "cross Notary boundary"
        )

    if (
        envoy_candidate
        .evidence_admitted
        is not True
    ):
        raise RuntimeError(
            "admission state did not "
            "cross Notary boundary"
        )

    admission_status = (
        admission.status()
    )

    assurance_status = (
        assurance_instance.status()
    )

    if (
        admission_status[
            "verification_owner"
        ]
        != "exile:notary"
    ):
        raise RuntimeError(
            "verification ownership leaked"
        )

    if (
        admission_status[
            "evidence_admission_owner"
        ]
        != "exile:notary"
    ):
        raise RuntimeError(
            "evidence admission ownership "
            "leaked"
        )

    if (
        assurance_status[
            "mechanics_owner"
        ]
        != "living:thryce"
    ):
        raise RuntimeError(
            "Thryce mechanics ownership "
            "changed"
        )

    if (
        assurance_status[
            "thryce_can_verify"
        ]
        is not False
    ):
        raise RuntimeError(
            "Thryce verification boundary "
            "regressed"
        )

    if (
        assurance_status[
            "thryce_can_admit_evidence"
        ]
        is not False
    ):
        raise RuntimeError(
            "Thryce admission boundary "
            "regressed"
        )

    if (
        admission_status[
            "creates_authority"
        ]
        or admission_status[
            "mutates_authority"
        ]
    ):
        raise RuntimeError(
            "admission unexpectedly "
            "creates or mutates authority"
        )

    print(
        "OROBOUROS NOTARY ADMISSION "
        "INTEGRATION: PASS"
    )

    print(
        "evidence_id="
        + projection_a[
            "evidence_id"
        ]
    )

    print(
        "validation_layer=syntax"
    )

    print(
        "assurance_passed=true"
    )

    print(
        "verified=true"
    )

    print(
        "evidence_admitted=true"
    )

    print(
        "mechanics_owner=living:thryce"
    )

    print(
        "verification_owner="
        + admission_status[
            "verification_owner"
        ]
    )

    print(
        "evidence_admission_owner="
        + admission_status[
            "evidence_admission_owner"
        ]
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

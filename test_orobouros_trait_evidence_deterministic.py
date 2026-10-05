#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/ontology/obelisks/"
    "_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/envoy/"
    "runtime/trait_evidence.py"
)


def load_module():
    specification = (
        importlib.util
        .spec_from_file_location(
            "envoy_trait_evidence",
            MODULE_PATH,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise RuntimeError(
            "cannot load trait_evidence.py"
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


def main() -> int:
    module = load_module()

    provenance_a = (
        module.ProviderProvenance(
            provider_id="OpenAI-Text",
            model_id="test-model",
            model_version="v1",
            route="text_inference_route",
            response_id="response-1",
        )
    )

    provenance_b = (
        module.ProviderProvenance(
            provider_id="openai_text",
            model_id="test-model",
            model_version="v1",
            route="text_inference_route",
            response_id="response-1",
        )
    )

    if (
        provenance_a.projection()
        != provenance_b.projection()
    ):
        raise RuntimeError(
            "provider provenance normalization "
            "is not deterministic"
        )

    observation_a = (
        module.TraitObservation(
            trait_id=(
                "Analytical-Rigor"
            ),
            description=(
                "Preserve explicit reasoning "
                "quality."
            ),
            provenance=provenance_a,
            confidence=0.90,
            domains=(
                "research",
                "analysis",
                "analysis",
            ),
            signals=(
                "evaluate",
                "analyze",
            ),
            conflicts=(),
            measurements=(
                (
                    "evidence_discrimination",
                    0.88,
                ),
                (
                    "consistency",
                    0.92,
                ),
            ),
            evidence_refs=(
                "benchmark:test:1",
            ),
            lineage=(
                "experiment:test:1",
            ),
            dependencies=(
                "opus:text_inference_route",
            ),
        )
    )

    observation_b = (
        module.TraitObservation(
            trait_id=(
                "analytical_rigor"
            ),
            description=(
                "Preserve explicit reasoning "
                "quality."
            ),
            provenance=provenance_b,
            confidence=0.90,
            domains=(
                "analysis",
                "research",
            ),
            signals=(
                "analyze",
                "evaluate",
            ),
            conflicts=(),
            measurements=(
                (
                    "consistency",
                    0.92,
                ),
                (
                    "evidence_discrimination",
                    0.88,
                ),
            ),
            evidence_refs=(
                "benchmark:test:1",
            ),
            lineage=(
                "experiment:test:1",
            ),
            dependencies=(
                "opus:text_inference_route",
            ),
        )
    )

    if (
        observation_a.observation_id
        != observation_b.observation_id
    ):
        raise RuntimeError(
            "observation identity changed "
            "under equivalent ordering"
        )

    if (
        observation_a.projection()
        != observation_b.projection()
    ):
        raise RuntimeError(
            "observation projection changed "
            "under equivalent ordering"
        )

    candidate_a = (
        module
        .candidate_from_observations(
            (
                observation_a,
            )
        )
    )

    candidate_b = (
        module
        .candidate_from_observations(
            (
                observation_b,
            )
        )
    )

    if (
        candidate_a.candidate_id
        != candidate_b.candidate_id
    ):
        raise RuntimeError(
            "candidate identity is not "
            "deterministic"
        )

    if (
        candidate_a.projection()
        != candidate_b.projection()
    ):
        raise RuntimeError(
            "candidate projection is not "
            "deterministic"
        )

    packet_a = (
        module.notary_candidate_payload(
            candidate_a
        )
    )

    packet_b = (
        module.notary_candidate_payload(
            candidate_b
        )
    )

    if packet_a != packet_b:
        raise RuntimeError(
            "Notary candidate payload is "
            "not deterministic"
        )

    if (
        packet_a[
            "subject"
        ]
        != (
            "orobouros-trait:"
            "analytical_rigor"
        )
    ):
        raise RuntimeError(
            "Notary subject projection "
            "is incorrect"
        )

    if (
        packet_a[
            "verification_owner"
        ]
        != "exile:notary"
    ):
        raise RuntimeError(
            "verification ownership leaked"
        )

    if (
        packet_a[
            "authoritative"
        ]
        is not False
    ):
        raise RuntimeError(
            "candidate unexpectedly became "
            "authoritative"
        )

    status = module.status()

    expected_status = {
        "owner": "exile:envoy",
        "verification_owner": (
            "exile:notary"
        ),
        "mechanics_owner": (
            "living:thryce"
        ),
        "provider_identity_role": (
            "provenance_only"
        ),
        "candidate_semantics_owner": (
            "exile:envoy"
        ),
        "verification_delegated": True,
        "evidence_admission_local": False,
        "champion_selection_local": False,
        "baseline_mutation": False,
        "crown_mutation": False,
        "persistent_store": False,
        "authoritative": False,
        "authority_effect": "none",
        "rebuildable": True,
    }

    for key, expected in (
        expected_status.items()
    ):
        actual = status.get(
            key
        )

        if actual != expected:
            raise RuntimeError(
                f"status mismatch for "
                f"{key}: "
                f"{actual!r} != "
                f"{expected!r}"
            )

    try:
        module.TraitObservation(
            trait_id="invalid_confidence",
            description=(
                "Invalid confidence test."
            ),
            provenance=provenance_a,
            confidence=1.01,
        )
    except module.TraitEvidenceError:
        pass
    else:
        raise RuntimeError(
            "invalid confidence accepted"
        )

    try:
        module.candidate_from_observations(
            (
                observation_a,
                module.TraitObservation(
                    trait_id=(
                        "coding_precision"
                    ),
                    description=(
                        "Preserve implementation "
                        "precision."
                    ),
                    provenance=(
                        provenance_a
                    ),
                    confidence=0.90,
                ),
            )
        )
    except module.TraitEvidenceError:
        pass
    else:
        raise RuntimeError(
            "mixed-trait candidate accepted"
        )

    print(
        "OROBOUROS TRAIT EVIDENCE "
        "DETERMINISM: PASS"
    )

    print(
        "observation_id="
        + observation_a.observation_id
    )

    print(
        "candidate_id="
        + candidate_a.candidate_id
    )

    print(
        "provider_identity_role="
        + status[
            "provider_identity_role"
        ]
    )

    print(
        "verification_owner="
        + status[
            "verification_owner"
        ]
    )

    print(
        "baseline_mutation="
        + str(
            status[
                "baseline_mutation"
            ]
        ).lower()
    )

    print(
        "crown_mutation="
        + str(
            status[
                "crown_mutation"
            ]
        ).lower()
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

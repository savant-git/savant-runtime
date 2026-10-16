#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/envoy/"
    "runtime/trait_evidence.py"
)


def load_module():
    specification = (
        importlib.util
        .spec_from_file_location(
            "orobouros_candidate_semantic_projection",
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

    provenance = (
        module.ProviderProvenance(
            provider_id="openai_text",
            model_id="test-model",
            model_version="v1",
            route="text_inference_route",
            response_id=(
                "semantic-projection-check"
            ),
        )
    )

    observation_a = (
        module.TraitObservation(
            trait_id="analytical_rigor",
            description=(
                "Preserve explicit reasoning "
                "quality."
            ),
            provenance=provenance,
            confidence=0.90,
            domains=(
                "research",
                "analysis",
            ),
            signals=(
                "evaluate",
            ),
            conflicts=(
                "conversational_naturalness",
            ),
        )
    )

    observation_b = (
        module.TraitObservation(
            trait_id="analytical_rigor",
            description=(
                "Preserve explicit reasoning "
                "quality."
            ),
            provenance=provenance,
            confidence=0.90,
            domains=(
                "engineering",
                "analysis",
            ),
            signals=(
                "analyze",
            ),
            conflicts=(),
        )
    )

    candidate_a = (
        module.candidate_from_observations(
            (
                observation_a,
                observation_b,
            )
        )
    )

    candidate_b = (
        module.candidate_from_observations(
            (
                observation_b,
                observation_a,
            )
        )
    )

    projection_a = (
        candidate_a.projection()
    )

    projection_b = (
        candidate_b.projection()
    )

    if projection_a != projection_b:
        raise RuntimeError(
            "candidate semantic projection "
            "is not deterministic"
        )

    expected_domains = [
        "analysis",
        "engineering",
        "research",
    ]

    if (
        projection_a.get(
            "domains"
        )
        != expected_domains
    ):
        raise RuntimeError(
            "candidate domains projection "
            "is incorrect"
        )

    expected_signals = [
        "analyze",
        "evaluate",
    ]

    if (
        projection_a.get(
            "signals"
        )
        != expected_signals
    ):
        raise RuntimeError(
            "candidate signals projection "
            "is incorrect"
        )

    expected_conflicts = [
        "conversational_naturalness",
    ]

    if (
        projection_a.get(
            "conflicts"
        )
        != expected_conflicts
    ):
        raise RuntimeError(
            "candidate conflicts projection "
            "is incorrect"
        )

    if "priority" in projection_a:
        raise RuntimeError(
            "candidate projection invented "
            "priority"
        )

    if (
        projection_a.get(
            "authoritative"
        )
        is not False
    ):
        raise RuntimeError(
            "candidate projection became "
            "authoritative"
        )

    if (
        projection_a.get(
            "authority_effect"
        )
        != "none"
    ):
        raise RuntimeError(
            "candidate projection changed "
            "authority"
        )

    if (
        projection_a.get(
            "verified"
        )
        is not False
    ):
        raise RuntimeError(
            "candidate bypassed Notary "
            "verification"
        )

    if (
        projection_a.get(
            "evidence_admitted"
        )
        is not False
    ):
        raise RuntimeError(
            "candidate bypassed Notary "
            "evidence admission"
        )

    print(
        "OROBOUROS CANDIDATE SEMANTIC "
        "PROJECTION: PASS"
    )

    print(
        "candidate_id="
        + projection_a[
            "candidate_id"
        ]
    )

    print(
        "domains="
        + ",".join(
            projection_a[
                "domains"
            ]
        )
    )

    print(
        "signals="
        + ",".join(
            projection_a[
                "signals"
            ]
        )
    )

    print(
        "conflicts="
        + ",".join(
            projection_a[
                "conflicts"
            ]
        )
    )

    print(
        "priority_invented=false"
    )

    print(
        "authoritative=false"
    )

    print(
        "verification_owner="
        + projection_a[
            "verification_owner"
        ]
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

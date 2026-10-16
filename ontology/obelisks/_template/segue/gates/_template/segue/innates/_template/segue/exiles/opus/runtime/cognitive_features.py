#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Dict, Mapping


FEATURES = {
    "capability_routing": True,
    "provider_health": True,
    "deterministic_fallback": True,
    "parallel_reasoning": True,
    "specialist_reasoning": True,
    "adversarial_reasoning": True,
    "semantic_consensus": True,
    "adjudication": True,
    "evidence_confidence": True,
    "authority_context": True,
    "lexicon_context": True,
    "kindred_context": True,
    "execution_lineage": True,
    "marginal_value": True,
    "benchmarking": True,
    "ablation": True,
}


def enabled(
    feature: str,
    overrides: Mapping[
        str,
        Any,
    ] | None = None,
) -> bool:
    key = str(
        feature
    ).strip().lower()

    if key not in FEATURES:
        return False

    if (
        overrides
        and key in overrides
    ):
        return bool(
            overrides[key]
        )

    return bool(
        FEATURES[key]
    )


def manifest() -> Dict[str, Any]:
    return {
        "id":
            "opus.cognitive_features",
        "owner":
            "opus",
        "schema":
            "opus.cognitive_features.v1",
        "features":
            dict(FEATURES),
    }

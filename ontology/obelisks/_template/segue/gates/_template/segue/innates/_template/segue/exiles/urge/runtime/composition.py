from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from .convergence import (
    project as project_convergence,
)
from .stability import (
    project as project_stability,
)


schema = (
    "savant://runtime/urge/"
    "convergence-composition/1.0.0"
)

owner = "exile:urge"
prodigal = "prodigal:convergence"


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        _canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def project(
    candidates: Iterable[Any],
) -> dict[str, Any]:
    convergence = (
        project_convergence(
            candidates
        )
    )

    stability = (
        project_stability(
            convergence
        )
    )

    projection = {
        "schema": schema,
        "owner": owner,
        "prodigal": prodigal,
        "authority_effect": "none",
        "projection_only": True,
        "deterministic": True,
        "rebuildable": True,
        "convergence": convergence,
        "stability": stability,
        "lineage": {
            "convergence_digest": (
                convergence[
                    "digest"
                ]
            ),
            "stability_digest": (
                stability[
                    "digest"
                ]
            ),
            "anchor_id": (
                convergence[
                    "anchor"
                ][
                    "id"
                ]
            ),
        },
        "capabilities": {
            "harmonic_resonance": True,
            "conceptual_focus": True,
            "semantic_attractor": True,
            "consensus_projection": True,
            "ambiguity_projection": True,
            "stability_projection": True,
            "separation_projection": True,
            "pairwise_projection": True,
            "provenance_preservation": True,
            "deterministic_replay": True,
        },
        "boundaries": {
            "declares_truth": False,
            "verifies_fact": False,
            "admits_evidence": False,
            "mutates_canon": False,
            "mutates_source": False,
            "creates_authority": False,
            "selects_provider": False,
            "executes_model": False,
        },
    }

    projection[
        "digest"
    ] = _digest(
        projection
    )

    return projection

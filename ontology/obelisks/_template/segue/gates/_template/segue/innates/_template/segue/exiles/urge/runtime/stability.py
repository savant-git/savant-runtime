from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping


schema = (
    "savant://runtime/urge/"
    "prodigal/convergence/"
    "stability/1.0.0"
)

owner = "exile:urge"
prodigal = "prodigal:convergence"


class stability_error(
    ValueError
):
    pass


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


def _finite(
    value: Any,
) -> float:
    try:
        number = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise stability_error(
            "expected numeric value"
        ) from exc

    if not math.isfinite(
        number
    ):
        raise stability_error(
            "expected finite value"
        )

    return number


def project(
    convergence: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        convergence,
        Mapping,
    ):
        raise stability_error(
            "convergence projection "
            "must be an object"
        )

    if convergence.get(
        "prodigal"
    ) != prodigal:
        raise stability_error(
            "unexpected convergence "
            "projection"
        )

    if convergence.get(
        "authority_effect"
    ) != "none":
        raise stability_error(
            "convergence projection "
            "must be non-authoritative"
        )

    ranking = convergence.get(
        "ranking"
    )

    if not isinstance(
        ranking,
        list,
    ) or not ranking:
        raise stability_error(
            "convergence ranking "
            "is required"
        )

    scores = [
        _finite(
            item.get(
                "weighted_score",
                0.0,
            )
        )
        for item in ranking
        if isinstance(
            item,
            Mapping,
        )
    ]

    if not scores:
        raise stability_error(
            "convergence scores "
            "are required"
        )

    top_score = scores[
        0
    ]

    runner_up = (
        scores[
            1
        ]
        if len(
            scores
        ) > 1
        else 0.0
    )

    separation = max(
        0.0,
        top_score
        - runner_up,
    )

    mean_score = sum(
        scores
    ) / len(
        scores
    )

    variance = sum(
        (
            score
            - mean_score
        ) ** 2
        for score in scores
    ) / len(
        scores
    )

    dispersion = math.sqrt(
        variance
    )

    pairwise = convergence.get(
        "pairwise"
    )

    similarities = []

    if isinstance(
        pairwise,
        list,
    ):
        for item in pairwise:
            if isinstance(
                item,
                Mapping,
            ):
                similarities.append(
                    _finite(
                        item.get(
                            "similarity",
                            0.0,
                        )
                    )
                )

    mean_pairwise = (
        sum(
            similarities
        )
        / len(
            similarities
        )
        if similarities
        else 1.0
    )

    candidate_count = int(
        convergence.get(
            "candidate_count",
            len(
                scores
            ),
        )
    )

    consensus = convergence.get(
        "consensus"
    )

    if not isinstance(
        consensus,
        Mapping,
    ):
        consensus = {}

    universal_count = len(
        consensus.get(
            "universal_tokens"
        )
        or []
    )

    majority_count = len(
        consensus.get(
            "majority_tokens"
        )
        or []
    )

    ambiguity = max(
        0.0,
        1.0
        - separation,
    )

    stability = max(
        0.0,
        min(
            1.0,
            (
                top_score
                + mean_pairwise
                + separation
            )
            / 3.0,
        ),
    )

    projection = {
        "schema": schema,
        "owner": owner,
        "prodigal": prodigal,
        "authority_effect": "none",
        "projection_only": True,
        "deterministic": True,
        "rebuildable": True,
        "source_digest": (
            convergence.get(
                "digest"
            )
        ),
        "anchor_id": (
            (
                convergence.get(
                    "anchor"
                )
                or {}
            ).get(
                "id"
            )
        ),
        "candidate_count": (
            candidate_count
        ),
        "signals": {
            "top_score": round(
                top_score,
                12,
            ),
            "runner_up_score": round(
                runner_up,
                12,
            ),
            "separation": round(
                separation,
                12,
            ),
            "mean_score": round(
                mean_score,
                12,
            ),
            "dispersion": round(
                dispersion,
                12,
            ),
            "mean_pairwise_similarity": (
                round(
                    mean_pairwise,
                    12,
                )
            ),
            "ambiguity": round(
                ambiguity,
                12,
            ),
            "stability": round(
                stability,
                12,
            ),
            "universal_token_count": (
                universal_count
            ),
            "majority_token_count": (
                majority_count
            ),
        },
        "interpretation": {
            "stable": (
                stability >= 0.75
            ),
            "ambiguous": (
                ambiguity >= 0.75
            ),
            "strongly_separated": (
                separation >= 0.25
            ),
        },
        "boundaries": {
            "changes_anchor": False,
            "declares_truth": False,
            "verifies_fact": False,
            "mutates_canon": False,
            "admits_evidence": False,
            "creates_authority": False,
        },
    }

    projection[
        "digest"
    ] = _digest(
        projection
    )

    return projection

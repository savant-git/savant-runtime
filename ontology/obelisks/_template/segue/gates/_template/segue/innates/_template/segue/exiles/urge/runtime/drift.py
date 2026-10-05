from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


schema = (
    "savant://runtime/urge/"
    "convergence-drift/1.0.0"
)

owner = "exile:urge"
prodigal = "prodigal:convergence"


class drift_error(
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


def _tokens(
    projection: Mapping[str, Any],
    field: str,
) -> set[str]:
    convergence = projection.get(
        "convergence"
    )

    if not isinstance(
        convergence,
        Mapping,
    ):
        raise drift_error(
            "composition convergence "
            "projection is required"
        )

    consensus = convergence.get(
        "consensus"
    )

    if not isinstance(
        consensus,
        Mapping,
    ):
        return set()

    values = consensus.get(
        field
    )

    if not isinstance(
        values,
        list,
    ):
        return set()

    return {
        str(
            value
        )
        for value in values
        if str(
            value
        ).strip()
    }


def _jaccard(
    left: set[str],
    right: set[str],
) -> float:
    union = left | right

    if not union:
        return 1.0

    return len(
        left & right
    ) / len(
        union
    )


def project(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        previous,
        Mapping,
    ) or not isinstance(
        current,
        Mapping,
    ):
        raise drift_error(
            "both compositions "
            "must be objects"
        )

    for value in (
        previous,
        current,
    ):
        if value.get(
            "prodigal"
        ) != prodigal:
            raise drift_error(
                "unexpected composition"
            )

        if value.get(
            "authority_effect"
        ) != "none":
            raise drift_error(
                "composition must "
                "be non-authoritative"
            )

    previous_anchor = (
        (
            previous.get(
                "convergence"
            )
            or {}
        ).get(
            "anchor"
        )
        or {}
    )

    current_anchor = (
        (
            current.get(
                "convergence"
            )
            or {}
        ).get(
            "anchor"
        )
        or {}
    )

    previous_majority = _tokens(
        previous,
        "majority_tokens",
    )

    current_majority = _tokens(
        current,
        "majority_tokens",
    )

    previous_universal = _tokens(
        previous,
        "universal_tokens",
    )

    current_universal = _tokens(
        current,
        "universal_tokens",
    )

    majority_similarity = _jaccard(
        previous_majority,
        current_majority,
    )

    universal_similarity = _jaccard(
        previous_universal,
        current_universal,
    )

    anchor_changed = (
        previous_anchor.get(
            "id"
        )
        != current_anchor.get(
            "id"
        )
    )

    semantic_drift = (
        (
            1.0
            - majority_similarity
        )
        + (
            1.0
            - universal_similarity
        )
        + (
            1.0
            if anchor_changed
            else 0.0
        )
    ) / 3.0

    projection = {
        "schema": schema,
        "owner": owner,
        "prodigal": prodigal,
        "authority_effect": "none",
        "projection_only": True,
        "deterministic": True,
        "rebuildable": True,
        "lineage": {
            "previous_digest": (
                previous.get(
                    "digest"
                )
            ),
            "current_digest": (
                current.get(
                    "digest"
                )
            ),
        },
        "anchor": {
            "previous_id": (
                previous_anchor.get(
                    "id"
                )
            ),
            "current_id": (
                current_anchor.get(
                    "id"
                )
            ),
            "changed": anchor_changed,
        },
        "consensus": {
            "majority_similarity": (
                round(
                    majority_similarity,
                    12,
                )
            ),
            "universal_similarity": (
                round(
                    universal_similarity,
                    12,
                )
            ),
            "majority_added": sorted(
                current_majority
                - previous_majority
            ),
            "majority_removed": sorted(
                previous_majority
                - current_majority
            ),
            "universal_added": sorted(
                current_universal
                - previous_universal
            ),
            "universal_removed": sorted(
                previous_universal
                - current_universal
            ),
        },
        "semantic_drift": round(
            semantic_drift,
            12,
        ),
        "changed": (
            semantic_drift > 0.0
        ),
        "boundaries": {
            "declares_regression": False,
            "declares_improvement": False,
            "declares_truth": False,
            "verifies_fact": False,
            "mutates_canon": False,
            "creates_authority": False,
        },
    }

    projection[
        "digest"
    ] = _digest(
        projection
    )

    return projection

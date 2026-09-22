from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping


SCHEMA = (
    "savant://runtime/urge/prodigal/"
    "convergence/policy/1.0.0"
)

OWNER = "exile:urge"
PRODIGAL = "prodigal:convergence"


class convergence_policy_error(
    ValueError
):
    pass


DEFAULT_THRESHOLDS = {
    "stable": 0.75,
    "ambiguous": 0.75,
    "strongly_separated": 0.25,
}


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
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


def _number(
    value: Any,
    *,
    name: str,
) -> float:
    if isinstance(
        value,
        bool,
    ):
        raise convergence_policy_error(
            f"{name} must be numeric"
        )

    try:
        number = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise convergence_policy_error(
            f"{name} must be numeric"
        ) from exc

    if not math.isfinite(
        number
    ):
        raise convergence_policy_error(
            f"{name} must be finite"
        )

    if not (
        0.0
        <= number
        <= 1.0
    ):
        raise convergence_policy_error(
            f"{name} must be between 0 and 1"
        )

    return number


def normalize(
    policy: Mapping[str, Any]
    | None = None,
) -> dict[str, Any]:
    source = (
        {}
        if policy is None
        else policy
    )

    if not isinstance(
        source,
        Mapping,
    ):
        raise convergence_policy_error(
            "policy must be an object"
        )

    unknown = (
        set(
            source
        )
        - set(
            DEFAULT_THRESHOLDS
        )
    )

    if unknown:
        raise convergence_policy_error(
            "unknown policy fields: "
            + ", ".join(
                sorted(
                    str(
                        item
                    )
                    for item in unknown
                )
            )
        )

    thresholds = {
        name: _number(
            source.get(
                name,
                default,
            ),
            name=name,
        )
        for (
            name,
            default,
        ) in DEFAULT_THRESHOLDS.items()
    }

    projection = {
        "schema": SCHEMA,
        "owner": OWNER,
        "prodigal": PRODIGAL,
        "authority_effect": "none",
        "projection_only": True,
        "deterministic": True,
        "rebuildable": True,
        "thresholds": thresholds,
        "boundaries": {
            "declares_truth": False,
            "verifies_fact": False,
            "changes_anchor": False,
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


def interpret(
    stability: Mapping[str, Any],
    *,
    policy: Mapping[str, Any]
    | None = None,
) -> dict[str, Any]:
    if not isinstance(
        stability,
        Mapping,
    ):
        raise convergence_policy_error(
            "stability must be an object"
        )

    if (
        stability.get(
            "authority_effect"
        )
        != "none"
    ):
        raise convergence_policy_error(
            "stability must be "
            "non-authoritative"
        )

    signals = stability.get(
        "signals"
    )

    if not isinstance(
        signals,
        Mapping,
    ):
        raise convergence_policy_error(
            "stability signals "
            "are required"
        )

    normalized_policy = normalize(
        policy
    )

    thresholds = (
        normalized_policy[
            "thresholds"
        ]
    )

    stability_score = _number(
        signals.get(
            "stability"
        ),
        name="stability",
    )

    ambiguity = _number(
        signals.get(
            "ambiguity"
        ),
        name="ambiguity",
    )

    separation = _number(
        signals.get(
            "separation"
        ),
        name="separation",
    )

    interpretation = {
        "stable": (
            stability_score
            >= thresholds[
                "stable"
            ]
        ),
        "ambiguous": (
            ambiguity
            >= thresholds[
                "ambiguous"
            ]
        ),
        "strongly_separated": (
            separation
            >= thresholds[
                "strongly_separated"
            ]
        ),
    }

    projection = {
        "schema": SCHEMA,
        "owner": OWNER,
        "prodigal": PRODIGAL,
        "authority_effect": "none",
        "projection_only": True,
        "deterministic": True,
        "rebuildable": True,
        "source_digest": stability.get(
            "digest"
        ),
        "policy_digest": (
            normalized_policy[
                "digest"
            ]
        ),
        "thresholds": dict(
            thresholds
        ),
        "signals": {
            "stability": (
                stability_score
            ),
            "ambiguity": ambiguity,
            "separation": separation,
        },
        "interpretation": (
            interpretation
        ),
        "boundaries": {
            "declares_truth": False,
            "verifies_fact": False,
            "changes_anchor": False,
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

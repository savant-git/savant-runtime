from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from typing import Any, Iterable, Mapping


schema = (
    "savant://runtime/urge/"
    "prodigal/convergence/1.0.0"
)

owner = "exile:urge"
prodigal = "prodigal:convergence"


class convergence_error(
    ValueError
):
    pass


def _string(
    value: Any,
) -> str:
    return str(
        value
        if value is not None
        else ""
    ).strip()


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


def _normalized_tokens(
    value: str,
) -> tuple[str, ...]:
    return tuple(
        token
        for token in (
            part.strip().casefold()
            for part in value.split()
        )
        if token
    )


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


def _candidate(
    value: Any,
    index: int,
) -> dict[str, Any]:
    if isinstance(
        value,
        Mapping,
    ):
        text = _string(
            value.get(
                "text"
            )
            or value.get(
                "content"
            )
            or value.get(
                "value"
            )
        )

        candidate_id = (
            _string(
                value.get(
                    "id"
                )
            )
            or f"candidate:{index}"
        )

        weight_value = value.get(
            "weight",
            1.0,
        )

        provenance = value.get(
            "provenance"
        )

    else:
        text = _string(
            value
        )

        candidate_id = (
            f"candidate:{index}"
        )

        weight_value = 1.0
        provenance = None

    if not text:
        raise convergence_error(
            "candidate text is required"
        )

    try:
        weight = float(
            weight_value
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise convergence_error(
            "candidate weight must "
            "be numeric"
        ) from exc

    if (
        not math.isfinite(
            weight
        )
        or weight < 0
    ):
        raise convergence_error(
            "candidate weight must be "
            "finite and non-negative"
        )

    tokens = _normalized_tokens(
        text
    )

    return {
        "id": candidate_id,
        "text": text,
        "weight": weight,
        "tokens": tokens,
        "token_set": set(
            tokens
        ),
        "provenance": provenance,
    }


def project(
    candidates: Iterable[Any],
) -> dict[str, Any]:
    material = [
        _candidate(
            value,
            index,
        )
        for index, value
        in enumerate(
            candidates
        )
    ]

    if not material:
        raise convergence_error(
            "at least one candidate "
            "is required"
        )

    token_frequency = Counter()

    for candidate in material:
        token_frequency.update(
            candidate[
                "token_set"
            ]
        )

    candidate_count = len(
        material
    )

    universal_tokens = sorted(
        token
        for token, count
        in token_frequency.items()
        if count == candidate_count
    )

    majority_threshold = (
        candidate_count / 2.0
    )

    majority_tokens = sorted(
        token
        for token, count
        in token_frequency.items()
        if count > majority_threshold
    )

    scored = []

    for candidate in material:
        others = [
            other
            for other in material
            if other is not candidate
        ]

        if others:
            resonance = sum(
                _jaccard(
                    candidate[
                        "token_set"
                    ],
                    other[
                        "token_set"
                    ],
                )
                for other in others
            ) / len(
                others
            )

        else:
            resonance = 1.0

        majority_alignment = (
            _jaccard(
                candidate[
                    "token_set"
                ],
                set(
                    majority_tokens
                ),
            )
            if majority_tokens
            else 0.0
        )

        weighted_score = (
            (
                resonance
                + majority_alignment
            )
            / 2.0
        ) * candidate[
            "weight"
        ]

        scored.append(
            {
                "id": candidate[
                    "id"
                ],
                "resonance": round(
                    resonance,
                    12,
                ),
                "majority_alignment": (
                    round(
                        majority_alignment,
                        12,
                    )
                ),
                "weight": candidate[
                    "weight"
                ],
                "weighted_score": round(
                    weighted_score,
                    12,
                ),
            }
        )

    ranked = sorted(
        scored,
        key=lambda item: (
            -item[
                "weighted_score"
            ],
            item[
                "id"
            ],
        ),
    )

    anchor_id = ranked[
        0
    ][
        "id"
    ]

    anchor = next(
        candidate
        for candidate in material
        if candidate[
            "id"
        ] == anchor_id
    )

    pairwise = []

    for left_index, left in enumerate(
        material
    ):
        for right in material[
            left_index + 1:
        ]:
            pairwise.append(
                {
                    "left": left[
                        "id"
                    ],
                    "right": right[
                        "id"
                    ],
                    "similarity": round(
                        _jaccard(
                            left[
                                "token_set"
                            ],
                            right[
                                "token_set"
                            ],
                        ),
                        12,
                    ),
                }
            )

    pairwise.sort(
        key=lambda item: (
            item[
                "left"
            ],
            item[
                "right"
            ],
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
        "historical_kernel": {
            "purpose": (
                "semantic stabilizer "
                "and anchor synthesis"
            ),
            "quirks": {
                "harmonee": (
                    "harmonic resonance "
                    "across tokens"
                ),
                "lens_locker": (
                    "conceptual focal "
                    "length locking"
                ),
                "unifyx": (
                    "unified semantic "
                    "attractor"
                ),
            },
            "quirk_execution": True,
        },
        "candidate_count": (
            candidate_count
        ),
        "anchor": {
            "id": anchor[
                "id"
            ],
            "text": anchor[
                "text"
            ],
            "provenance": anchor[
                "provenance"
            ],
        },
        "consensus": {
            "universal_tokens": (
                universal_tokens
            ),
            "majority_tokens": (
                majority_tokens
            ),
        },
        "ranking": ranked,
        "pairwise": pairwise,
        "boundaries": {
            "declares_truth": False,
            "verifies_fact": False,
            "mutates_canon": False,
            "admits_evidence": False,
            "mutates_candidates": False,
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

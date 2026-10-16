#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, Sequence


def _hash(
    value: Any,
) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(
        raw
    ).hexdigest()


@dataclass(frozen=True)
class Ablation:
    mechanism: str
    full_score: float
    ablated_score: float
    contribution: float
    beneficial: bool

    def as_dict(self) -> Dict[str, Any]:
        return {
            "mechanism":
                self.mechanism,
            "full_score":
                self.full_score,
            "ablated_score":
                self.ablated_score,
            "contribution":
                self.contribution,
            "beneficial":
                self.beneficial,
        }


def evaluate_ablation(
    *,
    mechanism: str,
    full_score: float,
    ablated_score: float,
) -> Ablation:
    full = float(
        full_score
    )

    ablated = float(
        ablated_score
    )

    contribution = (
        full
        - ablated
    )

    return Ablation(
        mechanism=str(
            mechanism
        ),
        full_score=round(
            full,
            6,
        ),
        ablated_score=round(
            ablated,
            6,
        ),
        contribution=round(
            contribution,
            6,
        ),
        beneficial=(
            contribution > 0
        ),
    )


def run_ablation(
    *,
    mechanisms: Sequence[str],
    execute_full: Callable[
        [],
        Mapping[str, Any],
    ],
    execute_without: Callable[
        [str],
        Mapping[str, Any],
    ],
    score_result: Callable[
        [Mapping[str, Any]],
        float,
    ],
) -> Dict[str, Any]:
    unique = tuple(
        dict.fromkeys(
            str(value).strip()
            for value in mechanisms
            if str(value).strip()
        )
    )

    if not unique:
        raise ValueError(
            "ablation requires mechanisms"
        )

    full_result = execute_full()

    if not isinstance(
        full_result,
        Mapping,
    ):
        raise RuntimeError(
            "full execution returned invalid result"
        )

    full_score = float(
        score_result(
            full_result
        )
    )

    results: List[
        Ablation
    ] = []

    raw: Dict[
        str,
        Mapping[str, Any]
    ] = {}

    for mechanism in unique:
        result = execute_without(
            mechanism
        )

        if not isinstance(
            result,
            Mapping,
        ):
            raise RuntimeError(
                f"ablation execution invalid for {mechanism}"
            )

        raw[
            mechanism
        ] = result

        ablated_score = float(
            score_result(
                result
            )
        )

        results.append(
            evaluate_ablation(
                mechanism=mechanism,
                full_score=full_score,
                ablated_score=ablated_score,
            )
        )

    results.sort(
        key=lambda value: (
            -value.contribution,
            value.mechanism,
        )
    )

    report = {
        "schema":
            "opus.cognitive_ablation.v1",
        "full_score":
            round(
                full_score,
                6,
            ),
        "mechanisms": [
            result.as_dict()
            for result in results
        ],
        "all_beneficial":
            all(
                result.beneficial
                for result in results
            ),
        "non_beneficial": [
            result.mechanism
            for result in results
            if not result.beneficial
        ],
    }

    report[
        "report_hash"
    ] = _hash(
        report
    )

    return report

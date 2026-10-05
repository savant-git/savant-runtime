#!/usr/bin/env python3

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import unicodedata
import re
from typing import Any, Iterable, Mapping, Sequence


schema = "savant://runtime/extr/partition/3.0.0"
owner = "extr"
authority_effect = "none"

family_weights = {
    "identity": 8.0,
    "distinctive": 4.0,
    "phrases": 6.0,
}

default_minimum_score = 4.0
default_minimum_confidence = 0.56
default_ambiguity_margin = 0.12
default_context_weight = 0.18
default_title_weight = 1.35


class partition_error(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class runtime_category:
    id: str
    minimum_score: float
    signals: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class runtime_profile:
    categories: tuple[runtime_category, ...]
    catchall: str
    source_digest: str

    @property
    def category_ids(self) -> tuple[str, ...]:
        return tuple(
            category.id
            for category in self.categories
        )

    @property
    def scored_category_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            category.id
            for category in self.categories
            if category.id != self.catchall
        )

    def category(
        self,
        category_id: str,
    ) -> runtime_category:
        for category in self.categories:
            if category.id == category_id:
                return category

        raise partition_error(
            f"unknown runtime category: {category_id}"
        )


@dataclass(frozen=True, slots=True)
class evidence:
    category: str
    raw_score: float
    calibrated_score: float
    confidence: float
    hits: tuple[str, ...]
    families: tuple[str, ...]
    local_rank: int

    def projection(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "raw_score": round(
                self.raw_score,
                6,
            ),
            "calibrated_score": round(
                self.calibrated_score,
                6,
            ),
            "confidence": round(
                self.confidence,
                6,
            ),
            "hits": list(self.hits),
            "families": list(self.families),
            "local_rank": self.local_rank,
        }


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def normalize(value: Any) -> str:
    return unicodedata.normalize(
        "NFKC",
        str(value or ""),
    ).casefold()


def normalize_category_id(
    value: Any,
) -> str:
    candidate = normalize(value).strip()

    candidate = re.sub(
        r"[^a-z0-9_-]+",
        "_",
        candidate,
    )

    candidate = re.sub(
        r"_+",
        "_",
        candidate,
    ).strip("_")

    if not candidate:
        raise partition_error(
            "runtime category id cannot be empty"
        )

    return candidate


def stable_id(
    prefix: str,
    value: Any,
) -> str:
    return f"{prefix}:{digest(value)}"


def load_json(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(value, dict):
        raise partition_error(
            f"expected JSON object: {path}"
        )

    return value


def load_runtime_profile(
    value: Mapping[str, Any],
) -> runtime_profile:
    raw_categories = value.get(
        "categories"
    )

    if not isinstance(
        raw_categories,
        list,
    ):
        raise partition_error(
            "runtime profile requires a categories array"
        )

    if len(raw_categories) < 2:
        raise partition_error(
            "runtime profile requires at least "
            "one category plus catchall"
        )

    raw_catchall = value.get(
        "catchall",
        "catchall",
    )

    catchall = normalize_category_id(
        raw_catchall
    )

    categories: list[
        runtime_category
    ] = []

    seen: set[str] = set()

    for raw in raw_categories:
        if isinstance(raw, str):
            raw = {
                "id": raw,
                "signals": {},
            }

        if not isinstance(raw, Mapping):
            raise partition_error(
                "each runtime category must be "
                "a string or object"
            )

        category_id = normalize_category_id(
            raw.get("id")
        )

        if category_id in seen:
            raise partition_error(
                f"duplicate runtime category: "
                f"{category_id}"
            )

        seen.add(category_id)

        raw_signals = raw.get(
            "signals",
            {},
        )

        if raw_signals is None:
            raw_signals = {}

        if not isinstance(
            raw_signals,
            Mapping,
        ):
            raise partition_error(
                f"signals must be an object: "
                f"{category_id}"
            )

        signals: dict[
            str,
            tuple[str, ...]
        ] = {}

        for family in family_weights:
            raw_values = raw_signals.get(
                family,
                [],
            )

            if raw_values is None:
                raw_values = []

            if not isinstance(
                raw_values,
                list,
            ):
                raise partition_error(
                    f"{category_id}.{family} "
                    f"must be an array"
                )

            signals[family] = tuple(
                sorted(
                    {
                        normalize(item).strip()
                        for item in raw_values
                        if normalize(
                            item
                        ).strip()
                    }
                )
            )

        minimum_score = float(
            raw.get(
                "minimum_score",
                default_minimum_score,
            )
        )

        if minimum_score < 0.0:
            raise partition_error(
                "minimum_score cannot be negative"
            )

        categories.append(
            runtime_category(
                id=category_id,
                minimum_score=minimum_score,
                signals=signals,
            )
        )

    if catchall not in seen:
        raise partition_error(
            "catchall must name one of the "
            "runtime categories"
        )

    for category in categories:
        if (
            category.id == catchall
            and any(
                category.signals.get(
                    family,
                    ()
                )
                for family in family_weights
            )
        ):
            raise partition_error(
                "catchall cannot contain "
                "classification signals"
            )

    normalized_projection = {
        "categories": [
            {
                "id": category.id,
                "minimum_score":
                    category.minimum_score,
                "signals": {
                    family:
                        list(
                            category.signals[
                                family
                            ]
                        )
                    for family
                    in family_weights
                },
            }
            for category in categories
        ],
        "catchall": catchall,
    }

    return runtime_profile(
        categories=tuple(categories),
        catchall=catchall,
        source_digest=digest(
            normalized_projection
        ),
    )


def load_runtime_profile_file(
    path: Path,
) -> runtime_profile:
    return load_runtime_profile(
        load_json(path)
    )


def read_jsonl(
    path: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    with path.open(
        "r",
        encoding="utf-8",
        errors="replace",
    ) as handle:
        for line_number, line in enumerate(
            handle,
            1,
        ):
            candidate = line.strip()

            if not candidate:
                continue

            try:
                value = json.loads(
                    candidate
                )
            except Exception as exc:
                raise partition_error(
                    f"invalid JSONL at line "
                    f"{line_number}: {exc}"
                ) from exc

            if isinstance(value, dict):
                rows.append(value)

    return rows


def row_text(
    row: Mapping[str, Any],
) -> str:
    candidates = (
        row.get("text"),
        row.get("content"),
        row.get("message"),
    )

    for candidate in candidates:
        if isinstance(
            candidate,
            str,
        ):
            return candidate

        if isinstance(
            candidate,
            (
                Mapping,
                list,
                tuple,
            ),
        ):
            return canonical_json(
                candidate
            )

    return ""


def row_title(
    row: Mapping[str, Any],
) -> str:
    for key in (
        "conversation_title",
        "title",
        "chat_title",
    ):
        value = row.get(key)

        if isinstance(value, str):
            return value

    conversation = row.get(
        "conversation"
    )

    if isinstance(
        conversation,
        Mapping,
    ):
        value = conversation.get(
            "title"
        )

        if isinstance(value, str):
            return value

    return ""


def conversation_identity(
    row: Mapping[str, Any],
) -> str:
    for key in (
        "conversation_id",
        "chat_id",
        "thread_id",
    ):
        value = row.get(key)

        if value:
            return str(value)

    conversation = row.get(
        "conversation"
    )

    if isinstance(
        conversation,
        Mapping,
    ):
        for key in (
            "id",
            "conversation_id",
        ):
            value = conversation.get(
                key
            )

            if value:
                return str(value)

    source = row.get("source")

    if isinstance(
        source,
        Mapping,
    ):
        value = source.get(
            "conversation_id"
        )

        if value:
            return str(value)

    return stable_id(
        "conversation",
        {
            "title":
                row_title(row),
            "source":
                row.get("source"),
        },
    )


def message_identity(
    row: Mapping[str, Any],
) -> str:
    for key in (
        "message_id",
        "id",
        "node_id",
        "fingerprint",
    ):
        value = row.get(key)

        if value:
            return str(value)

    return stable_id(
        "message",
        {
            "conversation":
                conversation_identity(
                    row
                ),
            "text":
                row_text(row),
            "timestamp":
                row.get(
                    "timestamp"
                ),
            "role":
                row.get("role"),
        },
    )


def corpus_document_frequency(
    rows: Iterable[
        Mapping[str, Any]
    ],
    profile: runtime_profile,
) -> tuple[
    int,
    Counter[str],
]:
    frequency: Counter[str] = Counter()
    count = 0

    all_signals = {
        signal
        for category
        in profile.categories
        if category.id
        != profile.catchall
        for values
        in category.signals.values()
        for signal in values
    }

    for row in rows:
        count += 1

        normalized = normalize(
            " ".join(
                (
                    row_title(row),
                    row_text(row),
                )
            )
        )

        for signal in all_signals:
            if signal in normalized:
                frequency[
                    signal
                ] += 1

    return count, frequency


def rarity(
    signal: str,
    *,
    document_count: int,
    frequency: Mapping[
        str,
        int,
    ],
) -> float:
    df = int(
        frequency.get(
            signal,
            0,
        )
    )

    if document_count <= 0:
        return 1.0

    return math.log(
        1.0
        + (
            document_count
            - df
            + 0.5
        )
        / (
            df
            + 0.5
        )
    )


def signal_occurrences(
    normalized_text: str,
    signal: str,
) -> int:
    if not signal:
        return 0

    return normalized_text.count(
        signal
    )


def score_local(
    row: Mapping[str, Any],
    *,
    profile: runtime_profile,
    document_count: int,
    frequency: Mapping[
        str,
        int,
    ],
) -> dict[
    str,
    dict[str, Any],
]:
    text = normalize(
        row_text(row)
    )

    title = normalize(
        row_title(row)
    )

    scores: dict[
        str,
        dict[str, Any],
    ] = {}

    for category in profile.categories:
        if (
            category.id
            == profile.catchall
        ):
            continue

        raw_score = 0.0
        hits: set[str] = set()
        hit_families: set[
            str
        ] = set()

        for (
            family,
            values,
        ) in category.signals.items():
            family_weight = (
                family_weights[
                    family
                ]
            )

            for signal in values:
                text_count = min(
                    signal_occurrences(
                        text,
                        signal,
                    ),
                    3,
                )

                title_count = min(
                    signal_occurrences(
                        title,
                        signal,
                    ),
                    2,
                )

                if (
                    text_count == 0
                    and title_count == 0
                ):
                    continue

                signal_rarity = rarity(
                    signal,
                    document_count=
                        document_count,
                    frequency=frequency,
                )

                contribution = (
                    family_weight
                    * signal_rarity
                    * (
                        1.0
                        + math.log1p(
                            text_count
                        )
                    )
                )

                if title_count:
                    contribution += (
                        family_weight
                        * signal_rarity
                        * default_title_weight
                        * title_count
                    )

                raw_score += contribution

                hits.add(signal)
                hit_families.add(
                    family
                )

        scores[
            category.id
        ] = {
            "raw_score":
                raw_score,
            "hits":
                tuple(
                    sorted(hits)
                ),
            "families":
                tuple(
                    sorted(
                        hit_families
                    )
                ),
        }

    return scores


def softmax(
    values: Mapping[
        str,
        float,
    ],
) -> dict[str, float]:
    if not values:
        return {}

    maximum = max(
        values.values()
    )

    exponentials = {
        key: math.exp(
            min(
                60.0,
                value - maximum,
            )
        )
        for key, value
        in values.items()
    }

    denominator = sum(
        exponentials.values()
    )

    if denominator <= 0.0:
        return {
            key: 0.0
            for key in values
        }

    return {
        key:
            value
            / denominator
        for key, value
        in exponentials.items()
    }


def conversation_priors(
    rows: list[
        dict[str, Any]
    ],
    local_scores: list[
        dict[
            str,
            dict[str, Any],
        ]
    ],
    profile: runtime_profile,
) -> dict[
    str,
    dict[str, float],
]:
    grouped: dict[
        str,
        Counter[str],
    ] = defaultdict(Counter)

    for row, scores in zip(
        rows,
        local_scores,
        strict=True,
    ):
        conversation = (
            conversation_identity(
                row
            )
        )

        ordered = sorted(
            (
                (
                    float(
                        data[
                            "raw_score"
                        ]
                    ),
                    category,
                )
                for category, data
                in scores.items()
            ),
            reverse=True,
        )

        if not ordered:
            continue

        winner_score, winner = (
            ordered[0]
        )

        runner_score = (
            ordered[1][0]
            if len(ordered) > 1
            else 0.0
        )

        if (
            winner_score > 0.0
            and winner_score
            >= runner_score * 1.35
        ):
            grouped[
                conversation
            ][winner] += 1

    priors: dict[
        str,
        dict[str, float],
    ] = {}

    for (
        conversation,
        counts,
    ) in grouped.items():
        total = sum(
            counts.values()
        )

        priors[
            conversation
        ] = {
            category_id: (
                counts.get(
                    category_id,
                    0,
                )
                / total
            )
            for category_id
            in profile.scored_category_ids
        } if total else {}

    return priors


def classify_rows(
    rows: list[
        dict[str, Any]
    ],
    profile: runtime_profile,
) -> list[
    dict[str, Any]
]:
    (
        document_count,
        frequency,
    ) = corpus_document_frequency(
        rows,
        profile,
    )

    local_scores = [
        score_local(
            row,
            profile=profile,
            document_count=
                document_count,
            frequency=frequency,
        )
        for row in rows
    ]

    priors = conversation_priors(
        rows,
        local_scores,
        profile,
    )

    results: list[
        dict[str, Any]
    ] = []

    for row, scores in zip(
        rows,
        local_scores,
        strict=True,
    ):
        conversation = (
            conversation_identity(
                row
            )
        )

        prior = priors.get(
            conversation,
            {},
        )

        calibrated: dict[
            str,
            float,
        ] = {}

        for (
            category_id,
            data,
        ) in scores.items():
            raw_score = float(
                data[
                    "raw_score"
                ]
            )

            context = float(
                prior.get(
                    category_id,
                    0.0,
                )
            )

            calibrated[
                category_id
            ] = (
                raw_score
                + (
                    raw_score
                    * default_context_weight
                    * context
                )
            )

        probabilities = softmax(
            {
                category_id:
                    math.log1p(
                        max(
                            0.0,
                            score,
                        )
                    )
                for (
                    category_id,
                    score,
                )
                in calibrated.items()
            }
        )

        ordered = sorted(
            calibrated,
            key=lambda category_id: (
                -calibrated[
                    category_id
                ],
                category_id,
            ),
        )

        candidate = (
            ordered[0]
            if ordered
            else profile.catchall
        )

        winner_score = (
            calibrated.get(
                candidate,
                0.0,
            )
        )

        runner = (
            ordered[1]
            if len(ordered) > 1
            else None
        )

        runner_score = (
            calibrated.get(
                runner,
                0.0,
            )
            if runner
            else 0.0
        )

        winner_confidence = (
            probabilities.get(
                candidate,
                0.0,
            )
        )

        margin = (
            (
                winner_score
                - runner_score
            )
            / max(
                winner_score,
                1.0,
            )
        )

        minimum_score = (
            profile.category(
                candidate
            ).minimum_score
            if candidate
            != profile.catchall
            else 0.0
        )

        accepted = (
            candidate
            != profile.catchall
            and winner_score
            >= minimum_score
            and winner_confidence
            >= default_minimum_confidence
            and (
                runner is None
                or margin
                >= default_ambiguity_margin
            )
        )

        category_id = (
            candidate
            if accepted
            else profile.catchall
        )

        ranked_evidence = []

        for rank, contender in enumerate(
            ordered,
            1,
        ):
            data = scores[
                contender
            ]

            ranked_evidence.append(
                evidence(
                    category=contender,
                    raw_score=float(
                        data[
                            "raw_score"
                        ]
                    ),
                    calibrated_score=float(
                        calibrated[
                            contender
                        ]
                    ),
                    confidence=float(
                        probabilities.get(
                            contender,
                            0.0,
                        )
                    ),
                    hits=tuple(
                        data["hits"]
                    ),
                    families=tuple(
                        data[
                            "families"
                        ]
                    ),
                    local_rank=rank,
                ).projection()
            )

        source_digest = digest(
            row
        )

        partition_projection = {
            "schema": schema,
            "owner": owner,
            "authority_effect":
                authority_effect,
            "authoritative": False,
            "rebuildable": True,
            "category": category_id,
            "accepted": accepted,
            "candidate": candidate,
            "score": round(
                winner_score,
                6,
            ),
            "confidence": round(
                winner_confidence,
                6,
            ),
            "margin": round(
                margin,
                6,
            ),
            "catchall":
                profile.catchall,
            "conversation_id":
                conversation,
            "message_id":
                message_identity(row),
            "runtime_profile_digest":
                profile.source_digest,
            "source_digest":
                source_digest,
            "evidence":
                ranked_evidence,
        }

        partition_projection[
            "classification_digest"
        ] = digest(
            partition_projection
        )

        projected = dict(row)

        projected[
            "extr_partition"
        ] = partition_projection

        results.append(
            projected
        )

    return results


def datrix_projection(
    row: Mapping[str, Any],
) -> dict[str, Any]:
    partition = row.get(
        "extr_partition"
    )

    if not isinstance(
        partition,
        Mapping,
    ):
        raise partition_error(
            "datrix projection requires "
            "extr_partition"
        )

    source_digest = partition.get(
        "source_digest"
    )

    classification_digest = (
        partition.get(
            "classification_digest"
        )
    )

    category = partition.get(
        "category"
    )

    if not source_digest:
        raise partition_error(
            "extr_partition requires "
            "source_digest"
        )

    if not classification_digest:
        raise partition_error(
            "extr_partition requires "
            "classification_digest"
        )

    if not category:
        raise partition_error(
            "extr_partition requires category"
        )

    projection = {
        "schema":
            "savant://runtime/extr/"
            "datrix-projection/1.0.0",
        "owner": owner,
        "authority_effect":
            authority_effect,
        "authoritative": False,
        "rebuildable": True,
        "storage_selected": False,
        "source_digest":
            source_digest,
        "classification_digest":
            classification_digest,
        "category":
            category,
        "accepted":
            bool(
                partition.get(
                    "accepted",
                    False,
                )
            ),
        "conversation_id":
            partition.get(
                "conversation_id"
            ),
        "message_id":
            partition.get(
                "message_id"
            ),
        "runtime_profile_digest":
            partition.get(
                "runtime_profile_digest"
            ),
        "evidence":
            partition.get(
                "evidence",
                [],
            ),
    }

    projection[
        "projection_digest"
    ] = digest(
        projection
    )

    return projection


def selftest() -> dict[str, Any]:
    profile = load_runtime_profile(
        {
            "categories": [
                {
                    "id": "alpha",
                    "minimum_score": 1.0,
                    "signals": {
                        "identity": [
                            "alpha_unique"
                        ]
                    },
                },
                {
                    "id": "beta",
                    "minimum_score": 1.0,
                    "signals": {
                        "identity": [
                            "beta_unique"
                        ]
                    },
                },
                {
                    "id": "other",
                },
            ],
            "catchall": "other",
        }
    )

    rows = [
        {
            "id": "one",
            "text": "alpha_unique",
        },
        {
            "id": "two",
            "text": "beta_unique",
        },
        {
            "id": "three",
            "text": "unrelated",
        },
    ]

    first = classify_rows(
        [
            dict(row)
            for row in rows
        ],
        profile,
    )

    second = classify_rows(
        [
            dict(row)
            for row in rows
        ],
        profile,
    )

    categories = [
        row[
            "extr_partition"
        ][
            "category"
        ]
        for row in first
    ]

    projections = [
        datrix_projection(row)
        for row in first
    ]

    checks = {
        "three_records":
            len(first) == 3,
        "runtime_categories":
            categories
            == [
                "alpha",
                "beta",
                "other",
            ],
        "deterministic_classification":
            first == second,
        "partition_non_authoritative":
            all(
                row[
                    "extr_partition"
                ][
                    "authoritative"
                ]
                is False
                for row in first
            ),
        "partition_rebuildable":
            all(
                row[
                    "extr_partition"
                ][
                    "rebuildable"
                ]
                is True
                for row in first
            ),
        "datrix_projection_count":
            len(projections) == 3,
        "datrix_non_authoritative":
            all(
                projection[
                    "authoritative"
                ]
                is False
                for projection
                in projections
            ),
        "datrix_rebuildable":
            all(
                projection[
                    "rebuildable"
                ]
                is True
                for projection
                in projections
            ),
        "no_datrix_storage":
            all(
                projection[
                    "storage_selected"
                ]
                is False
                for projection
                in projections
            ),
        "authority_none":
            all(
                projection[
                    "authority_effect"
                ]
                == "none"
                for projection
                in projections
            ),
        "projection_deterministic":
            projections
            == [
                datrix_projection(row)
                for row in second
            ],
    }

    return {
        "schema":
            "savant://runtime/extr/"
            "partition-selftest/3.0.0",
        "ok":
            all(
                checks.values()
            ),
        "checks":
            checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="extr-partition"
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
    )

    args = parser.parse_args()

    if args.selftest:
        result = selftest()

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
        )

        return (
            0
            if result["ok"]
            else 1
        )

    raise partition_error(
        "no operation selected"
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

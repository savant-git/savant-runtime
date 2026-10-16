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
import re
import tempfile
import unicodedata
from typing import Any, Iterable, Mapping


schema = "savant://runtime/extr/partition/2.0.0"
owner = "extr"
authority_effect = "none"

category_order = (
    "savant",
    "viscera",
    "low_life",
    "mayorgate",
    "catchall",
)

family_weights = {
    "identity": 8.0,
    "distinctive": 4.0,
    "phrases": 6.0,
}

default_minimum_confidence = 0.56
default_ambiguity_margin = 0.12
default_context_weight = 0.18
default_title_weight = 1.35


class partition_error(RuntimeError):
    pass


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
            "raw_score": round(self.raw_score, 6),
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


def tokens(value: Any) -> tuple[str, ...]:
    return tuple(
        re.findall(
            r"[a-z0-9_]+",
            normalize(value),
        )
    )


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}:{digest(value)}"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(value, dict):
        raise partition_error(
            f"expected JSON object: {path}"
        )

    return value


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
                value = json.loads(candidate)
            except Exception as exc:
                raise partition_error(
                    f"invalid JSONL at line "
                    f"{line_number}: {exc}"
                ) from exc

            if isinstance(value, dict):
                rows.append(value)

    return rows


def row_text(row: Mapping[str, Any]) -> str:
    candidates = (
        row.get("text"),
        row.get("content"),
        row.get("message"),
    )

    for candidate in candidates:
        if isinstance(candidate, str):
            return candidate

    return ""


def row_title(row: Mapping[str, Any]) -> str:
    for key in (
        "conversation_title",
        "title",
        "chat_title",
    ):
        value = row.get(key)

        if isinstance(value, str):
            return value

    conversation = row.get("conversation")

    if isinstance(conversation, Mapping):
        value = conversation.get("title")

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

    conversation = row.get("conversation")

    if isinstance(conversation, Mapping):
        for key in ("id", "conversation_id"):
            value = conversation.get(key)

            if value:
                return str(value)

    source = row.get("source")

    if isinstance(source, Mapping):
        value = source.get("conversation_id")

        if value:
            return str(value)

    return stable_id(
        "conversation",
        {
            "title": row_title(row),
            "source": row.get("source"),
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
                conversation_identity(row),
            "text": row_text(row),
            "timestamp": row.get("timestamp"),
            "role": row.get("role"),
        },
    )


def profile_signals(
    profiles: Mapping[str, Any],
) -> dict[
    str,
    dict[str, tuple[str, ...]]
]:
    projects = profiles.get(
        "projects",
        {},
    )

    if not isinstance(projects, Mapping):
        raise partition_error(
            "projects profile is invalid"
        )

    result: dict[
        str,
        dict[str, tuple[str, ...]]
    ] = {}

    for category in category_order:
        if category == "catchall":
            continue

        profile = projects.get(
            category,
            {},
        )

        if not isinstance(profile, Mapping):
            profile = {}

        raw_signals = profile.get(
            "signals",
            {},
        )

        if isinstance(raw_signals, list):
            raw_signals = {
                "distinctive": raw_signals
            }

        if not isinstance(
            raw_signals,
            Mapping,
        ):
            raw_signals = {}

        families: dict[
            str,
            tuple[str, ...]
        ] = {}

        for family in family_weights:
            values = raw_signals.get(
                family,
                [],
            )

            if not isinstance(values, list):
                values = []

            families[family] = tuple(
                sorted(
                    {
                        normalize(value).strip()
                        for value in values
                        if normalize(value).strip()
                    }
                )
            )

        result[category] = families

    return result


def corpus_document_frequency(
    rows: Iterable[Mapping[str, Any]],
    signals: Mapping[
        str,
        Mapping[str, tuple[str, ...]]
    ],
) -> tuple[int, Counter[str]]:
    frequency: Counter[str] = Counter()
    count = 0

    all_signals = {
        signal
        for families in signals.values()
        for values in families.values()
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
                frequency[signal] += 1

    return count, frequency


def rarity(
    signal: str,
    *,
    document_count: int,
    frequency: Mapping[str, int],
) -> float:
    df = int(
        frequency.get(signal, 0)
    )

    return (
        math.log(
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
        if document_count > 0
        else 1.0
    )


def signal_occurrences(
    normalized_text: str,
    signal: str,
) -> int:
    if not signal:
        return 0

    return normalized_text.count(signal)


def score_local(
    row: Mapping[str, Any],
    *,
    signals: Mapping[
        str,
        Mapping[str, tuple[str, ...]]
    ],
    document_count: int,
    frequency: Mapping[str, int],
) -> dict[str, dict[str, Any]]:
    text = normalize(row_text(row))
    title = normalize(row_title(row))

    scores: dict[
        str,
        dict[str, Any]
    ] = {}

    for category, families in signals.items():
        raw_score = 0.0
        hits: set[str] = set()
        hit_families: set[str] = set()

        for family, values in families.items():
            family_weight = family_weights[
                family
            ]

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
                    document_count=document_count,
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
                hit_families.add(family)

        scores[category] = {
            "raw_score": raw_score,
            "hits": tuple(sorted(hits)),
            "families": tuple(
                sorted(hit_families)
            ),
        }

    return scores


def softmax(
    values: Mapping[str, float],
) -> dict[str, float]:
    if not values:
        return {}

    maximum = max(values.values())

    exponentials = {
        key: math.exp(
            min(
                60.0,
                value - maximum,
            )
        )
        for key, value in values.items()
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
        key: value / denominator
        for key, value
        in exponentials.items()
    }


def conversation_priors(
    rows: list[dict[str, Any]],
    local_scores: list[
        dict[str, dict[str, Any]]
    ],
) -> dict[str, dict[str, float]]:
    grouped: dict[
        str,
        Counter[str]
    ] = defaultdict(Counter)

    for row, scores in zip(
        rows,
        local_scores,
        strict=True,
    ):
        conversation = (
            conversation_identity(row)
        )

        ordered = sorted(
            (
                (
                    data["raw_score"],
                    category,
                )
                for category, data
                in scores.items()
            ),
            reverse=True,
        )

        if not ordered:
            continue

        winner_score, winner = ordered[0]

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
        dict[str, float]
    ] = {}

    for conversation, counts in (
        grouped.items()
    ):
        total = sum(counts.values())

        priors[conversation] = {
            category: (
                counts.get(
                    category,
                    0,
                )
                / total
            )
            for category in signals_categories()
        } if total else {}

    return priors


def signals_categories() -> tuple[str, ...]:
    return tuple(
        category
        for category in category_order
        if category != "catchall"
    )


def classify_rows(
    rows: list[dict[str, Any]],
    profiles: Mapping[str, Any],
) -> list[dict[str, Any]]:
    signals = profile_signals(
        profiles
    )

    document_count, frequency = (
        corpus_document_frequency(
            rows,
            signals,
        )
    )

    local_scores = [
        score_local(
            row,
            signals=signals,
            document_count=document_count,
            frequency=frequency,
        )
        for row in rows
    ]

    priors = conversation_priors(
        rows,
        local_scores,
    )

    projects = profiles.get(
        "projects",
        {},
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
            conversation_identity(row)
        )

        prior = priors.get(
            conversation,
            {},
        )

        calibrated: dict[str, float] = {}

        for category, data in (
            scores.items()
        ):
            raw_score = float(
                data["raw_score"]
            )

            context = float(
                prior.get(
                    category,
                    0.0,
                )
            )

            context_bonus = (
                raw_score
                * default_context_weight
                * context
            )

            calibrated[category] = (
                raw_score
                + context_bonus
            )

        probabilities = softmax(
            {
                category:
                    math.log1p(
                        max(
                            0.0,
                            score,
                        )
                    )
                for category, score
                in calibrated.items()
            }
        )

        ordered = sorted(
            calibrated,
            key=lambda category: (
                -calibrated[category],
                category,
            ),
        )

        winner = (
            ordered[0]
            if ordered
            else "catchall"
        )

        winner_score = (
            calibrated.get(
                winner,
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
                winner,
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

        profile = (
            projects.get(
                winner,
                {},
            )
            if isinstance(
                projects,
                Mapping,
            )
            else {}
        )

        minimum_score = float(
            profile.get(
                "minimum_score",
                4.0,
            )
            if isinstance(
                profile,
                Mapping,
            )
            else 4.0
        )

        accepted = (
            winner != "catchall"
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

        category = (
            winner
            if accepted
            else "catchall"
        )

        ranked_evidence = []

        for rank, candidate in enumerate(
            ordered,
            1,
        ):
            data = scores[candidate]

            ranked_evidence.append(
                evidence(
                    category=candidate,
                    raw_score=float(
                        data["raw_score"]
                    ),
                    calibrated_score=float(
                        calibrated[candidate]
                    ),
                    confidence=float(
                        probabilities.get(
                            candidate,
                            0.0,
                        )
                    ),
                    hits=tuple(
                        data["hits"]
                    ),
                    families=tuple(
                        data["families"]
                    ),
                    local_rank=rank,
                ).projection()
            )

        source_digest = digest(row)

        classification = {
            "schema": schema,
            "owner": owner,
            "authority_effect":
                authority_effect,
            "authoritative": False,
            "rebuildable": True,
            "classification_owner":
                "unresolved",
            "intended_future_owner":
                "exile:underscore",
            "category": category,
            "candidate": winner,
            "accepted": accepted,
            "confidence": round(
                winner_confidence,
                6,
            ),
            "margin": round(
                margin,
                6,
            ),
            "runner_up": runner,
            "conversation_prior": {
                key: round(
                    value,
                    6,
                )
                for key, value
                in sorted(
                    prior.items()
                )
            },
            "evidence":
                ranked_evidence,
            "source_digest":
                source_digest,
        }

        classification[
            "classification_digest"
        ] = digest(
            classification
        )

        projected = dict(row)

        projected[
            "extr_partition"
        ] = classification

        results.append(projected)

    return results


def atomic_jsonl(
    path: Path,
    rows: Iterable[
        Mapping[str, Any]
    ],
) -> int:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=f".{path.name}.",
            dir=str(path.parent),
        )
    )

    temporary = Path(
        temporary_name
    )

    count = 0

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            for row in rows:
                handle.write(
                    canonical_json(row)
                )
                handle.write("\n")
                count += 1

            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary,
            path,
        )

    finally:
        temporary.unlink(
            missing_ok=True
        )

    return count


def datrix_projection(
    row: Mapping[str, Any],
) -> dict[str, Any]:
    partition = row.get(
        "extr_partition",
        {},
    )

    category = (
        partition.get(
            "category",
            "catchall",
        )
        if isinstance(
            partition,
            Mapping,
        )
        else "catchall"
    )

    source_digest = (
        partition.get(
            "source_digest"
        )
        if isinstance(
            partition,
            Mapping,
        )
        else digest(row)
    )

    node_id = stable_id(
        "datrix:extr:datum",
        source_digest,
    )

    classification_id = stable_id(
        "datrix:extr:classification",
        {
            "source": source_digest,
            "category": category,
            "classification_digest":
                partition.get(
                    "classification_digest"
                )
                if isinstance(
                    partition,
                    Mapping,
                )
                else None,
        },
    )

    return {
        "schema":
            "savant://projection/"
            "datrix/extr/1.0.0",
        "projection_only": True,
        "authority_effect": "none",
        "storage_engine_selected": False,
        "database_engine": None,
        "nodes": [
            {
                "id": node_id,
                "kind": "datum",
                "source_digest":
                    source_digest,
                "conversation_id":
                    conversation_identity(row),
                "message_id":
                    message_identity(row),
            },
            {
                "id":
                    classification_id,
                "kind":
                    "classification",
                "category":
                    category,
                "confidence":
                    partition.get(
                        "confidence",
                        0.0,
                    )
                    if isinstance(
                        partition,
                        Mapping,
                    )
                    else 0.0,
            },
        ],
        "segues": [
            {
                "type":
                    "classified-as",
                "source":
                    node_id,
                "target":
                    classification_id,
            }
        ],
        "lineage": {
            "source_digest":
                source_digest,
            "classification_digest":
                partition.get(
                    "classification_digest"
                )
                if isinstance(
                    partition,
                    Mapping,
                )
                else None,
        },
    }


def write_outputs(
    rows: list[dict[str, Any]],
    output_root: Path,
) -> dict[str, Any]:
    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    category_counts = Counter(
        str(
            row.get(
                "extr_partition",
                {},
            ).get(
                "category",
                "catchall",
            )
        )
        for row in rows
    )

    category_paths = {}

    for category in category_order:
        path = (
            output_root
            / f"{category}.jsonl"
        )

        selected = [
            row
            for row in rows
            if row.get(
                "extr_partition",
                {},
            ).get(
                "category"
            )
            == category
        ]

        atomic_jsonl(
            path,
            selected,
        )

        category_paths[
            category
        ] = str(path)

    combined = (
        output_root
        / "classified.jsonl"
    )

    atomic_jsonl(
        combined,
        rows,
    )

    datrix_path = (
        output_root
        / "datrix_projection.jsonl"
    )

    atomic_jsonl(
        datrix_path,
        (
            datrix_projection(row)
            for row in rows
        ),
    )

    manifest = {
        "schema":
            "savant://runtime/extr/"
            "partition-manifest/2.0.0",
        "owner": owner,
        "authority_effect": "none",
        "authoritative": False,
        "rebuildable": True,
        "categories":
            list(category_order),
        "records": len(rows),
        "category_counts": {
            category:
                category_counts.get(
                    category,
                    0,
                )
            for category
            in category_order
        },
        "outputs":
            category_paths,
        "combined":
            str(combined),
        "datrix_projection":
            str(datrix_path),
        "datrix_storage_selected":
            False,
        "classification_owner":
            "unresolved",
        "intended_future_owner":
            "exile:underscore",
    }

    manifest["digest"] = digest(
        manifest
    )

    manifest_path = (
        output_root
        / "manifest.json"
    )

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=".manifest.",
            dir=str(output_root),
        )
    )

    temporary = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                manifest,
                handle,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary,
            manifest_path,
        )

    finally:
        temporary.unlink(
            missing_ok=True
        )

    return manifest


def selftest() -> dict[str, Any]:
    profiles = {
        "projects": {
            "savant": {
                "minimum_score": 1.0,
                "signals": {
                    "identity": [
                        "savant-runtime"
                    ],
                    "distinctive": [],
                    "phrases": [],
                },
            },
            "viscera": {
                "minimum_score": 1.0,
                "signals": {
                    "identity": [
                        "viscera hood"
                    ],
                    "distinctive": [],
                    "phrases": [],
                },
            },
            "low_life": {
                "minimum_score": 1.0,
                "signals": {
                    "identity": [
                        "low life"
                    ],
                    "distinctive": [],
                    "phrases": [],
                },
            },
            "mayorgate": {
                "minimum_score": 1.0,
                "signals": {
                    "identity": [
                        "mayorgate"
                    ],
                    "distinctive": [],
                    "phrases": [],
                },
            },
            "catchall": {
                "minimum_score": 0.0,
                "signals": {},
            },
        }
    }

    rows = [
        {
            "message_id": "1",
            "conversation_id": "a",
            "text":
                "savant-runtime authority",
        },
        {
            "message_id": "2",
            "conversation_id": "b",
            "text":
                "viscera hood scene",
        },
        {
            "message_id": "3",
            "conversation_id": "c",
            "text":
                "official low life chat",
        },
        {
            "message_id": "4",
            "conversation_id": "d",
            "text":
                "mayorgate evidence",
        },
        {
            "message_id": "5",
            "conversation_id": "e",
            "text":
                "ordinary unrelated data",
        },
    ]

    first = classify_rows(
        rows,
        profiles,
    )

    second = classify_rows(
        rows,
        profiles,
    )

    categories = [
        row[
            "extr_partition"
        ]["category"]
        for row in first
    ]

    checks = {
        "deterministic":
            first == second,
        "five_categories":
            tuple(category_order)
            == (
                "savant",
                "viscera",
                "low_life",
                "mayorgate",
                "catchall",
            ),
        "savant":
            categories[0]
            == "savant",
        "viscera":
            categories[1]
            == "viscera",
        "low_life":
            categories[2]
            == "low_life",
        "mayorgate":
            categories[3]
            == "mayorgate",
        "catchall":
            categories[4]
            == "catchall",
        "no_authority":
            all(
                row[
                    "extr_partition"
                ][
                    "authority_effect"
                ]
                == "none"
                for row in first
            ),
        "rebuildable":
            all(
                row[
                    "extr_partition"
                ][
                    "rebuildable"
                ]
                is True
                for row in first
            ),
        "datrix_projection_only":
            datrix_projection(
                first[0]
            )[
                "projection_only"
            ]
            is True,
        "datrix_engine_unselected":
            datrix_projection(
                first[0]
            )[
                "storage_engine_selected"
            ]
            is False,
        "underscore_not_fabricated":
            first[0][
                "extr_partition"
            ][
                "classification_owner"
            ]
            == "unresolved",
    }

    return {
        "schema":
            "savant://runtime/extr/"
            "partition-selftest/2.0.0",
        "ok": all(
            checks.values()
        ),
        "checks": checks,
        "categories": categories,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="extr-partition"
    )

    parser.add_argument(
        "input",
        nargs="?",
    )

    parser.add_argument(
        "output",
        nargs="?",
    )

    parser.add_argument(
        "--profiles",
        default=(
            "/root/savant-runtime/"
            "tools/extr-enterprise/"
            "config/projects.json"
        ),
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
    )

    args = parser.parse_args()

    if args.selftest:
        print(
            json.dumps(
                selftest(),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
        )
        return (
            0
            if selftest()["ok"]
            else 1
        )

    if not args.input:
        raise partition_error(
            "input JSONL is required"
        )

    input_path = Path(
        os.path.expanduser(
            os.path.expandvars(
                args.input
            )
        )
    ).resolve()

    if not input_path.is_file():
        raise partition_error(
            f"input unavailable: "
            f"{input_path}"
        )

    output_root = Path(
        os.path.expanduser(
            os.path.expandvars(
                args.output
                or str(
                    input_path.parent
                    / (
                        input_path.stem
                        + ".partition"
                    )
                )
            )
        )
    ).resolve()

    profiles = load_json(
        Path(args.profiles).resolve()
    )

    rows = read_jsonl(
        input_path
    )

    classified = classify_rows(
        rows,
        profiles,
    )

    manifest = write_outputs(
        classified,
        output_root,
    )

    print(
        json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

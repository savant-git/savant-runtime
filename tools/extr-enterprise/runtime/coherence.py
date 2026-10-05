#!/usr/bin/env python3

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable


schema = "savant.extr.coherence.v1"

word_pattern = re.compile(
    r"[a-z0-9][a-z0-9_-]{1,}",
    re.IGNORECASE,
)

sentence_pattern = re.compile(
    r"(?<=[.!?])\s+"
)

stopwords = frozenset(
    {
        "about",
        "after",
        "again",
        "against",
        "also",
        "and",
        "any",
        "are",
        "because",
        "been",
        "before",
        "being",
        "between",
        "both",
        "but",
        "can",
        "could",
        "did",
        "does",
        "doing",
        "done",
        "each",
        "for",
        "from",
        "had",
        "has",
        "have",
        "having",
        "here",
        "how",
        "into",
        "its",
        "just",
        "more",
        "most",
        "not",
        "now",
        "only",
        "other",
        "our",
        "out",
        "over",
        "same",
        "should",
        "some",
        "such",
        "than",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "too",
        "under",
        "very",
        "was",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "will",
        "with",
        "would",
        "you",
        "your",
    }
)


try:
    import orjson
except Exception:
    orjson = None


def json_bytes(
    value: Any,
) -> bytes:
    if orjson is not None:
        return orjson.dumps(
            value
        )

    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    ).encode(
        "utf-8"
    )


def stable_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        stable_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def atomic_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=f".{path.name}.",
            dir=str(
                path.parent
            ),
        )
    )

    temporary = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "wb",
        ) as handle:
            handle.write(
                json.dumps(
                    value,
                    ensure_ascii=False,
                    sort_keys=True,
                    indent=2,
                    default=str,
                ).encode(
                    "utf-8"
                )
            )

            handle.write(
                b"\n"
            )

            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary,
            path,
        )

    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_jsonl(
    path: Path,
    rows: Iterable[
        dict[str, Any]
    ],
) -> int:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=f".{path.name}.",
            dir=str(
                path.parent
            ),
        )
    )

    temporary = Path(
        temporary_name
    )

    count = 0

    try:
        with os.fdopen(
            descriptor,
            "wb",
        ) as handle:
            for row in rows:
                handle.write(
                    json_bytes(
                        row
                    )
                )

                handle.write(
                    b"\n"
                )

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
        if temporary.exists():
            temporary.unlink()

    return count


def load_jsonl(
    path: Path,
) -> list[
    dict[str, Any]
]:
    rows = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line_number, line in enumerate(
            handle,
            start=1,
        ):
            candidate = line.strip()

            if not candidate:
                continue

            try:
                value = json.loads(
                    candidate
                )
            except json.JSONDecodeError as error:
                raise RuntimeError(
                    (
                        f"invalid jsonl "
                        f"{path}:{line_number}: "
                        f"{error}"
                    )
                ) from error

            if isinstance(
                value,
                dict,
            ):
                rows.append(
                    value
                )

    return rows


def text_of(
    row: dict[str, Any],
) -> str:
    value = row.get(
        "text",
        ""
    )

    return (
        value
        if isinstance(
            value,
            str,
        )
        else str(value)
    )


def source_of(
    row: dict[str, Any],
) -> str:
    source = row.get(
        "source",
        {}
    )

    if not isinstance(
        source,
        dict,
    ):
        return "unknown"

    return str(
        source.get(
            "path",
            "unknown",
        )
    )


def ordinal_of(
    row: dict[str, Any],
) -> int:
    source = row.get(
        "source",
        {}
    )

    if not isinstance(
        source,
        dict,
    ):
        return 0

    try:
        return int(
            source.get(
                "ordinal",
                0,
            )
            or 0
        )
    except Exception:
        return 0


def mtime_of(
    row: dict[str, Any],
) -> int:
    corpus = row.get(
        "corpus",
        {}
    )

    if isinstance(
        corpus,
        dict,
    ):
        try:
            return int(
                corpus.get(
                    "source_mtime_ns",
                    0,
                )
                or 0
            )
        except Exception:
            pass

    return 0


def classification_confidence(
    row: dict[str, Any],
) -> float:
    project = row.get(
        "project",
        {}
    )

    if not isinstance(
        project,
        dict,
    ):
        return 0.0

    try:
        return float(
            project.get(
                "confidence",
                0.0,
            )
            or 0.0
        )
    except Exception:
        return 0.0


def tokens(
    text: str,
) -> set[str]:
    return {
        token.casefold()
        for token in word_pattern.findall(
            text
        )
        if (
            len(token) >= 3
            and token.casefold()
            not in stopwords
            and not token.isdigit()
        )
    }


def weighted_tokens(
    text: str,
) -> dict[str, float]:
    result: dict[
        str,
        float
    ] = defaultdict(
        float
    )

    for token in word_pattern.findall(
        text.casefold()
    ):
        if (
            len(token) < 3
            or token in stopwords
            or token.isdigit()
        ):
            continue

        result[token] += 1.0

    return dict(
        result
    )


def cosine(
    left: dict[str, float],
    right: dict[str, float],
) -> float:
    if not left or not right:
        return 0.0

    common = (
        left.keys()
        & right.keys()
    )

    numerator = sum(
        left[key]
        * right[key]
        for key in common
    )

    left_norm = math.sqrt(
        sum(
            value * value
            for value in left.values()
        )
    )

    right_norm = math.sqrt(
        sum(
            value * value
            for value in right.values()
        )
    )

    denominator = (
        left_norm
        * right_norm
    )

    if denominator <= 0:
        return 0.0

    return numerator / denominator


def topic_signature(
    text: str,
    maximum: int = 8,
) -> tuple[str, ...]:
    weights = weighted_tokens(
        text
    )

    ordered = sorted(
        weights.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    )

    return tuple(
        key
        for key, _
        in ordered[:maximum]
    )


def cluster_rows(
    rows: list[
        dict[str, Any]
    ],
    threshold: float = 0.28,
) -> list[
    list[dict[str, Any]]
]:
    clusters: list[
        list[dict[str, Any]]
    ] = []

    centroids: list[
        dict[str, float]
    ] = []

    for row in rows:
        vector = weighted_tokens(
            text_of(
                row
            )
        )

        best_index = None
        best_score = 0.0

        for index, centroid in enumerate(
            centroids
        ):
            score = cosine(
                vector,
                centroid,
            )

            if score > best_score:
                best_score = score
                best_index = index

        if (
            best_index is None
            or best_score
            < threshold
        ):
            clusters.append(
                [row]
            )

            centroids.append(
                dict(
                    vector
                )
            )

            continue

        clusters[
            best_index
        ].append(
            row
        )

        centroid = centroids[
            best_index
        ]

        size = len(
            clusters[
                best_index
            ]
        )

        keys = (
            centroid.keys()
            | vector.keys()
        )

        centroids[
            best_index
        ] = {
            key: (
                (
                    centroid.get(
                        key,
                        0.0,
                    )
                    * (
                        size - 1
                    )
                )
                + vector.get(
                    key,
                    0.0,
                )
            )
            / size
            for key in keys
        }

    return clusters


def probable_metadata_debris(
    text: str,
) -> bool:
    stripped = text.strip()

    if not stripped:
        return True

    if len(
        stripped
    ) <= 2:
        return True

    if stripped.casefold() in {
        "null",
        "none",
        "true",
        "false",
        "undefined",
        "nan",
    }:
        return True

    punctuation = sum(
        1
        for character in stripped
        if not character.isalnum()
        and not character.isspace()
    )

    if (
        len(
            stripped
        ) > 0
        and punctuation
        / len(
            stripped
        )
        > 0.8
    ):
        return True

    return False


def quoted_fraction(
    text: str,
) -> float:
    lines = text.splitlines()

    if not lines:
        return 0.0

    quoted = sum(
        1
        for line in lines
        if line.lstrip().startswith(
            ">"
        )
    )

    return quoted / len(
        lines
    )


def contamination_score(
    row: dict[str, Any],
) -> float:
    text = text_of(
        row
    )

    score = 0.0

    if probable_metadata_debris(
        text
    ):
        score += 0.7

    corpus = row.get(
        "corpus",
        {}
    )

    if isinstance(
        corpus,
        dict,
    ) and corpus.get(
        "quoted_or_forwarded"
    ):
        score += 0.15

    score += min(
        0.15,
        quoted_fraction(
            text
        )
        * 0.15,
    )

    if classification_confidence(
        row
    ) < 0.55:
        score += 0.1

    return min(
        1.0,
        round(
            score,
            6,
        ),
    )


def sentence_units(
    text: str,
) -> list[str]:
    normalized = (
        text.replace(
            "\r\n",
            "\n",
        )
        .replace(
            "\r",
            "\n",
        )
        .strip()
    )

    pieces = []

    for paragraph in re.split(
        r"\n\s*\n",
        normalized,
    ):
        paragraph = paragraph.strip()

        if not paragraph:
            continue

        sentences = sentence_pattern.split(
            paragraph
        )

        for sentence in sentences:
            sentence = sentence.strip()

            if sentence:
                pieces.append(
                    sentence
                )

    return pieces


def claim_polarity(
    sentence: str,
) -> str:
    value = (
        " "
        + sentence.casefold()
        + " "
    )

    negative_markers = (
        " not ",
        " never ",
        " no ",
        " cannot ",
        " can't ",
        " isn't ",
        " wasn't ",
        " weren't ",
        " doesn't ",
        " didn't ",
        " won't ",
        " without ",
    )

    return (
        "negative"
        if any(
            marker in value
            for marker
            in negative_markers
        )
        else "positive"
    )


def claim_key(
    sentence: str,
) -> str:
    value = (
        " "
        + sentence.casefold()
        + " "
    )

    for marker in (
        " not ",
        " never ",
        " cannot ",
        " can't ",
        " isn't ",
        " wasn't ",
        " weren't ",
        " doesn't ",
        " didn't ",
        " won't ",
    ):
        value = value.replace(
            marker,
            " ",
        )

    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    return hashlib.sha256(
        value.encode(
            "utf-8"
        )
    ).hexdigest()


def contradiction_surface(
    rows: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    groups: dict[
        str,
        list[dict[str, Any]]
    ] = defaultdict(
        list
    )

    for row in rows:
        for sentence in sentence_units(
            text_of(
                row
            )
        ):
            if len(
                sentence
            ) < 20:
                continue

            groups[
                claim_key(
                    sentence
                )
            ].append(
                {
                    "sentence":
                        sentence,
                    "polarity":
                        claim_polarity(
                            sentence
                        ),
                    "source":
                        source_of(
                            row
                        ),
                    "mtime_ns":
                        mtime_of(
                            row
                        ),
                    "fingerprint":
                        row.get(
                            "fingerprint"
                        ),
                }
            )

    output = []

    for key, claims in groups.items():
        polarities = {
            claim[
                "polarity"
            ]
            for claim in claims
        }

        if len(
            polarities
        ) < 2:
            continue

        output.append(
            {
                "claim_key":
                    key,
                "resolved":
                    False,
                "claims":
                    sorted(
                        claims,
                        key=lambda claim: (
                            claim[
                                "mtime_ns"
                            ],
                            claim[
                                "source"
                            ].casefold(),
                        ),
                    ),
            }
        )

    return sorted(
        output,
        key=lambda item:
            item[
                "claim_key"
            ],
    )


def cluster_name(
    cluster: list[
        dict[str, Any]
    ],
) -> str:
    aggregate: dict[
        str,
        float
    ] = defaultdict(
        float
    )

    for row in cluster:
        for token, weight in (
            weighted_tokens(
                text_of(
                    row
                )
            ).items()
        ):
            aggregate[
                token
            ] += weight

    ordered = sorted(
        aggregate.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    )

    terms = [
        token
        for token, _
        in ordered[:4]
    ]

    if not terms:
        return "miscellaneous"

    return "-".join(
        terms
    )


def chronology(
    cluster: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    ordered = sorted(
        cluster,
        key=lambda row: (
            mtime_of(
                row
            ),
            source_of(
                row
            ).casefold(),
            ordinal_of(
                row
            ),
        ),
    )

    return [
        {
            "mtime_ns":
                mtime_of(
                    row
                ),
            "source":
                source_of(
                    row
                ),
            "ordinal":
                ordinal_of(
                    row
                ),
            "fingerprint":
                row.get(
                    "fingerprint"
                ),
        }
        for row in ordered
    ]


def canonical_projection(
    cluster: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:
    ordered = sorted(
        cluster,
        key=lambda row: (
            mtime_of(
                row
            ),
            classification_confidence(
                row
            ),
            len(
                text_of(
                    row
                )
            ),
        ),
        reverse=True,
    )

    selected = ordered[
        0
    ]

    return {
        "selection":
            "newest-projection-only",
        "authority_effect":
            "none",
        "selected_fingerprint":
            selected.get(
                "fingerprint"
            ),
        "selected_source":
            source_of(
                selected
            ),
        "selected_mtime_ns":
            mtime_of(
                selected
            ),
        "selected_text":
            text_of(
                selected
            ),
        "versions":
            chronology(
                cluster
            ),
    }


def refine_project(
    project_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    rows = load_jsonl(
        project_path
    )

    clean_rows = []
    quarantine_rows = []

    for row in rows:
        score = contamination_score(
            row
        )

        row.setdefault(
            "coherence",
            {}
        )

        row[
            "coherence"
        ][
            "contamination_score"
        ] = score

        if score >= 0.7:
            quarantine_rows.append(
                row
            )
        else:
            clean_rows.append(
                row
            )

    clean_rows.sort(
        key=lambda row: (
            source_of(
                row
            ).casefold(),
            ordinal_of(
                row
            ),
            str(
                row.get(
                    "fingerprint",
                    "",
                )
            ),
        )
    )

    clusters = cluster_rows(
        clean_rows
    )

    project_name = (
        project_path.stem
    )

    project_root = (
        output_root
        / project_name
    )

    topic_root = (
        project_root
        / "topics"
    )

    topic_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    topic_manifest = []

    for index, cluster in enumerate(
        clusters,
        start=1,
    ):
        name = cluster_name(
            cluster
        )

        identifier = (
            f"{index:04d}-"
            f"{name}"
        )

        cluster_rows_sorted = sorted(
            cluster,
            key=lambda row: (
                mtime_of(
                    row
                ),
                source_of(
                    row
                ).casefold(),
                ordinal_of(
                    row
                ),
            ),
        )

        atomic_jsonl(
            topic_root
            / (
                identifier
                + ".jsonl"
            ),
            cluster_rows_sorted,
        )

        projection = (
            canonical_projection(
                cluster
            )
        )

        atomic_json(
            topic_root
            / (
                identifier
                + ".projection.json"
            ),
            projection,
        )

        topic_manifest.append(
            {
                "id":
                    identifier,
                "rows":
                    len(
                        cluster
                    ),
                "topic_signature":
                    list(
                        topic_signature(
                            " ".join(
                                text_of(
                                    row
                                )
                                for row
                                in cluster
                            )
                        )
                    ),
                "projection":
                    projection[
                        "selected_fingerprint"
                    ],
            }
        )

    contradictions = (
        contradiction_surface(
            clean_rows
        )
    )

    atomic_jsonl(
        project_root
        / "clean.jsonl",
        clean_rows,
    )

    atomic_jsonl(
        project_root
        / "quarantine.jsonl",
        quarantine_rows,
    )

    atomic_json(
        project_root
        / "contradictions.json",
        {
            "schema":
                "savant.extr.coherence.contradictions.v1",
            "authority_effect":
                "none",
            "auto_resolution":
                False,
            "groups":
                contradictions,
        },
    )

    manifest = {
        "schema":
            "savant.extr.coherence.project.v1",
        "projection_only":
            True,
        "authority_effect":
            "none",
        "project":
            project_name,
        "input":
            str(
                project_path
            ),
        "statistics": {
            "rows_seen":
                len(
                    rows
                ),
            "rows_clean":
                len(
                    clean_rows
                ),
            "rows_quarantined":
                len(
                    quarantine_rows
                ),
            "topics":
                len(
                    clusters
                ),
            "contradiction_groups":
                len(
                    contradictions
                ),
        },
        "topics":
            topic_manifest,
    }

    manifest[
        "digest"
    ] = digest(
        manifest
    )

    atomic_json(
        project_root
        / "manifest.json",
        manifest,
    )

    return manifest


def refine_corpus(
    corpus_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    projects_root = (
        corpus_root
        / "projects"
    )

    if not projects_root.is_dir():
        raise RuntimeError(
            (
                "corpus projects directory "
                f"unavailable: {projects_root}"
            )
        )

    project_files = sorted(
        projects_root.glob(
            "*.jsonl"
        ),
        key=lambda path:
            path.name.casefold(),
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifests = []

    for project_path in (
        project_files
    ):
        manifests.append(
            refine_project(
                project_path,
                output_root,
            )
        )

    manifest = {
        "schema":
            schema,
        "projection_only":
            True,
        "authority_effect":
            "none",
        "source_corpus":
            str(
                corpus_root.resolve()
            ),
        "destination":
            str(
                output_root.resolve()
            ),
        "projects":
            [
                {
                    "project":
                        item[
                            "project"
                        ],
                    "digest":
                        item[
                            "digest"
                        ],
                    "statistics":
                        item[
                            "statistics"
                        ],
                }
                for item
                in manifests
            ],
        "capabilities": {
            "project_isolation":
                True,
            "contamination_scoring":
                True,
            "debris_quarantine":
                True,
            "topic_clustering":
                True,
            "deterministic_topic_projection":
                True,
            "topic_signatures":
                True,
            "source_chronology":
                True,
            "version_lineage":
                True,
            "newest_projection":
                True,
            "older_evidence_preserved":
                True,
            "contradiction_detection":
                True,
            "contradiction_auto_resolution":
                False,
            "quoted_content_awareness":
                True,
            "classification_confidence_awareness":
                True,
            "atomic_outputs":
                True,
            "authority_neutral":
                True,
        },
    }

    manifest[
        "digest"
    ] = digest(
        manifest
    )

    atomic_json(
        output_root
        / "manifest.json",
        manifest,
    )

    return manifest


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        prog="extr-coherence"
    )

    value.add_argument(
        "corpus"
    )

    value.add_argument(
        "destination"
    )

    return value


def main() -> int:
    arguments = parser().parse_args()

    corpus_root = Path(
        os.path.expanduser(
            os.path.expandvars(
                arguments.corpus
            )
        )
    ).resolve()

    output_root = Path(
        os.path.expanduser(
            os.path.expandvars(
                arguments.destination
            )
        )
    ).resolve()

    try:
        manifest = refine_corpus(
            corpus_root,
            output_root,
        )

    except Exception as error:
        print(
            (
                "extr-coherence: "
                f"{type(error).__name__}: "
                f"{error}"
            ),
            file=sys.stderr,
        )

        return 1

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
    raise SystemExit(
        main()
    )

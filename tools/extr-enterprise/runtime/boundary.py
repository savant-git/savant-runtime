#!/usr/bin/env python3

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Iterable


runtime_root = Path(
    "/root/savant-runtime"
)

extr_root = (
    runtime_root
    / "tools"
    / "extr-enterprise"
)

runtime_path = (
    extr_root
    / "runtime"
)

sys.path.insert(
    0,
    str(runtime_path),
)

import universal


schema = "savant.extr.boundary.v1"

policy_path = (
    extr_root
    / "config"
    / "boundary-policy.json"
)

profiles_path = (
    extr_root
    / "config"
    / "projects.json"
)

paragraph_break = re.compile(
    r"\n\s*\n+"
)

sentence_break = re.compile(
    r"(?<=[.!?])\s+"
)


try:
    import orjson
except Exception:
    orjson = None


def load_json(
    path: Path,
    default: Any,
) -> Any:
    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return default


def load_policy() -> dict[str, Any]:
    value = load_json(
        policy_path,
        {},
    )

    if not isinstance(
        value,
        dict,
    ):
        raise RuntimeError(
            "invalid boundary policy"
        )

    return value


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


def stable_digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
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


def read_jsonl(
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


def safe_slug(
    value: str,
) -> str:
    cleaned = "".join(
        character
        if (
            character.isalnum()
            or character
            in {
                "-",
                "_",
            }
        )
        else "-"
        for character
        in value.casefold()
    )

    while "--" in cleaned:
        cleaned = cleaned.replace(
            "--",
            "-",
        )

    return (
        cleaned.strip("-")
        or "unclassified"
    )


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
) -> dict[str, Any]:
    value = row.get(
        "source",
        {}
    )

    return (
        value
        if isinstance(
            value,
            dict,
        )
        else {}
    )


def sentence_units(
    text: str,
) -> list[str]:
    units = []

    for paragraph in paragraph_break.split(
        text
    ):
        paragraph = paragraph.strip()

        if not paragraph:
            continue

        sentences = sentence_break.split(
            paragraph
        )

        for sentence in sentences:
            sentence = sentence.strip()

            if sentence:
                units.append(
                    sentence
                )

    return units


def chunk_sentences(
    sentences: list[str],
    *,
    target_characters: int,
    maximum_characters: int,
) -> list[
    tuple[int, int, str]
]:
    chunks = []

    start = 0
    current = []

    for index, sentence in enumerate(
        sentences
    ):
        candidate_length = sum(
            len(value)
            for value in current
        ) + len(
            sentence
        ) + max(
            0,
            len(current)
        )

        if (
            current
            and (
                candidate_length
                > target_characters
            )
        ):
            chunks.append(
                (
                    start,
                    index,
                    " ".join(
                        current
                    ),
                )
            )

            start = index
            current = []

        current.append(
            sentence
        )

        current_length = len(
            " ".join(
                current
            )
        )

        if (
            current_length
            >= maximum_characters
        ):
            chunks.append(
                (
                    start,
                    index + 1,
                    " ".join(
                        current
                    ),
                )
            )

            start = index + 1
            current = []

    if current:
        chunks.append(
            (
                start,
                len(sentences),
                " ".join(
                    current
                ),
            )
        )

    return chunks


def classification_score(
    classification: dict[str, Any],
) -> tuple[
    str,
    float,
    int,
]:
    project = str(
        classification.get(
            "project",
            "unclassified",
        )
    )

    confidence = float(
        classification.get(
            "confidence",
            0.0,
        )
        or 0.0
    )

    signals = classification.get(
        "signals",
        [],
    )

    signal_count = (
        len(signals)
        if isinstance(
            signals,
            list,
        )
        else 0
    )

    return (
        project,
        confidence,
        signal_count,
    )


def classify_fragment(
    text: str,
    profiles: dict[
        str,
        dict[str, Any]
    ],
    policy: dict[str, Any],
    previous_project: str | None,
) -> tuple[
    str,
    dict[str, Any],
]:
    classification = (
        universal.classify_project(
            text,
            profiles,
        )
    )

    project, confidence, signals = (
        classification_score(
            classification
        )
    )

    settings = policy.get(
        "classification",
        {},
    )

    minimum_signals = int(
        settings.get(
            "minimum_signals",
            1,
        )
    )

    minimum_confidence = float(
        settings.get(
            "minimum_confidence",
            0.5,
        )
    )

    switch_margin = float(
        settings.get(
            "switch_margin",
            0.2,
        )
    )

    sticky = bool(
        settings.get(
            "sticky_context",
            True,
        )
    )

    ambiguous_bucket = str(
        settings.get(
            "ambiguous_bucket",
            "ambiguous",
        )
    )

    unclassified_bucket = str(
        settings.get(
            "unclassified_bucket",
            "unclassified",
        )
    )

    if (
        signals < minimum_signals
        or confidence
        < minimum_confidence
        or project
        == "unclassified"
    ):
        return (
            unclassified_bucket,
            classification,
        )

    alternatives = classification.get(
        "alternatives",
        [],
    )

    runner_score = 0

    if (
        isinstance(
            alternatives,
            list,
        )
        and alternatives
        and isinstance(
            alternatives[0],
            dict,
        )
    ):
        runner_score = int(
            alternatives[0].get(
                "score",
                0,
            )
            or 0
        )

    if signals > 0:
        margin = (
            signals
            - runner_score
        ) / signals

        if margin < switch_margin:
            return (
                ambiguous_bucket,
                classification,
            )

    if (
        sticky
        and previous_project
        and previous_project
        not in {
            ambiguous_bucket,
            unclassified_bucket,
        }
        and project
        != previous_project
        and confidence
        < (
            minimum_confidence
            + switch_margin
        )
    ):
        classification[
            "contextual_project"
        ] = previous_project

        classification[
            "contextual_reason"
        ] = (
            "insufficient-switch-margin"
        )

        return (
            previous_project,
            classification,
        )

    return (
        safe_slug(
            project
        ),
        classification,
    )


def fragment_row(
    original: dict[str, Any],
    *,
    text: str,
    project: str,
    classification: dict[str, Any],
    fragment_index: int,
    sentence_start: int,
    sentence_end: int,
    source_text_hash: str,
) -> dict[str, Any]:
    fingerprint = (
        universal.text_fingerprint(
            text
        )
    )

    source = dict(
        source_of(
            original
        )
    )

    source[
        "fragment_index"
    ] = fragment_index

    source[
        "sentence_start"
    ] = sentence_start

    source[
        "sentence_end"
    ] = sentence_end

    source[
        "parent_text_sha256"
    ] = source_text_hash

    corpus = original.get(
        "corpus",
        {}
    )

    if not isinstance(
        corpus,
        dict,
    ):
        corpus = {}

    corpus = dict(
        corpus
    )

    corpus[
        "classification_bucket"
    ] = project

    corpus[
        "fragment_reconstructed"
    ] = True

    return {
        "schema":
            schema,
        "text":
            text,
        "fingerprint":
            fingerprint,
        "source":
            source,
        "project":
            classification,
        "corpus":
            corpus,
        "lineage": {
            "parent_fingerprint":
                original.get(
                    "fingerprint"
                ),
            "parent_schema":
                original.get(
                    "schema"
                ),
            "source_text_sha256":
                source_text_hash,
            "fragment_index":
                fragment_index,
            "sentence_start":
                sentence_start,
            "sentence_end":
                sentence_end,
        },
        "authority_effect":
            "none",
        "authoritative":
            False,
        "rebuildable":
            True,
    }


def merge_adjacent(
    fragments: list[
        dict[str, Any]
    ],
    policy: dict[str, Any],
) -> list[
    dict[str, Any]
]:
    if not bool(
        policy.get(
            "reconstruction",
            {},
        ).get(
            "merge_adjacent_same_project",
            True,
        )
    ):
        return fragments

    merged = []

    for fragment in fragments:
        project = (
            fragment.get(
                "corpus",
                {},
            ).get(
                "classification_bucket",
                "unclassified",
            )
        )

        if not merged:
            merged.append(
                fragment
            )
            continue

        previous = merged[-1]

        previous_project = (
            previous.get(
                "corpus",
                {},
            ).get(
                "classification_bucket",
                "unclassified",
            )
        )

        if (
            project
            != previous_project
        ):
            merged.append(
                fragment
            )
            continue

        previous[
            "text"
        ] = (
            previous[
                "text"
            ].rstrip()
            + "\n\n"
            + fragment[
                "text"
            ].lstrip()
        )

        previous[
            "fingerprint"
        ] = universal.text_fingerprint(
            previous[
                "text"
            ]
        )

        previous[
            "source"
        ][
            "sentence_end"
        ] = fragment[
            "source"
        ][
            "sentence_end"
        ]

        previous[
            "lineage"
        ][
            "sentence_end"
        ] = fragment[
            "lineage"
        ][
            "sentence_end"
        ]

        previous[
            "lineage"
        ].setdefault(
            "merged_fragment_indices",
            [],
        ).append(
            fragment[
                "lineage"
            ][
                "fragment_index"
            ]
        )

    return merged


def bridge_short_unclassified(
    fragments: list[
        dict[str, Any]
    ],
    policy: dict[str, Any],
) -> list[
    dict[str, Any]
]:
    settings = policy.get(
        "reconstruction",
        {},
    )

    if not bool(
        settings.get(
            "bridge_short_unclassified_fragments",
            True,
        )
    ):
        return fragments

    maximum = int(
        settings.get(
            "maximum_bridge_characters",
            240,
        )
    )

    if len(
        fragments
    ) < 3:
        return fragments

    output = []
    index = 0

    while index < len(
        fragments
    ):
        fragment = fragments[
            index
        ]

        project = (
            fragment.get(
                "corpus",
                {},
            ).get(
                "classification_bucket",
                "unclassified",
            )
        )

        if (
            project
            == "unclassified"
            and len(
                fragment.get(
                    "text",
                    ""
                )
            )
            <= maximum
            and index > 0
            and index + 1
            < len(
                fragments
            )
        ):
            previous = output[
                -1
            ]

            following = fragments[
                index + 1
            ]

            previous_project = (
                previous.get(
                    "corpus",
                    {},
                ).get(
                    "classification_bucket"
                )
            )

            following_project = (
                following.get(
                    "corpus",
                    {},
                ).get(
                    "classification_bucket"
                )
            )

            if (
                previous_project
                == following_project
                and previous_project
                not in {
                    "unclassified",
                    "ambiguous",
                }
            ):
                previous[
                    "text"
                ] = (
                    previous[
                        "text"
                    ].rstrip()
                    + "\n\n"
                    + fragment[
                        "text"
                    ].strip()
                    + "\n\n"
                    + following[
                        "text"
                    ].lstrip()
                )

                previous[
                    "fingerprint"
                ] = (
                    universal.text_fingerprint(
                        previous[
                            "text"
                        ]
                    )
                )

                previous[
                    "source"
                ][
                    "sentence_end"
                ] = following[
                    "source"
                ][
                    "sentence_end"
                ]

                previous[
                    "lineage"
                ].setdefault(
                    "bridged_fragments",
                    [],
                ).append(
                    fragment[
                        "lineage"
                    ][
                        "fragment_index"
                    ]
                )

                index += 2
                continue

        output.append(
            fragment
        )

        index += 1

    return output


def split_row(
    row: dict[str, Any],
    profiles: dict[
        str,
        dict[str, Any]
    ],
    policy: dict[str, Any],
) -> list[
    dict[str, Any]
]:
    text = text_of(
        row
    ).strip()

    if not text:
        return []

    segmentation = policy.get(
        "segmentation",
        {},
    )

    minimum = int(
        segmentation.get(
            "minimum_fragment_characters",
            80,
        )
    )

    target = int(
        segmentation.get(
            "target_fragment_characters",
            1400,
        )
    )

    maximum = int(
        segmentation.get(
            "maximum_fragment_characters",
            4000,
        )
    )

    if len(
        text
    ) <= target:
        classification = (
            universal.classify_project(
                text,
                profiles,
            )
        )

        project, _, _ = (
            classification_score(
                classification
            )
        )

        return [
            fragment_row(
                row,
                text=text,
                project=safe_slug(
                    project
                ),
                classification=classification,
                fragment_index=0,
                sentence_start=0,
                sentence_end=1,
                source_text_hash=hashlib.sha256(
                    text.encode(
                        "utf-8"
                    )
                ).hexdigest(),
            )
        ]

    sentences = sentence_units(
        text
    )

    if not sentences:
        return []

    chunks = chunk_sentences(
        sentences,
        target_characters=target,
        maximum_characters=maximum,
    )

    source_text_hash = (
        hashlib.sha256(
            text.encode(
                "utf-8"
            )
        ).hexdigest()
    )

    fragments = []

    previous_project = None

    for fragment_index, (
        sentence_start,
        sentence_end,
        fragment_text,
    ) in enumerate(
        chunks
    ):
        fragment_text = (
            fragment_text.strip()
        )

        if len(
            fragment_text
        ) < minimum:
            project = (
                previous_project
                or "unclassified"
            )

            classification = {
                "project":
                    project,
                "confidence":
                    0.0,
                "signals":
                    [],
                "contextual_reason":
                    "short-fragment",
            }

        else:
            project, classification = (
                classify_fragment(
                    fragment_text,
                    profiles,
                    policy,
                    previous_project,
                )
            )

        fragment = fragment_row(
            row,
            text=fragment_text,
            project=project,
            classification=classification,
            fragment_index=fragment_index,
            sentence_start=sentence_start,
            sentence_end=sentence_end,
            source_text_hash=source_text_hash,
        )

        fragments.append(
            fragment
        )

        if project not in {
            "unclassified",
            "ambiguous",
        }:
            previous_project = project

    fragments = (
        bridge_short_unclassified(
            fragments,
            policy,
        )
    )

    fragments = merge_adjacent(
        fragments,
        policy,
    )

    return fragments


def repartition_corpus(
    corpus_root: Path,
    destination: Path,
) -> dict[str, Any]:
    projects_root = (
        corpus_root
        / "projects"
    )

    if not projects_root.is_dir():
        raise RuntimeError(
            (
                "corpus projects unavailable: "
                f"{projects_root}"
            )
        )

    policy = load_policy()

    profiles = (
        universal.load_project_profiles(
            profiles_path
        )
    )

    project_rows: dict[
        str,
        list[dict[str, Any]]
    ] = defaultdict(
        list
    )

    original_rows = []
    fragments_seen = 0
    source_rows_seen = 0
    mixed_source_rows = 0

    project_files = sorted(
        projects_root.glob(
            "*.jsonl"
        ),
        key=lambda path:
            path.name.casefold(),
    )

    for project_file in project_files:
        rows = read_jsonl(
            project_file
        )

        for row in rows:
            source_rows_seen += 1

            if bool(
                policy.get(
                    "reconstruction",
                    {},
                ).get(
                    "preserve_original_rows",
                    True,
                )
            ):
                original_rows.append(
                    row
                )

            fragments = split_row(
                row,
                profiles,
                policy,
            )

            fragments_seen += len(
                fragments
            )

            buckets = {
                str(
                    fragment.get(
                        "corpus",
                        {},
                    ).get(
                        "classification_bucket",
                        "unclassified",
                    )
                )
                for fragment
                in fragments
            }

            if len(
                buckets
            ) > 1:
                mixed_source_rows += 1

            for fragment in fragments:
                bucket = str(
                    fragment.get(
                        "corpus",
                        {},
                    ).get(
                        "classification_bucket",
                        "unclassified",
                    )
                )

                project_rows[
                    safe_slug(
                        bucket
                    )
                ].append(
                    fragment
                )

    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination_projects = (
        destination
        / "projects"
    )

    destination_projects.mkdir(
        parents=True,
        exist_ok=True,
    )

    project_counts = {}

    for project in sorted(
        project_rows,
        key=str.casefold,
    ):
        rows = project_rows[
            project
        ]

        rows.sort(
            key=lambda row: (
                str(
                    row.get(
                        "source",
                        {},
                    ).get(
                        "path",
                        ""
                    )
                ).casefold(),
                int(
                    row.get(
                        "source",
                        {},
                    ).get(
                        "ordinal",
                        0,
                    )
                    or 0
                ),
                int(
                    row.get(
                        "source",
                        {},
                    ).get(
                        "fragment_index",
                        0,
                    )
                    or 0
                ),
            )
        )

        project_counts[
            project
        ] = atomic_jsonl(
            destination_projects
            / (
                safe_slug(
                    project
                )
                + ".jsonl"
            ),
            rows,
        )

    evidence_root = (
        destination
        / "evidence"
    )

    evidence_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    if original_rows:
        atomic_jsonl(
            evidence_root
            / "pre-boundary-rows.jsonl",
            original_rows,
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
        "statistics": {
            "source_rows_seen":
                source_rows_seen,
            "fragments_emitted":
                fragments_seen,
            "mixed_source_rows":
                mixed_source_rows,
            "projects_emitted":
                len(
                    project_counts
                ),
        },
        "projects":
            project_counts,
        "capabilities": {
            "intra_document_project_detection":
                True,
            "sentence_boundary_segmentation":
                True,
            "adaptive_fragment_sizing":
                True,
            "project_switch_hysteresis":
                True,
            "sticky_context":
                True,
            "ambiguous_fragment_preservation":
                True,
            "unclassified_fragment_preservation":
                True,
            "short_fragment_bridging":
                True,
            "adjacent_fragment_reconstruction":
                True,
            "source_span_lineage":
                True,
            "parent_fingerprint_lineage":
                True,
            "pre_boundary_evidence_preserved":
                True,
            "authority_neutral":
                True,
        },
    }

    manifest[
        "digest"
    ] = stable_digest(
        manifest
    )

    atomic_json(
        destination
        / "manifest.json",
        manifest,
    )

    return manifest


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        prog="extr-boundary"
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

    destination = Path(
        os.path.expanduser(
            os.path.expandvars(
                arguments.destination
            )
        )
    ).resolve()

    try:
        manifest = repartition_corpus(
            corpus_root,
            destination,
        )

    except Exception as error:
        print(
            (
                "extr-boundary: "
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

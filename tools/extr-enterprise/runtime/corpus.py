#!/usr/bin/env python3

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import Any, Iterable


runtime_root = Path(
    "/root/savant-runtime"
)

extr_root = (
    runtime_root
    / "tools"
    / "extr-enterprise"
)

policy_path = (
    extr_root
    / "config"
    / "corpus-policy.json"
)

project_profiles_path = (
    extr_root
    / "config"
    / "projects.json"
)

sys.path.insert(
    0,
    str(
        extr_root
        / "runtime"
    ),
)

import universal


schema = "savant.extr.corpus.v1"


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
            "invalid corpus policy"
        )

    return value


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


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


def stable_digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        stable_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def json_line(
    value: Any,
) -> bytes:
    if orjson is not None:
        return (
            orjson.dumps(
                value
            )
            + b"\n"
        )

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        ).encode(
            "utf-8"
        )
        + b"\n"
    )


def atomic_write_json(
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


def atomic_write_jsonl(
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
                    json_line(
                        row
                    )
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


def discover_files(
    source: Path,
    policy: dict[str, Any],
) -> list[Path]:
    ignored_directories = {
        str(value).casefold()
        for value
        in policy.get(
            "ignored_directory_names",
            [],
        )
    }

    ignored_suffixes = {
        str(value).casefold()
        for value
        in policy.get(
            "ignored_suffixes",
            [],
        )
    }

    discovered: list[Path] = []

    for root, directories, files in os.walk(
        source
    ):
        directories[:] = sorted(
            [
                directory
                for directory
                in directories
                if directory.casefold()
                not in ignored_directories
            ],
            key=str.casefold,
        )

        for filename in sorted(
            files,
            key=str.casefold,
        ):
            path = (
                Path(root)
                / filename
            )

            if (
                path.suffix.casefold()
                in ignored_suffixes
            ):
                continue

            discovered.append(
                path
            )

    return sorted(
        discovered,
        key=lambda path:
            str(path).casefold(),
    )


def read_rows(
    path: Path,
) -> list[
    dict[str, Any]
]:
    rows: list[
        dict[str, Any]
    ] = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line in handle:
            candidate = line.strip()

            if not candidate:
                continue

            value = json.loads(
                candidate
            )

            if isinstance(
                value,
                dict,
            ):
                rows.append(
                    value
                )

    return rows


def extract_one(
    path: Path,
    work_root: Path,
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
]:
    identity = hashlib.sha256(
        str(
            path.resolve()
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    output = (
        work_root
        / f"{identity}.jsonl"
    )

    receipt = universal.extract(
        path,
        output,
        project_profiles_path,
    )

    return (
        read_rows(
            output
        ),
        receipt,
    )


def signal_count(
    row: dict[str, Any],
) -> int:
    project = row.get(
        "project",
        {},
    )

    if not isinstance(
        project,
        dict,
    ):
        return 0

    signals = project.get(
        "signals",
        [],
    )

    return (
        len(signals)
        if isinstance(
            signals,
            list,
        )
        else 0
    )


def classification_bucket(
    row: dict[str, Any],
    policy: dict[str, Any],
) -> str:
    classification = row.get(
        "project",
        {},
    )

    if not isinstance(
        classification,
        dict,
    ):
        return "unclassified"

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

    minimum_signals = int(
        policy.get(
            "classification",
            {},
        ).get(
            "minimum_signals",
            2,
        )
    )

    minimum_confidence = float(
        policy.get(
            "classification",
            {},
        ).get(
            "minimum_confidence",
            0.55,
        )
    )

    ambiguous_margin = float(
        policy.get(
            "classification",
            {},
        ).get(
            "ambiguous_margin",
            0.15,
        )
    )

    if (
        project
        == "unclassified"
        or signal_count(
            row
        )
        < minimum_signals
        or confidence
        < minimum_confidence
    ):
        return "unclassified"

    alternatives = classification.get(
        "alternatives",
        [],
    )

    if isinstance(
        alternatives,
        list,
    ) and alternatives:
        winner_score = signal_count(
            row
        )

        runner_score = int(
            alternatives[0].get(
                "score",
                0,
            )
            or 0
        )

        if winner_score > 0:
            margin = (
                winner_score
                - runner_score
            ) / winner_score

            if margin < ambiguous_margin:
                return "ambiguous"

    return safe_slug(
        project
    )


def boilerplate_signature(
    text: str,
) -> str:
    return universal.text_fingerprint(
        text
    )


def source_identity(
    row: dict[str, Any],
) -> str:
    source = row.get(
        "source",
        {},
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


def source_mtime_ns(
    row: dict[str, Any],
) -> int:
    path = Path(
        source_identity(
            row
        )
    )

    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


def proposition_key(
    text: str,
) -> str:
    normalized = (
        universal.normalized_for_hash(
            text
        )
    )

    for token in (
        " not ",
        " never ",
        " no ",
        " cannot ",
        " can't ",
        " isn't ",
        " wasn't ",
        " doesn't ",
        " didn't ",
        " won't ",
    ):
        normalized = normalized.replace(
            token,
            " ",
        )

    return universal.text_fingerprint(
        normalized
    )


def negation_present(
    text: str,
) -> bool:
    normalized = (
        " "
        + universal.normalized_for_hash(
            text
        )
        + " "
    )

    return any(
        token in normalized
        for token in (
            " not ",
            " never ",
            " no ",
            " cannot ",
            " can't ",
            " isn't ",
            " wasn't ",
            " doesn't ",
            " didn't ",
            " won't ",
        )
    )


def quoted_or_forwarded(
    text: str,
) -> bool:
    stripped = text.lstrip()

    if stripped.startswith(
        ">"
    ):
        return True

    lowered = stripped.casefold()

    return any(
        marker in lowered[:300]
        for marker in (
            "forwarded message",
            "original message",
            "from:",
            "sent:",
            "wrote:",
        )
    )


def corpus_extract(
    source: Path,
    destination: Path,
) -> dict[str, Any]:
    policy = load_policy()

    files = discover_files(
        source,
        policy,
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    staging = Path(
        tempfile.mkdtemp(
            prefix=".extr-corpus-",
            dir=str(
                destination.parent
            ),
        )
    )

    work_root = (
        staging
        / "work"
    )

    work_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_rows: list[
        dict[str, Any]
    ] = []

    file_receipts: list[
        dict[str, Any]
    ] = []

    failures: list[
        dict[str, Any]
    ] = []

    file_segments: dict[
        str,
        set[str]
    ] = defaultdict(
        set
    )

    try:
        for path in files:
            try:
                rows, receipt = (
                    extract_one(
                        path,
                        work_root,
                    )
                )

                file_receipts.append(
                    receipt
                )

                for row in rows:
                    fingerprint = str(
                        row.get(
                            "fingerprint",
                            "",
                        )
                    )

                    if fingerprint:
                        file_segments[
                            str(
                                path.resolve()
                            )
                        ].add(
                            fingerprint
                        )

                    row[
                        "corpus"
                    ] = {
                        "source_mtime_ns":
                            path.stat().st_mtime_ns,
                        "source_size":
                            path.stat().st_size,
                        "quoted_or_forwarded":
                            quoted_or_forwarded(
                                str(
                                    row.get(
                                        "text",
                                        "",
                                    )
                                )
                            ),
                    }

                    all_rows.append(
                        row
                    )

            except Exception as error:
                failures.append(
                    {
                        "path":
                            str(
                                path.resolve()
                            ),
                        "sha256":
                            (
                                sha256_file(
                                    path
                                )
                                if path.is_file()
                                else None
                            ),
                        "error":
                            (
                                type(
                                    error
                                ).__name__
                                + ": "
                                + str(
                                    error
                                )
                            ),
                    }
                )

        file_occurrence = Counter()

        for fingerprints in (
            file_segments.values()
        ):
            file_occurrence.update(
                fingerprints
            )

        boilerplate_policy = (
            policy.get(
                "boilerplate",
                {},
            )
        )

        minimum_files = int(
            boilerplate_policy.get(
                "minimum_files",
                3,
            )
        )

        minimum_fraction = float(
            boilerplate_policy.get(
                "minimum_fraction",
                0.35,
            )
        )

        source_file_count = max(
            1,
            len(
                file_segments
            ),
        )

        boilerplate = {
            fingerprint
            for fingerprint, count
            in file_occurrence.items()
            if (
                count >= minimum_files
                and (
                    count
                    / source_file_count
                )
                >= minimum_fraction
            )
        }

        exact_primary: dict[
            str,
            dict[str, Any]
        ] = {}

        duplicate_lineage: dict[
            str,
            list[dict[str, Any]]
        ] = defaultdict(
            list
        )

        suppressed_boilerplate: list[
            dict[str, Any]
        ] = []

        for row in all_rows:
            fingerprint = str(
                row.get(
                    "fingerprint",
                    "",
                )
            )

            if (
                fingerprint
                in boilerplate
            ):
                suppressed_boilerplate.append(
                    row
                )
                continue

            if (
                fingerprint
                not in exact_primary
            ):
                exact_primary[
                    fingerprint
                ] = row
                continue

            duplicate_lineage[
                fingerprint
            ].append(
                row
            )

        exact_rows = list(
            exact_primary.values()
        )

        exact_rows.sort(
            key=lambda row: (
                source_identity(
                    row
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
                str(
                    row.get(
                        "fingerprint",
                        "",
                    )
                ),
            )
        )

        near_primary: list[
            dict[str, Any]
        ] = []

        near_duplicate_lineage: dict[
            str,
            list[dict[str, Any]]
        ] = defaultdict(
            list
        )

        simhash_index: list[
            tuple[int, dict[str, Any]]
        ] = []

        for row in exact_rows:
            text = str(
                row.get(
                    "text",
                    "",
                )
            )

            value_hash = (
                universal.simhash64(
                    text
                )
            )

            match = None

            for previous_hash, previous_row in (
                simhash_index
            ):
                if (
                    universal.hamming_distance(
                        value_hash,
                        previous_hash,
                    )
                    <= 3
                ):
                    match = (
                        previous_row
                    )
                    break

            if match is None:
                near_primary.append(
                    row
                )

                simhash_index.append(
                    (
                        value_hash,
                        row,
                    )
                )

                continue

            primary_fingerprint = str(
                match.get(
                    "fingerprint",
                    "",
                )
            )

            near_duplicate_lineage[
                primary_fingerprint
            ].append(
                row
            )

        contradiction_groups: dict[
            str,
            list[dict[str, Any]]
        ] = defaultdict(
            list
        )

        for row in near_primary:
            text = str(
                row.get(
                    "text",
                    "",
                )
            )

            contradiction_groups[
                proposition_key(
                    text
                )
            ].append(
                row
            )

        contradictions = []

        for key, rows in (
            contradiction_groups.items()
        ):
            states = {
                negation_present(
                    str(
                        row.get(
                            "text",
                            "",
                        )
                    )
                )
                for row in rows
            }

            if len(states) < 2:
                continue

            contradictions.append(
                {
                    "proposition_key":
                        key,
                    "resolved":
                        False,
                    "claims": [
                        {
                            "fingerprint":
                                row.get(
                                    "fingerprint"
                                ),
                            "source":
                                source_identity(
                                    row
                                ),
                            "source_mtime_ns":
                                source_mtime_ns(
                                    row
                                ),
                            "negated":
                                negation_present(
                                    str(
                                        row.get(
                                            "text",
                                            "",
                                        )
                                    )
                                ),
                        }
                        for row in rows
                    ],
                }
            )

        project_rows: dict[
            str,
            list[dict[str, Any]]
        ] = defaultdict(
            list
        )

        for row in near_primary:
            bucket = (
                classification_bucket(
                    row,
                    policy,
                )
            )

            row[
                "corpus"
            ][
                "classification_bucket"
            ] = bucket

            fingerprint = str(
                row.get(
                    "fingerprint",
                    "",
                )
            )

            row[
                "corpus"
            ][
                "duplicate_lineage_count"
            ] = len(
                duplicate_lineage.get(
                    fingerprint,
                    [],
                )
            )

            row[
                "corpus"
            ][
                "near_duplicate_lineage_count"
            ] = len(
                near_duplicate_lineage.get(
                    fingerprint,
                    [],
                )
            )

            project_rows[
                bucket
            ].append(
                row
            )

        output_root = (
            staging
            / "output"
        )

        projects_root = (
            output_root
            / "projects"
        )

        projects_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        project_counts = {}

        for project in sorted(
            project_rows,
            key=str.casefold,
        ):
            rows = sorted(
                project_rows[
                    project
                ],
                key=lambda row: (
                    source_mtime_ns(
                        row
                    ),
                    source_identity(
                        row
                    ).casefold(),
                    str(
                        row.get(
                            "fingerprint",
                            "",
                        )
                    ),
                ),
            )

            count = (
                atomic_write_jsonl(
                    projects_root
                    / f"{safe_slug(project)}.jsonl",
                    rows,
                )
            )

            project_counts[
                project
            ] = count

        evidence_root = (
            output_root
            / "evidence"
        )

        evidence_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        atomic_write_jsonl(
            evidence_root
            / "boilerplate.jsonl",
            suppressed_boilerplate,
        )

        duplicate_rows = []

        for fingerprint in sorted(
            duplicate_lineage
        ):
            for row in (
                duplicate_lineage[
                    fingerprint
                ]
            ):
                duplicate_rows.append(
                    {
                        "primary_fingerprint":
                            fingerprint,
                        "duplicate":
                            row,
                    }
                )

        atomic_write_jsonl(
            evidence_root
            / "exact-duplicates.jsonl",
            duplicate_rows,
        )

        near_rows = []

        for fingerprint in sorted(
            near_duplicate_lineage
        ):
            for row in (
                near_duplicate_lineage[
                    fingerprint
                ]
            ):
                near_rows.append(
                    {
                        "primary_fingerprint":
                            fingerprint,
                        "duplicate":
                            row,
                    }
                )

        atomic_write_jsonl(
            evidence_root
            / "near-duplicates.jsonl",
            near_rows,
        )

        atomic_write_json(
            evidence_root
            / "contradictions.json",
            {
                "schema":
                    "savant.extr.contradictions.v1",
                "authority_effect":
                    "none",
                "resolved_automatically":
                    False,
                "groups":
                    contradictions,
            },
        )

        quarantine_root = (
            output_root
            / "quarantine"
        )

        quarantine_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        atomic_write_json(
            quarantine_root
            / "failures.json",
            {
                "schema":
                    "savant.extr.quarantine.v1",
                "authority_effect":
                    "none",
                "failures":
                    failures,
            },
        )

        manifest = {
            "schema":
                schema,
            "projection_only":
                True,
            "authority_effect":
                "none",
            "source": {
                "path":
                    str(
                        source.resolve()
                    ),
                "files_discovered":
                    len(
                        files
                    ),
            },
            "outputs": {
                "projects":
                    project_counts,
                "project_count":
                    len(
                        project_counts
                    ),
            },
            "statistics": {
                "segments_ingested":
                    len(
                        all_rows
                    ),
                "segments_after_exact_deduplication":
                    len(
                        exact_rows
                    ),
                "segments_after_near_deduplication":
                    len(
                        near_primary
                    ),
                "exact_duplicates":
                    sum(
                        len(value)
                        for value
                        in duplicate_lineage.values()
                    ),
                "near_duplicates":
                    sum(
                        len(value)
                        for value
                        in near_duplicate_lineage.values()
                    ),
                "boilerplate_suppressed":
                    len(
                        suppressed_boilerplate
                    ),
                "contradiction_groups":
                    len(
                        contradictions
                    ),
                "quarantined_files":
                    len(
                        failures
                    ),
            },
            "capabilities": {
                "recursive_ingestion":
                    True,
                "per_file_format_inference":
                    True,
                "mixed_format_corpora":
                    True,
                "cross_file_exact_deduplication":
                    True,
                "cross_file_near_deduplication":
                    True,
                "duplicate_lineage_preserved":
                    True,
                "boilerplate_frequency_detection":
                    True,
                "boilerplate_evidence_preserved":
                    True,
                "mixed_project_segmentation":
                    True,
                "ambiguous_project_quarantine":
                    True,
                "unclassified_preservation":
                    True,
                "quoted_forwarded_detection":
                    True,
                "contradiction_candidate_detection":
                    True,
                "automatic_contradiction_resolution":
                    False,
                "source_mtime_lineage":
                    True,
                "older_evidence_preserved":
                    True,
                "failure_quarantine":
                    True,
                "deterministic_project_outputs":
                    True,
                "atomic_projection":
                    True,
                "authority_neutral":
                    True,
            },
        }

        manifest[
            "manifest_digest"
        ] = stable_digest(
            manifest
        )

        atomic_write_json(
            output_root
            / "manifest.json",
            manifest,
        )

        if destination.exists():
            backup = (
                destination.parent
                / (
                    destination.name
                    + ".previous"
                )
            )

            if backup.exists():
                if backup.is_dir():
                    shutil.rmtree(
                        backup
                    )
                else:
                    backup.unlink()

            os.replace(
                destination,
                backup,
            )

        os.replace(
            output_root,
            destination,
        )

        return manifest

    finally:
        shutil.rmtree(
            staging,
            ignore_errors=True,
        )


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        prog="extr-corpus"
    )

    value.add_argument(
        "source"
    )

    value.add_argument(
        "destination"
    )

    return value


def main() -> int:
    arguments = parser().parse_args()

    source = Path(
        os.path.expanduser(
            os.path.expandvars(
                arguments.source
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

    if not source.is_dir():
        print(
            f"extr-corpus: source is not a directory: "
            f"{source}",
            file=sys.stderr,
        )
        return 1

    try:
        manifest = corpus_extract(
            source,
            destination,
        )

    except Exception as error:
        print(
            "extr-corpus: "
            + type(
                error
            ).__name__
            + ": "
            + str(
                error
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

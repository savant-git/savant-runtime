#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

REPORT_PATH = (
    ROOT
    / "runtime/reports/scyon-focal-compatibility-inventory.json"
)

AUTHORITY_FILES = (
    ROOT
    / "authority/accepted-decisions/"
    "AD-20260806-004-scyon-focal-architecture.md",
    ROOT
    / "authority/accepted-decisions/"
    "AD-20260806-005-scyon-focal-mutation-boundary.md",
    ROOT
    / "canon/structure/"
    "SAVANT_SCYON_FOCAL_CONTRACT_v1.0.0.json",
)

MAX_FILE_SIZE = 8 * 1024 * 1024

SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    "node_modules",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "vendor",
}

LEGACY_TERMS = {
    "dimensional_database_phrase": re.compile(
        r"\bdimensional database(?:s)?\b",
        re.IGNORECASE,
    ),
    "dimensional_database_hyphen": re.compile(
        r"\bdimensional-database\b",
        re.IGNORECASE,
    ),
    "dimensional_database_identifier": re.compile(
        r"\bdimensional_database\b",
        re.IGNORECASE,
    ),
    "dimensional_database_class": re.compile(
        r"\bDimensionalDatabase\b",
    ),
    "database_kernel": re.compile(
        r"\bdatabase kernel\b",
        re.IGNORECASE,
    ),
    "database_instance": re.compile(
        r"\bdatabase instance\b",
        re.IGNORECASE,
    ),
    "custom_overlay": re.compile(
        r"\bcustom overlay(?:s)?\b",
        re.IGNORECASE,
    ),
    "overlay_instance": re.compile(
        r"\boverlay instance\b",
        re.IGNORECASE,
    ),
    "overlay_identifier": re.compile(
        r"\boverlay identifier\b",
        re.IGNORECASE,
    ),
    "overlay_kind_phrase": re.compile(
        r"\boverlay kind\b",
        re.IGNORECASE,
    ),
    "overlay_id": re.compile(
        r"\boverlay_id\b",
        re.IGNORECASE,
    ),
    "overlay_kind": re.compile(
        r"\boverlay_kind\b",
        re.IGNORECASE,
    ),
    "overlays": re.compile(
        r"\boverlays\b",
        re.IGNORECASE,
    ),
}

CANONICAL_TERMS = {
    "scyon": re.compile(
        r"\bScyon(?:s)?\b",
        re.IGNORECASE,
    ),
    "scyon_kernel": re.compile(
        r"\bScyon kernel\b",
        re.IGNORECASE,
    ),
    "scyon_instance": re.compile(
        r"\bScyon instance\b",
        re.IGNORECASE,
    ),
    "focal": re.compile(
        r"\bFocal(?:s)?\b",
        re.IGNORECASE,
    ),
    "focal_instance": re.compile(
        r"\bFocal instance\b",
        re.IGNORECASE,
    ),
    "focal_id": re.compile(
        r"\bfocal_id\b",
        re.IGNORECASE,
    ),
    "focal_kind": re.compile(
        r"\bfocal_kind\b",
        re.IGNORECASE,
    ),
}

TERM_MAPPING = {
    "dimensional database": "Scyon",
    "dimensional database kernel": "Scyon kernel",
    "dimensional database instance": "Scyon instance",
    "custom overlay": "Focal",
    "overlay instance": "Focal instance",
    "overlay identifier": "Focal identifier",
    "overlay kind": "Focal kind",
    "overlay_id": "focal_id",
    "overlay_kind": "focal_kind",
    "overlays": "focals",
}

TEXT_SUFFIXES = {
    ".py",
    ".sh",
    ".bash",
    ".zsh",
    ".json",
    ".jsonl",
    ".ndjson",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".md",
    ".txt",
    ".sql",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
    ".xml",
    ".service",
    ".socket",
    ".target",
}


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def sha256_file(
    path: Path,
) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            hasher.update(chunk)

    return hasher.hexdigest()


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def report_digest(
    report: dict[str, Any],
) -> str:
    copy = dict(report)
    copy.pop(
        "report_digest",
        None,
    )

    return hashlib.sha256(
        canonical_json(
            copy
        ).encode("utf-8")
    ).hexdigest()


def is_text_candidate(
    path: Path,
) -> bool:
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True

    if path.name in {
        "Dockerfile",
        "Makefile",
        "Procfile",
    }:
        return True

    return False


def context_for(
    text: str,
    start: int,
    end: int,
    radius: int = 80,
) -> str:
    left = max(
        0,
        start - radius,
    )

    right = min(
        len(text),
        end + radius,
    )

    return (
        text[left:right]
        .replace("\n", " ")
        .replace("\r", " ")
    )


def authority_state() -> dict[str, Any]:
    records = []

    for path in AUTHORITY_FILES:
        exists = (
            path.is_file()
            and path.stat().st_size > 0
        )

        record = {
            "path": str(path),
            "exists": exists,
            "sha256": (
                sha256_file(path)
                if exists
                else None
            ),
        }

        records.append(record)

    return {
        "records": records,
        "ready": all(
            record["exists"]
            for record in records
        ),
    }


def scan_file(
    path: Path,
) -> dict[str, Any] | None:
    try:
        size = path.stat().st_size

    except OSError:
        return None

    if size > MAX_FILE_SIZE:
        return {
            "path": str(path),
            "status": "skipped_size",
            "size": size,
        }

    if not is_text_candidate(path):
        return None

    try:
        text = path.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:
        return {
            "path": str(path),
            "status": "skipped_binary_or_encoding",
            "size": size,
        }

    except OSError:
        return {
            "path": str(path),
            "status": "read_error",
            "size": size,
        }

    legacy_occurrences = []
    canonical_occurrences = []

    for key, pattern in LEGACY_TERMS.items():
        for match in pattern.finditer(text):
            legacy_occurrences.append(
                {
                    "term_key": key,
                    "match": match.group(0),
                    "line": (
                        text.count(
                            "\n",
                            0,
                            match.start(),
                        )
                        + 1
                    ),
                    "context": context_for(
                        text,
                        match.start(),
                        match.end(),
                    ),
                }
            )

    for key, pattern in CANONICAL_TERMS.items():
        for match in pattern.finditer(text):
            canonical_occurrences.append(
                {
                    "term_key": key,
                    "match": match.group(0),
                    "line": (
                        text.count(
                            "\n",
                            0,
                            match.start(),
                        )
                        + 1
                    ),
                    "context": context_for(
                        text,
                        match.start(),
                        match.end(),
                    ),
                }
            )

    if (
        not legacy_occurrences
        and not canonical_occurrences
    ):
        return None

    return {
        "path": str(path),
        "status": "scanned",
        "size": size,
        "sha256": sha256_file(path),
        "executable": os.access(
            path,
            os.X_OK,
        ),
        "legacy_occurrences": (
            legacy_occurrences
        ),
        "canonical_occurrences": (
            canonical_occurrences
        ),
    }


def walk() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    results = []
    skipped = []

    for current_root, directories, files in os.walk(
        ROOT
    ):
        directories[:] = sorted(
            directory
            for directory in directories
            if directory not in SKIP_DIR_NAMES
        )

        current = Path(current_root)

        for filename in sorted(files):
            path = (
                current
                / filename
            )

            result = scan_file(path)

            if result is None:
                continue

            if result["status"] == "scanned":
                results.append(result)
            else:
                skipped.append(result)

    return results, skipped


def count_terms(
    files: list[dict[str, Any]],
    field: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}

    for file_record in files:
        for occurrence in file_record[
            field
        ]:
            key = occurrence[
                "term_key"
            ]

            counts[key] = (
                counts.get(
                    key,
                    0,
                )
                + 1
            )

    return dict(
        sorted(
            counts.items()
        )
    )


def main() -> int:
    if not ROOT.is_dir():
        print(
            f"ERROR: root not found: {ROOT}",
            file=sys.stderr,
        )

        return 1

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    authority = authority_state()

    files, skipped = walk()

    legacy_counts = count_terms(
        files,
        "legacy_occurrences",
    )

    canonical_counts = count_terms(
        files,
        "canonical_occurrences",
    )

    legacy_total = sum(
        legacy_counts.values()
    )

    canonical_total = sum(
        canonical_counts.values()
    )

    affected_files = sorted(
        {
            record["path"]
            for record in files
            if record[
                "legacy_occurrences"
            ]
        }
    )

    executable_files = sorted(
        {
            record["path"]
            for record in files
            if (
                record["executable"]
                and record[
                    "legacy_occurrences"
                ]
            )
        }
    )

    occurrences = []

    for record in files:
        for occurrence in record[
            "legacy_occurrences"
        ]:
            occurrences.append(
                {
                    "classification": (
                        "legacy"
                    ),
                    "path": record["path"],
                    **occurrence,
                }
            )

        for occurrence in record[
            "canonical_occurrences"
        ]:
            occurrences.append(
                {
                    "classification": (
                        "canonical"
                    ),
                    "path": record["path"],
                    **occurrence,
                }
            )

    report: dict[str, Any] = {
        "report_type": (
            "savant.scyon-focal."
            "compatibility-inventory"
        ),
        "schema_version": "1.0.0",
        "generated_at": utc_now(),
        "root": str(ROOT),
        "mutation_performed": False,
        "migration_authorized": False,
        "authority_ready": (
            authority["ready"]
        ),
        "authority": authority,
        "expected_identity_tiers": [
            "iota",
            "mote",
            "trait",
            "quirk",
            "prodigal",
            "exile",
            "innate",
            "portal",
            "obelisk",
        ],
        "atomic_exclusions": [
            "iota",
            "mote",
        ],
        "term_mapping": TERM_MAPPING,
        "summary": {
            "files_with_relevant_terms": (
                len(files)
            ),
            "legacy_occurrences": (
                legacy_total
            ),
            "canonical_occurrences": (
                canonical_total
            ),
            "affected_files": (
                len(
                    affected_files
                )
            ),
            "affected_executables": (
                len(
                    executable_files
                )
            ),
            "skipped_files": (
                len(skipped)
            ),
        },
        "legacy_counts": legacy_counts,
        "canonical_counts": canonical_counts,
        "affected_files": affected_files,
        "executable_files": executable_files,
        "occurrences": occurrences,
        "files": files,
        "skipped": skipped,
    }

    report["report_digest"] = (
        report_digest(
            report
        )
    )

    temporary_path = (
        REPORT_PATH.parent
        / (
            REPORT_PATH.name
            + ".tmp"
        )
    )

    temporary_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    os.replace(
        temporary_path,
        REPORT_PATH,
    )

    print(
        f"REPORT: {REPORT_PATH}"
    )
    print(
        f"AUTHORITY READY: "
        f"{str(authority['ready']).lower()}"
    )
    print(
        f"LEGACY OCCURRENCES: "
        f"{legacy_total}"
    )
    print(
        f"CANONICAL OCCURRENCES: "
        f"{canonical_total}"
    )
    print(
        f"AFFECTED FILES: "
        f"{len(affected_files)}"
    )
    print(
        f"AFFECTED EXECUTABLES: "
        f"{len(executable_files)}"
    )
    print(
        "MUTATION PERFORMED: false"
    )
    print(
        "MIGRATION AUTHORIZED: false"
    )
    print(
        f"REPORT DIGEST: "
        f"{report['report_digest']}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

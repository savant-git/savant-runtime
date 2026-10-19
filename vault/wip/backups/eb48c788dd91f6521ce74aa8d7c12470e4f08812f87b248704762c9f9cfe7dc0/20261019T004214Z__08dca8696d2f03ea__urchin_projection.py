
#!/usr/bin/env python3
"""Read-only projection of undocumented source candidates from an sdump."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

SCHEMA = "savant.urchin.candidate_projection.v1"

EXCLUDED_PARTS = frozenset({
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "vendor",
    "backups",
    "backup",
    "archive",
    "archives",
})

SOURCE_SUFFIXES = frozenset({
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".html", ".css", ".sh", ".rs", ".go",
    ".java", ".c", ".h", ".cpp", ".sql",
    ".yaml", ".yml", ".json", ".toml",
})

FILE_HEADER = "=== file ==="
CONTENT_HEADER = "=== content ==="
FILE_END = "=== /file ==="


def canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def fingerprint(value):
    return hashlib.sha256(
        canonical(value).encode("utf-8")
    ).hexdigest()


def normalize_path(value):
    if not isinstance(value, str):
        return None

    value = value.replace("\\", "/")
    path = PurePosixPath(value)

    if (
        path.is_absolute()
        or ".." in path.parts
        or not path.parts
        or value.startswith("./")
    ):
        return None

    return path.as_posix()


def source_records(snapshot):
    with gzip.open(snapshot, "rt", encoding="utf-8", errors="replace") as stream:
        state = "outside"
        metadata = None

        for raw in stream:
            line = raw.rstrip("\r\n")

            if state == "outside":
                if line == FILE_HEADER:
                    state = "metadata"
                continue

            if state == "metadata":
                try:
                    candidate = json.loads(line)
                except json.JSONDecodeError:
                    state = "outside"
                    continue

                if not isinstance(candidate, dict):
                    state = "outside"
                    continue

                metadata = candidate
                state = "await_content"
                continue

            if state == "await_content":
                if line == CONTENT_HEADER:
                    yield metadata
                    state = "content"
                elif line == FILE_HEADER:
                    state = "metadata"
                continue

            if state == "content" and line == FILE_END:
                state = "outside"
                metadata = None


def read_doctrine(path):
    return Path(path).read_text(encoding="utf-8").lower()


def path_is_documented(path, doctrine):
    normalized = path.lower()
    filename = PurePosixPath(normalized).name

    if normalized in doctrine:
        return True

    if len(filename) >= 12 and filename in doctrine:
        return True

    return False


def classify(path):
    parts = PurePosixPath(path).parts
    return {
        "source_area": parts[0] if parts else "unknown",
        "extension": PurePosixPath(path).suffix.lower() or "none",
        "parent": str(PurePosixPath(path).parent),
    }


def candidates(snapshot, doctrine):
    seen = set()
    duplicates = 0
    rejected = 0
    records = []

    for metadata in source_records(snapshot):
        path = normalize_path(metadata.get("path"))

        if path is None:
            rejected += 1
            continue

        if path in seen:
            duplicates += 1
            continue

        seen.add(path)

        pure = PurePosixPath(path)

        if any(part.lower() in EXCLUDED_PARTS for part in pure.parts):
            continue

        if pure.suffix.lower() not in SOURCE_SUFFIXES:
            continue

        if path_is_documented(path, doctrine):
            continue

        try:
            size = int(metadata.get("size", 0))
        except (TypeError, ValueError):
            size = 0

        record = {
            "id": "candidate:" + fingerprint(path)[:24],
            "path": path,
            "size": max(0, size),
            "classification": classify(path),
            "evidence": {
                "kind": "sdump_file_record",
                "snapshot": Path(snapshot).name,
            },
            "documentation_match": "not_found_by_literal_path_or_filename",
            "authority": "unresolved",
            "urchin_status": "candidate_only",
            "frag_status": "not_established",
            "composition": {
                "edifice": None,
                "level": None,
                "instances": [],
                "typed_segues": [],
            },
        }

        records.append(record)

    records.sort(key=lambda record: record["path"])

    return records, duplicates, rejected, len(seen)


def project(snapshot, doctrine_path):
    doctrine = read_doctrine(doctrine_path)
    records, duplicates, rejected, unique = candidates(
        snapshot,
        doctrine,
    )

    areas = defaultdict(list)
    extensions = Counter()

    for record in records:
        area = record["classification"]["source_area"]
        areas[area].append(record["id"])
        extensions[record["classification"]["extension"]] += 1

    result = {
        "schema": SCHEMA,
        "authority_effect": "none",
        "projection_only": True,
        "snapshot": Path(snapshot).name,
        "doctrine": Path(doctrine_path).name,
        "method": {
            "selection": "source files without literal path or filename matches",
            "limitations": [
                "absence of a literal match does not prove undocumented functionality",
                "one file does not necessarily equal one frag",
                "a candidate is not an accepted urchin",
                "architectural levels require verified instance composition",
                "no source or doctrine files are modified",
            ],
        },
        "counts": {
            "unique_paths_seen": unique,
            "duplicate_path_records": duplicates,
            "invalid_path_records": rejected,
            "candidate_files": len(records),
        },
        "groups": {
            key: sorted(ids)
            for key, ids in sorted(areas.items())
        },
        "extensions": dict(sorted(extensions.items())),
        "candidates": records,
    }

    result["projection_digest"] = fingerprint(result)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Project source candidates without changing authority."
    )
    parser.add_argument(
        "--snapshot",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--doctrine",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--summary",
        action="store_true",
    )
    args = parser.parse_args()

    try:
        result = project(args.snapshot, args.doctrine)
    except (OSError, EOFError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.summary:
        result.pop("candidates")
        result.pop("groups")

    print(json.dumps(
        result,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

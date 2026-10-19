
#!/usr/bin/env python3
"""Deterministic, read-only sdump-to-doctrine candidate projection."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

SCHEMA = "savant.urchin.candidate_projection.v2"

SOURCE_EXTENSIONS = frozenset({
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".html", ".css", ".sh", ".rs", ".go",
    ".java", ".c", ".h", ".cpp", ".sql",
    ".yaml", ".yml", ".toml",
})

EXCLUDED_SEGMENTS = frozenset({
    ".git", "__pycache__", "node_modules",
    ".venv", "vendor", "backups", "backup",
    "archives", "archive",
})

BEGIN_FILE = "=== file ==="
END_FILE = "=== /file ==="
BEGIN_CONTENT = "=== content ==="

MAX_METADATA_BYTES = 65536
MAX_CANDIDATES = 1000000


def canonical_json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest(value):
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def normalize_path(value):
    if not isinstance(value, str) or not value:
        return None

    value = value.replace("\\", "/")
    path = PurePosixPath(value)

    if (
        path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
        or "\x00" in value
    ):
        return None

    return path.as_posix()


def snapshot_records(snapshot):
    """Read only record metadata; never execute archived source."""

    with gzip.open(snapshot, "rb") as stream:
        state = "outside"
        metadata = None

        for raw in stream:
            line = raw.rstrip(b"\r\n")

            if state == "outside":
                if line == BEGIN_FILE.encode():
                    state = "metadata"
                continue

            if state == "metadata":
                state = "outside"

                if len(line) > MAX_METADATA_BYTES:
                    continue

                try:
                    metadata = json.loads(line)
                except (UnicodeError, ValueError):
                    continue

                if not isinstance(metadata, dict):
                    continue

                state = "await_content"
                continue

            if state == "await_content":
                if line == BEGIN_CONTENT.encode():
                    state = "content"
                    yield metadata
                elif line == BEGIN_FILE.encode():
                    state = "metadata"
                else:
                    state = "outside"
                continue

            if state == "content":
                if line == END_FILE.encode():
                    state = "outside"
                    metadata = None


def doctrine_index(doctrine_path):
    text = doctrine_path.read_text(
        encoding="utf-8",
    ).casefold()

    tokens = set(
        re.findall(r"[a-z0-9][a-z0-9_.-]*", text)
    )

    return text, tokens


def documentation_match(path, doctrine_text, tokens):
    path_lower = path.casefold()
    name = PurePosixPath(path_lower).name
    stem = PurePosixPath(name).stem

    if path_lower in doctrine_text:
        return "exact_path"

    if len(name) >= 12 and name in tokens:
        return "filename"

    if len(stem) >= 12 and stem in tokens:
        return "stem"

    return None


def candidate_classification(path):
    parts = PurePosixPath(path).parts

    return {
        "source_area": parts[0] if parts else "unknown",
        "directory": str(PurePosixPath(path).parent),
        "extension": PurePosixPath(path).suffix.lower(),
    }


def project(snapshot, doctrine_path):
    doctrine_text, tokens = doctrine_index(
        doctrine_path
    )

    seen = set()
    candidates = []
    documented = Counter()
    exclusions = Counter()
    source_areas = defaultdict(list)
    extensions = Counter()

    for metadata in snapshot_records(snapshot):
        path = normalize_path(
            metadata.get("path")
        )

        if path is None:
            exclusions["invalid_path"] += 1
            continue

        if path in seen:
            exclusions["duplicate_path"] += 1
            continue

        seen.add(path)

        pure = PurePosixPath(path)

        if any(
            segment.casefold() in EXCLUDED_SEGMENTS
            for segment in pure.parts
        ):
            exclusions["excluded_directory"] += 1
            continue

        if pure.suffix.lower() not in SOURCE_EXTENSIONS:
            exclusions["non_source_extension"] += 1
            continue

        match = documentation_match(
            path,
            doctrine_text,
            tokens,
        )

        if match is not None:
            documented[match] += 1
            continue

        if len(candidates) >= MAX_CANDIDATES:
            raise ValueError(
                "candidate limit exceeded"
            )

        try:
            size = int(metadata.get("size", 0))
        except (TypeError, ValueError):
            size = 0

        classification = candidate_classification(path)

        record = {
            "candidate_id": "candidate:" + digest(path)[:24],
            "source_path": path,
            "source_bytes": max(0, size),
            "classification": classification,
            "evidence": {
                "kind": "sdump_file_metadata",
                "snapshot": snapshot.name,
            },
            "documentation": {
                "status": "no_literal_match",
                "method": "path_filename_stem",
            },
            "architectural_status": {
                "urchin": "unconfirmed",
                "frag": "unconfirmed",
                "edifice": None,
                "level": None,
                "vagary": None,
                "spasms": [],
                "iotas": [],
                "instances": [],
                "typed_segues": [],
            },
            "authority": "unresolved",
            "description": None,
            "provenance": [],
        }

        candidates.append(record)

        source_areas[
            classification["source_area"]
        ].append(record["candidate_id"])

        extensions[
            classification["extension"]
        ] += 1

    candidates.sort(
        key=lambda item: item["source_path"]
    )

    result = {
        "schema": SCHEMA,
        "authority_effect": "none",
        "read_only": True,
        "snapshot": snapshot.name,
        "doctrine": doctrine_path.name,
        "terminology": {
            "urchin": {
                "status": "user_directive",
                "meaning": (
                    "implementation present in source "
                    "but not yet incorporated into doctrine"
                ),
            },
            "utility_level_03": "vagary",
            "utility_lower_composition": [
                "glyph",
                "iota",
                "spasm",
                "vagary",
            ],
        },
        "method": {
            "source": "sdump file metadata",
            "documentation": (
                "casefolded literal path, filename, "
                "or stem occurrence"
            ),
            "limitations": [
                "literal absence does not prove undocumented functionality",
                "source file count does not equal frag count",
                "source file count does not equal urchin count",
                "candidates are not accepted authority",
                "architectural composition requires source evidence",
                "no source, doctrine, or lexicon is modified",
            ],
        },
        "counts": {
            "unique_source_paths": len(seen),
            "candidate_files": len(candidates),
            "documented_matches": dict(
                sorted(documented.items())
            ),
            "excluded": dict(
                sorted(exclusions.items())
            ),
        },
        "groups": {
            area: sorted(ids)
            for area, ids in sorted(
                source_areas.items()
            )
        },
        "extensions": dict(
            sorted(extensions.items())
        ),
        "candidates": candidates,
    }

    result["projection_digest"] = digest(result)
    return result


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Read-only source-to-doctrine "
            "candidate projection"
        )
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
        result = project(
            args.snapshot,
            args.doctrine,
        )
    except (
        OSError,
        EOFError,
        UnicodeError,
        ValueError,
    ) as error:
        print(
            str(error),
            file=sys.stderr,
        )
        return 1

    if args.summary:
        result.pop("candidates")
        result.pop("groups")

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


#!/usr/bin/env python3
"""Deterministic, read-only organization of source-derived urchin candidates.

This utility does not create authoritative frags, vagaries, spasms, or iotas.
It produces rebuildable directory, extension, and source-area projections.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import PurePosixPath

INPUT_SCHEMA = "savant.urchin.candidate_projection.v2"
OUTPUT_SCHEMA = "savant.urchin.organization_projection.v2"


def canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def digest(value):
    return hashlib.sha256(
        canonical(value).encode("utf-8")
    ).hexdigest()


def identity(kind, value):
    return kind + ":" + digest(value)[:32]


def normalize_path(value):
    if not isinstance(value, str) or not value:
        raise ValueError("missing source path")

    if "\x00" in value or "\\" in value:
        raise ValueError("invalid source path")

    path = PurePosixPath(value)

    if (
        path.is_absolute()
        or value.startswith("./")
        or "//" in value
        or any(part == ".." for part in path.parts)
        or path.as_posix() != value
    ):
        raise ValueError("noncanonical source path")

    return value


def normalize_candidate(record):
    if not isinstance(record, dict):
        raise ValueError("candidate must be an object")

    path = normalize_path(record.get("source_path"))
    candidate_id = record.get("candidate_id")

    if not isinstance(candidate_id, str):
        raise ValueError("invalid candidate identifier")

    expected = identity_legacy(path)

    if candidate_id != expected:
        raise ValueError(
            "candidate identifier does not match source path"
        )

    return {
        "candidate_id": candidate_id,
        "source_path": path,
        "source_bytes": normalize_size(
            record.get("source_bytes")
        ),
        "authority": record.get(
            "authority",
            "unresolved",
        ),
        "evidence": record.get("evidence", {}),
        "documentation": record.get(
            "documentation",
            {},
        ),
        "architectural_status": record.get(
            "architectural_status",
            {},
        ),
    }


def identity_legacy(path):
    return "candidate:" + hashlib.sha256(
        canonical(path).encode("utf-8")
    ).hexdigest()[:24]


def normalize_size(value):
    if isinstance(value, bool):
        raise ValueError("invalid source size")

    if not isinstance(value, int) or value < 0:
        raise ValueError("invalid source size")

    return value


def ancestors(path):
    parts = PurePosixPath(path).parts[:-1]

    yield ""

    for index in range(1, len(parts) + 1):
        yield "/".join(parts[:index])


def parent_directory(directory):
    if not directory:
        return None

    parent = PurePosixPath(directory).parent
    return "" if str(parent) == "." else parent.as_posix()


def project(source):
    if not isinstance(source, dict):
        raise ValueError("input must be an object")

    if source.get("schema") != INPUT_SCHEMA:
        raise ValueError("unsupported input schema")

    if source.get("authority_effect") != "none":
        raise ValueError("authoritative input is not accepted")

    raw = source.get("candidates")

    if not isinstance(raw, list):
        raise ValueError("candidate collection is missing")

    candidates = {}
    paths = {}

    directories = defaultdict(
        lambda: {
            "direct": set(),
            "descendants": set(),
            "children": set(),
        }
    )

    extensions = defaultdict(set)
    areas = defaultdict(set)

    for item in raw:
        record = normalize_candidate(item)
        candidate_id = record["candidate_id"]
        path = record["source_path"]

        previous = candidates.get(candidate_id)

        if previous is not None:
            if previous != record:
                raise ValueError(
                    "conflicting duplicate candidate"
                )
            continue

        if path in paths and paths[path] != candidate_id:
            raise ValueError(
                "multiple identities for one source path"
            )

        candidates[candidate_id] = record
        paths[path] = candidate_id

        chain = list(ancestors(path))

        for directory in chain:
            directories[directory]["descendants"].add(
                candidate_id
            )

        direct_parent = chain[-1]
        directories[direct_parent]["direct"].add(
            candidate_id
        )

        for index in range(1, len(chain)):
            parent = chain[index - 1]
            child = chain[index]

            directories[parent]["children"].add(child)

        suffix = (
            PurePosixPath(path).suffix.lower()
            or "none"
        )

        extensions[suffix].add(candidate_id)

        area = PurePosixPath(path).parts[0]
        areas[area].add(candidate_id)

    nodes = []

    for directory, data in sorted(directories.items()):
        parent = parent_directory(directory)

        nodes.append({
            "id": identity("directory", directory),
            "kind": "directory_projection",
            "path": directory,
            "parent": (
                identity("directory", parent)
                if parent is not None
                else None
            ),
            "children": [
                identity("directory", child)
                for child in sorted(data["children"])
            ],
            "direct_candidates": sorted(
                data["direct"]
            ),
            "direct_count": len(data["direct"]),
            "descendant_count": len(
                data["descendants"]
            ),
        })

    facets = []

    for kind, mapping in (
        ("extension", extensions),
        ("source_area", areas),
    ):
        for value, members in sorted(mapping.items()):
            facets.append({
                "id": identity(
                    kind,
                    value,
                ),
                "kind": kind,
                "value": value,
                "candidate_ids": sorted(members),
                "candidate_count": len(members),
            })

    ordered = sorted(
        candidates.values(),
        key=lambda item: (
            item["source_path"],
            item["candidate_id"],
        ),
    )

    result = {
        "schema": OUTPUT_SCHEMA,
        "authority_effect": "none",
        "projection_only": True,
        "input_schema": INPUT_SCHEMA,
        "source_projection_digest": source.get(
            "projection_digest"
        ),
        "snapshot": source.get("snapshot"),
        "doctrine": source.get("doctrine"),
        "organization": {
            "directory_tree": "derived",
            "extension_facets": "derived",
            "source_area_facets": "derived",
            "candidate_identity": "preserved",
            "source_mutation": False,
            "authority_mutation": False,
        },
        "architectural_status": {
            "urchin": "candidate_only",
            "frag": "not_inferred",
            "vagary": "not_instantiated",
            "spasm": "not_instantiated",
            "iota": "not_instantiated",
            "typed_segues": "not_inferred",
        },
        "counts": {
            "candidates": len(ordered),
            "directory_nodes": len(nodes),
            "facets": len(facets),
        },
        "directory_nodes": nodes,
        "facets": facets,
        "candidates": ordered,
    }

    result["projection_digest"] = digest(result)
    return result


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Organize source-derived urchin candidates "
            "without changing architectural authority."
        )
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to the candidate projection JSON",
    )

    parser.add_argument(
        "--summary",
        action="store_true",
    )

    args = parser.parse_args()

    try:
        with open(
            args.input,
            "r",
            encoding="utf-8",
        ) as stream:
            source = json.load(stream)

        result = project(source)

    except (
        OSError,
        ValueError,
        TypeError,
        OverflowError,
    ) as error:
        print(str(error), file=sys.stderr)
        return 1

    if args.summary:
        result.pop("directory_nodes")
        result.pop("facets")
        result.pop("candidates")

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

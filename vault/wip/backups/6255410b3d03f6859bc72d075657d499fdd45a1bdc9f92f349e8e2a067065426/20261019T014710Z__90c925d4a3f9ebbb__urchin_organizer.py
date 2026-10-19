
#!/usr/bin/env python3
"""Deterministic, non-authoritative organization of urchin candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import PurePosixPath

INPUT_SCHEMA = "savant.urchin.candidate_projection.v2"
OUTPUT_SCHEMA = "savant.urchin.organization_projection.v1"


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def digest(value):
    return hashlib.sha256(
        canonical(value).encode("utf-8")
    ).hexdigest()


def identifier(kind, value):
    return kind + ":" + digest(value)[:24]


def normalize_record(record):
    if not isinstance(record, dict):
        raise ValueError("candidate must be an object")

    candidate_id = record.get("candidate_id")
    path = record.get("source_path")

    if not isinstance(candidate_id, str) or not candidate_id:
        raise ValueError("invalid candidate identifier")

    if not isinstance(path, str) or not path:
        raise ValueError("invalid source path")

    pure = PurePosixPath(path)

    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError("unsafe source path")

    return {
        "candidate_id": candidate_id,
        "source_path": pure.as_posix(),
        "source_bytes": record.get("source_bytes"),
        "authority": record.get("authority", "unresolved"),
        "evidence": record.get("evidence", {}),
    }


def directory_ancestors(path):
    parent = PurePosixPath(path).parent

    if str(parent) == ".":
        return [""]

    ancestors = []
    current = parent

    while str(current) != ".":
        ancestors.append(current.as_posix())
        current = current.parent

    ancestors.append("")
    ancestors.reverse()
    return ancestors


def organize(source):
    if not isinstance(source, dict):
        raise ValueError("input must be an object")

    if source.get("schema") != INPUT_SCHEMA:
        raise ValueError("unsupported projection schema")

    if source.get("authority_effect") != "none":
        raise ValueError("input must be non-authoritative")

    raw_candidates = source.get("candidates")

    if not isinstance(raw_candidates, list):
        raise ValueError("input lacks candidate records")

    candidates = {}
    directories = defaultdict(set)
    extensions = defaultdict(set)

    for raw in raw_candidates:
        record = normalize_record(raw)
        candidate_id = record["candidate_id"]
        path = record["source_path"]

        if candidate_id in candidates:
            if candidates[candidate_id] != record:
                raise ValueError("conflicting candidate identifier")
            continue

        candidates[candidate_id] = record

        for directory in directory_ancestors(path):
            directories[directory].add(candidate_id)

        suffix = PurePosixPath(path).suffix.lower() or "none"
        extensions[suffix].add(candidate_id)

    nodes = []

    for directory, members in sorted(directories.items()):
        direct_members = sorted(
            candidate_id
            for candidate_id in members
            if str(
                PurePosixPath(
                    candidates[candidate_id]["source_path"]
                ).parent
            ) == (directory or ".")
        )

        children = sorted(
            child
            for child in directories
            if child != directory
            and str(PurePosixPath(child).parent) == (
                directory or "."
            )
        )

        nodes.append({
            "node_id": identifier("directory", directory),
            "kind": "directory_projection",
            "path": directory,
            "parent_id": (
                identifier(
                    "directory",
                    str(PurePosixPath(directory).parent)
                    if str(PurePosixPath(directory).parent) != "."
                    else "",
                )
                if directory else None
            ),
            "children": [
                identifier("directory", child)
                for child in children
            ],
            "direct_candidate_ids": direct_members,
            "descendant_candidate_count": len(members),
        })

    facets = [
        {
            "facet_id": identifier("extension", suffix),
            "kind": "extension",
            "value": suffix,
            "candidate_ids": sorted(members),
        }
        for suffix, members in sorted(extensions.items())
    ]

    ordered_candidates = sorted(
        candidates.values(),
        key=lambda record: (
            record["source_path"],
            record["candidate_id"],
        ),
    )

    result = {
        "schema": OUTPUT_SCHEMA,
        "authority_effect": "none",
        "projection_only": True,
        "source_projection_digest": source.get(
            "projection_digest"
        ),
        "snapshot": source.get("snapshot"),
        "doctrine": source.get("doctrine"),
        "counts": {
            "candidates": len(ordered_candidates),
            "directory_nodes": len(nodes),
            "extension_facets": len(facets),
        },
        "architectural_constraints": {
            "urchin": "unconfirmed_candidate",
            "frag": "not_inferred_from_file",
            "vagary": "not_instantiated",
            "spasm": "not_instantiated",
            "iota": "not_instantiated",
            "typed_segues": "not_inferred",
            "authority": "unresolved",
        },
        "directory_nodes": nodes,
        "facets": facets,
        "candidates": ordered_candidates,
    }

    result["projection_digest"] = digest(result)
    return result


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Organize urchin candidates without changing "
            "Savant architectural authority."
        )
    )
    parser.add_argument(
        "--summary",
        action="store_true",
    )
    args = parser.parse_args()

    try:
        source = json.load(sys.stdin)
        result = organize(source)
    except (ValueError, TypeError, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 1

    if args.summary:
        result.pop("candidates")
        result.pop("directory_nodes")
        result.pop("facets")

    print(json.dumps(
        result,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path("/root/savant-runtime")

GRAPH_PATH = (
    ROOT
    / "authority"
    / "task-graph"
    / "masterplan.json"
)

INTEGRITY_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "integrity"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "integrity-tree"
)

AUTHORITATIVE_COLLECTIONS = (
    "records",
    "segues",
    "events",
    "decisions",
    "evidence",
    "receipts",
    "attestations",
)

VOLATILE_FIELDS = {
    "generated_at",
    "created_at",
    "captured_at",
    "accepted_at",
    "occurred_at",
    "issued_at",
    "expires_at",
    "timestamp",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
}


class MerkleTreeError(RuntimeError):
    pass


@dataclass(frozen=True)
class Leaf:
    address: str
    collection: str
    record_id: str
    digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "collection": self.collection,
            "record_id": self.record_id,
            "digest": self.digest,
        }


@dataclass(frozen=True)
class MerkleNode:
    level: int
    index: int
    left: str
    right: str
    digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "index": self.index,
            "left": self.left,
            "right": self.right,
            "digest": self.digest,
        }


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def deterministic_projection(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: deterministic_projection(child)
            for key, child in sorted(
                value.items(),
                key=lambda item: item[0],
            )
            if key not in VOLATILE_FIELDS
        }

    if isinstance(value, list):
        return [
            deterministic_projection(child)
            for child in value
        ]

    if isinstance(value, tuple):
        return tuple(
            deterministic_projection(child)
            for child in value
        )

    return value


def semantic_digest(value: Any) -> str:
    return sha256_bytes(
        canonical_bytes(
            deterministic_projection(value)
        )
    )


def sha256_path(path: Path) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(value, dict):
        raise MerkleTreeError(
            f"Expected JSON object: {path}"
        )

    return value


def atomic_write_text(
    path: Path,
    value: str,
    mode: int = 0o644,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )

    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(
            temporary_path,
            mode,
        )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_write_json(
    path: Path,
    value: Any,
) -> None:
    atomic_write_text(
        path,
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


def relative_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()

    except ValueError:
        return str(path)


def record_identifier(
    collection: str,
    record: dict[str, Any],
) -> str:
    identifier = record.get("id")

    if not isinstance(identifier, str):
        raise MerkleTreeError(
            (
                "Authoritative record has no "
                f"string identifier: {collection}"
            )
        )

    return identifier


def authoritative_leaves(
    graph: dict[str, Any],
) -> tuple[Leaf, ...]:
    leaves: list[Leaf] = []

    for collection in AUTHORITATIVE_COLLECTIONS:
        values = graph.get(
            collection,
            [],
        )

        if not isinstance(values, list):
            raise MerkleTreeError(
                (
                    "Authoritative collection "
                    f"is not a list: {collection}"
                )
            )

        for record in values:
            if not isinstance(record, dict):
                raise MerkleTreeError(
                    (
                        "Authoritative collection "
                        f"contains invalid record: {collection}"
                    )
                )

            record_id = record_identifier(
                collection,
                record,
            )

            address = (
                f"savant://masterplan/"
                f"{collection}/{record_id}"
            )

            leaf_digest = semantic_digest(
                {
                    "address": address,
                    "record": record,
                }
            )

            leaves.append(
                Leaf(
                    address=address,
                    collection=collection,
                    record_id=record_id,
                    digest=leaf_digest,
                )
            )

    return tuple(
        sorted(
            leaves,
            key=lambda leaf: (
                leaf.collection,
                leaf.record_id,
                leaf.address,
            ),
        )
    )


def pair_digest(
    left: str,
    right: str,
) -> str:
    return sha256_bytes(
        bytes.fromhex(left)
        + bytes.fromhex(right)
    )


def build_levels(
    leaf_digests: Iterable[str],
) -> tuple[
    tuple[str, ...],
    tuple[tuple[MerkleNode, ...], ...],
]:
    current = tuple(leaf_digests)

    if not current:
        empty_root = semantic_digest(
            {
                "type": "masterplan-empty-merkle-root",
                "version": "1.0.0",
            }
        )

        return (
            (empty_root,),
            (),
        )

    levels: list[
        tuple[MerkleNode, ...]
    ] = []

    level_number = 1

    while len(current) > 1:
        next_level: list[str] = []
        nodes: list[MerkleNode] = []

        for index in range(
            0,
            len(current),
            2,
        ):
            left = current[index]

            right = (
                current[index + 1]
                if index + 1 < len(current)
                else left
            )

            node_digest = pair_digest(
                left,
                right,
            )

            nodes.append(
                MerkleNode(
                    level=level_number,
                    index=index // 2,
                    left=left,
                    right=right,
                    digest=node_digest,
                )
            )

            next_level.append(
                node_digest
            )

        levels.append(
            tuple(nodes)
        )

        current = tuple(
            next_level
        )

        level_number += 1

    return (
        current,
        tuple(levels),
    )


def build_merkle_tree(
    graph: dict[str, Any],
) -> dict[str, Any]:
    leaves = authoritative_leaves(
        graph
    )

    roots, levels = build_levels(
        leaf.digest
        for leaf in leaves
    )

    root_digest = roots[0]

    tree: dict[str, Any] = {
        "schema": (
            "savant://niche/masterplan/"
            "merkle-tree/1.0.0"
        ),
        "algorithm": "sha256",
        "leaf_encoding": (
            "canonical-json-semantic-digest"
        ),
        "pair_encoding": (
            "raw-left-digest-bytes"
            "+raw-right-digest-bytes"
        ),
        "odd_leaf_policy": (
            "duplicate-final-leaf"
        ),
        "root_digest": root_digest,
        "graph": {
            "path": relative_path(
                GRAPH_PATH
            ),
            "sha256": sha256_path(
                GRAPH_PATH
            ),
            "semantic_digest": (
                semantic_digest(graph)
            ),
            "schema_version": graph.get(
                "schema_version"
            ),
        },
        "leaves": [
            leaf.to_dict()
            for leaf in leaves
        ],
        "levels": [
            [
                node.to_dict()
                for node in level
            ]
            for level in levels
        ],
        "statistics": {
            "leaf_count": len(leaves),
            "level_count": len(levels),
            "node_count": sum(
                len(level)
                for level in levels
            ),
            "collection_counts": {
                collection: sum(
                    leaf.collection == collection
                    for leaf in leaves
                )
                for collection
                in AUTHORITATIVE_COLLECTIONS
            },
        },
        "generated_at": utc_now(),
    }

    tree["tree_id"] = (
        "merkle-"
        + root_digest[:24]
    )

    tree["semantic_digest"] = (
        semantic_digest(
            {
                key: value
                for key, value
                in tree.items()
                if key not in {
                    "generated_at",
                    "semantic_digest",
                }
            }
        )
    )

    return tree


def verify_merkle_tree(
    tree: dict[str, Any],
    graph: dict[str, Any],
) -> dict[str, Any]:
    rebuilt = build_merkle_tree(
        graph
    )

    checks = {
        "root_digest_matches": (
            tree.get("root_digest")
            == rebuilt.get("root_digest")
        ),
        "tree_id_matches": (
            tree.get("tree_id")
            == rebuilt.get("tree_id")
        ),
        "leaf_count_matches": (
            (
                tree.get("statistics")
                or {}
            ).get("leaf_count")
            == rebuilt[
                "statistics"
            ][
                "leaf_count"
            ]
        ),
        "leaves_match": (
            semantic_digest(
                tree.get(
                    "leaves",
                    [],
                )
            )
            == semantic_digest(
                rebuilt[
                    "leaves"
                ]
            )
        ),
        "levels_match": (
            semantic_digest(
                tree.get(
                    "levels",
                    [],
                )
            )
            == semantic_digest(
                rebuilt[
                    "levels"
                ]
            )
        ),
        "graph_digest_matches": (
            (
                tree.get("graph")
                or {}
            ).get(
                "semantic_digest"
            )
            == rebuilt[
                "graph"
            ][
                "semantic_digest"
            ]
        ),
    }

    return {
        "passed": all(
            checks.values()
        ),
        "checks": checks,
        "expected_root_digest": (
            rebuilt[
                "root_digest"
            ]
        ),
        "actual_root_digest": (
            tree.get(
                "root_digest"
            )
        ),
        "expected_tree_id": (
            rebuilt[
                "tree_id"
            ]
        ),
        "actual_tree_id": (
            tree.get(
                "tree_id"
            )
        ),
    }


def persist_tree(
    tree: dict[str, Any],
) -> dict[str, str]:
    INTEGRITY_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    historical = (
        INTEGRITY_ROOT
        / f"{tree['tree_id']}.json"
    )

    latest = (
        INTEGRITY_ROOT
        / "latest.json"
    )

    if historical.exists():
        existing = load_json(
            historical
        )

        if (
            semantic_digest(existing)
            != semantic_digest(tree)
        ):
            raise MerkleTreeError(
                "Merkle tree ID collision."
            )

    else:
        atomic_write_json(
            historical,
            tree,
        )

    atomic_write_json(
        latest,
        tree,
    )

    return {
        "historical": relative_path(
            historical
        ),
        "latest": relative_path(
            latest
        ),
    }


def persist_report(
    operation: str,
    result: dict[str, Any],
) -> dict[str, str]:
    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = timestamp()

    historical = (
        REPORT_ROOT
        / f"{run_id}__{operation}.json"
    )

    latest = (
        REPORT_ROOT
        / "latest.json"
    )

    atomic_write_json(
        historical,
        result,
    )

    atomic_write_json(
        latest,
        result,
    )

    return {
        "historical": relative_path(
            historical
        ),
        "latest": relative_path(
            latest
        ),
    }


def command_build(
    persist: bool,
) -> dict[str, Any]:
    graph = load_json(
        GRAPH_PATH
    )

    tree = build_merkle_tree(
        graph
    )

    files = (
        persist_tree(tree)
        if persist
        else None
    )

    result: dict[str, Any] = {
        "operation": (
            "build_masterplan_merkle_tree"
        ),
        "passed": True,
        "persisted": persist,
        "tree": tree,
        "files": files,
    }

    result["semantic_digest"] = (
        semantic_digest(result)
    )

    return result


def command_verify(
    tree_path: Path,
) -> dict[str, Any]:
    path = tree_path.expanduser()

    if not path.is_absolute():
        path = ROOT / path

    path = path.resolve()

    if not path.is_file():
        raise FileNotFoundError(path)

    tree = load_json(
        path
    )

    graph = load_json(
        GRAPH_PATH
    )

    verification = verify_merkle_tree(
        tree,
        graph,
    )

    result: dict[str, Any] = {
        "operation": (
            "verify_masterplan_merkle_tree"
        ),
        "passed": verification[
            "passed"
        ],
        "tree_path": relative_path(
            path
        ),
        "tree_sha256": sha256_path(
            path
        ),
        "verification": verification,
    }

    result["semantic_digest"] = (
        semantic_digest(result)
    )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build and verify a deterministic "
            "Merkle integrity tree over authoritative "
            "Masterplan primitives."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    build_parser = subparsers.add_parser(
        "build"
    )

    build_parser.add_argument(
        "--persist",
        action="store_true",
    )

    verify_parser = subparsers.add_parser(
        "verify"
    )

    verify_parser.add_argument(
        "tree_path",
        type=Path,
    )

    arguments = parser.parse_args()

    try:
        if arguments.command == "build":
            result = command_build(
                arguments.persist
            )

        elif arguments.command == "verify":
            result = command_verify(
                arguments.tree_path
            )

        else:
            return 2

        result["reports"] = persist_report(
            arguments.command,
            result,
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "build_masterplan_merkle_tree"
                    ),
                    "passed": False,
                    "error": {
                        "type": type(
                            exc
                        ).__name__,
                        "message": str(
                            exc
                        ),
                    },
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if result.get("passed")
        is True
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError:
    yaml = None


ROOT = Path("/root/savant-runtime")
OUT = ROOT / "context/AUTHORITY_GRAPH_COMPILED.json"

IGNORE = {
    ".git",
    ".venv",
    ".venv_voice",
    "node_modules",
    "__pycache__",
    "site-packages",
    "exports",
    "repair_backups",
    "backups",
    "reports",
    "projections",
    "snapshots",
}

AUTHORITY_ROOTS = [
    ROOT / "canon",
    ROOT / "authority_graph",
    ROOT / "canon-system" / "authority",
    ROOT / "authority" / "task-graph",
    ROOT / "ontology",
]

AUTHORITY_JSON_NAMES = {
    "entity.json",
    "module.json",
    "contracts.json",
    "capabilities.json",
    "interfaces.json",
    "manifests.json",
    "templates.json",
    "versions.json",
    "defaults.json",
    "inheritance.json",
    "edges.json",
    "nodes.json",
    "relationships.json",
}

REFERENCE_KEYS = {
    "parent",
    "parents",
    "child",
    "children",
    "source",
    "sources",
    "target",
    "targets",
    "from",
    "to",
    "depends_on",
    "dependencies",
    "requires",
    "required_by",
    "provides",
    "inherits",
    "extends",
    "template",
    "templates",
    "archetype",
    "archetypes",
    "meta_archetype",
    "meta_archetypes",
    "instance",
    "instances",
    "shade",
    "shades",
    "segue",
    "segues",
    "relationship",
    "relationships",
    "supersedes",
    "superseded_by",
    "derived_from",
    "references",
    "owner",
    "owners",
    "implementation_ref",
    "implementation_refs",
}

NON_REFERENCE_KEYS = {
    "id",
    "kind",
    "type",
    "status",
    "version",
    "title",
    "name",
    "canonical",
    "canonical_name",
    "display_name",
    "description",
    "purpose",
    "rule",
    "claim",
    "value",
    "path",
    "paths",
    "authority",
    "authority_state",
    "authority_class",
    "authority_tier",
    "confidence",
    "created_at",
    "updated_at",
    "occurred_at",
    "generated_at",
    "accepted_at",
    "accepted_by",
    "asserted_by",
    "method",
    "schema",
    "$schema",
    "sha256",
    "digest",
    "semantic_digest",
    "content_digest",
}

REFERENCE_PREFIXES = (
    "foundation:",
    "meta_archetype:",
    "archetype:",
    "template:",
    "instance:",
    "shade:",
    "segue:",
    "policy:",
    "domain:",
    "service:",
    "system:",
    "exile:",
    "prodigal:",
    "quirk:",
    "ink:",
    "mote:",
    "iota:",
    "obelisk:",
    "wyrmhole:",
    "tidal:",
    "mood:",
    "lex:",
    "savant:",
    "savant://",
)

REFERENCE_PATH_PREFIXES = (
    "canon/",
    "authority/",
    "authority_graph/",
    "canon-system/authority/",
    "ontology/",
    "hierarchies/",
    "runtime/",
)


def ignored(path: Path) -> bool:
    return any(
        part in IGNORE
        for part in path.parts
    )


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_structured(path: Path) -> Any:
    text = path.read_text(
        encoding="utf-8",
        errors="strict",
    )

    suffix = path.suffix.casefold()

    if suffix == ".json":
        return json.loads(text)

    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError(
                "PyYAML is required to compile YAML authority."
            )

        return yaml.safe_load(text)

    return None


def authority_tier(path: Path) -> int:
    r = rel(path)

    if r.startswith("canon/foundation/"):
        return 0

    if r.startswith(
        "canon-system/authority/foundation/"
    ):
        return 0

    if r.startswith(
        "canon-system/authority/policies/"
    ):
        return 0

    if r.startswith(
        "authority/task-graph/"
    ):
        return 0

    if r.startswith(
        "authority_graph/meta_archetypes/"
    ):
        return 1

    if r.startswith(
        "authority_graph/archetypes/"
    ):
        return 2

    if r.startswith(
        "authority_graph/templates/"
    ):
        return 3

    if r.startswith(
        "authority_graph/instances/"
    ):
        return 4

    if r.startswith(
        "authority_graph/segues/"
    ):
        return 5

    if r.startswith(
        "authority_graph/policies/"
    ):
        return 6

    if r.startswith(
        "canon-system/authority/"
    ):
        return 7

    if (
        "/authority/" in r
        or "/canon/" in r
    ):
        return 7

    if any(
        marker in r
        for marker in (
            "/registry/",
            "/lineage/",
            "/graph/",
        )
    ):
        return 8

    return 9


def kind_from_path(
    path: Path,
    data: Any | None,
) -> str:
    if isinstance(data, dict):
        kind = data.get("kind")

        if isinstance(kind, str) and kind:
            return kind

    r = rel(path)

    if r.startswith("canon/foundation/"):
        return "foundation"

    if r.startswith(
        "canon-system/authority/foundation/"
    ):
        return "foundation"

    if r.startswith(
        "canon-system/authority/policies/"
    ):
        return "policy"

    if r.startswith(
        "canon-system/authority/exiles/"
    ):
        return "exile"

    if r.startswith(
        "authority/task-graph/"
    ):
        return "task_authority"

    if "meta_archetypes" in r:
        return "meta_archetype"

    if "archetypes" in r:
        return "archetype"

    if "templates" in r:
        return "template"

    if "instances" in r:
        return "instance"

    if "segues" in r:
        return "segue"

    if "policies" in r:
        return "policy"

    if path.name == "entity.json":
        return "entity"

    if path.name == "module.json":
        return "module"

    if r.startswith("canon/"):
        return "canon"

    return "authority_artifact"


def owner_from_path(path: Path) -> str:
    parts = path.parts

    if "exiles" in parts:
        index = parts.index("exiles")

        if index + 1 < len(parts):
            return parts[index + 1]

    if "innates" in parts:
        return "innates"

    if "gates" in parts:
        return "wyrmhole"

    if "obelisks" in parts:
        return "obelisks"

    if "task-graph" in parts:
        return "masterplan"

    if (
        "canon-system" in parts
        and "authority" in parts
    ):
        return "canon-system"

    return "savant"


def include_authority_file(path: Path) -> bool:
    if ignored(path):
        return False

    if not path.is_file():
        return False

    suffix = path.suffix.casefold()

    if suffix == ".md":
        return (
            "canon" in path.parts
            or "foundation" in path.parts
        )

    if suffix in {
        ".yaml",
        ".yml",
    }:
        return any(
            marker in path.parts
            for marker in (
                "authority",
                "authority_graph",
                "canon",
                "foundation",
                "policies",
                "lineage",
                "segues",
                "instances",
                "templates",
                "archetypes",
                "meta_archetypes",
            )
        )

    if suffix != ".json":
        return False

    if path.name in AUTHORITY_JSON_NAMES:
        return True

    return any(
        marker in path.parts
        for marker in (
            "authority",
            "authority_graph",
            "canon",
            "registry",
            "lineage",
            "graph",
            "segue",
            "segues",
            "instances",
            "templates",
            "archetypes",
            "meta_archetypes",
            "task-graph",
        )
    )


def iter_authority_files() -> list[Path]:
    files: set[Path] = set()

    for root in AUTHORITY_ROOTS:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if include_authority_file(path):
                files.add(path)

    return sorted(
        files,
        key=rel,
    )


def normalized_reference(
    value: str,
) -> str | None:
    candidate = value.strip()

    if not candidate:
        return None

    if candidate.startswith(
        REFERENCE_PREFIXES
    ):
        return candidate

    if candidate.startswith(
        REFERENCE_PATH_PREFIXES
    ):
        return candidate

    return None


def collect_reference_values(
    value: Any,
) -> Iterable[str]:
    if isinstance(value, str):
        ref = normalized_reference(
            value
        )

        if ref is not None:
            yield ref

        return

    if isinstance(value, list):
        for item in value:
            yield from collect_reference_values(
                item
            )

        return

    if isinstance(value, dict):
        identifier = value.get("id")

        if isinstance(identifier, str):
            ref = normalized_reference(
                identifier
            )

            if ref is not None:
                yield ref

        target = value.get("target")

        if isinstance(target, str):
            ref = normalized_reference(
                target
            )

            if ref is not None:
                yield ref


def collect_refs(
    obj: Any,
) -> list[str]:
    refs: list[str] = []

    if not isinstance(obj, dict):
        return refs

    for key, value in obj.items():
        normalized_key = str(
            key
        ).casefold()

        if normalized_key in NON_REFERENCE_KEYS:
            continue

        if normalized_key in REFERENCE_KEYS:
            refs.extend(
                collect_reference_values(
                    value
                )
            )
            continue

        if isinstance(value, dict):
            refs.extend(
                collect_refs(
                    value
                )
            )

        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    refs.extend(
                        collect_refs(
                            item
                        )
                    )

    return sorted(
        set(refs)
    )


def record_id(
    path: Path,
    data: Any | None,
) -> str:
    if isinstance(data, dict):
        identifier = data.get("id")

        if (
            isinstance(identifier, str)
            and identifier.strip()
        ):
            return identifier.strip()

    return rel(path)


def resolve_reference(
    reference: str,
    id_to_path: dict[str, str],
) -> tuple[bool, str]:
    if reference in id_to_path:
        return (
            True,
            reference,
        )

    if reference.startswith(
        "savant://"
    ):
        return (
            False,
            "",
        )

    if reference.startswith(
        REFERENCE_PATH_PREFIXES
    ):
        target_path = (
            ROOT
            / reference
        )

        if target_path.exists():
            return (
                True,
                reference,
            )

    return (
        False,
        "",
    )


def main() -> int:
    nodes: dict[
        str,
        dict[str, Any],
    ] = {}

    edges: list[
        dict[str, Any]
    ] = []

    conflicts: list[
        dict[str, Any]
    ] = []

    parse_failures: list[
        dict[str, str]
    ] = []

    id_to_path: dict[
        str,
        str
    ] = {}

    files = iter_authority_files()

    parsed: dict[
        Path,
        Any
    ] = {}

    for path in files:
        data = None
        parse_error = ""

        if path.suffix.casefold() in {
            ".json",
            ".yaml",
            ".yml",
        }:
            try:
                data = read_structured(
                    path
                )
            except Exception as exc:
                parse_error = str(exc)

                parse_failures.append(
                    {
                        "path": rel(path),
                        "error": parse_error,
                    }
                )

        parsed[path] = data

        node_id = record_id(
            path,
            data,
        )

        if node_id in nodes:
            conflicts.append(
                {
                    "id": node_id,
                    "first_path": (
                        nodes[node_id][
                            "path"
                        ]
                    ),
                    "second_path": rel(
                        path
                    ),
                }
            )

            continue

        node = {
            "id": node_id,
            "path": rel(path),
            "kind": kind_from_path(
                path,
                data,
            ),
            "owner": owner_from_path(
                path
            ),
            "authority_tier": (
                authority_tier(
                    path
                )
            ),
            "parse_error": (
                parse_error
            ),
        }

        nodes[node_id] = node
        id_to_path[node_id] = rel(
            path
        )

    for path in files:
        data = parsed.get(
            path
        )

        if not isinstance(
            data,
            dict,
        ):
            continue

        source_id = record_id(
            path,
            data,
        )

        for reference in collect_refs(
            data
        ):
            resolved, target = (
                resolve_reference(
                    reference,
                    id_to_path,
                )
            )

            edges.append(
                {
                    "source": source_id,
                    "reference": (
                        reference
                    ),
                    "target": target,
                    "resolved": (
                        resolved
                    ),
                }
            )

    unresolved = [
        edge
        for edge in edges
        if not edge["resolved"]
    ]

    graph = {
        "id": (
            "authority_graph_compiled"
        ),
        "authority_roots": [
            rel(root)
            for root in AUTHORITY_ROOTS
            if root.exists()
        ],
        "node_count": len(
            nodes
        ),
        "edge_count": len(
            edges
        ),
        "unresolved_count": len(
            unresolved
        ),
        "conflict_count": len(
            conflicts
        ),
        "parse_failure_count": len(
            parse_failures
        ),
        "nodes": nodes,
        "edges": edges,
        "unresolved": unresolved,
        "conflicts": conflicts,
        "parse_failures": (
            parse_failures
        ),
    }

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUT.write_text(
        json.dumps(
            graph,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "id": graph["id"],
                "authority_root_count": len(
                    graph[
                        "authority_roots"
                    ]
                ),
                "node_count": graph[
                    "node_count"
                ],
                "edge_count": graph[
                    "edge_count"
                ],
                "unresolved_count": graph[
                    "unresolved_count"
                ],
                "conflict_count": graph[
                    "conflict_count"
                ],
                "parse_failure_count": graph[
                    "parse_failure_count"
                ],
                "out": str(
                    OUT
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if (
            not conflicts
            and not parse_failures
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

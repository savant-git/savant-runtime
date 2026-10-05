#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path("/root/savant-runtime").resolve()

OBELISKS_SEGUE = ROOT / "ontology/obelisks/segue"
AUTHORITY_DB = (
    OBELISKS_SEGUE
    / "authority_db/savant_authority.sqlite"
)
AUTHORITY_GRAPH = (
    OBELISKS_SEGUE
    / "authority_graph"
)

EXILES = (
    ROOT
    / "ontology/obelisks/_template/segue/gates/_template/"
    "segue/innates/_template/segue/exiles"
)
FILAMENT = EXILES / "filament"

PROJECTIONS = FILAMENT / "projections"
JSON_PROJECTIONS = PROJECTIONS / "json"
MD_PROJECTIONS = PROJECTIONS / "md"
SCRIPT_PROJECTIONS = PROJECTIONS / "scripts"
AUDIT_PROJECTIONS = PROJECTIONS / "audit"

CANON_TREE_SCHEMA = (
    "savant://projection/filament/canon-tree/1.0.0"
)
CANON_TREE_MANIFEST_SCHEMA = (
    "savant://projection/filament/"
    "canon-tree-manifest/1.0.0"
)
CANON_TREE_AI_SCHEMA = (
    "savant://projection/filament/"
    "canon-tree-ai/1.0.0"
)
PROJECTION_POLICY_VERSION = "1.0.0"
ORDERING_POLICY = (
    "root; composition_edges.ordinal; "
    "stable identity tie-breaker; "
    "filesystem lexical fallback only when "
    "semantic composition is unavailable"
)

CANON_MD_NAMES = (
    "CANON.md",
    "canon.md",
)
CANON_JSON_NAMES = (
    "canon.json",
    "CANON.json",
)


class ProjectionError(RuntimeError):
    pass


def parse_json(
    value: Any,
    fallback: Any,
) -> Any:
    if value is None:
        return fallback

    try:
        return json.loads(value)
    except Exception:
        return fallback


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256(
    text: str,
) -> str:
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def file_sha256(
    path: Path | None,
) -> str | None:
    if path is None or not path.is_file():
        return None

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def write_if_changed(
    path: Path,
    text: str,
) -> bool:
    path = Path(path)
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    old = (
        path.read_text(encoding="utf-8")
        if path.exists()
        else None
    )

    if old == text:
        return False

    path.write_text(
        text,
        encoding="utf-8",
    )
    return True


def connect() -> sqlite3.Connection:
    if not AUTHORITY_DB.is_file():
        raise ProjectionError(
            f"authority database missing: "
            f"{AUTHORITY_DB}"
        )

    con = sqlite3.connect(
        AUTHORITY_DB
    )
    con.row_factory = sqlite3.Row
    return con


def instance_row(
    con: sqlite3.Connection,
    instance_id: str,
) -> sqlite3.Row:
    row = con.execute(
        """
        SELECT
            id,
            kind,
            type,
            level,
            status,
            authority,
            version,
            metadata_json,
            extensions_json,
            future_extensions_json,
            created_at,
            updated_at
        FROM instances
        WHERE id = ?
        """,
        (instance_id,),
    ).fetchone()

    if row is None:
        raise ProjectionError(
            "instance not found: "
            f"{instance_id}"
        )

    return row


def composition_rows(
    con: sqlite3.Connection,
    instance_id: str,
) -> list[sqlite3.Row]:
    return con.execute(
        """
        SELECT
            child_id,
            edge_type,
            ordinal,
            authority,
            metadata_json
        FROM composition_edges
        WHERE parent_id = ?
        ORDER BY
            CASE
                WHEN ordinal IS NULL THEN 1
                ELSE 0
            END,
            ordinal,
            child_id
        """,
        (instance_id,),
    ).fetchall()


def relationship_rows(
    con: sqlite3.Connection,
    instance_id: str,
) -> list[sqlite3.Row]:
    return con.execute(
        """
        SELECT
            target_id,
            relationship_type,
            authority,
            metadata_json
        FROM relationships
        WHERE source_id = ?
        ORDER BY
            relationship_type,
            target_id
        """,
        (instance_id,),
    ).fetchall()


def instance_projection(
    con: sqlite3.Connection,
    instance_id: str,
) -> dict[str, Any]:
    row = instance_row(
        con,
        instance_id,
    )
    children = composition_rows(
        con,
        instance_id,
    )
    relationships = relationship_rows(
        con,
        instance_id,
    )

    return {
        "id": row["id"],
        "kind": row["kind"],
        "type": row["type"],
        "level": row["level"],
        "status": row["status"],
        "authority": row["authority"],
        "version": row["version"],
        "metadata": parse_json(
            row["metadata_json"],
            {},
        ),
        "composition": {
            "children": [
                {
                    "id": child["child_id"],
                    "edge_type": (
                        child["edge_type"]
                    ),
                    "ordinal": (
                        child["ordinal"]
                    ),
                    "authority": (
                        child["authority"]
                    ),
                    "metadata": parse_json(
                        child["metadata_json"],
                        {},
                    ),
                }
                for child in children
            ],
        },
        "relationships": [
            {
                "target": rel["target_id"],
                "type": (
                    rel[
                        "relationship_type"
                    ]
                ),
                "authority": (
                    rel["authority"]
                ),
                "metadata": parse_json(
                    rel["metadata_json"],
                    {},
                ),
            }
            for rel in relationships
        ],
        "extensions": parse_json(
            row["extensions_json"],
            {},
        ),
        "future_extensions": parse_json(
            row["future_extensions_json"],
            {},
        ),
        "projection": {
            "owner": "filament",
            "engine": (
                "filament.runtime."
                "projection_engine"
            ),
            "source": (
                "sqlite.authority_db"
            ),
            "database": str(
                AUTHORITY_DB
            ),
            "authoritative": False,
            "rebuildable": True,
        },
        "provenance": {
            "created_at": (
                row["created_at"]
            ),
            "updated_at": (
                row["updated_at"]
            ),
        },
    }


def project_instance_json(
    con: sqlite3.Connection,
    instance_id: str,
) -> None:
    projection = instance_projection(
        con,
        instance_id,
    )

    text = (
        json.dumps(
            projection,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    target = (
        JSON_PROJECTIONS
        / (
            instance_id.replace(
                ".",
                "__",
            )
            + ".json"
        )
    )

    changed = write_if_changed(
        target,
        text,
    )

    con.execute(
        """
        INSERT INTO projections
        (
            id,
            source_instance_id,
            projection_type,
            target_path,
            template_path,
            authority,
            checksum,
            generated_at,
            metadata_json
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?,
            CURRENT_TIMESTAMP, ?
        )
        ON CONFLICT(id) DO UPDATE SET
            target_path=excluded.target_path,
            checksum=excluded.checksum,
            generated_at=CURRENT_TIMESTAMP,
            metadata_json=excluded.metadata_json
        """,
        (
            f"projection.json.{instance_id}",
            instance_id,
            "json",
            str(target),
            (
                "filament/runtime/"
                "projection_engine/project.py"
            ),
            "FILAMENT_PROJECTION_ENGINE",
            sha256(text),
            json.dumps(
                {
                    "owner": "filament",
                    "reason": (
                        "Filament owns "
                        "projection."
                    ),
                    "authoritative": False,
                    "rebuildable": True,
                },
                sort_keys=True,
            ),
        ),
    )

    print(
        (
            "[WRITE] "
            if changed
            else "[SKIP]  "
        )
        + str(target)
    )


def resolve_root(
    raw_path: str,
) -> Path:
    candidate = Path(raw_path)

    if not candidate.is_absolute():
        raise ProjectionError(
            "canon-tree root must be "
            "an absolute path"
        )

    resolved = candidate.resolve()

    try:
        resolved.relative_to(ROOT)
    except ValueError as exc:
        raise ProjectionError(
            "canon-tree root escapes "
            f"Savant root: {resolved}"
        ) from exc

    if not resolved.exists():
        raise ProjectionError(
            f"root does not exist: "
            f"{resolved}"
        )

    if not resolved.is_dir():
        raise ProjectionError(
            "canon-tree root must be "
            f"a directory: {resolved}"
        )

    return resolved


def local_canon_file(
    root: Path,
    names: tuple[str, ...],
) -> Path | None:
    for name in names:
        candidate = root / name

        if candidate.is_file():
            return candidate

    return None


def local_canon_bundle(
    root: Path,
) -> tuple[Path | None, Path | None]:
    return (
        local_canon_file(
            root,
            CANON_MD_NAMES,
        ),
        local_canon_file(
            root,
            CANON_JSON_NAMES,
        ),
    )


def instance_path_candidates(
    projection: dict[str, Any],
) -> tuple[str, ...]:
    values: list[str] = []

    metadata = projection.get(
        "metadata",
        {},
    )

    if isinstance(metadata, dict):
        for key in (
            "path",
            "root",
            "root_path",
            "materialized_path",
            "filesystem_path",
            "target_path",
        ):
            value = metadata.get(key)

            if isinstance(value, str):
                value = value.strip()

                if value:
                    values.append(value)

    extensions = projection.get(
        "extensions",
        {},
    )

    if isinstance(extensions, dict):
        for key in (
            "path",
            "root",
            "root_path",
            "materialized_path",
            "filesystem_path",
        ):
            value = extensions.get(key)

            if isinstance(value, str):
                value = value.strip()

                if value:
                    values.append(value)

    return tuple(values)


def instance_for_path(
    con: sqlite3.Connection,
    root: Path,
) -> str | None:
    resolved = root.resolve()

    rows = con.execute(
        """
        SELECT id
        FROM instances
        ORDER BY id
        """
    ).fetchall()

    exact: list[str] = []

    for row in rows:
        projection = instance_projection(
            con,
            row["id"],
        )

        for raw in instance_path_candidates(
            projection
        ):
            candidate = Path(raw)

            if not candidate.is_absolute():
                candidate = ROOT / candidate

            try:
                candidate = candidate.resolve()
            except OSError:
                continue

            if candidate == resolved:
                exact.append(
                    row["id"]
                )
                break

    if len(exact) > 1:
        raise ProjectionError(
            "multiple authoritative "
            "instances resolve to root: "
            + ", ".join(exact)
        )

    if exact:
        return exact[0]

    return None


def authority_source_refs(
    projection: dict[str, Any] | None,
) -> list[str]:
    if projection is None:
        return []

    refs: set[str] = set()

    authority = projection.get(
        "authority"
    )

    if authority:
        refs.add(str(authority))

    metadata = projection.get(
        "metadata",
        {},
    )

    if isinstance(metadata, dict):
        for key in (
            "authority_source",
            "authority_sources",
            "source",
            "sources",
            "source_refs",
            "authority_source_refs",
        ):
            value = metadata.get(key)

            if isinstance(value, str):
                if value.strip():
                    refs.add(
                        value.strip()
                    )

            elif isinstance(
                value,
                (list, tuple),
            ):
                for item in value:
                    if str(item).strip():
                        refs.add(
                            str(item).strip()
                        )

    return sorted(refs)


def filesystem_children(
    root: Path,
) -> list[Path]:
    children: list[Path] = []

    try:
        entries = sorted(
            root.iterdir(),
            key=lambda path: path.name,
        )
    except OSError as exc:
        raise ProjectionError(
            f"cannot inspect root: {root}"
        ) from exc

    for child in entries:
        if (
            child.is_dir()
            and local_canon_bundle(
                child
            )
            != (None, None)
        ):
            children.append(
                child.resolve()
            )

    return children


def descendant_canon_roots(
    root: Path,
) -> list[Path]:
    result: list[Path] = []

    try:
        entries = sorted(
            root.rglob("*"),
            key=lambda path: (
                len(path.parts),
                str(path),
            ),
        )
    except OSError as exc:
        raise ProjectionError(
            f"cannot recurse root: {root}"
        ) from exc

    for candidate in entries:
        if not candidate.is_dir():
            continue

        if local_canon_bundle(
            candidate
        ) == (None, None):
            continue

        result.append(
            candidate.resolve()
        )

    return result


def semantic_child_ids(
    con: sqlite3.Connection,
    instance_id: str,
) -> list[str]:
    return [
        row["child_id"]
        for row in composition_rows(
            con,
            instance_id,
        )
    ]


def path_instance_index(
    con: sqlite3.Connection,
    roots: list[Path],
) -> dict[Path, str]:
    result: dict[Path, str] = {}

    for root in roots:
        instance_id = instance_for_path(
            con,
            root,
        )

        if instance_id is not None:
            result[root] = instance_id

    return result


def order_children(
    con: sqlite3.Connection,
    parent_path: Path,
    parent_instance: str | None,
    candidates: list[Path],
    index: dict[Path, str],
    warnings: list[str],
) -> list[Path]:
    if not candidates:
        return []

    if parent_instance is None:
        warnings.append(
            "lexical-order fallback: "
            f"{parent_path}"
        )
        return sorted(
            candidates,
            key=lambda path: (
                path.name,
                str(path),
            ),
        )

    semantic = semantic_child_ids(
        con,
        parent_instance,
    )
    rank = {
        identity: position
        for position, identity
        in enumerate(semantic)
    }

    semantic_candidates = [
        path
        for path in candidates
        if index.get(path) in rank
    ]

    fallback_candidates = [
        path
        for path in candidates
        if index.get(path) not in rank
    ]

    semantic_candidates.sort(
        key=lambda path: (
            rank[index[path]],
            index[path],
            str(path),
        )
    )

    fallback_candidates.sort(
        key=lambda path: (
            index.get(path, ""),
            path.name,
            str(path),
        )
    )

    if fallback_candidates:
        warnings.append(
            "lexical-order fallback for "
            f"{parent_path}: "
            + ", ".join(
                str(path)
                for path
                in fallback_candidates
            )
        )

    return (
        semantic_candidates
        + fallback_candidates
    )


def build_ordered_roots(
    con: sqlite3.Connection,
    root: Path,
    scope: str,
    warnings: list[str],
) -> list[tuple[Path, int]]:
    root_bundle = local_canon_bundle(
        root
    )

    if root_bundle == (None, None):
        raise ProjectionError(
            "selected root has no local "
            "CANON.md/canon.json projection: "
            f"{root}"
        )

    if scope == "self":
        return [(root, 0)]

    all_roots = [
        root,
        *descendant_canon_roots(root),
    ]

    index = path_instance_index(
        con,
        all_roots,
    )

    root_instance = index.get(root)

    if scope == "children":
        children = filesystem_children(
            root
        )
        ordered = order_children(
            con,
            root,
            root_instance,
            children,
            index,
            warnings,
        )
        return [
            (root, 0),
            *[
                (child, 1)
                for child in ordered
            ],
        ]

    if scope != "recursive":
        raise ProjectionError(
            f"unsupported scope: {scope}"
        )

    canon_set = set(all_roots)
    direct: dict[
        Path,
        list[Path],
    ] = {
        path: []
        for path in all_roots
    }

    for child in all_roots:
        if child == root:
            continue

        parent = child.parent

        while (
            parent != root
            and parent not in canon_set
        ):
            if root not in parent.parents:
                break

            parent = parent.parent

        if parent in canon_set:
            direct[parent].append(
                child
            )

    result: list[
        tuple[Path, int]
    ] = []
    seen: set[Path] = set()

    def visit(
        current: Path,
        depth: int,
    ) -> None:
        if current in seen:
            raise ProjectionError(
                "duplicate canon path during "
                f"composition: {current}"
            )

        seen.add(current)
        result.append(
            (current, depth)
        )

        ordered = order_children(
            con,
            current,
            index.get(current),
            direct.get(
                current,
                [],
            ),
            index,
            warnings,
        )

        for child in ordered:
            visit(
                child,
                depth + 1,
            )

    visit(
        root,
        0,
    )

    return result


def load_json_file(
    path: Path | None,
) -> Any:
    if path is None:
        return None

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ProjectionError(
            f"invalid canon JSON: {path}"
        ) from exc


def relative_to_request(
    root: Path,
    candidate: Path,
) -> str:
    if candidate == root:
        return "."

    return str(
        candidate.relative_to(root)
    )


def build_element(
    con: sqlite3.Connection,
    request_root: Path,
    path: Path,
    depth: int,
) -> dict[str, Any]:
    md_path, json_path = (
        local_canon_bundle(path)
    )

    instance_id = instance_for_path(
        con,
        path,
    )

    projection = (
        instance_projection(
            con,
            instance_id,
        )
        if instance_id is not None
        else None
    )

    canon_json = load_json_file(
        json_path
    )

    if instance_id is not None:
        element_id = instance_id
    elif (
        isinstance(canon_json, dict)
        and canon_json.get("id")
    ):
        element_id = str(
            canon_json["id"]
        )
    else:
        element_id = (
            "path:"
            + relative_to_request(
                request_root,
                path,
            )
        )

    md_text = (
        md_path.read_text(
            encoding="utf-8"
        )
        if md_path is not None
        else None
    )

    return {
        "element_id": element_id,
        "relative_path": (
            relative_to_request(
                request_root,
                path,
            )
        ),
        "absolute_path": str(path),
        "depth": depth,
        "canon_md_path": (
            str(md_path)
            if md_path is not None
            else None
        ),
        "canon_json_path": (
            str(json_path)
            if json_path is not None
            else None
        ),
        "canon_md_digest": (
            file_sha256(md_path)
        ),
        "canon_json_digest": (
            file_sha256(json_path)
        ),
        "authority_source_refs": (
            authority_source_refs(
                projection
            )
        ),
        "instance_projection": (
            projection
        ),
        "canon_json": canon_json,
        "canon_md": md_text,
    }


def validate_elements(
    elements: list[dict[str, Any]],
) -> None:
    identities: set[str] = set()

    for element in elements:
        identity = str(
            element["element_id"]
        )

        if identity in identities:
            raise ProjectionError(
                "duplicate element identity: "
                f"{identity}"
            )

        identities.add(identity)

        if (
            element["canon_md_path"]
            is None
            and element[
                "canon_json_path"
            ]
            is None
        ):
            raise ProjectionError(
                "included element has no "
                "local canon projection: "
                f"{identity}"
            )


def source_graph_digest(
    elements: list[dict[str, Any]],
) -> str:
    basis = [
        {
            "element_id": (
                element["element_id"]
            ),
            "relative_path": (
                element["relative_path"]
            ),
            "depth": element["depth"],
            "canon_md_digest": (
                element[
                    "canon_md_digest"
                ]
            ),
            "canon_json_digest": (
                element[
                    "canon_json_digest"
                ]
            ),
            "authority_source_refs": (
                element[
                    "authority_source_refs"
                ]
            ),
        }
        for element in elements
    ]

    return sha256(
        canonical_json(basis)
    )


def md_output(
    elements: list[dict[str, Any]],
) -> str:
    parts: list[str] = []

    for element in elements:
        header = (
            "<!-- SAVANT_CANON_ELEMENT "
            f"id={element['element_id']} "
            f"path={element['relative_path']} "
            f"depth={element['depth']} "
            "-->"
        )

        body = element.get(
            "canon_md"
        )

        if body is None:
            body = (
                "```json\n"
                + json.dumps(
                    element.get(
                        "canon_json"
                    ),
                    indent=2,
                    sort_keys=True,
                )
                + "\n```\n"
            )

        parts.append(
            header
            + "\n\n"
            + body.rstrip()
            + "\n\n"
            + (
                "<!-- "
                "SAVANT_CANON_ELEMENT_END "
                f"id={element['element_id']} "
                "-->"
            )
        )

    return "\n\n".join(parts) + "\n"


def machine_element(
    element: dict[str, Any],
) -> dict[str, Any]:
    return {
        "element_id": (
            element["element_id"]
        ),
        "relative_path": (
            element["relative_path"]
        ),
        "depth": element["depth"],
        "canon_md_digest": (
            element[
                "canon_md_digest"
            ]
        ),
        "canon_json_digest": (
            element[
                "canon_json_digest"
            ]
        ),
        "authority_source_refs": (
            element[
                "authority_source_refs"
            ]
        ),
        "canon": (
            element["canon_json"]
            if element["canon_json"]
            is not None
            else {
                "markdown": (
                    element["canon_md"]
                )
            }
        ),
    }


def json_output(
    root: Path,
    scope: str,
    elements: list[dict[str, Any]],
) -> str:
    payload = {
        "schema": CANON_TREE_SCHEMA,
        "authority_state": (
            "projection"
        ),
        "projection_authoritative": (
            False
        ),
        "rebuildable": True,
        "request_root": str(root),
        "scope": scope,
        "elements": [
            machine_element(element)
            for element in elements
        ],
    }

    return (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def jsonl_output(
    elements: list[dict[str, Any]],
) -> str:
    return "".join(
        canonical_json(
            machine_element(element)
        )
        + "\n"
        for element in elements
    )


def ai_record(
    element: dict[str, Any],
) -> dict[str, Any]:
    canon = element.get(
        "canon_json"
    )

    if not isinstance(canon, dict):
        return {
            "identity": (
                element["element_id"]
            ),
            "relative_path": (
                element["relative_path"]
            ),
            "depth": element["depth"],
            "authority_source_refs": (
                element[
                    "authority_source_refs"
                ]
            ),
            "source_refs": {
                "canon_md_digest": (
                    element[
                        "canon_md_digest"
                    ]
                ),
                "canon_json_digest": (
                    element[
                        "canon_json_digest"
                    ]
                ),
            },
            "canon_markdown": (
                element["canon_md"]
            ),
        }

    projection = element.get(
        "instance_projection"
    ) or {}

    keys = (
        "identity",
        "id",
        "authority",
        "constraints",
        "relationships",
        "dependencies",
        "dependents",
        "lineage",
        "provenance",
        "unresolved_conflicts",
        "conflicts",
        "technical_contracts",
        "contracts",
        "extensions",
        "future_extensions",
    )

    record: dict[str, Any] = {
        "identity": (
            canon.get("identity")
            or canon.get("id")
            or element["element_id"]
        ),
        "relative_path": (
            element["relative_path"]
        ),
        "depth": element["depth"],
    }

    for key in keys:
        if key in canon:
            record[key] = canon[key]

    if (
        "authority" not in record
        and projection.get(
            "authority"
        )
        is not None
    ):
        record["authority"] = (
            projection["authority"]
        )

    if (
        "relationships" not in record
        and projection.get(
            "relationships"
        )
    ):
        record["relationships"] = (
            projection[
                "relationships"
            ]
        )

    if (
        "extensions" not in record
        and projection.get(
            "extensions"
        )
    ):
        record["extensions"] = (
            projection[
                "extensions"
            ]
        )

    if (
        "future_extensions"
        not in record
        and projection.get(
            "future_extensions"
        )
    ):
        record[
            "future_extensions"
        ] = projection[
            "future_extensions"
        ]

    record[
        "authority_source_refs"
    ] = element[
        "authority_source_refs"
    ]

    record["source_refs"] = {
        "canon_md_digest": (
            element[
                "canon_md_digest"
            ]
        ),
        "canon_json_digest": (
            element[
                "canon_json_digest"
            ]
        ),
    }

    return record


def ai_output(
    root: Path,
    scope: str,
    elements: list[dict[str, Any]],
) -> str:
    payload = {
        "schema": (
            CANON_TREE_AI_SCHEMA
        ),
        "authority_state": (
            "projection"
        ),
        "projection_authoritative": (
            False
        ),
        "request_root": str(root),
        "scope": scope,
        "records": [
            ai_record(element)
            for element in elements
        ],
    }

    return (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def render_output(
    format_name: str,
    root: Path,
    scope: str,
    elements: list[dict[str, Any]],
) -> str:
    if format_name == "md":
        return md_output(
            elements
        )

    if format_name == "json":
        return json_output(
            root,
            scope,
            elements,
        )

    if format_name == "jsonl":
        return jsonl_output(
            elements
        )

    if format_name == "ai":
        return ai_output(
            root,
            scope,
            elements,
        )

    raise ProjectionError(
        f"unsupported format: "
        f"{format_name}"
    )


def manifest_payload(
    *,
    request_root: str,
    resolved_root: Path,
    scope: str,
    format_name: str,
    elements: list[dict[str, Any]],
    warnings: list[str],
    output_text: str,
) -> dict[str, Any]:
    included = [
        {
            "element_id": (
                element["element_id"]
            ),
            "relative_path": (
                element["relative_path"]
            ),
            "depth": element["depth"],
            "canon_md_digest": (
                element[
                    "canon_md_digest"
                ]
            ),
            "canon_json_digest": (
                element[
                    "canon_json_digest"
                ]
            ),
            "authority_source_refs": (
                element[
                    "authority_source_refs"
                ]
            ),
        }
        for element in elements
    ]

    payload = {
        "schema": (
            CANON_TREE_MANIFEST_SCHEMA
        ),
        "authority_state": (
            "projection"
        ),
        "projection_authoritative": (
            False
        ),
        "rebuildable": True,
        "request_root": request_root,
        "resolved_root": (
            str(resolved_root)
        ),
        "scope": scope,
        "format": format_name,
        "ordering_policy": (
            ORDERING_POLICY
        ),
        "projection_policy_version": (
            PROJECTION_POLICY_VERSION
        ),
        "included_count": len(
            included
        ),
        "included_elements": included,
        "skipped": [],
        "warnings": sorted(
            set(warnings)
        ),
        "source_graph_digest": (
            source_graph_digest(
                elements
            )
        ),
        "output_digest": (
            sha256(output_text)
        ),
    }

    payload["manifest_digest"] = (
        sha256(
            canonical_json(payload)
        )
    )

    return payload


def canon_tree(
    con: sqlite3.Connection,
    *,
    request_root: str,
    scope: str,
    format_name: str,
) -> tuple[str, dict[str, Any]]:
    root = resolve_root(
        request_root
    )
    warnings: list[str] = []

    ordered = build_ordered_roots(
        con,
        root,
        scope,
        warnings,
    )

    elements = [
        build_element(
            con,
            root,
            path,
            depth,
        )
        for path, depth
        in ordered
    ]

    validate_elements(
        elements
    )

    output_text = render_output(
        format_name,
        root,
        scope,
        elements,
    )

    manifest = manifest_payload(
        request_root=request_root,
        resolved_root=root,
        scope=scope,
        format_name=format_name,
        elements=elements,
        warnings=warnings,
        output_text=output_text,
    )

    return (
        output_text,
        manifest,
    )


def run_all_projections() -> int:
    JSON_PROJECTIONS.mkdir(
        parents=True,
        exist_ok=True,
    )
    MD_PROJECTIONS.mkdir(
        parents=True,
        exist_ok=True,
    )
    SCRIPT_PROJECTIONS.mkdir(
        parents=True,
        exist_ok=True,
    )
    AUDIT_PROJECTIONS.mkdir(
        parents=True,
        exist_ok=True,
    )

    with connect() as con:
        ids = [
            row["id"]
            for row
            in con.execute(
                """
                SELECT id
                FROM instances
                ORDER BY id
                """
            ).fetchall()
        ]

        for instance_id in ids:
            project_instance_json(
                con,
                instance_id,
            )

        con.commit()

    return 0


def run_canon_tree(
    arguments: argparse.Namespace,
) -> int:
    with connect() as con:
        output_text, manifest = (
            canon_tree(
                con,
                request_root=(
                    arguments.root
                ),
                scope=arguments.scope,
                format_name=(
                    arguments.format
                ),
            )
        )

    if arguments.output:
        output_path = Path(
            arguments.output
        )

        if not output_path.is_absolute():
            raise ProjectionError(
                "--output must be an "
                "absolute path"
            )

        write_if_changed(
            output_path,
            output_text,
        )
    else:
        sys.stdout.write(
            output_text
        )

    if arguments.manifest:
        manifest_path = Path(
            arguments.manifest
        )

        if not manifest_path.is_absolute():
            raise ProjectionError(
                "--manifest must be an "
                "absolute path"
            )

        write_if_changed(
            manifest_path,
            (
                json.dumps(
                    manifest,
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            ),
        )

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Filament deterministic "
            "projection runtime"
        )
    )

    commands = parser.add_subparsers(
        dest="command"
    )

    commands.add_parser(
        "project-all",
        help=(
            "preserve existing all-instance "
            "JSON projection behavior"
        ),
    )

    tree = commands.add_parser(
        "canon-tree",
        help=(
            "compose colocated canon "
            "projections"
        ),
    )

    tree.add_argument(
        "root",
        help=(
            "absolute materialized element "
            "root"
        ),
    )

    scope = tree.add_mutually_exclusive_group()

    scope.add_argument(
        "--self",
        dest="scope",
        action="store_const",
        const="self",
    )
    scope.add_argument(
        "--children",
        dest="scope",
        action="store_const",
        const="children",
    )
    scope.add_argument(
        "--recursive",
        dest="scope",
        action="store_const",
        const="recursive",
    )

    tree.set_defaults(
        scope="recursive"
    )

    tree.add_argument(
        "--format",
        choices=(
            "md",
            "json",
            "jsonl",
            "ai",
        ),
        default="md",
    )

    tree.add_argument(
        "--output",
        help=(
            "optional absolute output path"
        ),
    )

    tree.add_argument(
        "--manifest",
        help=(
            "optional absolute manifest path"
        ),
    )

    return parser


def main() -> int:
    parser = build_parser()
    arguments = parser.parse_args()

    if arguments.command is None:
        return run_all_projections()

    if arguments.command == "project-all":
        return run_all_projections()

    if arguments.command == "canon-tree":
        return run_canon_tree(
            arguments
        )

    raise ProjectionError(
        f"unsupported command: "
        f"{arguments.command}"
    )


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )
    except (
        OSError,
        UnicodeError,
        sqlite3.Error,
        ProjectionError,
    ) as exc:
        print(
            (
                "ERROR: "
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
            file=sys.stderr,
        )
        raise SystemExit(1)

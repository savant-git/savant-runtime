#!/usr/bin/env python3
import json
import hashlib
import sqlite3
from pathlib import Path

ROOT = Path("/root/savant-runtime")
BASE = ROOT / "ontology/obelisks/segue"
DB = BASE / "authority_db/savant_authority.sqlite"
GRAPH = BASE / "authority_graph"

def stable_json(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value

def checksum(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def write_if_changed(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    old = path.read_text() if path.exists() else None
    if old == text:
        return False

    path.write_text(text)
    return True

def project_instance_json(con, instance_id):
    row = con.execute(
        """
        SELECT id, kind, type, level, status, authority, version,
               metadata_json, extensions_json, future_extensions_json,
               created_at, updated_at
        FROM instances
        WHERE id = ?
        """,
        (instance_id,),
    ).fetchone()

    if not row:
        raise SystemExit(f"[MISSING INSTANCE] {instance_id}")

    children = con.execute(
        """
        SELECT child_id, edge_type, ordinal
        FROM composition_edges
        WHERE parent_id = ?
        ORDER BY ordinal, child_id
        """,
        (instance_id,),
    ).fetchall()

    relationships = con.execute(
        """
        SELECT target_id, relationship_type
        FROM relationships
        WHERE source_id = ?
        ORDER BY relationship_type, target_id
        """,
        (instance_id,),
    ).fetchall()

    data = {
        "id": row["id"],
        "kind": row["kind"],
        "type": row["type"],
        "level": row["level"],
        "status": row["status"],
        "authority": row["authority"],
        "version": row["version"],
        "metadata": stable_json(row["metadata_json"]),
        "composition": {
            "children": [
                {
                    "id": c["child_id"],
                    "edge_type": c["edge_type"],
                    "ordinal": c["ordinal"]
                }
                for c in children
            ]
        },
        "relationships": [
            {
                "target": r["target_id"],
                "type": r["relationship_type"]
            }
            for r in relationships
        ],
        "extensions": stable_json(row["extensions_json"]),
        "future_extensions": stable_json(row["future_extensions_json"]),
        "provenance": {
            "source": "sqlite",
            "database": str(DB),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
    }

    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    target = GRAPH / "projections/json" / f"{instance_id.replace('.', '__')}.json"

    changed = write_if_changed(target, text)

    con.execute(
        """
        INSERT INTO projections
        (id, source_instance_id, projection_type, target_path, template_path, authority, checksum, generated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            checksum=excluded.checksum,
            generated_at=CURRENT_TIMESTAMP
        """,
        (
            f"projection.json.{instance_id}",
            instance_id,
            "json",
            str(target),
            "projection_engine/project.py:project_instance_json",
            "INSTANCE_PROJECTION_RULE",
            checksum(text),
        ),
    )

    print(("[WRITE] " if changed else "[SKIP]  ") + str(target))

def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    ids = [
        r["id"]
        for r in con.execute("SELECT id FROM instances ORDER BY id").fetchall()
    ]

    for instance_id in ids:
        project_instance_json(con, instance_id)

    con.commit()
    con.close()

if __name__ == "__main__":
    main()

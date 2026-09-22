#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
BASE="$ROOT/ontology/obelisks/segue"
EXILES="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"
FILAMENT="$EXILES/filament"
ENGINE="$FILAMENT/runtime/projection_engine"

mkdir -p "$ENGINE"

cat > "$ENGINE/project.py" <<'PY'
#!/usr/bin/env python3
import json
import hashlib
import sqlite3
from pathlib import Path

ROOT = Path("/root/savant-runtime")

OBELISKS_SEGUE = ROOT / "ontology/obelisks/segue"
AUTHORITY_DB = OBELISKS_SEGUE / "authority_db/savant_authority.sqlite"
AUTHORITY_GRAPH = OBELISKS_SEGUE / "authority_graph"

EXILES = ROOT / "ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"
FILAMENT = EXILES / "filament"

PROJECTIONS = FILAMENT / "projections"
JSON_PROJECTIONS = PROJECTIONS / "json"
MD_PROJECTIONS = PROJECTIONS / "md"
SCRIPT_PROJECTIONS = PROJECTIONS / "scripts"
AUDIT_PROJECTIONS = PROJECTIONS / "audit"

def parse_json(value, fallback):
    if value is None:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback

def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def write_if_changed(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old == text:
        return False

    path.write_text(text, encoding="utf-8")
    return True

def project_instance_json(con, instance_id):
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
        raise SystemExit(f"[MISSING] instance not found: {instance_id}")

    children = con.execute(
        """
        SELECT child_id, edge_type, ordinal, authority, metadata_json
        FROM composition_edges
        WHERE parent_id = ?
        ORDER BY ordinal, child_id
        """,
        (instance_id,),
    ).fetchall()

    relationships = con.execute(
        """
        SELECT target_id, relationship_type, authority, metadata_json
        FROM relationships
        WHERE source_id = ?
        ORDER BY relationship_type, target_id
        """,
        (instance_id,),
    ).fetchall()

    projection = {
        "id": row["id"],
        "kind": row["kind"],
        "type": row["type"],
        "level": row["level"],
        "status": row["status"],
        "authority": row["authority"],
        "version": row["version"],
        "metadata": parse_json(row["metadata_json"], {}),
        "composition": {
            "children": [
                {
                    "id": child["child_id"],
                    "edge_type": child["edge_type"],
                    "ordinal": child["ordinal"],
                    "authority": child["authority"],
                    "metadata": parse_json(child["metadata_json"], {})
                }
                for child in children
            ]
        },
        "relationships": [
            {
                "target": rel["target_id"],
                "type": rel["relationship_type"],
                "authority": rel["authority"],
                "metadata": parse_json(rel["metadata_json"], {})
            }
            for rel in relationships
        ],
        "extensions": parse_json(row["extensions_json"], {}),
        "future_extensions": parse_json(row["future_extensions_json"], {}),
        "projection": {
            "owner": "filament",
            "engine": "filament.runtime.projection_engine",
            "source": "sqlite.authority_db",
            "database": str(AUTHORITY_DB)
        },
        "provenance": {
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
    }

    text = json.dumps(projection, indent=2, sort_keys=True) + "\n"
    target = JSON_PROJECTIONS / f"{instance_id.replace('.', '__')}.json"

    changed = write_if_changed(target, text)

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
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
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
            "filament/runtime/projection_engine/project.py",
            "FILAMENT_PROJECTION_ENGINE",
            sha256(text),
            json.dumps({
                "owner": "filament",
                "reason": "Filament owns projection."
            }, sort_keys=True),
        ),
    )

    print(("[WRITE] " if changed else "[SKIP]  ") + str(target))

def main():
    if not AUTHORITY_DB.exists():
        raise SystemExit(f"[MISSING DB] {AUTHORITY_DB}")

    JSON_PROJECTIONS.mkdir(parents=True, exist_ok=True)
    MD_PROJECTIONS.mkdir(parents=True, exist_ok=True)
    SCRIPT_PROJECTIONS.mkdir(parents=True, exist_ok=True)
    AUDIT_PROJECTIONS.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(AUTHORITY_DB)
    con.row_factory = sqlite3.Row

    ids = [
        row["id"]
        for row in con.execute("SELECT id FROM instances ORDER BY id").fetchall()
    ]

    for instance_id in ids:
        project_instance_json(con, instance_id)

    con.commit()
    con.close()

if __name__ == "__main__":
    main()
PY

chmod +x "$ENGINE/project.py"

echo "[OK] Filament projection engine patched:"
echo "$ENGINE/project.py"

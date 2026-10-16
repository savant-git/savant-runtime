#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
DB="$ROOT/ontology/obelisks/segue/authority_db/savant_authority.sqlite"

python3 - <<'PY'
import json
import sqlite3
from pathlib import Path

db = Path("/root/savant-runtime/ontology/obelisks/segue/authority_db/savant_authority.sqlite")

con = sqlite3.connect(db)
cur = con.cursor()

items = [
    {
        "id": "exile.filament",
        "kind": "instance",
        "type": "exile",
        "level": "exile",
        "authority": "USER_DIRECTIVE",
        "metadata": {
            "function": "projection",
            "owns": [
                "projection_engine",
                "projection_runtime",
                "projection_workers",
                "generated_file_emission"
            ]
        }
    },
    {
        "id": "runtime.filament.projection_engine",
        "kind": "instance",
        "type": "runtime",
        "level": "runtime",
        "authority": "USER_DIRECTIVE",
        "metadata": {
            "owner": "exile.filament",
            "path": "ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/filament/runtime/projection_engine/project.py",
            "purpose": "Generate file projections from SQLite authority."
        }
    },
    {
        "id": "authority_db.savant",
        "kind": "instance",
        "type": "authority_db",
        "level": "authority",
        "authority": "USER_DIRECTIVE",
        "metadata": {
            "path": "ontology/obelisks/segue/authority_db/savant_authority.sqlite",
            "purpose": "Store authoritative primitives."
        }
    }
]

for item in items:
    cur.execute(
        """
        INSERT INTO instances
        (id, kind, type, level, status, authority, metadata_json)
        VALUES (?, ?, ?, ?, 'active', ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            kind=excluded.kind,
            type=excluded.type,
            level=excluded.level,
            authority=excluded.authority,
            metadata_json=excluded.metadata_json,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            item["id"],
            item["kind"],
            item["type"],
            item["level"],
            item["authority"],
            json.dumps(item["metadata"], sort_keys=True)
        )
    )

edges = [
    ("exile.filament", "runtime.filament.projection_engine", "owns", 10),
    ("runtime.filament.projection_engine", "authority_db.savant", "reads", 20)
]

for parent, child, edge_type, ordinal in edges:
    cur.execute(
        """
        INSERT INTO composition_edges
        (parent_id, child_id, edge_type, ordinal, authority)
        VALUES (?, ?, ?, ?, 'USER_DIRECTIVE')
        ON CONFLICT(parent_id, child_id, edge_type) DO UPDATE SET
            ordinal=excluded.ordinal,
            authority=excluded.authority
        """,
        (parent, child, edge_type, ordinal)
    )

con.commit()
con.close()

print("[OK] seeded Filament projection authority")
PY

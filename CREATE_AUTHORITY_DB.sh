#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
BASE="$ROOT/ontology/obelisks/segue"
DB_DIR="$BASE/authority_db"
GRAPH="$BASE/authority_graph"

mkdir -p \
  "$DB_DIR" \
  "$GRAPH/projection_engine" \
  "$GRAPH/projection_templates" \
  "$GRAPH/projections/json" \
  "$GRAPH/projections/md" \
  "$GRAPH/projections/scripts"

python3 - <<'PY'
import sqlite3
from pathlib import Path

db_path = Path("/root/savant-runtime/ontology/obelisks/segue/authority_db/savant_authority.sqlite")
db_path.parent.mkdir(parents=True, exist_ok=True)

con = sqlite3.connect(db_path)
cur = con.cursor()

cur.executescript("""
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS instances (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    type TEXT NOT NULL,
    level TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    authority TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '1.0.0',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    extensions_json TEXT NOT NULL DEFAULT '{}',
    future_extensions_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS composition_edges (
    parent_id TEXT NOT NULL,
    child_id TEXT NOT NULL,
    edge_type TEXT NOT NULL DEFAULT 'composes',
    ordinal INTEGER NOT NULL DEFAULT 0,
    authority TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (parent_id, child_id, edge_type),
    FOREIGN KEY(parent_id) REFERENCES instances(id) ON DELETE CASCADE,
    FOREIGN KEY(child_id) REFERENCES instances(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS relationships (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    authority TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (source_id, target_id, relationship_type),
    FOREIGN KEY(source_id) REFERENCES instances(id) ON DELETE CASCADE,
    FOREIGN KEY(target_id) REFERENCES instances(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS projections (
    id TEXT PRIMARY KEY,
    source_instance_id TEXT NOT NULL,
    projection_type TEXT NOT NULL,
    target_path TEXT NOT NULL,
    template_path TEXT NOT NULL,
    authority TEXT NOT NULL,
    checksum TEXT DEFAULT '',
    generated_at TEXT DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(source_instance_id) REFERENCES instances(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS policies (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'active',
    authority TEXT NOT NULL,
    rule TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS segues (
    id TEXT PRIMARY KEY,
    source_id TEXT,
    target_id TEXT,
    segue_type TEXT NOT NULL,
    authority TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
""")

cur.execute("""
INSERT OR IGNORE INTO policies (id, authority, rule)
VALUES (
  'policy.files_are_projections',
  'USER_DIRECTIVE',
  'Files are projections. SQLite stores authoritative primitives.'
)
""")

cur.execute("""
INSERT OR IGNORE INTO instances
(id, kind, type, level, status, authority, metadata_json)
VALUES
(
  'template.universal_instance',
  'instance',
  'template',
  'template',
  'active',
  'USER_DIRECTIVE',
  '{"purpose":"Universal instance template projected from SQLite authority."}'
)
""")

con.commit()
con.close()

print(f"[OK] authority db created: {db_path}")
PY

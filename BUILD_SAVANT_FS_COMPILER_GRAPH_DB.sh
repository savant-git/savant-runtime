#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
AUDIT="$ROOT/audit/fs_compiler"
DB_DIR="$AUDIT/db"
DB="$DB_DIR/savant_fs_compiler.sqlite"

mkdir -p "$DB_DIR"

python3 - <<'PY'
import sqlite3
from pathlib import Path

db = Path("/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite")
db.parent.mkdir(parents=True, exist_ok=True)

con = sqlite3.connect(db)
cur = con.cursor()

cur.executescript("""
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    relpath TEXT NOT NULL,
    basename TEXT NOT NULL,
    kind TEXT NOT NULL,
    extension TEXT NOT NULL DEFAULT '',
    size_bytes INTEGER NOT NULL DEFAULT 0,
    modified_utc TEXT NOT NULL DEFAULT '',
    sha256 TEXT NOT NULL DEFAULT '',
    ignored INTEGER NOT NULL DEFAULT 0,
    observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classifications (
    file_id TEXT PRIMARY KEY,
    owner TEXT NOT NULL DEFAULT 'unknown',
    scope TEXT NOT NULL DEFAULT 'unknown',
    containment TEXT NOT NULL DEFAULT 'unknown',
    edifice_level TEXT NOT NULL DEFAULT 'unknown',
    authority_class TEXT NOT NULL DEFAULT 'unknown',
    move_policy TEXT NOT NULL DEFAULT 'MANUAL_REVIEW',
    confidence INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS references_found (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file_id TEXT NOT NULL,
    reference_type TEXT NOT NULL,
    reference_value TEXT NOT NULL,
    target_guess TEXT NOT NULL DEFAULT '',
    line_number INTEGER NOT NULL DEFAULT 0,
    line_text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(source_file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS python_imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file_id TEXT NOT NULL,
    import_type TEXT NOT NULL,
    module TEXT NOT NULL,
    symbol TEXT NOT NULL DEFAULT '',
    level INTEGER NOT NULL DEFAULT 0,
    resolved_path TEXT NOT NULL DEFAULT '',
    resolution_status TEXT NOT NULL DEFAULT 'unresolved',
    line_number INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(source_file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS shell_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file_id TEXT NOT NULL,
    dep_type TEXT NOT NULL,
    command TEXT NOT NULL DEFAULT '',
    target_text TEXT NOT NULL,
    resolved_path TEXT NOT NULL DEFAULT '',
    resolution_status TEXT NOT NULL DEFAULT 'unresolved',
    line_number INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(source_file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS service_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file_id TEXT,
    service_type TEXT NOT NULL,
    name TEXT NOT NULL,
    exec_text TEXT NOT NULL DEFAULT '',
    resolved_path TEXT NOT NULL DEFAULT '',
    resolution_status TEXT NOT NULL DEFAULT 'unresolved',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS symlinks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT NOT NULL,
    link_path TEXT NOT NULL,
    target_text TEXT NOT NULL,
    resolved_path TEXT NOT NULL DEFAULT '',
    target_exists INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS duplicate_hashes (
    sha256 TEXT NOT NULL,
    file_count INTEGER NOT NULL,
    paths_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (sha256)
);

CREATE TABLE IF NOT EXISTS move_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT NOT NULL,
    proposed_target TEXT NOT NULL,
    decision TEXT NOT NULL DEFAULT 'BLOCK',
    reason TEXT NOT NULL DEFAULT '',
    confidence INTEGER NOT NULL DEFAULT 0,
    reference_count INTEGER NOT NULL DEFAULT 0,
    package_risk TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS simulations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulation_id TEXT NOT NULL,
    file_id TEXT NOT NULL,
    source_path TEXT NOT NULL,
    proposed_target TEXT NOT NULL,
    status TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS validation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    validation_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    check_name TEXT NOT NULL,
    file_id TEXT,
    path TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
CREATE INDEX IF NOT EXISTS idx_files_relpath ON files(relpath);
CREATE INDEX IF NOT EXISTS idx_files_sha ON files(sha256);
CREATE INDEX IF NOT EXISTS idx_class_scope ON classifications(scope);
CREATE INDEX IF NOT EXISTS idx_class_owner ON classifications(owner);
CREATE INDEX IF NOT EXISTS idx_refs_source ON references_found(source_file_id);
CREATE INDEX IF NOT EXISTS idx_py_source ON python_imports(source_file_id);
CREATE INDEX IF NOT EXISTS idx_shell_source ON shell_dependencies(source_file_id);
CREATE INDEX IF NOT EXISTS idx_move_file ON move_candidates(file_id);
""")

con.commit()
con.close()

print(f"[OK] graph DB ready: {db}")
PY

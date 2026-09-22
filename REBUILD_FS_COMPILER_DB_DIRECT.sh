#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
AUDIT="$ROOT/audit/fs_compiler"
DB_DIR="$AUDIT/db"
DB="$DB_DIR/savant_fs_compiler.sqlite"

mkdir -p "$DB_DIR"

python3 - <<'PY'
import hashlib
import os
import sqlite3
from pathlib import Path

ROOT = Path("/root/savant-runtime")
DB = ROOT / "audit/fs_compiler/db/savant_fs_compiler.sqlite"

IGNORE_PARTS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    "dist",
    "build",
    ".venv",
    ".venv_voice",
    "venv",
    "site-packages",
    "exports",
    "repair_backups",
}

def ignored(path: Path) -> bool:
    parts = set(path.parts)
    if parts & IGNORE_PARTS:
        return True
    if "/audit/fs_compiler/" in str(path):
        return True
    return False

def sha256(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        return ""
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""

def kind(path: Path) -> str:
    if path.is_symlink():
        return "symlink"
    if path.is_dir():
        return "directory"
    if path.is_file():
        return "file"
    return "unknown"

def ext(path: Path) -> str:
    return path.suffix[1:] if path.suffix else ""

def owner_scope(rel: str):
    exiles_root = "ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"
    exiles = [
        "carbon","cataxis","coda","envoy","filament","graffiti","lore","mobius",
        "modus","niche","notary","opus","pact","palaver","shatter","underscore",
        "urge","zero"
    ]

    owner = "unknown"
    scope = "unknown"

    for exile in exiles:
        if rel == f"{exiles_root}/{exile}" or rel.startswith(f"{exiles_root}/{exile}/"):
            owner = exile
            scope = "single_exile"
            break

    if rel.startswith("ontology/obelisks/segue/"):
        scope = "all_obelisks"
    elif rel.startswith(f"{exiles_root}/segue/"):
        scope = "all_exiles"
    elif rel.startswith("ontology/"):
        scope = "ontology"
    elif rel.startswith("ops/"):
        scope = "runtime_ops"
    elif rel.endswith(".sh"):
        base = Path(rel).name.lower()
        if "exile" in base:
            scope = "all_exiles"
        elif "ontology" in base:
            scope = "ontology"
        elif "runtime" in base or "savant" in base:
            scope = "runtime"
        else:
            scope = "runtime_ops"

    return owner, scope

def containment(rel: str, extension: str) -> str:
    if "/apps/" in rel:
        return "application_package"
    if "/runtime/protocol/" in rel:
        return "runtime_protocol_package"
    if "/runtime/providers/" in rel:
        return "runtime_provider_package"
    if "/runtime/event_bus/" in rel:
        return "runtime_event_bus_package"
    if "/runtime/projection_engine/" in rel:
        return "projection_engine_package"
    if "/runtime/" in rel:
        return "runtime_package"
    if "/segue/" in rel:
        return "segue_container"
    if extension == "sh":
        return "shell_script"
    if extension == "py":
        return "python_module"
    return "unknown"

def edifice(scope: str, cont: str) -> str:
    if scope == "all_obelisks":
        return "obelisks.segue"
    if scope == "all_exiles":
        return "exiles.segue"
    if scope == "single_exile":
        if cont == "application_package":
            return "prodigal.app"
        if cont.endswith("_package"):
            return "prodigal.runtime_package"
        return "exile"
    return scope

def authority(rel: str, extension: str) -> str:
    if "/audit/" in rel:
        return "generated_audit"
    if "/reports/" in rel:
        return "generated_report"
    if "/projections/" in rel:
        return "generated_projection"
    if "/canon/" in rel:
        return "canon"
    if "/authority" in rel or "/authority_db/" in rel:
        return "authority"
    if "/registry/" in rel:
        return "registry"
    if "/runtime/" in rel:
        return "runtime"
    if extension == "sh":
        return "operational_mote"
    if extension == "py":
        return "implementation"
    return "unknown"

def move_policy(cont: str, auth: str, scope: str) -> str:
    if cont in {
        "application_package",
        "runtime_protocol_package",
        "runtime_provider_package",
        "runtime_event_bus_package",
        "projection_engine_package",
    }:
        return "DO_NOT_FLATTEN_PACKAGE"
    if auth.startswith("generated_"):
        return "DO_NOT_MOVE_GENERATED"
    if scope in {"all_exiles","all_obelisks","ontology","runtime","runtime_ops","single_exile"}:
        return "ELIGIBLE_FOR_PLANNING"
    return "MANUAL_REVIEW"

con = sqlite3.connect(DB)
cur = con.cursor()

cur.executescript("""
PRAGMA journal_mode=WAL;
DROP TABLE IF EXISTS files;
DROP TABLE IF EXISTS classifications;
DROP TABLE IF EXISTS references_found;
DROP TABLE IF EXISTS python_imports;
DROP TABLE IF EXISTS shell_dependencies;
DROP TABLE IF EXISTS service_references;
DROP TABLE IF EXISTS symlinks;
DROP TABLE IF EXISTS duplicate_hashes;

CREATE TABLE files (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    relpath TEXT NOT NULL,
    basename TEXT NOT NULL,
    kind TEXT NOT NULL,
    extension TEXT NOT NULL DEFAULT '',
    size_bytes INTEGER NOT NULL DEFAULT 0,
    modified_utc TEXT NOT NULL DEFAULT '',
    sha256 TEXT NOT NULL DEFAULT '',
    ignored INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE classifications (
    file_id TEXT PRIMARY KEY,
    owner TEXT NOT NULL DEFAULT 'unknown',
    scope TEXT NOT NULL DEFAULT 'unknown',
    containment TEXT NOT NULL DEFAULT 'unknown',
    edifice_level TEXT NOT NULL DEFAULT 'unknown',
    authority_class TEXT NOT NULL DEFAULT 'unknown',
    move_policy TEXT NOT NULL DEFAULT 'MANUAL_REVIEW',
    confidence INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE references_found (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file_id TEXT NOT NULL,
    reference_type TEXT NOT NULL,
    reference_value TEXT NOT NULL,
    target_guess TEXT NOT NULL DEFAULT '',
    line_number INTEGER NOT NULL DEFAULT 0,
    line_text TEXT NOT NULL DEFAULT ''
);

CREATE TABLE python_imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file_id TEXT NOT NULL,
    import_type TEXT NOT NULL,
    module TEXT NOT NULL,
    symbol TEXT NOT NULL DEFAULT '',
    level INTEGER NOT NULL DEFAULT 0,
    resolved_path TEXT NOT NULL DEFAULT '',
    resolution_status TEXT NOT NULL DEFAULT 'unresolved',
    line_number INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE shell_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file_id TEXT NOT NULL,
    dep_type TEXT NOT NULL,
    command TEXT NOT NULL DEFAULT '',
    target_text TEXT NOT NULL,
    resolved_path TEXT NOT NULL DEFAULT '',
    resolution_status TEXT NOT NULL DEFAULT 'unresolved',
    line_number INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE service_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file_id TEXT,
    service_type TEXT NOT NULL,
    name TEXT NOT NULL,
    exec_text TEXT NOT NULL DEFAULT '',
    resolved_path TEXT NOT NULL DEFAULT '',
    resolution_status TEXT NOT NULL DEFAULT 'unresolved'
);

CREATE TABLE symlinks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT NOT NULL,
    link_path TEXT NOT NULL,
    target_text TEXT NOT NULL,
    resolved_path TEXT NOT NULL DEFAULT '',
    target_exists INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE duplicate_hashes (
    sha256 TEXT PRIMARY KEY,
    file_count INTEGER NOT NULL,
    paths_json TEXT NOT NULL
);
""")

count = 0

for dirpath, dirnames, filenames in os.walk(ROOT, followlinks=False):
    pdir = Path(dirpath)

    dirnames[:] = [
        d for d in dirnames
        if not ignored(pdir / d)
    ]

    for name in dirnames + filenames:
        path = pdir / name
        rel = str(path.relative_to(ROOT))
        is_ignored = ignored(path)
        k = kind(path)
        e = ext(path)

        try:
            st = path.lstat()
            size = st.st_size
            modified = str(st.st_mtime)
        except Exception:
            size = 0
            modified = ""

        fid = hashlib.sha256(str(path).encode()).hexdigest()
        file_sha = sha256(path)

        cur.execute(
            """
            INSERT INTO files
            (id,path,relpath,basename,kind,extension,size_bytes,modified_utc,sha256,ignored)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (fid, str(path), rel, name, k, e, size, modified, file_sha, 1 if is_ignored else 0)
        )

        own, sc = owner_scope(rel)
        cont = containment(rel, e)
        hier = edifice(sc, cont)
        auth = authority(rel, e)
        policy = move_policy(cont, auth, sc)

        conf = 0
        if policy == "DO_NOT_FLATTEN_PACKAGE":
            conf = 100
        elif policy == "ELIGIBLE_FOR_PLANNING":
            conf = 80

        cur.execute(
            """
            INSERT INTO classifications
            (file_id,owner,scope,containment,edifice_level,authority_class,move_policy,confidence)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (fid, own, sc, cont, hier, auth, policy, conf)
        )

        count += 1

con.commit()

print("[OK] direct DB rebuild complete")
print("objects:", count)
print("files:", cur.execute("select count(*) from files where ignored=0 and kind='file'").fetchone()[0])
print("python files:", cur.execute("select count(*) from files where ignored=0 and kind='file' and extension='py'").fetchone()[0])
print("shell files:", cur.execute("select count(*) from files where ignored=0 and kind='file' and extension='sh'").fetchone()[0])

con.close()
PY

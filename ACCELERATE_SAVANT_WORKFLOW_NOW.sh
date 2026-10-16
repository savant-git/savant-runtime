#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
TOOLS="$ROOT/tools/savant_accelerator"
BIN="$ROOT/bin"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$TOOLS" "$BIN" "$ROOT/audit/accelerator" "$ROOT/repair_backups/$STAMP"

cat > "$TOOLS/savant_accelerator.py" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import py_compile
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path("/root/savant-runtime")
AUDIT = ROOT / "audit"
DB = ROOT / "audit/fs_compiler/db/savant_fs_compiler.sqlite"
CTX = ROOT / "context"
OUT = ROOT / "audit/accelerator"

IGNORE = {
    ".git", ".venv", ".venv_voice", "node_modules", "__pycache__",
    "site-packages", "exports", "repair_backups"
}

EXILES = {
    "carbon", "cataxis", "coda", "envoy", "filament", "graffiti", "lore", "mobius",
    "modus", "niche", "notary", "opus", "pact", "palaver", "shatter", "underscore",
    "urge", "zero",
}

TEXT_EXTS = {
    ".py", ".sh", ".json", ".md", ".txt", ".yaml", ".yml", ".toml",
    ".service", ".timer", ".js", ".jsx", ".ts", ".tsx", ".css", ".html"
}

def ignored(p: Path) -> bool:
    return any(part in IGNORE for part in p.parts)

def run(cmd: list[str], ok: bool = True) -> subprocess.CompletedProcess:
    print("+", " ".join(cmd), flush=True)
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if p.stdout:
        print(p.stdout, end="")
    if p.stderr:
        print(p.stderr, end="", file=sys.stderr)
    if ok and p.returncode != 0:
        raise SystemExit(p.returncode)
    return p

def sh(script: str, ok: bool = True) -> subprocess.CompletedProcess:
    return run(["bash", "-lc", script], ok=ok)

def fast_audit() -> None:
    scripts = [
        "REBUILD_FS_COMPILER_DB_DIRECT.sh",
        "BUILD_SAVANT_FS_COMPILER_PASS_06_PY_IMPORTS.sh",
        "BUILD_SAVANT_FS_COMPILER_PASS_07_SHELL_DEPS.sh",
        "BUILD_SAVANT_FS_COMPILER_PASS_08_RUNTIME_LAUNCHERS.sh",
        "BUILD_SAVANT_FS_COMPILER_PASS_09_SYMLINKS.sh",
        "BUILD_SAVANT_FS_COMPILER_PASS_10_DUPLICATES.sh",
    ]
    for s in scripts:
        p = ROOT / s
        if p.exists():
            run(["bash", str(p)], ok=False)

def compile_all() -> dict:
    failures = []
    counts = Counter()

    for p in ROOT.rglob("*"):
        if ignored(p) or not p.is_file():
            continue

        if p.suffix == ".py":
            counts["python"] += 1
            try:
                py_compile.compile(str(p), doraise=True)
            except Exception as e:
                failures.append({"kind": "python", "path": str(p.relative_to(ROOT)), "error": str(e)})

        elif p.suffix == ".sh":
            counts["shell"] += 1
            proc = subprocess.run(["bash", "-n", str(p)], text=True, capture_output=True)
            if proc.returncode != 0:
                failures.append({"kind": "shell", "path": str(p.relative_to(ROOT)), "error": proc.stderr.strip()})

        elif p.suffix == ".json":
            counts["json"] += 1
            try:
                json.loads(p.read_text(encoding="utf-8", errors="replace"))
            except Exception as e:
                failures.append({"kind": "json", "path": str(p.relative_to(ROOT)), "error": str(e)})

    return {"counts": dict(counts), "failures": failures}

def owner(rel: str) -> dict:
    p = Path(rel)
    parts = p.parts
    first = parts[0] if parts else rel

    if "exiles" in parts:
        i = parts.index("exiles")
        if i + 1 < len(parts):
            x = parts[i + 1]
            if x in EXILES:
                return {"owner": x, "scope": "single_exile", "zone": f"exile.{x}", "generated": False}
            if x == "segue":
                return {"owner": "exiles", "scope": "all_exiles", "zone": "exiles.segue", "generated": False}

    generated = {
        "audit": "audit",
        "imports": "imports",
        "exports": "exports",
        "_reports": "reports",
        "repair_backups": "backup",
    }
    authority = {
        "canon": "canon",
        "authority_graph": "authority_graph",
        "ontology": "ontology",
    }
    runtime = {
        "runtime": "runtime",
        "vault": "vault",
        "tools": "tools",
        "scripts": "scripts",
        "ops": "ops",
        "context": "context",
        "port": "port",
        "webui_ultra": "palaver.webui_ultra",
    }

    if first in generated:
        return {"owner": generated[first], "scope": "generated", "zone": generated[first], "generated": True}
    if first in authority:
        return {"owner": authority[first], "scope": "authority", "zone": authority[first], "generated": False}
    if first in runtime:
        return {"owner": runtime[first], "scope": "runtime", "zone": runtime[first], "generated": False}

    if "/" not in rel:
        if rel.endswith(".sh"):
            return {"owner": "runtime_ops", "scope": "root_orchestration_script", "zone": "ops.runtime.scripts", "generated": False}
        if rel.endswith(".py"):
            return {"owner": "runtime", "scope": "root_runtime_python", "zone": "runtime.root", "generated": False}
        if rel.endswith(".log"):
            return {"owner": "runtime_logs", "scope": "runtime_log", "zone": "logs", "generated": True}
        if rel.startswith("current_runtime_source_dump_"):
            return {"owner": "imports", "scope": "source_dump", "zone": "imports.source_dump", "generated": True}
        if rel in {"audit", "imports", "ontology", "authority_graph", "canon", "context", "runtime", "scripts", "tools", "vault", "port", "_reports"}:
            return {"owner": "namespace", "scope": "top_level_namespace", "zone": f"namespace.{rel}", "generated": False}

    return {"owner": "unknown", "scope": "unknown", "zone": "unknown", "generated": False}

def ownership_graph() -> dict:
    nodes = {}
    unknowns = []
    violations = []

    if not DB.exists():
        return {"error": "missing db"}

    con = sqlite3.connect(DB)
    cur = con.cursor()

    rows = cur.execute("""
        SELECT path, relpath, basename, kind, extension, sha256
        FROM files
        WHERE ignored=0
        ORDER BY relpath
    """).fetchall()

    con.close()

    for abspath, rel, basename, kind, ext, sha in rows:
        o = owner(rel)
        canonical = True
        reason = "ok"

        if o["owner"] == "unknown":
            canonical = False
            reason = "unknown_owner"
            unknowns.append(rel)

        elif kind == "file" and ext == "sh" and "/" not in rel:
            canonical = False
            reason = "root_shell_script_should_be_ops_scoped"

        node = {
            "path": rel,
            "absolute_path": abspath,
            "basename": basename,
            "kind": kind,
            "extension": ext,
            "sha256": sha,
            "owner": o["owner"],
            "scope": o["scope"],
            "canonical_zone": o["zone"],
            "generated": o["generated"],
            "canonical": canonical,
            "reason": reason,
        }
        nodes[rel] = node
        if not canonical:
            violations.append(node)

    graph = {
        "id": "canonical_ownership_graph",
        "node_count": len(nodes),
        "unknown_count": len(unknowns),
        "violation_count": len(violations),
        "nodes": nodes,
        "unknowns": unknowns,
        "violations": violations,
    }

    (CTX / "CANONICAL_OWNERSHIP_GRAPH.json").write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n")
    return graph

def semantic_graph() -> dict:
    nodes = {}
    edges = []
    unresolved = []
    parse_failures = []

    semantic_names = {
        "entity.json", "module.json", "contracts.json", "capabilities.json",
        "interfaces.json", "manifests.json", "templates.json", "versions.json",
        "defaults.json", "inheritance.json", "edges.json", "nodes.json",
        "relationships.json", "projection_engine.json", "runtime_graph.json",
        "authority_index.json", "lineage_index.json",
    }

    json_files = []
    for p in ROOT.rglob("*.json"):
        if ignored(p):
            continue
        if p.name in semantic_names or any(x in p.parts for x in ("registry", "authority", "lineage", "graph", "interface", "segue", "authority_graph")):
            json_files.append(p)

    id_index = {}

    for p in sorted(json_files):
        rel = str(p.relative_to(ROOT))
        try:
            data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        except Exception as e:
            parse_failures.append({"path": rel, "error": str(e)})
            continue

        nid = data.get("id") if isinstance(data, dict) and isinstance(data.get("id"), str) else rel
        kind = data.get("kind") if isinstance(data, dict) else "json"
        nodes[nid] = {"id": nid, "path": rel, "kind": kind or "json"}
        id_index[nid] = rel

    def walk(obj, src, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                kp = f"{path}.{k}" if path else k
                if isinstance(v, str) and (":" in v or "/" in v or "." in v):
                    target = ""
                    resolved = False
                    if v in id_index:
                        target = id_index[v]; resolved = True
                    elif v.startswith(("/root/savant-runtime/", "ontology/", "canon/", "authority_graph/")):
                        target_path = Path(v) if v.startswith("/") else ROOT / v
                        resolved = target_path.exists()
                        target = str(target_path)
                    e = {"source": src, "key_path": kp, "relationship": k, "reference": v, "target": target, "resolved": resolved}
                    edges.append(e)
                    if not resolved:
                        unresolved.append(e)
                walk(v, src, kp)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, src, f"{path}[{i}]")

    for p in sorted(json_files):
        rel = str(p.relative_to(ROOT))
        try:
            data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        src = data.get("id") if isinstance(data, dict) and data.get("id") else rel
        walk(data, src)

    graph = {
        "id": "semantic_reference_graph",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "unresolved_count": len(unresolved),
        "parse_failure_count": len(parse_failures),
        "nodes": nodes,
        "edges": edges,
        "unresolved": unresolved,
        "parse_failures": parse_failures,
    }
    (CTX / "SEMANTIC_REFERENCE_GRAPH.json").write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n")
    return graph

def blocker_summary() -> dict:
    if not DB.exists():
        return {"error": "missing db"}

    con = sqlite3.connect(DB)
    cur = con.cursor()
    out = {}

    queries = {
        "python_imports_unresolved": "SELECT count(*) FROM python_imports WHERE resolution_status!='resolved'",
        "shell_deps_unresolved": "SELECT count(*) FROM shell_dependencies WHERE resolution_status NOT IN ('resolved','dynamic')",
        "service_refs_unresolved": "SELECT count(*) FROM service_references WHERE resolution_status!='resolved'",
        "broken_symlinks": "SELECT count(*) FROM symlinks WHERE target_exists=0",
    }

    for k, q in queries.items():
        try:
            out[k] = cur.execute(q).fetchone()[0]
        except Exception as e:
            out[k] = f"ERR {e}"

    con.close()
    return out

def status() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    CTX.mkdir(parents=True, exist_ok=True)

    start = time.time()
    fast_audit()

    compile_report = compile_all()
    sem = semantic_graph()
    own = ownership_graph()
    blockers = blocker_summary()

    final = {
        "id": "savant_accelerated_status",
        "elapsed_seconds": round(time.time() - start, 3),
        "compile": compile_report,
        "semantic": {
            "nodes": sem.get("node_count"),
            "edges": sem.get("edge_count"),
            "unresolved": sem.get("unresolved_count"),
            "parse_failures": sem.get("parse_failure_count"),
        },
        "ownership": {
            "nodes": own.get("node_count"),
            "unknown": own.get("unknown_count"),
            "violations": own.get("violation_count"),
        },
        "blockers": blockers,
        "move_safe": False,
        "move_safe_reason": "Moves remain blocked until compile failures, unknown ownership, broken symlinks, and semantic unresolved references are resolved or classified.",
    }

    path = OUT / "latest_status.json"
    path.write_text(json.dumps(final, indent=2, sort_keys=True) + "\n")

    md = OUT / "latest_status.md"
    md.write_text(
        "# Savant accelerated status\n\n"
        f"- elapsed_seconds: {final['elapsed_seconds']}\n"
        f"- compile_failures: {len(compile_report['failures'])}\n"
        f"- semantic_unresolved: {final['semantic']['unresolved']}\n"
        f"- ownership_unknown: {final['ownership']['unknown']}\n"
        f"- ownership_violations: {final['ownership']['violations']}\n"
        f"- broken_symlinks: {blockers.get('broken_symlinks')}\n"
        f"- move_safe: false\n\n"
        "## Compile failures\n\n"
        + "\n".join(f"- {x['kind']} | `{x['path']}` | {x['error']}" for x in compile_report["failures"][:100])
        + "\n\n## Unknown owners\n\n"
        + "\n".join(f"- `{x}`" for x in own.get("unknowns", [])[:200])
        + "\n",
        encoding="utf-8",
    )

    print(json.dumps(final, indent=2, sort_keys=True))
    print()
    print(md)
    print(path)
    return final

def install() -> None:
    (ROOT / "bin").mkdir(exist_ok=True)
    wrapper = ROOT / "bin/savant"
    wrapper.write_text(f"""#!/usr/bin/env bash
set -euo pipefail
cd /root/savant-runtime
exec python3 "{ROOT}/tools/savant_accelerator/savant_accelerator.py" "$@"
""")
    wrapper.chmod(0o755)
    print("[OK] installed: /root/savant-runtime/bin/savant")
    print("Use: /root/savant-runtime/bin/savant status")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["install", "status", "fast-audit", "compile", "ownership", "semantic", "blockers"])
    args = ap.parse_args()

    if args.cmd == "install":
        install()
    elif args.cmd == "status":
        status()
    elif args.cmd == "fast-audit":
        fast_audit()
    elif args.cmd == "compile":
        print(json.dumps(compile_all(), indent=2, sort_keys=True))
    elif args.cmd == "ownership":
        fast_audit()
        print(json.dumps(ownership_graph(), indent=2, sort_keys=True))
    elif args.cmd == "semantic":
        print(json.dumps(semantic_graph(), indent=2, sort_keys=True))
    elif args.cmd == "blockers":
        print(json.dumps(blocker_summary(), indent=2, sort_keys=True))

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod +x "$TOOLS/savant_accelerator.py"

python3 "$TOOLS/savant_accelerator.py" install

cat > "$ROOT/FAST_SAVANT_STATUS.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
cd /root/savant-runtime
/root/savant-runtime/bin/savant status
SH

chmod +x "$ROOT/FAST_SAVANT_STATUS.sh"

echo
echo "[OK] accelerator installed."
echo
echo "Run this from now on:"
echo "cd /root/savant-runtime && ./FAST_SAVANT_STATUS.sh"

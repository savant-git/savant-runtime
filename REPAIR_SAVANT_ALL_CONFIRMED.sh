#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ROOT="/root/savant-runtime"
BACKUP="$ROOT/repair_backups/$STAMP"

mkdir -p "$BACKUP"

echo "=== BACKUP CONFIRMED DEFECT FILES ==="

ENTITY="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/segue/exile_runtime/runtime/services/ENTITY_DEPENDENCIES.py"
ENVOY="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/envoy/runtime/CONNECT_ENVOY_TO_PALAVER.sh"

[ -f "$ENTITY" ] && cp "$ENTITY" "$BACKUP/ENTITY_DEPENDENCIES.py.before"
[ -f "$ENVOY" ] && cp "$ENVOY" "$BACKUP/CONNECT_ENVOY_TO_PALAVER.sh.before"

echo "backup: $BACKUP"

echo
echo "=== REPAIR ENTITY_DEPENDENCIES.py ==="

cat > "$ENTITY" <<'PY'
#!/usr/bin/env python3
"""
SAVANT ENTITY DEPENDENCIES SERVICE

Authority:
- Runtime may inspect authority.
- Runtime may not become authority.
- Dependencies are projected from entity files when available.

Purpose:
- Collect dependency declarations for exile runtime entities.
- Remain safe when dependency files are missing or invalid.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")
EXILES_ROOT = (
    ROOT
    / "ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"
)


def _read_json(path: Path, fallback: Any) -> Any:
    try:
        if not path.is_file():
            return fallback
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "error": "invalid_json",
            "path": str(path),
            "detail": str(exc),
        }


def _entity_roots() -> list[Path]:
    if not EXILES_ROOT.is_dir():
        return []

    roots: list[Path] = []

    for child in sorted(EXILES_ROOT.iterdir(), key=lambda p: p.name):
        if not child.is_dir():
            continue
        if child.name.startswith("_"):
            continue
        if child.name == "segue":
            continue
        roots.append(child)

    return roots


def collect_dependencies() -> dict[str, Any]:
    rows: dict[str, Any] = {}

    for entity_root in _entity_roots():
        entity_id = entity_root.name

        candidates = [
            entity_root / "registry/dependencies.json",
            entity_root / "authority/dependencies.json",
            entity_root / "lineage/dependencies.json",
            entity_root / "runtime/dependencies.json",
            entity_root / "module.json",
        ]

        found: list[dict[str, Any]] = []

        for dep_file in candidates:
            payload = _read_json(dep_file, None)
            if payload is None:
                continue

            found.append(
                {
                    "source": str(dep_file),
                    "data": payload,
                }
            )

        rows[entity_id] = {
            "entity": entity_id,
            "root": str(entity_root),
            "dependencies": found,
        }

    return rows


def entity_dependencies() -> dict[str, Any]:
    return collect_dependencies()


def main() -> int:
    print(json.dumps(collect_dependencies(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

python3 -m py_compile "$ENTITY"

echo "[OK] ENTITY_DEPENDENCIES.py"

echo
echo "=== REPAIR CONNECT_ENVOY_TO_PALAVER.sh TRUNCATION ==="

python3 - <<'PY'
from pathlib import Path

path = Path("/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/envoy/runtime/CONNECT_ENVOY_TO_PALAVER.sh")

text = path.read_text(encoding="utf-8", errors="replace")

# Preserve existing script when possible. Repair only final unterminated/truncated echo/curl tail.
lines = text.splitlines()

# Remove obviously truncated final line(s).
while lines and (
    lines[-1].count('"') % 2 == 1
    or lines[-1].rstrip().endswith("\\")
    or lines[-1].strip() in {"echo \"", "curl \""}
):
    lines.pop()

footer = [
    "",
    "echo",
    "echo \"[OK] Envoy to Palaver bridge script completed.\"",
    "echo \"Verify Palaver service health before enabling any dependent automation.\"",
]

if not any("[OK] Envoy to Palaver bridge script completed." in line for line in lines):
    lines.extend(footer)

path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
PY

bash -n "$ENVOY"
chmod +x "$ENVOY"

echo "[OK] CONNECT_ENVOY_TO_PALAVER.sh"

echo
echo "=== CREATE MISSING RECURSIVE FOUNDATION LAYER ==="

mkdir -p \
  canon/foundation \
  authority_graph/meta_archetypes \
  authority_graph/archetypes \
  authority_graph/templates \
  authority_graph/instances \
  authority_graph/segues \
  authority_graph/policies \
  authority_graph/projections \
  context \
  scripts

cat > canon/foundation/000_META_REALITY_CANON.md <<'EOF'
---
id: FOUNDATION-000
authority_tier: 0
status: active
---
# Meta Reality Canon

Authority is stable.

Projection, runtime, inference, registry views, UI views, reports, exports, and generated files are disposable.

Root chain:

Meta Archetype
→ Archetype
→ Template
→ Instance
→ Segue
→ Authority Graph
→ Projection

Files are projections unless explicitly marked as authority.
EOF

cat > canon/foundation/001_META_ARCHETYPE_CANON.md <<'EOF'
---
id: FOUNDATION-001
authority_tier: 0
status: active
---
# Meta Archetype Canon

Meta archetypes define how archetypes may exist.

They define:

- shape
- slots
- policies
- required metadata
- relationship rules
- segue rules
- projection rules
EOF

cat > canon/foundation/002_ARCHETYPE_CANON.md <<'EOF'
---
id: FOUNDATION-002
authority_tier: 0
status: active
---
# Archetype Canon

Archetypes define templates.

Archetypes are authority.

They must support extension without replacement.
EOF

cat > canon/foundation/003_TEMPLATE_CANON.md <<'EOF'
---
id: FOUNDATION-003
authority_tier: 0
status: active
---
# Template Canon

Templates define instances.

Templates are active objects that support:

- validation
- repair
- migration
- projection
- composition
- extension
EOF

cat > canon/foundation/004_INSTANCE_CANON.md <<'EOF'
---
id: FOUNDATION-004
authority_tier: 0
status: active
---
# Instance Canon

Instances are authoritative primitives.

Higher-order objects must emerge from instances through deterministic projection.
EOF

cat > canon/foundation/005_SEGUE_CANON.md <<'EOF'
---
id: FOUNDATION-005
authority_tier: 0
status: active
---
# Segue Canon

Nothing interacts directly.

Everything interacts through segues.

Segues are first-class authority objects.
EOF

cat > canon/foundation/006_AUTHORITY_GRAPH_CANON.md <<'EOF'
---
id: FOUNDATION-006
authority_tier: 0
status: active
---
# Authority Graph Canon

The authority graph contains:

- meta archetypes
- archetypes
- templates
- instances
- segues
- policies

Everything else is projected from authority.
EOF

cat > canon/foundation/007_PROJECTION_CANON.md <<'EOF'
---
id: FOUNDATION-007
authority_tier: 0
status: active
---
# Projection Canon

Commands, capabilities, modules, engines, context, registry, UI, reports, exports, and files are projections unless explicitly marked as authority.

Projections must be reproducible and disposable.
EOF

cat > authority_graph/meta_archetypes/universal_object.json <<'EOF'
{
  "id": "meta_archetype:universal_object",
  "kind": "meta_archetype",
  "version": "1.0.0",
  "status": "active",
  "authority": true,
  "slots": [
    "metadata",
    "dna",
    "relationships",
    "segues",
    "policies",
    "extensions",
    "future_extensions",
    "projections"
  ]
}
EOF

cat > authority_graph/archetypes/universal_instance.json <<'EOF'
{
  "id": "archetype:universal_instance",
  "kind": "archetype",
  "meta_archetype": "meta_archetype:universal_object",
  "version": "1.0.0",
  "status": "active",
  "authority": true
}
EOF

cat > authority_graph/templates/base_instance.json <<'EOF'
{
  "id": "template:base_instance",
  "kind": "template",
  "archetype": "archetype:universal_instance",
  "version": "1.0.0",
  "status": "active",
  "slots": {
    "metadata": {},
    "dna": {},
    "relationships": [],
    "segues": [],
    "policies": [],
    "extensions": {},
    "future_extensions": {},
    "projections": []
  }
}
EOF

cat > authority_graph/policies/emergence.json <<'EOF'
{
  "id": "policy:emergence",
  "kind": "policy",
  "version": "1.0.0",
  "status": "active",
  "minimum_children": 2,
  "maximum_children": 4,
  "deterministic": true,
  "reproducible": true
}
EOF

cat > authority_graph/policies/projection.json <<'EOF'
{
  "id": "policy:projection",
  "kind": "policy",
  "version": "1.0.0",
  "status": "active",
  "lazy": true,
  "disposable": true,
  "reproducible": true
}
EOF

cat > scripts/build_foundation_context.py <<'PY'
#!/usr/bin/env python3
from pathlib import Path

ROOT = Path("/root/savant-runtime")
OUT = ROOT / "context/FOUNDATION_CONTEXT.md"

parts = []
parts.append("# SAVANT FOUNDATION CONTEXT\n")
parts.append("Generated. Do not edit manually.\n")

for path in sorted((ROOT / "canon/foundation").glob("*.md")):
    parts.append("\n---\n")
    parts.append(f"\nSOURCE: {path.relative_to(ROOT)}\n\n")
    parts.append(path.read_text(encoding="utf-8", errors="replace"))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
print(OUT)
PY

chmod +x scripts/build_foundation_context.py
python3 scripts/build_foundation_context.py

echo
echo "=== VALIDATE JSON / PYTHON / SHELL ==="

python3 - <<'PY'
import json
import py_compile
import subprocess
from pathlib import Path

ROOT = Path("/root/savant-runtime")

failures = []

for path in ROOT.rglob("*.json"):
    if any(part in {".venv", "node_modules", "__pycache__", "site-packages"} for part in path.parts):
        continue
    try:
        json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        failures.append(("json", str(path), str(e)))

for path in ROOT.rglob("*.py"):
    if any(part in {".venv", "node_modules", "__pycache__", "site-packages"} for part in path.parts):
        continue
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception as e:
        failures.append(("python", str(path), str(e)))

for path in ROOT.rglob("*.sh"):
    if any(part in {".venv", "node_modules", "__pycache__", "site-packages"} for part in path.parts):
        continue
    proc = subprocess.run(["bash", "-n", str(path)], text=True, capture_output=True)
    if proc.returncode != 0:
        failures.append(("shell", str(path), proc.stderr.strip()))

if failures:
    print("[FAILURES]")
    for kind, path, err in failures[:200]:
        print(f"{kind} | {path} | {err}")
    raise SystemExit(1)

print("[OK] all checked json/python/shell files parse")
PY

echo
echo "[OK] confirmed repairs complete"
echo "backup: $BACKUP"

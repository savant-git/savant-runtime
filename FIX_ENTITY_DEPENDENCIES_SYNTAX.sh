#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

TARGET="/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/segue/exile_runtime/runtime/services/ENTITY_DEPENDENCIES.py"
BACKUP="${TARGET}.before_syntax_fix_$(date -u +%Y%m%dT%H%M%SZ)"

cp "$TARGET" "$BACKUP"

python3 - <<'PY'
from pathlib import Path

target = Path("/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/segue/exile_runtime/runtime/services/ENTITY_DEPENDENCIES.py")

text = target.read_text(encoding="utf-8", errors="replace")

text = text.replace(
    'if __name__ == "__main',
    'if __name__ == "__main__":'
)

target.write_text(text, encoding="utf-8")
PY

python3 -m py_compile "$TARGET"

echo "[OK] fixed syntax"
echo "backup: $BACKUP"

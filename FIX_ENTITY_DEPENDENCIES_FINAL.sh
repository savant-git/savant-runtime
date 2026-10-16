#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

TARGET="/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/segue/exile_runtime/runtime/services/ENTITY_DEPENDENCIES.py"
BACKUP="${TARGET}.before_final_repair_$(date -u +%Y%m%dT%H%M%SZ)"

cp "$TARGET" "$BACKUP"

python3 - <<'PY'
from pathlib import Path

target = Path("/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/segue/exile_runtime/runtime/services/ENTITY_DEPENDENCIES.py")

text = target.read_text(encoding="utf-8", errors="replace")

bad = 'if __name__ == "__main'
good = '''if __name__ == "__main__":
    import json
    print(json.dumps(entity_dependencies(), indent=2, sort_keys=True))
'''

if bad in text:
    text = text.split(bad)[0].rstrip() + "\n\n\n" + good

target.write_text(text, encoding="utf-8")
PY

python3 -m py_compile "$TARGET"

echo "[OK] ENTITY_DEPENDENCIES.py repaired"
echo "backup: $BACKUP"

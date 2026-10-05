#!/usr/bin/env bash
set -euo pipefail
ROOT="/mnt/data/savant_upgrade_packet"
PY="$ROOT/rubric/structural_intelligence/source/savant_structural_intelligence.py"
TEST="$ROOT/rubric/structural_intelligence/tests/test_savant_structural_intelligence.py"
DUMP="/mnt/data/sdump_savant-runtime_080426.txt"
OUT="/mnt/data/savant_upgrade_packet/generated-audit"
python3 -m py_compile "$PY"
python3 "$TEST"
rm -rf "$OUT"
python3 "$PY" --dump "$DUMP" --output "$OUT" --passes 50
python3 -m json.tool "$OUT/audit.json" >/dev/null
python3 -m json.tool "$OUT/migration-proposal.json" >/dev/null
python3 -m json.tool "$OUT/opus-apertures.json" >/dev/null
printf 'validated: %s\n' "$OUT"

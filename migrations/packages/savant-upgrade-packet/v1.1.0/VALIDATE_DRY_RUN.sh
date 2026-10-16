#!/usr/bin/env bash
set -euo pipefail
ROOT="/mnt/data/savant_upgrade_packet"
PY="$ROOT/rubric/dry_run/source/savant_dry_run.py"
TEST="$ROOT/rubric/dry_run/tests/test_savant_dry_run.py"
DUMP="/mnt/data/sdump_savant-runtime_080526.txt"
PROPOSAL="$ROOT/generated-audit-080526/migration-proposal.json"
OUT="$ROOT/generated-dry-run-080526"
python3 -m py_compile "$PY"
python3 "$TEST"
rm -rf "$OUT"
set +e
python3 "$PY" --dump "$DUMP" --proposal "$PROPOSAL" --output "$OUT"
rc=$?
set -e
case "$rc" in
  0|2|3) ;;
  *) exit "$rc" ;;
esac
python3 -m json.tool "$OUT/dry-run-result.json" >/dev/null
printf 'validated dry-run verdict: '
python3 -c 'import json; print(json.load(open("/mnt/data/savant_upgrade_packet/generated-dry-run-080526/dry-run-result.json"))["verdict"])'

#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
AUDIT="$ROOT/audit/scope_tree"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

SAFE="$(
  find "$AUDIT" \
    -type f \
    -name 'safety_validated_moves_*.tsv' \
    2>/dev/null |
  sort |
  tail -1
)"

if [ -z "$SAFE" ]; then
  echo "[ERROR] No safety validated move file found."
  echo "Run:"
  echo "cd /root/savant-runtime && ./VALIDATE_SCOPE_MOVE_SAFETY.sh"
  exit 1
fi

OUT="$AUDIT/execution_dry_run_$STAMP.tsv"

printf "action\tsource\tproposed_target\tmkdir_target_parent\twrapper_needed\n" > "$OUT"

awk -F '\t' 'NR>1 && $1=="SAFE_MOVE"{print $3 "\t" $4}' "$SAFE" |
while IFS=$'\t' read -r src dst
do
  parent="$(dirname "$dst")"
  wrapper_needed="no"

  case "$src" in
    *.sh)
      wrapper_needed="yes"
      ;;
  esac

  printf "WOULD_MOVE\t%s\t%s\t%s\t%s\n" \
    "$src" \
    "$dst" \
    "$parent" \
    "$wrapper_needed" >> "$OUT"
done

echo
echo "[OK] execution dry-run generated:"
echo "$OUT"

echo
echo "=== WOULD MOVE ==="
column -t -s $'\t' "$OUT" | sed -n '1,160p'

echo
echo "No files moved."

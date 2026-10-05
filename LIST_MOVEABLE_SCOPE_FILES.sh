#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

LATEST_REPORT="$(
  find /root/savant-runtime/audit/scope_tree \
    -type f \
    -name 'dry_run_scope_tree_audit_*.tsv' \
    2>/dev/null |
  sort |
  tail -1
)"

if [ -z "$LATEST_REPORT" ]; then
  echo "[ERROR] No dry-run report found."
  echo "Run:"
  echo "cd /root/savant-runtime && ./DRY_RUN_SCOPE_TREE_AUDIT.sh"
  exit 1
fi

OUT="/root/savant-runtime/audit/scope_tree/moveable_files_clear_list_$(date -u +%Y%m%dT%H%M%SZ).tsv"

{
  printf "status\tkind\tsize_bytes\tmodified_utc\tbasename\tsource\tproposed_target\n"

  awk -F '\t' '$1=="MOVE"{print $3 "\t" $4}' "$LATEST_REPORT" |
  while IFS=$'\t' read -r src dst
  do
    if [ -d "$src" ]; then
      kind="directory"
      size="$(du -sb "$src" 2>/dev/null | awk '{print $1}')"
    elif [ -f "$src" ]; then
      kind="file"
      size="$(stat -c '%s' "$src")"
    else
      kind="missing"
      size=""
    fi

    modified="$(stat -c '%y' "$src" 2>/dev/null | sed 's/\..*//' || true)"
    basename="$(basename "$src")"

    printf "MOVE\t%s\t%s\t%s\t%s\t%s\t%s\n" \
      "$kind" \
      "$size" \
      "$modified" \
      "$basename" \
      "$src" \
      "$dst"
  done
} > "$OUT"

echo
echo "[OK] Moveable file list:"
echo "$OUT"

echo
echo "=== CLEAR LIST ==="
column -t -s $'\t' "$OUT" | sed -n '1,120p'

echo
echo "=== COUNTS ==="
awk -F '\t' 'NR>1{count[$2]++; bytes[$2]+=$3} END{for(k in count) print k, count[k], bytes[k] " bytes"}' "$OUT"

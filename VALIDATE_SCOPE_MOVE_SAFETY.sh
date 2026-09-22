#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
AUDIT="$ROOT/audit/scope_tree"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

EXEC="$(
  find "$AUDIT" \
    -type f \
    -name 'executable_move_candidates_*.tsv' \
    2>/dev/null |
  sort |
  tail -1
)"

if [ -z "$EXEC" ]; then
  echo "[ERROR] No executable move candidate file found."
  echo "Run:"
  echo "cd /root/savant-runtime && ./BUILD_SCOPE_MOVE_REWRITE_PLAN.sh"
  exit 1
fi

OUT="$AUDIT/safety_validated_moves_$STAMP.tsv"

printf "decision\treason\tsource\tproposed_target\tsource_exists\ttarget_exists\tsource_sha256\ttarget_parent_exists\n" > "$OUT"

tail -n +2 "$EXEC" |
while IFS=$'\t' read -r src dst confidence refs warnings
do
  decision="BLOCK"
  reason="unknown"

  source_exists="no"
  target_exists="no"
  target_parent_exists="no"
  source_sha=""

  if [ -e "$src" ]; then
    source_exists="yes"
  fi

  if [ -e "$dst" ]; then
    target_exists="yes"
  fi

  if [ -d "$(dirname "$dst")" ]; then
    target_parent_exists="yes"
  fi

  if [ -f "$src" ]; then
    source_sha="$(sha256sum "$src" | awk '{print $1}')"
  fi

  if [ "$source_exists" != "yes" ]; then
    reason="source_missing"
  elif [ "$target_exists" = "yes" ]; then
    reason="target_exists"
  elif [ "$target_parent_exists" != "yes" ]; then
    reason="target_parent_missing"
  elif [ "$confidence" -lt 90 ]; then
    reason="confidence_below_threshold"
  elif [ "$refs" != "0" ]; then
    reason="references_require_rewrite"
  else
    decision="SAFE_MOVE"
    reason="passed_all_safety_checks"
  fi

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$decision" \
    "$reason" \
    "$src" \
    "$dst" \
    "$source_exists" \
    "$target_exists" \
    "$source_sha" \
    "$target_parent_exists" >> "$OUT"
done

echo
echo "[OK] safety validation generated:"
echo "$OUT"

echo
echo "=== SUMMARY ==="
awk -F '\t' 'NR>1{count[$1 ":" $2]++} END{for(k in count) print count[k], k}' "$OUT" | sort -nr

echo
echo "=== SAFE MOVES ==="
awk -F '\t' 'NR>1 && $1=="SAFE_MOVE"{print $3 " -> " $4}' "$OUT" | sed -n '1,120p'

echo
echo "=== BLOCKED ==="
awk -F '\t' 'NR>1 && $1=="BLOCK"{print $2 "\t" $3 " -> " $4}' "$OUT" | column -t -s $'\t' | sed -n '1,120p'

echo
echo "No files moved."

#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
AUDIT="$ROOT/audit/scope_tree"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

PLAN="$(
  find "$AUDIT" \
    -type f \
    -name 'multipass_move_plan_*.tsv' \
    2>/dev/null |
  sort |
  tail -1
)"

if [ -z "$PLAN" ]; then
  echo "[ERROR] No multipass move plan found."
  echo "Run:"
  echo "cd /root/savant-runtime && ./MULTIPASS_SCOPE_AUDIT_DRY_RUN.sh"
  exit 1
fi

REWRITE="$AUDIT/rewrite_plan_$STAMP.tsv"
WRAPPERS="$AUDIT/wrapper_plan_$STAMP.tsv"
EXEC="$AUDIT/executable_move_candidates_$STAMP.tsv"

printf "source\tproposed_target\treference_file\trewrite_kind\told_text\tnew_text\n" > "$REWRITE"
printf "source\tproposed_target\twrapper_path\twrapper_kind\n" > "$WRAPPERS"
printf "source\tproposed_target\tconfidence\treference_count\twarnings\n" > "$EXEC"

awk -F '\t' 'NR>1 && $1=="MOVE_CANDIDATE"{print $4 "\t" $5 "\t" $3 "\t" $6 "\t" $7}' "$PLAN" |
while IFS=$'\t' read -r src dst confidence refs warnings
do
  printf "%s\t%s\t%s\t%s\t%s\n" \
    "$src" \
    "$dst" \
    "$confidence" \
    "$refs" \
    "$warnings" >> "$EXEC"

  base="$(basename "$src")"

  grep -RIlF "$src" "$ROOT" \
    --exclude-dir=node_modules \
    --exclude-dir=.git \
    --exclude-dir=__pycache__ \
    --exclude-dir=.venv \
    --exclude-dir=.venv_voice \
    --exclude-dir=site-packages \
    --exclude='multipass_*.tsv' \
    --exclude='rewrite_plan_*.tsv' \
    --exclude='wrapper_plan_*.tsv' \
    --exclude='*.pyc' \
    2>/dev/null |
  sort -u |
  while IFS= read -r ref
  do
    printf "%s\t%s\t%s\tabsolute_path\t%s\t%s\n" \
      "$src" \
      "$dst" \
      "$ref" \
      "$src" \
      "$dst" >> "$REWRITE"
  done

  grep -RIlF "$base" "$ROOT" \
    --exclude-dir=node_modules \
    --exclude-dir=.git \
    --exclude-dir=__pycache__ \
    --exclude-dir=.venv \
    --exclude-dir=.venv_voice \
    --exclude-dir=site-packages \
    --exclude='multipass_*.tsv' \
    --exclude='rewrite_plan_*.tsv' \
    --exclude='wrapper_plan_*.tsv' \
    --exclude='*.pyc' \
    2>/dev/null |
  sort -u |
  while IFS= read -r ref
  do
    printf "%s\t%s\t%s\tbasename_reference\t%s\t%s\n" \
      "$src" \
      "$dst" \
      "$ref" \
      "$base" \
      "$base" >> "$REWRITE"
  done

  if [ -f "$src" ] && [ "${src##*.}" = "sh" ]; then
    printf "%s\t%s\t%s\tcompatibility_forwarder\n" \
      "$src" \
      "$dst" \
      "$src" >> "$WRAPPERS"
  fi
done

echo
echo "[OK] rewrite plan generated"
echo "$REWRITE"

echo
echo "[OK] wrapper plan generated"
echo "$WRAPPERS"

echo
echo "[OK] executable move candidates"
echo "$EXEC"

echo
echo "=== EXECUTABLE CANDIDATES ==="
column -t -s $'\t' "$EXEC" | sed -n '1,120p'

echo
echo "=== REWRITE REFERENCES ==="
column -t -s $'\t' "$REWRITE" | sed -n '1,120p'

echo
echo "=== WRAPPERS ==="
column -t -s $'\t' "$WRAPPERS" | sed -n '1,120p'

echo
echo "No files moved."

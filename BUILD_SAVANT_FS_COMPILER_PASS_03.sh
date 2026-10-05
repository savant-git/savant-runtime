#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
AUDIT="$ROOT/audit/fs_compiler"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

INVENTORY="$(
  find "$AUDIT" -type f -name 'pass01_inventory_*.tsv' 2>/dev/null |
  sort |
  tail -1
)"

CLASSIFIED="$(
  find "$AUDIT" -type f -name 'pass02_semantic_classification_*.tsv' 2>/dev/null |
  sort |
  tail -1
)"

if [ -z "$INVENTORY" ] || [ -z "$CLASSIFIED" ]; then
  echo "[ERROR] Missing pass 01 or pass 02 output."
  echo "Run pass 01 and pass 02 first."
  exit 1
fi

OUT="$AUDIT/pass03_reference_graph_$STAMP.tsv"
SUMMARY="$AUDIT/pass03_summary_$STAMP.txt"

printf "source_path\treference_type\treference_value\ttarget_guess\tline_number\tline_text\n" > "$OUT"

is_text_file() {
  local p="$1"

  if [ ! -f "$p" ]; then
    return 1
  fi

  file -b --mime "$p" 2>/dev/null | grep -Eq 'text/|application/json|application/x-shellscript|application/xml|application/x-empty'
}

scan_file() {
  local p="$1"

  if ! is_text_file "$p"; then
    return
  fi

  awk '
    {
      line=$0

      if (line ~ /^[[:space:]]*from[[:space:]]+[A-Za-z0-9_\.]+[[:space:]]+import[[:space:]]+/) {
        print FILENAME "\tpython_from_import\t" line "\t\t" NR "\t" line
      }

      if (line ~ /^[[:space:]]*import[[:space:]]+[A-Za-z0-9_\.]+/) {
        print FILENAME "\tpython_import\t" line "\t\t" NR "\t" line
      }

      if (line ~ /(source|\.)[[:space:]]+[^;&|]+/) {
        print FILENAME "\tshell_source\t" line "\t\t" NR "\t" line
      }

      if (line ~ /(bash|sh|python3?|node|npm)[[:space:]]+[^;&|]+/) {
        print FILENAME "\texec_call\t" line "\t\t" NR "\t" line
      }

      if (line ~ /\/root\/savant-runtime\//) {
        print FILENAME "\tabsolute_path\t" line "\t\t" NR "\t" line
      }

      if (line ~ /\.\.?\//) {
        print FILENAME "\trelative_path\t" line "\t\t" NR "\t" line
      }

      if (line ~ /sqlite|\.db|\.sqlite/) {
        print FILENAME "\tdatabase_reference\t" line "\t\t" NR "\t" line
      }

      if (line ~ /systemctl|\.service|\.timer|cron|crontab/) {
        print FILENAME "\tservice_reference\t" line "\t\t" NR "\t" line
      }
    }
  ' "$p" >> "$OUT"
}

awk -F '\t' 'NR>1 && $5=="file"{print $2}' "$CLASSIFIED" |
while IFS= read -r p
do
  scan_file "$p"
done

{
  echo "SAVANT FILESYSTEM COMPILER PASS 03"
  echo "timestamp: $STAMP"
  echo "reference_graph: $OUT"
  echo
  echo "reference counts:"
  awk -F '\t' 'NR>1{count[$2]++} END{for(k in count) print k, count[k]}' "$OUT" | sort
  echo
  echo "files with references:"
  awk -F '\t' 'NR>1{count[$1]++} END{for(k in count) print k, count[k]}' "$OUT" | sort -k2 -nr | head -80
} > "$SUMMARY"

echo
echo "[OK] pass 03 reference graph complete"
echo "$SUMMARY"
echo
cat "$SUMMARY"

echo
echo "=== SAMPLE REFERENCES ==="
column -t -s $'\t' "$OUT" | sed -n '1,120p'

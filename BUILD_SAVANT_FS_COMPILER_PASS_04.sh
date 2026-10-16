#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
AUDIT="$ROOT/audit/fs_compiler"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

CLASSIFIED="$(
  find "$AUDIT" -type f -name 'pass02_semantic_classification_*.tsv' 2>/dev/null |
  sort |
  tail -1
)"

REFERENCES="$(
  find "$AUDIT" -type f -name 'pass03_reference_graph_*.tsv' 2>/dev/null |
  sort |
  tail -1
)"

if [ -z "$CLASSIFIED" ] || [ -z "$REFERENCES" ]; then
  echo "[ERROR] Missing pass 02 or pass 03 output."
  exit 1
fi

OUT="$AUDIT/pass04_package_boundary_report_$STAMP.tsv"
SUMMARY="$AUDIT/pass04_summary_$STAMP.txt"

printf "path\tcontainment\tmove_policy\timport_reference_count\tabsolute_reference_count\trelative_reference_count\tpackage_risk\n" > "$OUT"

awk -F '\t' 'NR>1 && $5=="file"{print $2 "\t" $9 "\t" $12}' "$CLASSIFIED" |
while IFS=$'\t' read -r p containment policy
do
  import_count="$(
    awk -F '\t' -v p="$p" 'NR>1 && $1==p && ($2=="python_import" || $2=="python_from_import"){c++} END{print c+0}' "$REFERENCES"
  )"

  abs_count="$(
    awk -F '\t' -v p="$p" 'NR>1 && $1==p && $2=="absolute_path"{c++} END{print c+0}' "$REFERENCES"
  )"

  rel_count="$(
    awk -F '\t' -v p="$p" 'NR>1 && $1==p && $2=="relative_path"{c++} END{print c+0}' "$REFERENCES"
  )"

  risk="low"

  case "$containment" in
    application_package|runtime_protocol_package|runtime_provider_package|runtime_event_bus_package|projection_engine_package)
      risk="critical_do_not_flatten"
      ;;
  esac

  if [ "$import_count" -gt 0 ] || [ "$rel_count" -gt 0 ]; then
    if [ "$risk" = "low" ]; then
      risk="dependency_sensitive"
    fi
  fi

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$p" \
    "$containment" \
    "$policy" \
    "$import_count" \
    "$abs_count" \
    "$rel_count" \
    "$risk" >> "$OUT"
done

{
  echo "SAVANT FILESYSTEM COMPILER PASS 04"
  echo "timestamp: $STAMP"
  echo "package_boundary_report: $OUT"
  echo
  echo "risk counts:"
  awk -F '\t' 'NR>1{count[$7]++} END{for(k in count) print k, count[k]}' "$OUT" | sort
  echo
  echo "critical do-not-flatten:"
  awk -F '\t' 'NR>1 && $7=="critical_do_not_flatten"{print $1}' "$OUT" | sed -n '1,80p'
} > "$SUMMARY"

echo
echo "[OK] pass 04 package boundary report complete"
echo "$SUMMARY"
echo
cat "$SUMMARY"

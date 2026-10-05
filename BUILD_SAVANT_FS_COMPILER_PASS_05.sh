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

BOUNDARY="$(
  find "$AUDIT" -type f -name 'pass04_package_boundary_report_*.tsv' 2>/dev/null |
  sort |
  tail -1
)"

if [ -z "$CLASSIFIED" ] || [ -z "$BOUNDARY" ]; then
  echo "[ERROR] Missing pass 02 or pass 04 output."
  exit 1
fi

OUT="$AUDIT/pass05_move_eligibility_$STAMP.tsv"
SUMMARY="$AUDIT/pass05_summary_$STAMP.txt"

printf "decision\treason\tpath\tscope\towner\tcontainment\tedifice_level\tauthority_class\n" > "$OUT"

awk -F '\t' 'NR>1{print}' "$CLASSIFIED" |
while IFS=$'\t' read -r id path rel base kind ext owner scope containment level authority policy
do
  risk="$(
    awk -F '\t' -v p="$path" 'NR>1 && $1==p{print $7; found=1} END{if(!found) print "unknown"}' "$BOUNDARY"
  )"

  decision="BLOCK"
  reason="manual_review_required"

  if [ "$kind" != "file" ]; then
    reason="not_a_file"
  elif [ "$risk" = "critical_do_not_flatten" ]; then
    reason="package_boundary_must_be_preserved"
  elif [ "$authority" = "generated_audit" ] || [ "$authority" = "generated_report" ] || [ "$authority" = "generated_projection" ]; then
    reason="generated_output_do_not_move"
  elif [ "$policy" = "ELIGIBLE_FOR_PLANNING" ]; then
    decision="ELIGIBLE"
    reason="eligible_for_target_planning"
  else
    reason="$policy"
  fi

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$decision" \
    "$reason" \
    "$path" \
    "$scope" \
    "$owner" \
    "$containment" \
    "$level" \
    "$authority" >> "$OUT"
done

{
  echo "SAVANT FILESYSTEM COMPILER PASS 05"
  echo "timestamp: $STAMP"
  echo "move_eligibility: $OUT"
  echo
  echo "decisions:"
  awk -F '\t' 'NR>1{count[$1 ":" $2]++} END{for(k in count) print k, count[k]}' "$OUT" | sort
  echo
  echo "eligible:"
  awk -F '\t' 'NR>1 && $1=="ELIGIBLE"{print $3}' "$OUT" | sed -n '1,120p'
} > "$SUMMARY"

echo
echo "[OK] pass 05 move eligibility complete"
echo "$SUMMARY"
echo
cat "$SUMMARY"

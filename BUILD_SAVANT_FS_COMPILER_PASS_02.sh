#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
AUDIT="$ROOT/audit/fs_compiler"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

INVENTORY="$(
  find "$AUDIT" \
    -type f \
    -name 'pass01_inventory_*.tsv' \
    2>/dev/null |
  sort |
  tail -1
)"

if [ -z "$INVENTORY" ]; then
  echo "[ERROR] No pass 01 inventory found."
  echo "Run:"
  echo "cd /root/savant-runtime && ./BUILD_SAVANT_FS_COMPILER_PASS_01.sh"
  exit 1
fi

OUT="$AUDIT/pass02_semantic_classification_$STAMP.tsv"
SUMMARY="$AUDIT/pass02_summary_$STAMP.txt"

EXILES_ROOT="ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"

EXILES_LIST=(
  carbon
  cataxis
  coda
  envoy
  filament
  graffiti
  lore
  mobius
  modus
  niche
  notary
  opus
  pact
  palaver
  shatter
  underscore
  urge
  zero
)

detect_owner() {
  local rel="$1"

  for exile in "${EXILES_LIST[@]}"; do
    case "$rel" in
      "$EXILES_ROOT/$exile"|"$EXILES_ROOT/$exile/"*)
        echo "$exile"
        return
        ;;
    esac
  done

  echo "unknown"
}

detect_scope() {
  local rel="$1"
  local base="$2"

  case "$rel" in
    ontology/obelisks/segue/*)
      echo "all_obelisks"
      return
      ;;
    ontology/obelisks/_template/segue/gates/segue/*)
      echo "all_gates"
      return
      ;;
    ontology/obelisks/_template/segue/gates/_template/segue/innates/segue/*)
      echo "all_innates"
      return
      ;;
    "$EXILES_ROOT/segue/"*)
      echo "all_exiles"
      return
      ;;
    "$EXILES_ROOT/"*/segue/*)
      echo "single_exile"
      return
      ;;
    "$EXILES_ROOT/"*/runtime/*)
      echo "single_exile"
      return
      ;;
    "$EXILES_ROOT/"*/apps/*)
      echo "single_exile_app"
      return
      ;;
    "$EXILES_ROOT/"*)
      echo "single_exile"
      return
      ;;
  esac

  case "$rel" in
    ontology/*)
      echo "ontology"
      ;;
    ops/*)
      echo "runtime_ops"
      ;;
    *.sh)
      case "$base" in
        *EXILE*|*EXILES*|*Exile*|*Exiles*)
          echo "all_exiles"
          ;;
        *ONTOLOGY*|*Ontology*|*ontology*)
          echo "ontology"
          ;;
        *SAVANT*|*RUNTIME*|*Runtime*|*runtime*)
          echo "runtime"
          ;;
        *)
          echo "runtime_ops"
          ;;
      esac
      ;;
    *)
      echo "unknown"
      ;;
  esac
}

detect_containment() {
  local rel="$1"
  local ext="$2"

  case "$rel" in
    */apps/*)
      echo "application_package"
      return
      ;;
    */runtime/protocol/*)
      echo "runtime_protocol_package"
      return
      ;;
    */runtime/providers/*)
      echo "runtime_provider_package"
      return
      ;;
    */runtime/event_bus/*)
      echo "runtime_event_bus_package"
      return
      ;;
    */runtime/projection_engine/*)
      echo "projection_engine_package"
      return
      ;;
    */runtime/*)
      echo "runtime_package"
      return
      ;;
    */segue/*)
      echo "segue_container"
      return
      ;;
  esac

  case "$ext" in
    sh)
      echo "shell_script"
      ;;
    py)
      echo "python_module"
      ;;
    json)
      echo "json_data"
      ;;
    md)
      echo "markdown_document"
      ;;
    sqlite|db)
      echo "database"
      ;;
    *)
      echo "unknown"
      ;;
  esac
}

detect_edifice_level() {
  local scope="$1"
  local containment="$2"

  case "$scope" in
    runtime)
      echo "runtime"
      ;;
    runtime_ops)
      echo "runtime.ops"
      ;;
    ontology)
      echo "ontology"
      ;;
    all_obelisks)
      echo "obelisks.segue"
      ;;
    all_gates)
      echo "gates.segue"
      ;;
    all_innates)
      echo "innates.segue"
      ;;
    all_exiles)
      echo "exiles.segue"
      ;;
    single_exile|single_exile_app)
      case "$containment" in
        application_package)
          echo "prodigal.app"
          ;;
        runtime_protocol_package|runtime_provider_package|runtime_event_bus_package|projection_engine_package)
          echo "prodigal.runtime_package"
          ;;
        runtime_package)
          echo "exile.runtime"
          ;;
        segue_container)
          echo "exile.segue"
          ;;
        *)
          echo "exile"
          ;;
      esac
      ;;
    *)
      echo "unknown"
      ;;
  esac
}

detect_authority() {
  local rel="$1"
  local ext="$2"

  case "$rel" in
    */audit/*|audit/*)
      echo "generated_audit"
      ;;
    */reports/*)
      echo "generated_report"
      ;;
    */projections/*)
      echo "generated_projection"
      ;;
    */canon/*)
      echo "canon"
      ;;
    */authority/*|*/authority_db/*)
      echo "authority"
      ;;
    */registry/*)
      echo "registry"
      ;;
    */lineage/*)
      echo "lineage"
      ;;
    */runtime/*)
      echo "runtime"
      ;;
    *)
      case "$ext" in
        sh)
          echo "operational_mote"
          ;;
        py)
          echo "implementation"
          ;;
        json)
          echo "data"
          ;;
        md)
          echo "docs_or_canon"
          ;;
        *)
          echo "unknown"
          ;;
      esac
      ;;
  esac
}

detect_move_policy() {
  local scope="$1"
  local containment="$2"
  local authority="$3"

  case "$containment" in
    application_package|runtime_protocol_package|runtime_provider_package|runtime_event_bus_package|projection_engine_package)
      echo "DO_NOT_FLATTEN_PACKAGE"
      return
      ;;
  esac

  case "$authority" in
    generated_audit|generated_report|generated_projection)
      echo "DO_NOT_MOVE_GENERATED"
      return
      ;;
  esac

  case "$scope" in
    all_exiles|all_obelisks|all_gates|all_innates|ontology|runtime|runtime_ops|single_exile)
      echo "ELIGIBLE_FOR_PLANNING"
      ;;
    *)
      echo "MANUAL_REVIEW"
      ;;
  esac
}

printf "id\tpath\trelpath\tbasename\tkind\textension\towner\tscope\tcontainment\tedifice_level\tauthority_class\tmove_policy\n" > "$OUT"

awk -F '\t' 'NR>1 && $10=="no"{print}' "$INVENTORY" |
while IFS=$'\t' read -r id path rel base kind ext size mod sha ignored
do
  owner="$(detect_owner "$rel")"
  scope="$(detect_scope "$rel" "$base")"
  containment="$(detect_containment "$rel" "$ext")"
  level="$(detect_edifice_level "$scope" "$containment")"
  authority="$(detect_authority "$rel" "$ext")"
  policy="$(detect_move_policy "$scope" "$containment" "$authority")"

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$id" \
    "$path" \
    "$rel" \
    "$base" \
    "$kind" \
    "$ext" \
    "$owner" \
    "$scope" \
    "$containment" \
    "$level" \
    "$authority" \
    "$policy" >> "$OUT"
done

{
  echo "SAVANT FILESYSTEM COMPILER PASS 02"
  echo "timestamp: $STAMP"
  echo "source_inventory: $INVENTORY"
  echo "classification: $OUT"
  echo
  echo "by scope:"
  awk -F '\t' 'NR>1{count[$8]++} END{for(k in count) print k, count[k]}' "$OUT" | sort
  echo
  echo "by containment:"
  awk -F '\t' 'NR>1{count[$9]++} END{for(k in count) print k, count[k]}' "$OUT" | sort
  echo
  echo "by edifice:"
  awk -F '\t' 'NR>1{count[$10]++} END{for(k in count) print k, count[k]}' "$OUT" | sort
  echo
  echo "by move policy:"
  awk -F '\t' 'NR>1{count[$12]++} END{for(k in count) print k, count[k]}' "$OUT" | sort
} > "$SUMMARY"

echo
echo "[OK] pass 02 semantic classification complete"
echo "$SUMMARY"
echo
cat "$SUMMARY"

echo
echo "=== DO NOT FLATTEN PACKAGE ==="
awk -F '\t' 'NR>1 && $12=="DO_NOT_FLATTEN_PACKAGE"{print $8 "\t" $9 "\t" $3}' "$OUT" | column -t -s $'\t' | sed -n '1,80p'

echo
echo "=== ELIGIBLE FOR PLANNING ==="
awk -F '\t' 'NR>1 && $12=="ELIGIBLE_FOR_PLANNING"{print $8 "\t" $10 "\t" $3}' "$OUT" | column -t -s $'\t' | sed -n '1,120p'

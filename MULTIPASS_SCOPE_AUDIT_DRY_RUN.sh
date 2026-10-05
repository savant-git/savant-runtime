#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
ONTOLOGY="$ROOT/ontology"
OBELISKS="$ONTOLOGY/obelisks"
EXILES="$OBELISKS/_template/segue/gates/_template/segue/innates/_template/segue/exiles"

AUDIT="$ROOT/audit/scope_tree"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

INVENTORY="$AUDIT/multipass_inventory_$STAMP.tsv"
CLASSIFIED="$AUDIT/multipass_classified_$STAMP.tsv"
REFERENCES="$AUDIT/multipass_references_$STAMP.tsv"
PLAN="$AUDIT/multipass_move_plan_$STAMP.tsv"
SUMMARY="$AUDIT/multipass_summary_$STAMP.txt"

mkdir -p "$AUDIT"

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

is_ignored() {
  local p="$1"

  case "$p" in
    */node_modules|*/node_modules/*) return 0 ;;
    */.git|*/.git/*) return 0 ;;
    */__pycache__|*/__pycache__/*) return 0 ;;
    */.pytest_cache|*/.pytest_cache/*) return 0 ;;
    */.mypy_cache|*/.mypy_cache/*) return 0 ;;
    */.ruff_cache|*/.ruff_cache/*) return 0 ;;
    */.cache|*/.cache/*) return 0 ;;
    */dist|*/dist/*) return 0 ;;
    */build|*/build/*) return 0 ;;
    */.venv|*/.venv/*) return 0 ;;
    */.venv_*|*/.venv_*/*) return 0 ;;
    */venv|*/venv/*) return 0 ;;
    */site-packages|*/site-packages/*) return 0 ;;
    */audit/scope_tree/*) return 0 ;;
    *) return 1 ;;
  esac
}

kind_of() {
  if [ -d "$1" ]; then
    echo "directory"
  elif [ -f "$1" ]; then
    echo "file"
  elif [ -L "$1" ]; then
    echo "symlink"
  else
    echo "unknown"
  fi
}

ext_of() {
  local b
  b="$(basename "$1")"

  case "$b" in
    *.*) echo "${b##*.}" ;;
    *) echo "" ;;
  esac
}

sha_file() {
  if [ -f "$1" ]; then
    sha256sum "$1" | awk '{print $1}'
  else
    echo ""
  fi
}

detect_owner_from_path() {
  local p="$1"

  for exile in "${EXILES_LIST[@]}"; do
    case "$p" in
      *"/exiles/$exile/"*|*"/exiles/$exile") echo "$exile"; return ;;
    esac
  done

  echo "unknown"
}

detect_owner_from_name() {
  local b
  b="$(basename "$1" | tr '[:upper:]' '[:lower:]')"

  for exile in "${EXILES_LIST[@]}"; do
    case "$b" in
      *"$exile"*) echo "$exile"; return ;;
    esac
  done

  echo "unknown"
}

detect_scope() {
  local p="$1"
  local b
  b="$(basename "$p" | tr '[:upper:]' '[:lower:]')"

  case "$p" in
    "$ROOT"/*.sh)
      case "$b" in
        *18*exile*|*exiles*|*exile*) echo "all_exiles"; return ;;
        *ontology*) echo "entire_ontology"; return ;;
        *runtime*|*savant*) echo "entire_runtime"; return ;;
        *) echo "root_operational"; return ;;
      esac
      ;;
  esac

  case "$p" in
    "$ONTOLOGY"/authority_graph/*|"$ONTOLOGY"/authority_db/*|"$ONTOLOGY"/indexes/*|"$ONTOLOGY"/segue/*)
      echo "all_obelisks"
      return
      ;;
    "$OBELISKS"/segue/*)
      echo "all_obelisks"
      return
      ;;
    "$EXILES"/segue/*)
      echo "all_exiles"
      return
      ;;
    "$EXILES"/*/segue/*)
      echo "single_exile"
      return
      ;;
    "$EXILES"/*/runtime/*)
      echo "single_exile"
      return
      ;;
    "$EXILES"/*/apps/*)
      echo "single_exile_app"
      return
      ;;
    "$EXILES"/*)
      echo "single_exile"
      return
      ;;
  esac

  echo "unknown"
}

edifice_for_scope() {
  case "$1" in
    entire_runtime) echo "runtime" ;;
    root_operational) echo "runtime.ops" ;;
    entire_ontology) echo "ontology" ;;
    all_obelisks) echo "obelisks.segue" ;;
    all_exiles) echo "exiles.segue" ;;
    single_exile|single_exile_app) echo "exile" ;;
    *) echo "unknown" ;;
  esac
}

authority_type() {
  local p="$1"
  local b
  b="$(basename "$p" | tr '[:upper:]' '[:lower:]')"

  case "$p" in
    */projections/*|*/reports/*|*/audit/*) echo "generated"; return ;;
  esac

  case "$b" in
    *.sh) echo "operational_mote" ;;
    *.py) echo "runtime_implementation" ;;
    *.json) echo "data_or_manifest" ;;
    *.md) echo "canon_or_docs" ;;
    *.sql) echo "authority_schema_or_migration" ;;
    *) echo "unknown" ;;
  esac
}

target_for() {
  local p="$1"
  local scope="$2"
  local owner_path="$3"
  local owner_name="$4"
  local kind="$5"
  local ext="$6"
  local base
  base="$(basename "$p")"

  if [ "$kind" != "file" ]; then
    echo ""
    return
  fi

  case "$scope:$ext" in
    all_exiles:sh)
      echo "$EXILES/segue/authority_db/seeds/$base"
      ;;
    all_obelisks:sh)
      echo "$OBELISKS/segue/authority_db/seeds/$base"
      ;;
    entire_ontology:sh)
      echo "$OBELISKS/segue/ontology_ops/scripts/$base"
      ;;
    entire_runtime:sh|root_operational:sh)
      echo "$ROOT/ops/runtime/scripts/$base"
      ;;
    single_exile:sh|single_exile_app:sh)
      if [ "$owner_path" != "unknown" ]; then
        echo "$EXILES/$owner_path/segue/scripts/$base"
      else
        echo ""
      fi
      ;;
    *)
      echo ""
      ;;
  esac
}

confidence_for() {
  local p="$1"
  local target="$2"
  local scope="$3"
  local owner_path="$4"
  local owner_name="$5"
  local ext="$6"

  if [ -z "$target" ]; then
    echo "0"
    return
  fi

  if [ "$p" = "$target" ]; then
    echo "100"
    return
  fi

  case "$scope" in
    all_exiles) echo "95" ;;
    all_obelisks) echo "90" ;;
    single_exile|single_exile_app)
      if [ "$owner_path" != "unknown" ]; then
        echo "90"
      elif [ "$owner_name" != "unknown" ]; then
        echo "70"
      else
        echo "40"
      fi
      ;;
    entire_runtime|root_operational|entire_ontology) echo "80" ;;
    *) echo "0" ;;
  esac
}

contains_reference_to_source() {
  local src="$1"
  local base
  base="$(basename "$src")"

  grep -RIlF "$src" "$ROOT" \
    --exclude-dir=node_modules \
    --exclude-dir=.git \
    --exclude-dir=__pycache__ \
    --exclude-dir=.venv \
    --exclude-dir=.venv_voice \
    --exclude-dir=site-packages \
    --exclude='multipass_*.tsv' \
    --exclude='*.pyc' \
    2>/dev/null || true

  grep -RIlF "$base" "$ROOT" \
    --exclude-dir=node_modules \
    --exclude-dir=.git \
    --exclude-dir=__pycache__ \
    --exclude-dir=.venv \
    --exclude-dir=.venv_voice \
    --exclude-dir=site-packages \
    --exclude='multipass_*.tsv' \
    --exclude='*.pyc' \
    2>/dev/null || true
}

echo "=== PASS 1: INVENTORY ==="

printf "id\tpath\tbasename\tkind\textension\tsize_bytes\tmodified_utc\tsha256\n" > "$INVENTORY"

find "$ROOT" -mindepth 1 \( -type f -o -type d -o -type l \) | sort |
while IFS= read -r p; do
  if is_ignored "$p"; then
    continue
  fi

  kind="$(kind_of "$p")"
  ext="$(ext_of "$p")"
  size="$(du -sb "$p" 2>/dev/null | awk '{print $1}' || echo 0)"
  mod="$(stat -c '%y' "$p" 2>/dev/null | sed 's/\..*//' || true)"
  sha="$(sha_file "$p")"
  id="$(printf '%s' "$p" | sha256sum | awk '{print $1}')"

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$id" "$p" "$(basename "$p")" "$kind" "$ext" "$size" "$mod" "$sha" >> "$INVENTORY"
done

echo "=== PASS 2: CLASSIFICATION ==="

printf "id\tpath\tbasename\tkind\textension\tscope\towner_path\towner_name\tedifice_level\tauthority_type\tconfidence\tproposed_target\twarnings\n" > "$CLASSIFIED"

tail -n +2 "$INVENTORY" |
while IFS=$'\t' read -r id p base kind ext size mod sha; do
  scope="$(detect_scope "$p")"
  owner_path="$(detect_owner_from_path "$p")"
  owner_name="$(detect_owner_from_name "$p")"
  level="$(edifice_for_scope "$scope")"
  atype="$(authority_type "$p")"
  target="$(target_for "$p" "$scope" "$owner_path" "$owner_name" "$kind" "$ext")"
  confidence="$(confidence_for "$p" "$target" "$scope" "$owner_path" "$owner_name" "$ext")"

  warnings=""

  if [ "$scope" = "unknown" ]; then
    warnings="${warnings:+$warnings,}unknown_scope"
  fi

  if [ "$owner_path" = "unknown" ] && [ "$owner_name" != "unknown" ]; then
    warnings="${warnings:+$warnings,}owner_only_from_filename"
  fi

  if [ -n "$target" ] && [ -e "$target" ] && [ "$target" != "$p" ]; then
    warnings="${warnings:+$warnings,}target_exists"
  fi

  if [ "$p" = "$target" ]; then
    warnings="${warnings:+$warnings,}already_correct"
  fi

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$id" "$p" "$base" "$kind" "$ext" "$scope" "$owner_path" "$owner_name" "$level" "$atype" "$confidence" "$target" "$warnings" >> "$CLASSIFIED"
done

echo "=== PASS 3: REFERENCE SCAN ==="

printf "source\tproposed_target\treference_count\treferences\n" > "$REFERENCES"

awk -F '\t' 'NR>1 && $12!="" && $2!=$12 {print $2 "\t" $12}' "$CLASSIFIED" |
while IFS=$'\t' read -r src dst; do
  refs="$(contains_reference_to_source "$src" | sort -u | tr '\n' ';' | sed 's/;$//')"

  if [ -z "$refs" ]; then
    count="0"
  else
    count="$(printf '%s' "$refs" | tr ';' '\n' | wc -l)"
  fi

  printf "%s\t%s\t%s\t%s\n" "$src" "$dst" "$count" "$refs" >> "$REFERENCES"
done

echo "=== PASS 4: SAFE MOVE PLAN ==="

printf "decision\treason\tconfidence\tsource\tproposed_target\treference_count\twarnings\n" > "$PLAN"

awk -F '\t' 'NR>1 {print}' "$CLASSIFIED" |
while IFS=$'\t' read -r id p base kind ext scope owner_path owner_name level atype confidence target warnings; do
  [ -z "$target" ] && continue
  [ "$p" = "$target" ] && continue

  ref_count="$(
    awk -F '\t' -v src="$p" 'NR>1 && $1==src {print $3; found=1} END{if(!found) print 0}' "$REFERENCES"
  )"

  decision="BLOCK"
  reason="manual_review_required"

  if [ "$confidence" -ge 95 ] && [ "$ref_count" = "0" ] && [[ "$warnings" != *target_exists* ]]; then
    decision="MOVE_CANDIDATE"
    reason="high_confidence_no_references_no_conflict"
  elif [ "$confidence" -ge 90 ] && [ "$ref_count" = "0" ] && [[ "$warnings" != *target_exists* ]]; then
    decision="MOVE_CANDIDATE"
    reason="strong_confidence_no_references_no_conflict"
  elif [ "$ref_count" != "0" ]; then
    reason="references_must_be_rewritten_or_wrapped_before_move"
  elif [[ "$warnings" == *target_exists* ]]; then
    reason="target_conflict_requires_merge_or_manual_decision"
  fi

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$decision" "$reason" "$confidence" "$p" "$target" "$ref_count" "$warnings" >> "$PLAN"
done

echo "=== PASS 5: SUMMARY ==="

{
  echo "MULTIPASS SCOPE AUDIT"
  echo "timestamp: $STAMP"
  echo
  echo "inventory:   $INVENTORY"
  echo "classified:  $CLASSIFIED"
  echo "references:  $REFERENCES"
  echo "move_plan:   $PLAN"
  echo
  echo "Inventory count:"
  tail -n +2 "$INVENTORY" | wc -l
  echo
  echo "Classification scopes:"
  awk -F '\t' 'NR>1{count[$6]++} END{for(k in count) print k, count[k]}' "$CLASSIFIED" | sort
  echo
  echo "Move plan decisions:"
  awk -F '\t' 'NR>1{count[$1]++} END{for(k in count) print k, count[k]}' "$PLAN" | sort
  echo
  echo "Blocked reasons:"
  awk -F '\t' 'NR>1 && $1=="BLOCK"{count[$2]++} END{for(k in count) print k, count[k]}' "$PLAN" | sort
} > "$SUMMARY"

echo
echo "[OK] multipass dry-run complete"
echo "$SUMMARY"

echo
cat "$SUMMARY"

echo
echo "=== MOVE CANDIDATES ==="
awk -F '\t' 'NR>1 && $1=="MOVE_CANDIDATE"{print $4 " -> " $5}' "$PLAN" | sed -n '1,120p'

echo
echo "=== BLOCKED ==="
awk -F '\t' 'NR>1 && $1=="BLOCK"{print $2 "\t" $4 " -> " $5}' "$PLAN" | column -t -s $'\t' | sed -n '1,120p'

echo
echo "No files moved."

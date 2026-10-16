#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
AUDIT="$ROOT/audit/fs_compiler"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

INVENTORY="$AUDIT/pass01_inventory_$STAMP.tsv"
SUMMARY="$AUDIT/pass01_summary_$STAMP.txt"

mkdir -p "$AUDIT"

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
    */audit/fs_compiler/*) return 0 ;;
    *) return 1 ;;
  esac
}

kind_of() {
  if [ -L "$1" ]; then
    echo "symlink"
  elif [ -d "$1" ]; then
    echo "directory"
  elif [ -f "$1" ]; then
    echo "file"
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

sha_of() {
  if [ -f "$1" ]; then
    sha256sum "$1" | awk '{print $1}'
  else
    echo ""
  fi
}

printf "id\tpath\trelpath\tbasename\tkind\textension\tsize_bytes\tmodified_utc\tsha256\tignored\n" > "$INVENTORY"

find "$ROOT" -mindepth 1 \( -type f -o -type d -o -type l \) | sort |
while IFS= read -r p
do
  ignored="no"

  if is_ignored "$p"; then
    ignored="yes"
  fi

  id="$(printf '%s' "$p" | sha256sum | awk '{print $1}')"
  rel="${p#$ROOT/}"
  kind="$(kind_of "$p")"
  ext="$(ext_of "$p")"
  size="$(du -sb "$p" 2>/dev/null | awk '{print $1}' || echo 0)"
  mod="$(stat -c '%y' "$p" 2>/dev/null | sed 's/\..*//' || true)"
  sha="$(sha_of "$p")"

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$id" \
    "$p" \
    "$rel" \
    "$(basename "$p")" \
    "$kind" \
    "$ext" \
    "$size" \
    "$mod" \
    "$sha" \
    "$ignored" >> "$INVENTORY"
done

{
  echo "SAVANT FILESYSTEM COMPILER PASS 01"
  echo "timestamp: $STAMP"
  echo "inventory: $INVENTORY"
  echo
  echo "total objects:"
  tail -n +2 "$INVENTORY" | wc -l
  echo
  echo "ignored objects:"
  awk -F '\t' 'NR>1 && $10=="yes"{c++} END{print c+0}' "$INVENTORY"
  echo
  echo "active objects:"
  awk -F '\t' 'NR>1 && $10=="no"{c++} END{print c+0}' "$INVENTORY"
  echo
  echo "by kind:"
  awk -F '\t' 'NR>1 && $10=="no"{count[$5]++} END{for(k in count) print k, count[k]}' "$INVENTORY" | sort
  echo
  echo "by extension:"
  awk -F '\t' 'NR>1 && $10=="no" && $6!=""{count[$6]++} END{for(k in count) print k, count[k]}' "$INVENTORY" | sort
} > "$SUMMARY"

echo
echo "[OK] pass 01 inventory complete"
echo "$SUMMARY"
echo
cat "$SUMMARY"

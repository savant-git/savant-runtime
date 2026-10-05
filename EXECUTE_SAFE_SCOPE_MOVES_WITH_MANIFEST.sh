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

MANIFEST="$AUDIT/executed_scope_moves_$STAMP.tsv"

if [ "${EXECUTE_SCOPE_MOVES:-NO}" != "YES" ]; then
  echo "[BLOCKED] This script is armed only when EXECUTE_SCOPE_MOVES=YES."
  echo
  echo "Dry-run source:"
  echo "$SAFE"
  echo
  echo "To execute:"
  echo "cd /root/savant-runtime && EXECUTE_SCOPE_MOVES=YES ./EXECUTE_SAFE_SCOPE_MOVES_WITH_MANIFEST.sh"
  exit 1
fi

printf "moved_at_utc\tsource\tnew_path\tsha256_before\tsha256_after\twrapper_created\n" > "$MANIFEST"

awk -F '\t' 'NR>1 && $1=="SAFE_MOVE"{print $3 "\t" $4 "\t" $7}' "$SAFE" |
while IFS=$'\t' read -r src dst sha_before
do
  parent="$(dirname "$dst")"

  mkdir -p "$parent"

  if [ ! -e "$src" ]; then
    echo "[SKIP missing] $src"
    continue
  fi

  if [ -e "$dst" ]; then
    echo "[SKIP target exists] $dst"
    continue
  fi

  mv "$src" "$dst"

  chmod --reference="$dst" "$dst" 2>/dev/null || true

  sha_after=""
  if [ -f "$dst" ]; then
    sha_after="$(sha256sum "$dst" | awk '{print $1}')"
  fi

  wrapper_created="no"

  case "$src" in
    *.sh)
      cat > "$src" <<EOF
#!/usr/bin/env bash
set -euo pipefail

exec "$dst" "\$@"
EOF
      chmod +x "$src"
      wrapper_created="yes"
      ;;
  esac

  printf "%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$(date -u +%Y%m%dT%H%M%SZ)" \
    "$src" \
    "$dst" \
    "$sha_before" \
    "$sha_after" \
    "$wrapper_created" >> "$MANIFEST"
done

echo
echo "[OK] executed safe moves"
echo "$MANIFEST"

echo
echo "=== MANIFEST ==="
column -t -s $'\t' "$MANIFEST" | sed -n '1,160p'

#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

AUDIT="/root/savant-runtime/audit/fs_compiler"
PLAN="$(
  find "$AUDIT" \
    -type f \
    -name 'execution_plan_*.tsv' \
    2>/dev/null |
  sort |
  tail -1
)"

if [ -z "$PLAN" ]; then
  echo "[ERROR] No execution plan found."
  echo "Run BUILD_SAVANT_FS_COMPILER_PASS_15_EXECUTION_PLAN.sh first."
  exit 1
fi

if [ "${EXECUTE_FS_PLAN:-NO}" != "YES" ]; then
  echo "[BLOCKED] Dry safety mode."
  echo
  echo "Plan:"
  echo "$PLAN"
  echo
  echo "To execute:"
  echo "cd /root/savant-runtime && EXECUTE_FS_PLAN=YES ./EXECUTE_FS_COMPILER_PLAN_WITH_WRAPPERS.sh"
  exit 1
fi

MANIFEST="$AUDIT/executed_plan_$(date -u +%Y%m%dT%H%M%SZ).tsv"

printf "moved_at_utc\tsource\tnew_path\tsha256_before\tsha256_after\twrapper_created\n" > "$MANIFEST"

tail -n +2 "$PLAN" |
while IFS=$'\t' read -r action src dst wrapper parent sha_before
do
  [ "$action" = "MOVE" ] || continue

  if [ ! -e "$src" ]; then
    echo "[SKIP source missing] $src"
    continue
  fi

  if [ -e "$dst" ]; then
    echo "[SKIP target exists] $dst"
    continue
  fi

  mkdir -p "$parent"

  mv "$src" "$dst"

  sha_after=""
  if [ -f "$dst" ]; then
    sha_after="$(sha256sum "$dst" | awk '{print $1}')"
  fi

  wrapper_created="no"

  if [ -n "$wrapper" ]; then
    cat > "$wrapper" <<EOF
#!/usr/bin/env bash
set -euo pipefail

exec "$dst" "\$@"
EOF
    chmod +x "$wrapper"
    wrapper_created="yes"
  fi

  printf "%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$(date -u +%Y%m%dT%H%M%SZ)" \
    "$src" \
    "$dst" \
    "$sha_before" \
    "$sha_after" \
    "$wrapper_created" >> "$MANIFEST"
done

echo
echo "[OK] executed plan:"
echo "$MANIFEST"

echo
column -t -s $'\t' "$MANIFEST"

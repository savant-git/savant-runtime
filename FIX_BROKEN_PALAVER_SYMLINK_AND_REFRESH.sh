#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

LINK="/root/savant-runtime/palaver_ultra"
TARGET_REL="ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver/commands/palaver_ultra"
TARGET="/root/savant-runtime/$TARGET_REL"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="/root/savant-runtime/repair_backups/$STAMP"

mkdir -p "$BACKUP"

echo "=== CURRENT LINK ==="
ls -la "$LINK" 2>/dev/null || true

if [ -L "$LINK" ]; then
  cp -a "$LINK" "$BACKUP/palaver_ultra.symlink.before" || true
  rm "$LINK"
fi

if [ ! -e "$TARGET" ]; then
  mkdir -p "$(dirname "$TARGET")"
  cat > "$TARGET" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

PALAVER_ROOT="/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver"

if [ -x "$PALAVER_ROOT/runtime/server.py" ]; then
  exec python3 "$PALAVER_ROOT/runtime/server.py" "$@"
fi

if [ -x "$PALAVER_ROOT/apps/webui_ultra/server.py" ]; then
  exec python3 "$PALAVER_ROOT/apps/webui_ultra/server.py" "$@"
fi

echo "[ERROR] No executable Palaver server entrypoint found." >&2
exit 1
EOF
  chmod +x "$TARGET"
fi

ln -s "$TARGET_REL" "$LINK"

echo
echo "=== NEW LINK ==="
ls -la "$LINK"
readlink -f "$LINK" || true

echo
echo "[OK] palaver_ultra symlink repaired"
echo "backup: $BACKUP"

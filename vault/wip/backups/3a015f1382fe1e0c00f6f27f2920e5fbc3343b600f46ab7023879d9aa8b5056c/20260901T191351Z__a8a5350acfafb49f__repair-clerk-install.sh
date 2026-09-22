#!/usr/bin/env bash
set -euo pipefail

CLERK_ROOT="$HOME/clerk"
SYS_DIR="$CLERK_ROOT/sys"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RECOVERY="$CLERK_ROOT/tmp/cleanup-$STAMP"

mkdir -p "$RECOVERY"

# Preserve unused extraction artifacts instead of permanently deleting them.
if [ -f "$SYS_DIR/court-monitor.py" ]; then
  mv "$SYS_DIR/court-monitor.py" "$RECOVERY/court-monitor.py.unused"
fi
if [ -d "$SYS_DIR/s3_downloads" ]; then
  mv "$SYS_DIR/s3_downloads" "$RECOVERY/s3_downloads.unused"
fi

required=(
  "$SYS_DIR/court_monitor.py"
  "$SYS_DIR/court-monitor.json"
  "$SYS_DIR/run-court-monitor.sh"
  "$SYS_DIR/install-court-monitor.sh"
)
for path in "${required[@]}"; do
  if [ ! -f "$path" ]; then
    echo "ERROR: required file missing: $path" >&2
    exit 1
  fi
done

chmod 700 "$SYS_DIR/run-court-monitor.sh" "$SYS_DIR/install-court-monitor.sh"
chmod 600 "$SYS_DIR/court_monitor.py" "$SYS_DIR/court-monitor.json"
if [ -f "$HOME/.env" ]; then chmod 600 "$HOME/.env"; fi

bash "$SYS_DIR/install-court-monitor.sh"
python3 "$SYS_DIR/court_monitor.py" doctor --config "$SYS_DIR/court-monitor.json"

echo
echo "Repair complete. Previous unused files are recoverable from:"
echo "  $RECOVERY"
echo
echo "Canonical program files:"
find "$SYS_DIR" -maxdepth 1 -type f -printf '  %f\n' | sort
echo
echo "Do not run another paid check until API units have been added."

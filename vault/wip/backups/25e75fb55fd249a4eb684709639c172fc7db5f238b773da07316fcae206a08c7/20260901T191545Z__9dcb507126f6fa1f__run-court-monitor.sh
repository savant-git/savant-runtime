#!/usr/bin/env bash
set -u
CLERK_ROOT="${CLERK_ROOT:-$HOME/clerk}"
SYS_DIR="$CLERK_ROOT/sys"
mkdir -p "$CLERK_ROOT/logs"
umask 077
exec python3 "$SYS_DIR/court_monitor.py" check \
  --config "$SYS_DIR/court-monitor.json" \
  >>"$CLERK_ROOT/logs/court-monitor.log" 2>&1

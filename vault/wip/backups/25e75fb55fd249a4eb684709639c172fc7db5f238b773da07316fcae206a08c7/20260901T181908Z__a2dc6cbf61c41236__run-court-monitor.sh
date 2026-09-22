#!/usr/bin/env bash
set -u
RUNTIME_DIR="${SAVANT_RUNTIME_DIR:-$HOME/savant-runtime}"
mkdir -p "$RUNTIME_DIR/logs"
umask 077
exec python3 "$RUNTIME_DIR/court_monitor.py" check \
  --config "$RUNTIME_DIR/court-monitor.json" \
  >>"$RUNTIME_DIR/logs/court-monitor.log" 2>&1

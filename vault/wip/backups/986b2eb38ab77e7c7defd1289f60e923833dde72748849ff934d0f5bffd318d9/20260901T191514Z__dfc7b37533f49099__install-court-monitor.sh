#!/usr/bin/env bash
set -eu
CLERK_ROOT="${CLERK_ROOT:-$HOME/clerk}"
SYS_DIR="$CLERK_ROOT/sys"
CASE_DIR="$CLERK_ROOT/data/cases/2026-115436-CC-26"
mkdir -p "$SYS_DIR" "$CLERK_ROOT/logs" "$CLERK_ROOT/tmp" \
  "$CASE_DIR/case-information/current" "$CASE_DIR/case-information/snapshots" \
  "$CASE_DIR/dockets/current" "$CASE_DIR/dockets/snapshots" \
  "$CASE_DIR/documents/originals" "$CASE_DIR/documents/quarantine" \
  "$CASE_DIR/events" "$CASE_DIR/database" "$CASE_DIR/exports"
chmod 700 "$CLERK_ROOT" "$SYS_DIR" "$CLERK_ROOT/data" "$CLERK_ROOT/logs" "$CLERK_ROOT/tmp"
chmod 700 "$SYS_DIR/run-court-monitor.sh" "$SYS_DIR/install-court-monitor.sh"
chmod 600 "$SYS_DIR/court_monitor.py" "$SYS_DIR/court-monitor.json"
if [ -f "$HOME/.env" ]; then chmod 600 "$HOME/.env"; fi
python3 "$SYS_DIR/court_monitor.py" doctor --config "$SYS_DIR/court-monitor.json"
echo
echo "Run the first paid API check with:"
echo "  $SYS_DIR/run-court-monitor.sh"
echo
echo "For Termux:Widget, place a launcher in ~/.shortcuts or schedule with termux-job-scheduler."

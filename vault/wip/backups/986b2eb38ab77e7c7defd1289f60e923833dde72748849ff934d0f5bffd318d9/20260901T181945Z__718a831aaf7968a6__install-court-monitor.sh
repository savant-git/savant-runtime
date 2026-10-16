#!/usr/bin/env bash
set -eu
RUNTIME_DIR="${SAVANT_RUNTIME_DIR:-$HOME/savant-runtime}"
mkdir -p "$RUNTIME_DIR/logs"
chmod 700 "$RUNTIME_DIR"
chmod 700 "$RUNTIME_DIR/run-court-monitor.sh"
chmod 600 "$RUNTIME_DIR/court_monitor.py" "$RUNTIME_DIR/court-monitor.json"
if [ -f "$HOME/.env" ]; then chmod 600 "$HOME/.env"; fi
python3 "$RUNTIME_DIR/court_monitor.py" doctor --config "$RUNTIME_DIR/court-monitor.json"
echo
echo "Run the first paid API check with:"
echo "  $RUNTIME_DIR/run-court-monitor.sh"
echo
echo "For Termux:Widget, place a launcher in ~/.shortcuts or schedule with termux-job-scheduler."

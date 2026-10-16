#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

./RERUN_FS_COMPILER_FAST_NONMOVE_PASSES.sh
./PATCH_FAST_BLOCKER_CLASSIFIER.sh
./REPORT_ACTIONABLE_BLOCKERS.sh
python3 tools/refactor_engine/refactor_engine.py
python3 tools/refactor_engine/report_rewrite_plan.py

echo
echo "[OK] refreshed fast audit, blockers, and refactor plan. No files moved."

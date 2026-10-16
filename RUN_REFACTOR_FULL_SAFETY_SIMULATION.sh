#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

./RERUN_FS_COMPILER_ALL_NONMOVE_PASSES.sh || true
python3 tools/refactor_engine/refactor_engine.py
python3 tools/refactor_engine/report_rewrite_plan.py
python3 tools/refactor_engine/simulate_refactor.py

echo
echo "[OK] full safety simulation complete. No live files moved."

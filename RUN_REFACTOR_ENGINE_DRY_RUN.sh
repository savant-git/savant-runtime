#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

./RERUN_FS_COMPILER_FAST_NONMOVE_PASSES.sh
python3 tools/refactor_engine/refactor_engine.py
python3 tools/refactor_engine/report_rewrite_plan.py

echo
echo "[OK] dry run only. No files moved. No files rewritten."

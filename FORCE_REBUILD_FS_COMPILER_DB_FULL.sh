#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

AUDIT="/root/savant-runtime/audit/fs_compiler"

mkdir -p "$AUDIT/archive"

if [ -f "$AUDIT/db/savant_fs_compiler.sqlite" ]; then
  mv "$AUDIT/db/savant_fs_compiler.sqlite" \
     "$AUDIT/archive/savant_fs_compiler.sqlite.$(date -u +%Y%m%dT%H%M%SZ).bak"
fi

./BUILD_SAVANT_FS_COMPILER_PASS_01.sh
./BUILD_SAVANT_FS_COMPILER_PASS_02.sh
./BUILD_SAVANT_FS_COMPILER_PASS_03.sh
./BUILD_SAVANT_FS_COMPILER_PASS_04.sh
./BUILD_SAVANT_FS_COMPILER_PASS_05.sh
./BUILD_SAVANT_FS_COMPILER_GRAPH_DB.sh
./INGEST_FS_COMPILER_PASSES_TO_DB.sh
./BUILD_SAVANT_FS_COMPILER_PASS_06_PY_IMPORTS.sh
./BUILD_SAVANT_FS_COMPILER_PASS_07_SHELL_DEPS.sh
./BUILD_SAVANT_FS_COMPILER_PASS_08_RUNTIME_LAUNCHERS.sh
./BUILD_SAVANT_FS_COMPILER_PASS_09_SYMLINKS.sh
./BUILD_SAVANT_FS_COMPILER_PASS_10_DUPLICATES.sh
./REPORT_FS_COMPILER_DEEP_GRAPH.sh

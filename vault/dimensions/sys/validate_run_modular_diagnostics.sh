#!/usr/bin/env bash

set -euo pipefail

DIAGNOSTIC_SCRIPT="/root/savant-runtime/vault/dimensions/sys/run_modular_diagnostics.sh"
TEST_SCRIPT="/root/savant-runtime/vault/dimensions/sys/tests/test_run_modular_diagnostics.py"

test -f \
    "${DIAGNOSTIC_SCRIPT}"

test -f \
    "${TEST_SCRIPT}"

chmod 0755 \
    "${DIAGNOSTIC_SCRIPT}" \
    "${TEST_SCRIPT}"

bash -n \
    "${DIAGNOSTIC_SCRIPT}"

python3 -m py_compile \
    "${TEST_SCRIPT}"

python3 \
    "${TEST_SCRIPT}" \
    -v

"${DIAGNOSTIC_SCRIPT}"

status=$?

test \
    "${status}" -eq 0 \
    -o "${status}" -eq 2

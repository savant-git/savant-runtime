#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"

EXILES="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"

ENVOY="${EXILES}/envoy"
CODA="${EXILES}/coda"

HISTORY="${ENVOY}/runtime/trait_history.py"
EVIDENCE="${ENVOY}/runtime/trait_evidence.py"
PERSONA="${ENVOY}/runtime/persona_engine.py"
MUTATION="${CODA}/runtime/mutation.py"

printf '%s\n' \
    '=== OROBOUROS PERSISTENCE IMPLEMENTATION BOUNDARY ==='

printf '\n%s\n' \
    '=== TRAIT HISTORY IMPORTS / CONSTANTS ==='

sed -n '1,130p' \
    "${HISTORY}"

printf '\n%s\n' \
    '=== TRAIT HISTORY SERIALIZATION / REPLAY ==='

sed -n '128,430p' \
    "${HISTORY}"

printf '\n%s\n' \
    '=== TRAIT HISTORY APPEND / VALIDATION ==='

sed -n '420,715p' \
    "${HISTORY}"

printf '\n%s\n' \
    '=== TRAIT HISTORY ACCEPTED PROJECTION / STATUS ==='

sed -n '715,900p' \
    "${HISTORY}"

printf '\n%s\n' \
    '=== TRAIT CANDIDATE SERIALIZATION ==='

sed -n '540,900p' \
    "${EVIDENCE}"

printf '\n%s\n' \
    '=== CODA MUTATION COMPLETE PUBLIC SURFACE ==='

sed -n '1,390p' \
    "${MUTATION}"

printf '\n%s\n' \
    '=== EXISTING JSON LOAD / SAVE / HISTORY PRIMITIVES ==='

grep -RInE \
    'load_.*history|save_.*history|history.*json|candidate.*json|json\.load|json\.dump|read_text|write_text|replace_text|mutation.*receipt|append.*record' \
    "${ENVOY}/runtime" \
    "${CODA}/runtime" \
    --exclude='*.pyc' \
    --exclude-dir='__pycache__' \
    2>/dev/null \
    | head -n 300 \
    || true

printf '\n%s\n' \
    '=== EXISTING STATE / HISTORY DIRECTORIES ==='

find \
    "${ENVOY}" \
    -maxdepth 4 \
    -type d \
    \( \
        -name state \
        -o -name history \
        -o -name evolution \
        -o -name projections \
    \) \
    -print \
    | sort

printf '\n%s\n' \
    '=== EXISTING STATE / HISTORY FILES ==='

find \
    "${ENVOY}" \
    -maxdepth 6 \
    -type f \
    \( \
        -path '*/state/*' \
        -o -path '*/history/*' \
        -o -path '*/evolution/*' \
        -o -path '*/projections/*' \
    \) \
    ! -path '*/__pycache__/*' \
    -print \
    | sort

printf '\n%s\n' \
    '=== PERSONA ENGINE HISTORY / ACCEPTED REFERENCES ==='

grep -nE \
    'trait_history|accepted_trait|champion|candidate|living_trait_crown|load_trait_pool|compose_persona' \
    "${PERSONA}" \
    || true

printf '\n%s\n' \
    '=== CODA DEPENDENTS ==='

grep -RInE \
    'coda.*mutation|replace_text|resolve_target|digest_file|mutation_receipt' \
    "${EXILES}" \
    --exclude='*.pyc' \
    --exclude-dir='__pycache__' \
    --exclude-dir='node_modules' \
    2>/dev/null \
    | head -n 300 \
    || true

printf '\n%s\n' \
    '=== RESULT ==='

printf '%s\n' \
    'OROBOUROS PERSISTENCE IMPLEMENTATION BOUNDARY: complete'

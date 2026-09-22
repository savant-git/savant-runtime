#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"

EXILES="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"
ENVOY="${EXILES}/envoy"

PERSISTENCE="${ENVOY}/runtime/trait_persistence.py"
HISTORY="${ENVOY}/runtime/trait_history.py"
PERSONA="${ENVOY}/runtime/persona_engine.py"
STATE="${ENVOY}/state/orobouros_trait_history.json"

printf '%s\n' \
    '=== OROBOUROS PERSISTENCE / PERSONA COMPOSITION BOUNDARY ==='

printf '\n%s\n' \
    '=== TRAIT PERSISTENCE COMPLETE PUBLIC SURFACE ==='

if [ ! -f "${PERSISTENCE}" ]; then
    printf 'MISSING %s\n' "${PERSISTENCE}"
    exit 1
fi

grep -nE \
    '^class |^def |STATE_|PERSISTENCE_OWNER|load_|save_|persist|append_|projection|record|status|coda' \
    "${PERSISTENCE}" \
    || true

printf '\n%s\n' \
    '=== TRAIT PERSISTENCE IMPLEMENTATION 1-700 ==='

sed -n '1,700p' \
    "${PERSISTENCE}"

printf '\n%s\n' \
    '=== HISTORY ACCEPTED-PROJECTION SURFACE ==='

grep -nE \
    '^def accepted_trait_projection|^def current_champions|^def append_record|^def validate_history|persistent_state|persistence_owner_required|projection_only' \
    "${HISTORY}" \
    || true

printf '\n%s\n' \
    '=== PERSONA CURRENT COMPOSITION SURFACE ==='

grep -nE \
    '^def load_trait_pool|^def select_living_traits|^def compose_persona|accepted_trait|trait_persistence|trait_history|living_trait_crown|DEFAULT_TRAIT_POOL_ID' \
    "${PERSONA}" \
    || true

printf '\n%s\n' \
    '=== PERSISTED STATE ==='

if [ -f "${STATE}" ]; then
    python3 -m json.tool \
        "${STATE}"
else
    printf '%s\n' \
        'NO PERSISTED OROBOUROS TRAIT HISTORY'
fi

printf '\n%s\n' \
    '=== PERSISTENCE DEPENDENTS ==='

grep -RniE \
    'trait_persistence|load_store_projection|save_store|persist_history|orobouros_trait_history\.json' \
    "${ENVOY}" \
    --exclude='*.pyc' \
    --exclude-dir='__pycache__' \
    || true

printf '\n%s\n' \
    '=== ACCEPTED PROJECTION CONSUMERS ==='

grep -RniE \
    'accepted_trait_projection|current_champions' \
    "${ENVOY}" \
    --exclude='*.pyc' \
    --exclude-dir='__pycache__' \
    || true

printf '\n%s\n' \
    '=== SYNTAX ==='

python3 -m py_compile \
    "${PERSISTENCE}" \
    "${HISTORY}" \
    "${PERSONA}"

printf '%s\n' \
    'PASS python syntax'

printf '\n%s\n' \
    '=== RESULT ==='

printf '%s\n' \
    'OROBOUROS PERSISTENCE / PERSONA COMPOSITION BOUNDARY: inspected'

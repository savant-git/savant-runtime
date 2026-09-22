#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"

EXILES="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"
ENVOY="${EXILES}/envoy"

EVIDENCE="${ENVOY}/runtime/trait_evidence.py"
PERSISTENCE="${ENVOY}/runtime/trait_persistence.py"
HISTORY="${ENVOY}/runtime/trait_history.py"
STATE="${ENVOY}/state"
EVOLUTION="${ENVOY}/evolution"
PROJECTIONS="${ENVOY}/graph/projections"

printf '%s\n' \
    '=== OROBOUROS CANDIDATE PERSISTENCE BOUNDARY ==='

printf '\n%s\n' \
    '=== TRAIT CANDIDATE SERIALIZATION SURFACE ==='

grep -nE \
    '^class TraitCandidate|^class TraitObservation|candidate_id|observation_id|def projection|def candidate_from_observations|notary_candidate_payload|rebuildable|persistent' \
    "${EVIDENCE}" \
    || true

printf '\n%s\n' \
    '=== PERSISTENCE RUNTIME CANDIDATE REFERENCES ==='

grep -nE \
    'candidate|catalog|accepted_projection|record|state|persist|load|save' \
    "${PERSISTENCE}" \
    || true

printf '\n%s\n' \
    '=== HISTORY CANDIDATE DEPENDENCY ==='

sed -n '715,835p' \
    "${HISTORY}"

printf '\n%s\n' \
    '=== ENVOY CANDIDATE STORAGE REFERENCES ==='

grep -RniE \
    'trait-candidate:|candidate_catalog|candidate.*store|candidate.*state|persist.*candidate|load.*candidate|save.*candidate|candidate_projection' \
    "${ENVOY}" \
    --exclude='*.pyc' \
    --exclude-dir='__pycache__' \
    || true

printf '\n%s\n' \
    '=== CURRENT STATE TREE ==='

find \
    "${STATE}" \
    -maxdepth 4 \
    -type f \
    -print \
    2>/dev/null \
    | sort \
    || true

printf '\n%s\n' \
    '=== CURRENT EVOLUTION TREE ==='

find \
    "${EVOLUTION}" \
    -maxdepth 5 \
    -type f \
    -print \
    2>/dev/null \
    | sort \
    || true

printf '\n%s\n' \
    '=== CURRENT GRAPH PROJECTIONS ==='

find \
    "${PROJECTIONS}" \
    -maxdepth 5 \
    -type f \
    -print \
    2>/dev/null \
    | sort \
    || true

printf '\n%s\n' \
    '=== CODA WRITERS TARGETING ENVOY ==='

grep -RniE \
    'replace_text|save_file|STATE_RELATIVE_PATH|envoy/state|envoy/evolution|envoy/graph/projections' \
    "${EXILES}/coda" \
    "${EXILES}/palaver" \
    "${ENVOY}" \
    --exclude='*.pyc' \
    --exclude-dir='__pycache__' \
    --exclude-dir='node_modules' \
    --exclude-dir='dist' \
    || true

printf '\n%s\n' \
    '=== RESTART REPLAY REQUIREMENTS ==='

python3 -c '
from pathlib import Path

root = Path(
    "/root/savant-runtime/ontology/obelisks/"
    "_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/envoy"
)

history_state = (
    root
    / "state"
    / "orobouros_trait_history.json"
)

candidate_files = []

for base in (
    root / "state",
    root / "evolution",
    root / "graph" / "projections",
):
    if not base.exists():
        continue

    for path in base.rglob("*"):
        if not path.is_file():
            continue

        name = path.name.lower()

        if (
            "candidate" in name
            or "observation" in name
        ):
            candidate_files.append(
                str(path)
            )

print(
    "history_state_present="
    + str(
        history_state.is_file()
    ).lower()
)

print(
    "candidate_persistence_file_count="
    + str(
        len(candidate_files)
    )
)

for path in sorted(candidate_files):
    print(
        "candidate_persistence_file="
        + path
    )

if candidate_files:
    print(
        "candidate_restart_replay_surface=present"
    )
else:
    print(
        "candidate_restart_replay_surface=not_proven"
    )
'

printf '\n%s\n' \
    '=== SYNTAX ==='

python3 -m py_compile \
    "${EVIDENCE}" \
    "${PERSISTENCE}" \
    "${HISTORY}"

printf '%s\n' \
    'PASS python syntax'

printf '\n%s\n' \
    '=== RESULT ==='

printf '%s\n' \
    'OROBOUROS CANDIDATE PERSISTENCE BOUNDARY: inspected'

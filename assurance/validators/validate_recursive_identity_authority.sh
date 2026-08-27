#!/usr/bin/env bash

set -euo pipefail

readonly RUNTIME_ROOT="/root/savant-runtime"

readonly DECISION_PATH="${RUNTIME_ROOT}/authority/accepted-decisions/AD-20260806-003-recursive-identity-tier-criteria.md"

readonly CRITERIA_PATH="${RUNTIME_ROOT}/canon/structure/SAVANT_IDENTITY_TIER_CRITERIA_v1.0.0.json"

readonly DOCUMENTATION_PATH="${RUNTIME_ROOT}/docs/architecture/SAVANT_RECURSIVE_IDENTITY_SCAFFOLD_v1.0.0.md"

readonly VALIDATOR_PATH="${RUNTIME_ROOT}/assurance/validators/validate_savant_identity_tier_criteria.py"

readonly EXPECTED_CRITERIA_SHA256="9f5c81cdeb68fc6e6ae6d79186ce68f908dcfd34a55262841a13c4a99c13c4ca"

readonly EXPECTED_DOCUMENTATION_SHA256="d9ca933eec9fe9b8a0d94795605f553bafc7316f8ba9581d134577482b9a1d20"

readonly EXPECTED_VALIDATOR_SHA256="5d23e3609bf57ab8b3469d17e030e9136c3041788fe9b2145974532a473a23be"


fail() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 1
}


require_command() {
    local command_name="$1"

    command -v "${command_name}" >/dev/null 2>&1 \
        || fail "required command not found: ${command_name}"
}


require_nonempty_file() {
    local path="$1"

    [[ -f "${path}" ]] \
        || fail "required file does not exist: ${path}"

    [[ -s "${path}" ]] \
        || fail "required file is empty: ${path}"
}


require_exact_line() {
    local expected_line="$1"
    local path="$2"

    grep -Fqx \
        "${expected_line}" \
        "${path}" \
        || fail "required exact line not found in ${path}: ${expected_line}"
}


verify_sha256() {
    local expected_digest="$1"
    local path="$2"

    printf '%s  %s\n' \
        "${expected_digest}" \
        "${path}" \
        | sha256sum --check --strict
}


main() {
    require_command "grep"
    require_command "python3"
    require_command "sha256sum"

    require_nonempty_file \
        "${DECISION_PATH}"

    require_nonempty_file \
        "${CRITERIA_PATH}"

    require_nonempty_file \
        "${DOCUMENTATION_PATH}"

    require_nonempty_file \
        "${VALIDATOR_PATH}"

    require_exact_line \
        "## Status" \
        "${DECISION_PATH}"

    require_exact_line \
        "Accepted" \
        "${DECISION_PATH}"

    require_exact_line \
        "## Mutation authorization" \
        "${DECISION_PATH}"

    require_exact_line \
        '`false`' \
        "${DECISION_PATH}"

    require_exact_line \
        '`iota → mote → trait → quirk → prodigal → exile → innate → portal → obelisk`' \
        "${DECISION_PATH}"

    require_exact_line \
        '`iota → mote → trait → quirk → prodigal → exile → innate → portal → obelisk`' \
        "${DOCUMENTATION_PATH}"

    python3 -m json.tool \
        "${CRITERIA_PATH}" \
        >/dev/null

    python3 -m py_compile \
        "${VALIDATOR_PATH}"

    "${VALIDATOR_PATH}" \
        "${CRITERIA_PATH}"

    verify_sha256 \
        "${EXPECTED_CRITERIA_SHA256}" \
        "${CRITERIA_PATH}"

    verify_sha256 \
        "${EXPECTED_DOCUMENTATION_SHA256}" \
        "${DOCUMENTATION_PATH}"

    verify_sha256 \
        "${EXPECTED_VALIDATOR_SHA256}" \
        "${VALIDATOR_PATH}"

    printf '\n'
    printf 'ACCEPTED DECISION: validated\n'
    printf 'IDENTITY CRITERIA: validated\n'
    printf 'DOCUMENTATION: validated\n'
    printf 'VALIDATOR: validated\n'
    printf 'MUTATION AUTHORIZED: false\n'
    printf '\n'

    sha256sum \
        "${DECISION_PATH}"
}


main "$@"

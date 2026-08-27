#!/usr/bin/env bash

set -euo pipefail

readonly RUNTIME_ROOT="/root/savant-runtime"

readonly ARCHITECTURE_DECISION="${RUNTIME_ROOT}/authority/accepted-decisions/AD-20260806-004-scyon-focal-architecture.md"
readonly MUTATION_DECISION="${RUNTIME_ROOT}/authority/accepted-decisions/AD-20260806-005-scyon-focal-mutation-boundary.md"

readonly IDENTITY_DECISION="${RUNTIME_ROOT}/authority/accepted-decisions/AD-20260806-003-recursive-identity-tier-criteria.md"
readonly CRITERIA_PATH="${RUNTIME_ROOT}/canon/structure/SAVANT_IDENTITY_TIER_CRITERIA_v1.0.0.json"
readonly CRITERIA_VALIDATOR="${RUNTIME_ROOT}/assurance/validators/validate_savant_identity_tier_criteria.py"


fail() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 1
}


require_command() {
    local command_name="$1"

    command -v "${command_name}" >/dev/null 2>&1 \
        || fail "required command unavailable: ${command_name}"
}


require_file() {
    local path="$1"

    [[ -f "${path}" ]] \
        || fail "required file not found: ${path}"

    [[ -s "${path}" ]] \
        || fail "required file is empty: ${path}"
}


require_text() {
    local path="$1"
    local text="$2"

    grep -Fq \
        -- "${text}" \
        "${path}" \
        || fail "required authority text not found in ${path}: ${text}"
}


require_exact_line() {
    local path="$1"
    local text="$2"

    grep -Fqx \
        -- "${text}" \
        "${path}" \
        || fail "required exact authority line not found in ${path}: ${text}"
}


validate_architecture() {
    require_exact_line \
        "${ARCHITECTURE_DECISION}" \
        "# AD-20260806-004: Scyon and Focal Architecture"

    require_exact_line \
        "${ARCHITECTURE_DECISION}" \
        "Accepted"

    require_text \
        "${ARCHITECTURE_DECISION}" \
        "Savant adopts **Scyon** as the canonical term"

    require_text \
        "${ARCHITECTURE_DECISION}" \
        "Savant adopts **Focal** as the canonical term"

    require_text \
        "${ARCHITECTURE_DECISION}" \
        "Every Scyon is fundamentally an instance of one shared modular kernel."

    require_text \
        "${ARCHITECTURE_DECISION}" \
        "A Focal extends the shared kernel without copying, replacing, weakening, or independently reimplementing it."

    require_text \
        "${ARCHITECTURE_DECISION}" \
        "Scyons are used by all Savant identity tiers except the two atomic tiers."

    require_text \
        "${ARCHITECTURE_DECISION}" \
        "Trait → Quirk → Prodigal → Exile → Innate → Portal → Obelisk"

    require_text \
        "${ARCHITECTURE_DECISION}" \
        "### Identity dimension"

    require_text \
        "${ARCHITECTURE_DECISION}" \
        "### State dimension"

    require_text \
        "${ARCHITECTURE_DECISION}" \
        "### Situated-depth dimension"

    require_text \
        "${ARCHITECTURE_DECISION}" \
        "Scyons accept arbitrary structured metadata."

    require_text \
        "${ARCHITECTURE_DECISION}" \
        "Every Scyon may expose a graphic equalizer"
}


validate_mutation_authority() {
    require_exact_line \
        "${MUTATION_DECISION}" \
        "# AD-20260806-005: Scyon and Focal Mutation Boundary"

    require_exact_line \
        "${MUTATION_DECISION}" \
        "Accepted"

    require_exact_line \
        "${MUTATION_DECISION}" \
        "## Mutation authorization"

    require_exact_line \
        "${MUTATION_DECISION}" \
        '`false`'

    require_text \
        "${MUTATION_DECISION}" \
        "AD-20260806-004 remains immutable historical authority and must not be edited merely to add this missing boundary."

    require_text \
        "${MUTATION_DECISION}" \
        "The current Scyon/Focal architecture does not authorize destructive physical mutation of the existing Savant implementation."

    require_text \
        "${MUTATION_DECISION}" \
        "Destructive physical migration is not authorized."

    require_text \
        "${MUTATION_DECISION}" \
        "A physical Scyon/Focal migration may be authorized only after all of the following are available and validated:"

    require_text \
        "${MUTATION_DECISION}" \
        "Scyon/Focal implementation must proceed through extension and compatibility before replacement."

    require_text \
        "${MUTATION_DECISION}" \
        "Scyon migration must prefer:"

    require_text \
        "${MUTATION_DECISION}" \
        "A database-engine transition is not implied by Scyon adoption."

    require_text \
        "${MUTATION_DECISION}" \
        "A Focal must not be introduced by duplicating behavior already owned elsewhere."

    require_text \
        "${MUTATION_DECISION}" \
        "No migration stage may claim success from syntax validity alone."

    require_text \
        "${MUTATION_DECISION}" \
        "Every authorized migration operation must emit sufficient evidence"
}


validate_identity_authority() {
    require_file \
        "${IDENTITY_DECISION}"

    require_file \
        "${CRITERIA_PATH}"

    require_file \
        "${CRITERIA_VALIDATOR}"

    python3 -m json.tool \
        "${CRITERIA_PATH}" \
        >/dev/null

    python3 -m py_compile \
        "${CRITERIA_VALIDATOR}"

    "${CRITERIA_VALIDATOR}" \
        "${CRITERIA_PATH}"
}


main() {
    require_command "grep"
    require_command "python3"
    require_command "sha256sum"

    require_file \
        "${ARCHITECTURE_DECISION}"

    require_file \
        "${MUTATION_DECISION}"

    validate_architecture
    validate_mutation_authority
    validate_identity_authority

    printf '\n'
    printf 'SCYON ARCHITECTURE: validated\n'
    printf 'FOCAL ARCHITECTURE: validated\n'
    printf 'SCYON TIER LAW: validated\n'
    printf 'THREE-DIMENSIONAL MODEL: validated\n'
    printf 'METADATA LAW: validated\n'
    printf 'EQUALIZER LAW: validated\n'
    printf 'AD-004 HISTORICAL AUTHORITY: preserved\n'
    printf 'AD-005 MUTATION BOUNDARY: validated\n'
    printf 'DESTRUCTIVE MIGRATION: unauthorized\n'
    printf 'MUTATION AUTHORIZED: false\n'
    printf '\n'

    sha256sum \
        "${ARCHITECTURE_DECISION}" \
        "${MUTATION_DECISION}" \
        "${IDENTITY_DECISION}" \
        "${CRITERIA_PATH}" \
        "${CRITERIA_VALIDATOR}" \
        "/root/savant-runtime/assurance/validators/validate_scyon_focal_authority.sh"
}


main "$@"

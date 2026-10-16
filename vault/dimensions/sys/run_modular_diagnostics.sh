#!/usr/bin/env bash

set -u
set -o pipefail

ROOT="/root/savant-runtime"
SYS_ROOT="${ROOT}/vault/dimensions/sys"
TEST_ROOT="${SYS_ROOT}/tests"
REPORT_ROOT="${SYS_ROOT}/reports"
PIPELINE_ROOT="${REPORT_ROOT}/modular-pipeline-run"

PIPELINE_SCRIPT="${SYS_ROOT}/run_modular_pipeline.py"
INSPECTOR_SCRIPT="${SYS_ROOT}/inspect_modular_pipeline.py"

PIPELINE_TEST="${TEST_ROOT}/test_run_modular_pipeline.py"
INSPECTOR_TEST="${TEST_ROOT}/test_inspect_modular_pipeline.py"

LATEST_PIPELINE="${PIPELINE_ROOT}/latest.json"

EXIT_SUCCESS=0
EXIT_BLOCKED=2
EXIT_FAILURE=1

declare -a REQUIRED_FILES=(
    "${PIPELINE_SCRIPT}"
    "${INSPECTOR_SCRIPT}"
    "${PIPELINE_TEST}"
    "${INSPECTOR_TEST}"
)

declare -a STAGE_FILES=(
    "${SYS_ROOT}/audit_modular_conformance.py"
    "${SYS_ROOT}/plan_modular_migration.py"
    "${SYS_ROOT}/classify_modular_migration.py"
    "${SYS_ROOT}/prepare_modular_decisions.py"
    "${SYS_ROOT}/accept_modular_decisions.py"
    "${SYS_ROOT}/compile_modular_execution.py"
    "${SYS_ROOT}/bind_modular_execution.py"
    "${SYS_ROOT}/review_modular_binding.py"
    "${SYS_ROOT}/compile_modular_replacement.py"
)

declare -a STAGE_OUTPUTS=(
    "${REPORT_ROOT}/modular-conformance/latest.json"
    "${REPORT_ROOT}/modular-migration/latest.json"
    "${REPORT_ROOT}/modular-classification/latest.json"
    "${REPORT_ROOT}/modular-decisions/latest.json"
    "${REPORT_ROOT}/modular-accepted-decisions/latest.json"
    "${REPORT_ROOT}/modular-execution/latest.json"
    "${REPORT_ROOT}/modular-binding/latest.json"
    "${REPORT_ROOT}/modular-review/latest.json"
    "${REPORT_ROOT}/modular-replacement/latest.json"
)

print_rule() {
    printf '%s\n' \
        "========================================================================"
}

print_heading() {
    print_rule
    printf '%s\n' "$1"
    print_rule
}

fail() {
    printf 'ERROR: %s\n' "$1" >&2
    exit "${EXIT_FAILURE}"
}

verify_required_files() {
    local path

    print_heading "REQUIRED FILES"

    for path in "${REQUIRED_FILES[@]}"; do
        if [[ ! -f "${path}" ]]; then
            printf 'MISSING: %s\n' "${path}"
            return "${EXIT_FAILURE}"
        fi

        printf 'FOUND: %s\n' "${path}"
    done

    return "${EXIT_SUCCESS}"
}

inventory_stage_files() {
    local ordinal
    local path

    print_heading "PIPELINE STAGE FILES"

    ordinal=0

    for path in "${STAGE_FILES[@]}"; do
        ordinal=$((ordinal + 1))

        if [[ -f "${path}" ]]; then
            printf '%d FOUND   %s\n' \
                "${ordinal}" \
                "${path}"
        else
            printf '%d MISSING %s\n' \
                "${ordinal}" \
                "${path}"
        fi
    done
}

inventory_stage_outputs() {
    local ordinal
    local path

    print_heading "EXISTING STAGE OUTPUTS"

    ordinal=0

    for path in "${STAGE_OUTPUTS[@]}"; do
        ordinal=$((ordinal + 1))

        if [[ -f "${path}" ]]; then
            if python3 -m json.tool \
                "${path}" \
                >/dev/null 2>&1
            then
                printf '%d VALID   %s\n' \
                    "${ordinal}" \
                    "${path}"
            else
                printf '%d INVALID %s\n' \
                    "${ordinal}" \
                    "${path}"
            fi
        else
            printf '%d MISSING %s\n' \
                "${ordinal}" \
                "${path}"
        fi
    done
}

validate_syntax() {
    print_heading "PYTHON SYNTAX"

    python3 -m py_compile \
        "${PIPELINE_SCRIPT}" \
        "${INSPECTOR_SCRIPT}" \
        "${PIPELINE_TEST}" \
        "${INSPECTOR_TEST}"

    local status=$?

    if [[ "${status}" -ne 0 ]]; then
        printf 'SYNTAX FAILED: %d\n' "${status}"
        return "${EXIT_FAILURE}"
    fi

    printf '%s\n' "SYNTAX PASSED"

    return "${EXIT_SUCCESS}"
}

run_tests() {
    print_heading "FOCUSED TESTS"

    python3 \
        "${PIPELINE_TEST}" \
        -v

    local pipeline_test_status=$?

    if [[ "${pipeline_test_status}" -ne 0 ]]; then
        printf 'PIPELINE TEST FAILED: %d\n' \
            "${pipeline_test_status}"

        return "${EXIT_FAILURE}"
    fi

    python3 \
        "${INSPECTOR_TEST}" \
        -v

    local inspector_test_status=$?

    if [[ "${inspector_test_status}" -ne 0 ]]; then
        printf 'INSPECTOR TEST FAILED: %d\n' \
            "${inspector_test_status}"

        return "${EXIT_FAILURE}"
    fi

    printf '%s\n' "FOCUSED TESTS PASSED"

    return "${EXIT_SUCCESS}"
}

run_pipeline() {
    print_heading "PIPELINE RUN"

    python3 \
        "${PIPELINE_SCRIPT}" \
        run

    local status=$?

    case "${status}" in
        "${EXIT_SUCCESS}")
            printf '%s\n' "PIPELINE RETURNED SUCCESS"
            ;;
        "${EXIT_BLOCKED}")
            printf '%s\n' \
                "PIPELINE STOPPED AT A GOVERNED BLOCKER"
            ;;
        *)
            printf 'PIPELINE FAILED: %d\n' "${status}"
            return "${EXIT_FAILURE}"
            ;;
    esac

    if [[ ! -f "${LATEST_PIPELINE}" ]]; then
        printf 'PIPELINE OUTPUT MISSING: %s\n' \
            "${LATEST_PIPELINE}"

        return "${EXIT_FAILURE}"
    fi

    if ! python3 -m json.tool \
        "${LATEST_PIPELINE}" \
        >/dev/null
    then
        printf 'PIPELINE OUTPUT INVALID: %s\n' \
            "${LATEST_PIPELINE}"

        return "${EXIT_FAILURE}"
    fi

    return "${status}"
}

verify_pipeline_report() {
    print_heading "PIPELINE REPORT VERIFICATION"

    python3 \
        "${PIPELINE_SCRIPT}" \
        verify

    local status=$?

    if [[ "${status}" -ne 0 ]]; then
        printf 'PIPELINE REPORT VERIFICATION FAILED: %d\n' \
            "${status}"

        return "${EXIT_FAILURE}"
    fi

    printf '%s\n' "PIPELINE REPORT VERIFIED"

    return "${EXIT_SUCCESS}"
}

inspect_pipeline() {
    print_heading "PIPELINE INSPECTION"

    python3 \
        "${INSPECTOR_SCRIPT}"

    local human_status=$?

    if [[ "${human_status}" -ne 0 ]]; then
        printf 'HUMAN INSPECTION FAILED: %d\n' \
            "${human_status}"

        return "${EXIT_FAILURE}"
    fi

    print_heading "PIPELINE INSPECTION JSON"

    python3 \
        "${INSPECTOR_SCRIPT}" \
        --json

    local json_status=$?

    if [[ "${json_status}" -ne 0 ]]; then
        printf 'JSON INSPECTION FAILED: %d\n' \
            "${json_status}"

        return "${EXIT_FAILURE}"
    fi

    return "${EXIT_SUCCESS}"
}

print_latest_summary() {
    print_heading "LATEST PIPELINE SUMMARY"

    python3 -c '
import json
from pathlib import Path

latest_path = Path(
    "/root/savant-runtime/vault/dimensions/sys/"
    "reports/modular-pipeline-run/latest.json"
)

if not latest_path.is_file():
    raise SystemExit(
        f"missing latest pipeline report: {latest_path}"
    )

latest = json.loads(
    latest_path.read_text(encoding="utf-8")
)

report_path = Path(latest["report"])

report = json.loads(
    report_path.read_text(encoding="utf-8")
)

print(f"passed: {report['"'"'passed'"'"']}")
print(
    "executed_stage_count: "
    f"{report['"'"'executed_stage_count'"'"']}"
)
print(
    "first_blocker: "
    f"{report['"'"'first_blocker'"'"']}"
)
print(
    "implementation_mutation_performed: "
    f"{report['"'"'implementation_mutation_performed'"'"']}"
)

print()

for stage in report["stages"]:
    print(
        f"{stage['"'"'ordinal'"'"']}. "
        f"{stage['"'"'key'"'"']}: "
        f"passed={stage['"'"'passed'"'"']}; "
        f"return_code={stage['"'"'return_code'"'"']}; "
        f"output_exists={stage['"'"'output_exists_after'"'"']}"
    )

    blocker = stage.get("blocker")

    if blocker:
        print(f"   blocker: {blocker}")

    stderr = stage.get("stderr", "").strip()

    if stderr:
        print("   stderr:")
        for line in stderr.splitlines():
            print(f"     {line}")

    stdout = stage.get("stdout", "").strip()

    if stdout:
        print("   stdout:")
        for line in stdout.splitlines():
            print(f"     {line}")
'

    local status=$?

    if [[ "${status}" -ne 0 ]]; then
        printf 'LATEST SUMMARY FAILED: %d\n' \
            "${status}"

        return "${EXIT_FAILURE}"
    fi

    return "${EXIT_SUCCESS}"
}

main() {
    verify_required_files \
        || fail "required diagnostic files are incomplete"

    inventory_stage_files
    inventory_stage_outputs

    validate_syntax \
        || fail "syntax validation failed"

    run_tests \
        || fail "focused tests failed"

    run_pipeline
    local pipeline_status=$?

    if [[ "${pipeline_status}" -eq "${EXIT_FAILURE}" ]]; then
        fail "pipeline execution failed"
    fi

    verify_pipeline_report \
        || fail "pipeline report verification failed"

    inspect_pipeline \
        || fail "pipeline inspection failed"

    print_latest_summary \
        || fail "pipeline summary failed"

    print_heading "DIAGNOSTIC RESULT"

    if [[ "${pipeline_status}" -eq "${EXIT_BLOCKED}" ]]; then
        printf '%s\n' \
            "BLOCKED: repair the reported first blocker only."

        printf '%s\n' \
            "No implementation mutation was requested."

        exit "${EXIT_BLOCKED}"
    fi

    printf '%s\n' \
        "PASSED: all nine pipeline stages produced valid outputs."

    printf '%s\n' \
        "No implementation mutation was requested."

    exit "${EXIT_SUCCESS}"
}


main "$@"

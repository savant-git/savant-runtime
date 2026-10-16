#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"
MASTERPLAN_ROOT="${ROOT}/tools/niche/masterplan"
TEST_ROOT="${ROOT}/edifices/identity/exiles/niche/prodigals/masterplan/tests"

RESUMER="${MASTERPLAN_ROOT}/resume_masterplan_opus_binding_chain.sh"
STATUS_TEST="${TEST_ROOT}/test_inspect_masterplan_opus_binding_state.py"
WORKSPACE_TEST="${TEST_ROOT}/test_compile_masterplan_opus_binding_workspace.py"

if [[ ! -s "${RESUMER}" ]]; then
    printf 'ERROR: required resumer is missing or empty: %s\n' \
        "${RESUMER}" \
        >&2

    exit 1
fi

if [[ ! -s "${STATUS_TEST}" ]]; then
    printf 'ERROR: required status test is missing or empty: %s\n' \
        "${STATUS_TEST}" \
        >&2

    exit 1
fi

if [[ ! -s "${WORKSPACE_TEST}" ]]; then
    printf 'ERROR: required workspace test is missing or empty: %s\n' \
        "${WORKSPACE_TEST}" \
        >&2

    exit 1
fi

resumer_first_line="$(
    head -n 1 \
        "${RESUMER}"
)"

status_test_first_line="$(
    head -n 1 \
        "${STATUS_TEST}"
)"

workspace_test_first_line="$(
    head -n 1 \
        "${WORKSPACE_TEST}"
)"

if [[ "${resumer_first_line}" != "#!/usr/bin/env bash" ]]; then
    printf 'ERROR: invalid resumer shebang: %q\n' \
        "${resumer_first_line}" \
        >&2

    exit 1
fi

if [[ "${status_test_first_line}" != "#!/usr/bin/env python3" ]]; then
    printf 'ERROR: invalid status-test shebang: %q\n' \
        "${status_test_first_line}" \
        >&2

    exit 1
fi

if [[ "${workspace_test_first_line}" != "#!/usr/bin/env python3" ]]; then
    printf 'ERROR: invalid workspace-test shebang: %q\n' \
        "${workspace_test_first_line}" \
        >&2

    exit 1
fi

if grep -q $'\033\\[200~' \
    "${RESUMER}"
then
    printf '%s\n' \
        "ERROR: bracketed-paste control sequence remains in resumer" \
        >&2

    exit 1
fi

if grep -q $'\033\\[200~' \
    "${STATUS_TEST}"
then
    printf '%s\n' \
        "ERROR: bracketed-paste control sequence remains in status test" \
        >&2

    exit 1
fi

if grep -q $'\033\\[200~' \
    "${WORKSPACE_TEST}"
then
    printf '%s\n' \
        "ERROR: bracketed-paste control sequence remains in workspace test" \
        >&2

    exit 1
fi

chmod 0755 \
    "${RESUMER}" \
    "${STATUS_TEST}" \
    "${WORKSPACE_TEST}"

bash -n \
    "${RESUMER}"

python3 -m py_compile \
    "${STATUS_TEST}" \
    "${WORKSPACE_TEST}"

python3 \
    "${STATUS_TEST}" \
    -v

python3 \
    "${WORKSPACE_TEST}" \
    -v

exec /usr/bin/bash \
    "${RESUMER}"

#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

TOOL="${ROOT}/tools/niche/masterplan/inspect_masterplan_opus_binding_state.py"
TEST="${ROOT}/hierarchies/identity/exiles/niche/prodigals/masterplan/tests/test_inspect_masterplan_opus_binding_state.py"
COMMAND="${ROOT}/bin/masterplan-opus-status"
RESUMER="${ROOT}/tools/niche/masterplan/resume_masterplan_opus_binding_chain.sh"

for path in \
    "${TOOL}" \
    "${TEST}" \
    "${COMMAND}" \
    "${RESUMER}"
do
    if [[ ! -s "${path}" ]]; then
        printf 'ERROR: required file missing or empty: %s\n' \
            "${path}" \
            >&2

        exit 1
    fi
done

tool_first_line="$(
    head -n 1 \
        "${TOOL}"
)"

if [[ "${tool_first_line}" != "#!/usr/bin/env python3" ]]; then
    printf 'ERROR: invalid inspector shebang: %q\n' \
        "${tool_first_line}" \
        >&2

    exit 1
fi

if grep -q "inspector = load_module()" \
    "${TOOL}"
then
    printf '%s\n' \
        "ERROR: test code remains inside inspector implementation" \
        >&2

    exit 1
fi

chmod 0755 \
    "${TOOL}" \
    "${TEST}" \
    "${COMMAND}" \
    "${RESUMER}"

python3 -m py_compile \
    "${TOOL}" \
    "${TEST}" \
    "${COMMAND}"

python3 \
    "${TEST}" \
    -v

"${COMMAND}"

set +e

/usr/bin/bash \
    "${RESUMER}"

status="$?"

set -e

test \
    "${status}" -eq 0 \
    -o "${status}" -eq 2

exit "${status}"

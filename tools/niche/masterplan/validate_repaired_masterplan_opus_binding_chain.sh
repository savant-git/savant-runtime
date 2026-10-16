#!/usr/bin/env bash

set -euo pipefail

REPAIR="/root/savant-runtime/tools/niche/masterplan/repair_and_resume_masterplan_opus_binding_chain.sh"
RUNNER="/root/savant-runtime/tools/niche/masterplan/run_now_repaired_masterplan_opus_binding_chain.sh"

for path in \
    "${REPAIR}" \
    "${RUNNER}"
do
    if [[ ! -s "${path}" ]]; then
        printf 'ERROR: file is missing or empty: %s\n' \
            "${path}" \
            >&2

        exit 1
    fi

    first_line="$(
        head -n 1 \
            "${path}"
    )"

    if [[ "${first_line}" != "#!/usr/bin/env bash" ]]; then
        printf 'ERROR: invalid shebang in %s: %q\n' \
            "${path}" \
            "${first_line}" \
            >&2

        exit 1
    fi

    if grep -q $'\033\\[200~' \
        "${path}"
    then
        printf 'ERROR: bracketed-paste sequence found in %s\n' \
            "${path}" \
            >&2

        exit 1
    fi
done

chmod 0755 \
    "${REPAIR}" \
    "${RUNNER}"

bash -n \
    "${REPAIR}" \
    "${RUNNER}"

exec /usr/bin/bash \
    "${RUNNER}"

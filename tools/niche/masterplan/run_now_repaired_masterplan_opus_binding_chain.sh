#!/usr/bin/env bash

set -euo pipefail

REPAIR="/root/savant-runtime/tools/niche/masterplan/repair_and_resume_masterplan_opus_binding_chain.sh"

if [[ ! -s "${REPAIR}" ]]; then
    printf 'ERROR: repair script is missing or empty: %s\n' \
        "${REPAIR}" \
        >&2

    exit 1
fi

first_line="$(
    head -n 1 \
        "${REPAIR}"
)"

if [[ "${first_line}" != "#!/usr/bin/env bash" ]]; then
    printf 'ERROR: invalid repair-script shebang: %q\n' \
        "${first_line}" \
        >&2

    exit 1
fi

if grep -q $'\033\\[200~' \
    "${REPAIR}"
then
    printf '%s\n' \
        "ERROR: bracketed-paste control sequence remains in repair script" \
        >&2

    exit 1
fi

chmod 0755 \
    "${REPAIR}"

bash -n \
    "${REPAIR}"

exec /usr/bin/bash \
    "${REPAIR}"

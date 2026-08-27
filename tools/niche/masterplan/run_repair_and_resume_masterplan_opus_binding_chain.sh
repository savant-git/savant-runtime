#!/usr/bin/env bash

set -euo pipefail

REPAIR="/root/savant-runtime/tools/niche/masterplan/repair_and_resume_masterplan_opus_binding_chain.sh"

test -f \
    "${REPAIR}"

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

chmod 0755 \
    "${REPAIR}"

bash -n \
    "${REPAIR}"

exec /usr/bin/bash \
    "${REPAIR}"

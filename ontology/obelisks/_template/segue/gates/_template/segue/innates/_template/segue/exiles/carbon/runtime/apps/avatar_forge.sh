#!/usr/bin/env bash
set -euo pipefail

root="/root/savant-runtime"
carbon="${root}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/carbon"
app="${carbon}/apps/avatar_forge"
launcher="${app}/run.sh"

if [[ ! -d "${app}" ]]; then
    printf 'carbon avatar forge unavailable: %s\n' "${app}" >&2
    exit 1
fi

if [[ ! -f "${launcher}" ]]; then
    printf 'carbon avatar forge launcher unavailable: %s\n' "${launcher}" >&2
    exit 1
fi

exec /usr/bin/env bash "${launcher}" "$@"

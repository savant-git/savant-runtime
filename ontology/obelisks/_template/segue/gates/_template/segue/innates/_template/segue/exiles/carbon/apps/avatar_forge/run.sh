#!/usr/bin/env bash
set -euo pipefail

app="/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/carbon/apps/avatar_forge"
venv="${app}/.venv"
requirements="${app}/requirements.txt"
src="${app}/src"

host="${CARBON_AVATAR_FORGE_HOST:-127.0.0.1}"
port="${CARBON_AVATAR_FORGE_PORT:-8787}"

if [[ ! -d "${venv}" ]]; then
    python3 -m venv "${venv}"
fi

python="${venv}/bin/python"
pip="${venv}/bin/pip"

if [[ ! -x "${python}" ]]; then
    printf 'carbon avatar forge python unavailable: %s\n' "${python}" >&2
    exit 1
fi

if [[ ! -x "${pip}" ]]; then
    printf 'carbon avatar forge pip unavailable: %s\n' "${pip}" >&2
    exit 1
fi

if [[ -f "${requirements}" ]]; then
    requirements_digest="$(
        sha256sum "${requirements}" |
        awk '{print $1}'
    )"

    installed_digest_file="${venv}/.carbon-requirements.sha256"
    installed_digest=""

    if [[ -f "${installed_digest_file}" ]]; then
        installed_digest="$(
            cat "${installed_digest_file}"
        )"
    fi

    if [[ "${requirements_digest}" != "${installed_digest}" ]]; then
        "${pip}" install -r "${requirements}"
        printf '%s\n' "${requirements_digest}" > "${installed_digest_file}"
    fi
fi

if [[ ! -d "${src}" ]]; then
    printf 'carbon avatar forge source unavailable: %s\n' "${src}" >&2
    exit 1
fi

export PYTHONPATH="${src}${PYTHONPATH:+:${PYTHONPATH}}"

exec "${python}" -m uvicorn \
    avatar_forge.api.main:app \
    --host "${host}" \
    --port "${port}"

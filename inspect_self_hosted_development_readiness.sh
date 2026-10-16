#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
EXILES="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"

section() {
    printf '\n=== %s ===\n' "$1"
}

show_file() {
    local file="$1"

    if [ -f "${file}" ]; then
        printf '\n--- %s ---\n' "${file}"
        sed -n '1,320p' "${file}"
    else
        printf 'MISSING: %s\n' "${file}"
    fi
}

section "ROOT"

printf 'root=%s\n' "${ROOT}"

test -d "${ROOT}" \
    && printf 'root_present=true\n' \
    || printf 'root_present=false\n'

printf 'python='
python3 --version 2>&1 || true

printf 'git='
git --version 2>&1 || true

printf 'curl='
curl --version 2>/dev/null | head -n 1 || true

section "AUTHORITY / CANON"

for file in \
    "${ROOT}/canon-system/canon.yaml" \
    "${ROOT}/canon-system/authority/foundation/dynamic_canon.yaml" \
    "${ROOT}/canon-system/authority/exiles/niche.yaml" \
    "${ROOT}/canon-system/authority/exiles/opus.yaml" \
    "${ROOT}/canon-system/authority/exiles/coda.yaml" \
    "${ROOT}/canon-system/authority/exiles/notary.yaml" \
    "${ROOT}/canon-system/authority/exiles/palaver.yaml" \
    "${ROOT}/canon-system/authority/exiles/envoy.yaml"
do
    if [ -f "${file}" ]; then
        printf '%s\n' "${file}"
    fi
done

if [ -f "${ROOT}/canon-system/runtime/canon.sqlite3" ]; then
    printf 'canon_database=true\n'
else
    printf 'canon_database=false\n'
fi

section "MASTERPLAN / NICHE"

for file in \
    "${ROOT}/masterplan.json" \
    "${ROOT}/MASTERPLAN.md" \
    "${EXILES}/niche/runtime/__init__.py"
do
    show_file "${file}"
done

find \
    "${EXILES}/niche" \
    -type f \
    \( \
        -name '*.py' \
        -o -name '*.json' \
    \) \
    ! -path '*/__pycache__/*' \
    -print \
    2>/dev/null \
    | sort \
    | head -n 120

section "OPUS AI EXECUTION"

find \
    "${EXILES}/opus/runtime" \
    -maxdepth 3 \
    -type f \
    \( \
        -name '*.py' \
        -o -name '*.json' \
        -o -name '*.yaml' \
        -o -name '*.yml' \
    \) \
    ! -path '*/__pycache__/*' \
    -print \
    2>/dev/null \
    | sort \
    | head -n 160

for file in \
    "${EXILES}/opus/runtime/__init__.py" \
    "${EXILES}/opus/runtime/router.py" \
    "${EXILES}/opus/runtime/environment.py"
do
    show_file "${file}"
done

section "OPUS PROVIDER ROUTE"

OPUS_RUNTIME="${EXILES}/opus/runtime"

if [ -f "${OPUS_RUNTIME}/router.py" ]; then
    PYTHONPATH="${OPUS_RUNTIME}" \
    python3 -c '
from router import select_provider

try:
    provider = select_provider("text_inference_route")
except Exception as exc:
    print({
        "route": "text_inference_route",
        "passed": False,
        "error_type": type(exc).__name__,
        "error": str(exc),
    })
else:
    print({
        "route": "text_inference_route",
        "provider": provider.get("id"),
        "passed": True,
    })
' || true
else
    printf 'router.py missing\n'
fi

section "CODA MUTATION"

find \
    "${EXILES}/coda/runtime" \
    -maxdepth 3 \
    -type f \
    -name '*.py' \
    ! -path '*/__pycache__/*' \
    -print \
    2>/dev/null \
    | sort

show_file \
    "${EXILES}/coda/runtime/mutation.py"

section "NOTARY VERIFICATION"

find \
    "${EXILES}/notary/runtime" \
    -maxdepth 3 \
    -type f \
    -name '*.py' \
    ! -path '*/__pycache__/*' \
    -print \
    2>/dev/null \
    | sort

show_file \
    "${EXILES}/notary/runtime/__init__.py"

section "PALAVER"

find \
    "${EXILES}/palaver/runtime" \
    -maxdepth 3 \
    -type f \
    -name '*.py' \
    ! -path '*/__pycache__/*' \
    -print \
    2>/dev/null \
    | sort \
    | head -n 160

for file in \
    "${EXILES}/palaver/runtime/__init__.py" \
    "${EXILES}/palaver/runtime/server.py"
do
    show_file "${file}"
done

section "ENVOY / OROBOUROS"

find \
    "${EXILES}/envoy" \
    -type f \
    \( \
        -name '*.py' \
        -o -name '*.json' \
        -o -name '*.yaml' \
        -o -name '*.yml' \
    \) \
    ! -path '*/__pycache__/*' \
    ! -path '*/node_modules/*' \
    -print \
    2>/dev/null \
    | sort \
    | head -n 180

printf '\n--- OROBOUROS REFERENCES ---\n'

grep -RIn \
    --exclude='*.pyc' \
    --exclude-dir='__pycache__' \
    --exclude-dir='node_modules' \
    --exclude-dir='vault' \
    -E 'Orobouros|orobouros|Living Trait Crown|living_trait|trait crown' \
    "${EXILES}/envoy" \
    "${EXILES}/palaver" \
    "${ROOT}/runtime" \
    2>/dev/null \
    | head -n 180 \
    || true

section "LORE / SCRYBE"

for file in \
    "${ROOT}/runtime/scrybe/engine.py" \
    "${ROOT}/runtime/scrybe/instances/lore.json" \
    "${EXILES}/lore/runtime/living_canon.py"
do
    if [ -f "${file}" ]; then
        printf '%s\n' "${file}"
    else
        printf 'MISSING: %s\n' "${file}"
    fi
done

if [ -x "${ROOT}/lore_scrybe_fluid_canon_final_verify.sh" ]; then
    "${ROOT}/lore_scrybe_fluid_canon_final_verify.sh" \
        || true
fi

section "LIVING SUBSTRATES"

for substrate in \
    scyon \
    splyce \
    scrybe \
    pryme \
    cypher \
    thryce \
    spyral \
    lythe \
    dryve
do
    if [ -d "${ROOT}/runtime/${substrate}" ]; then
        printf '%-10s present\n' "${substrate}"
    else
        printf '%-10s MISSING\n' "${substrate}"
    fi
done

section "DEVELOPER COMMANDS"

find \
    "${ROOT}/bin" \
    -maxdepth 1 \
    -type f \
    -printf '%f\n' \
    2>/dev/null \
    | sort

section "SYSTEM SERVICES"

systemctl list-unit-files \
    --type=service \
    2>/dev/null \
    | grep -Ei \
        'savant|palaver|opus|nginx' \
    || true

section "LISTENING PORTS"

ss -lntp \
    2>/dev/null \
    | grep -E \
        '(:80|:443|:8787|:8000|:8080|:5173|:11434)' \
    || true

section "NGINX"

if command -v nginx >/dev/null 2>&1; then
    nginx -t 2>&1 || true
fi

if [ -e /etc/nginx/sites-enabled/savant-nexus ]; then
    ls -l /etc/nginx/sites-enabled/savant-nexus
fi

section "LOCAL MODEL / PROVIDER RUNTIMES"

for command in \
    ollama \
    llama-server \
    llama-cli \
    vllm
do
    if command -v "${command}" >/dev/null 2>&1; then
        printf '%s=%s\n' \
            "${command}" \
            "$(command -v "${command}")"
    else
        printf '%s=absent\n' \
            "${command}"
    fi
done

if command -v ollama >/dev/null 2>&1; then
    ollama list 2>/dev/null || true
fi

section "SECRETS PRESENCE"

for file in \
    /root/.env \
    "${ROOT}/.env"
do
    if [ -f "${file}" ]; then
        printf '%s present\n' "${file}"

        python3 - "${file}" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])

keys = []

for raw in path.read_text(
    encoding="utf-8",
    errors="replace",
).splitlines():
    line = raw.strip()

    if (
        not line
        or line.startswith("#")
        or "=" not in line
    ):
        continue

    key = line.split(
        "=",
        1,
    )[0].strip()

    if key:
        keys.append(key)

for key in sorted(set(keys)):
    print(f"  {key}=<present>")
PY
    else
        printf '%s absent\n' "${file}"
    fi
done

section "SELF-DEVELOPMENT BINDING REFERENCES"

grep -RIn \
    --exclude='*.pyc' \
    --exclude-dir='__pycache__' \
    --exclude-dir='node_modules' \
    --exclude-dir='vault' \
    --exclude-dir='.git' \
    -E \
    'Niche|niche|Opus|opus|Coda|coda|Notary|notary|Palaver|palaver|task.*execute|execute.*task|mutation.*receipt|evidence.*receipt|development.*task' \
    "${ROOT}/runtime" \
    "${EXILES}/niche/runtime" \
    "${EXILES}/opus/runtime" \
    "${EXILES}/coda/runtime" \
    "${EXILES}/notary/runtime" \
    "${EXILES}/palaver/runtime" \
    2>/dev/null \
    | head -n 500 \
    || true

section "RESULT"

printf '%s\n' \
    'SELF-HOSTED DEVELOPMENT READINESS INSPECTION: complete'

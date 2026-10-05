#!/usr/bin/env bash
set -euo pipefail

root="/root/savant-runtime"
exiles="${root}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"

opus="${exiles}/opus"
envoy="${exiles}/envoy"
palaver="${exiles}/palaver"
niche="${exiles}/niche"
coda="${exiles}/coda"
notary="${exiles}/notary"

opus_runtime="${opus}/runtime"

failures=0

pass() {
    printf 'pass  %s\n' "$1"
}

fail() {
    printf 'fail  %s\n' "$1"
    failures=$((failures + 1))
}

check_file() {
    local path="$1"
    local label="$2"

    if [[ -f "$path" ]]; then
        pass "$label"
    else
        fail "$label"
    fi
}

check_python() {
    local path="$1"
    local label="$2"

    if [[ ! -f "$path" ]]; then
        fail "$label"
        return
    fi

    if python3 -m py_compile "$path"; then
        pass "$label"
    else
        fail "$label"
    fi
}

printf '%s\n' '=== savant migration gate ==='

printf '\n%s\n' '=== authority ==='

if [[ -f "${root}/authority/task-graph/masterplan.json" ]]; then
    pass "authoritative task graph"
elif [[ -f "${root}/masterplan.json" ]]; then
    pass "masterplan projection"
else
    fail "task authority"
fi

check_file \
    "${root}/canon-system/runtime/canon.sqlite3" \
    "fluid canon database"

printf '\n%s\n' '=== opus ==='

check_python \
    "${opus_runtime}/router.py" \
    "opus router"

if PYTHONPATH="${root}" python3 - <<'PY'
import importlib

base = (
    "ontology.obelisks._template.segue.gates._template."
    "segue.innates._template.segue.exiles.opus.runtime"
)

router = importlib.import_module(
    base + ".router"
)

provider = router.select_provider(
    "text_inference_route"
)

if not isinstance(
    provider,
    dict,
):
    raise SystemExit(1)

if not callable(
    getattr(
        router,
        "execute_text_request",
        None,
    )
):
    raise SystemExit(1)
PY
then
    pass "opus text inference surface"
else
    fail "opus text inference surface"
fi

printf '\n%s\n' '=== envoy ==='

check_python \
    "${envoy}/runtime/persona_engine.py" \
    "envoy persona engine"

check_python \
    "${envoy}/runtime/voice_engine.py" \
    "envoy voice engine"

check_python \
    "${envoy}/runtime/opus_bridge.py" \
    "envoy opus bridge"

if PYTHONPATH="${root}" python3 - <<'PY'
import importlib
import sys

base = (
    "ontology.obelisks._template.segue.gates._template."
    "segue.innates._template.segue.exiles"
)

opus = (
    base
    + ".opus.runtime"
)

envoy = (
    base
    + ".envoy.runtime"
)

palaver = (
    base
    + ".palaver.runtime"
)


def alias(
    short_name,
    qualified_name,
):
    module = importlib.import_module(
        qualified_name
    )

    sys.modules[
        short_name
    ] = module

    return module


alias(
    "environment",
    opus + ".environment",
)

alias(
    "model_projection",
    opus + ".model_projection",
)

alias(
    "router",
    opus + ".router",
)

alias(
    "voice_orchestrator",
    opus + ".voice_orchestrator",
)

importlib.import_module(
    envoy
    + ".canonical_primitives"
)

moral_self = importlib.import_module(
    envoy
    + ".moral_self"
)

sys.modules[
    "moral_self"
] = moral_self

persona_engine = importlib.import_module(
    envoy
    + ".persona_engine"
)

sys.modules[
    "persona_engine"
] = persona_engine

sys.modules[
    "savant_selfhost_persona_engine"
] = persona_engine

cognitive_projection = (
    importlib.import_module(
        envoy
        + ".cognitive_projection"
    )
)

sys.modules[
    "cognitive_projection"
] = cognitive_projection

opus_bridge = importlib.import_module(
    envoy
    + ".opus_bridge"
)

sys.modules[
    "opus_bridge"
] = opus_bridge

sys.modules[
    "savant_selfhost_envoy_opus_bridge"
] = opus_bridge

voice_engine = importlib.import_module(
    envoy
    + ".voice_engine"
)

for module, symbols in (
    (
        opus_bridge,
        (
            "infer_with_opus",
            "project_cognitive_layers",
        ),
    ),
    (
        voice_engine,
        (
            "synthesize",
        ),
    ),
):
    for symbol in symbols:
        if not callable(
            getattr(
                module,
                symbol,
                None,
            )
        ):
            raise SystemExit(1)

self_hosted = importlib.import_module(
    palaver
    + ".self_hosted_development"
)

result = self_hosted.selftest()

if result is False:
    raise SystemExit(1)

if (
    isinstance(
        result,
        dict,
    )
    and result.get(
        "passed"
    )
    is False
):
    raise SystemExit(1)
PY
then
    pass "envoy opus authority bridge"
    pass "envoy persona voice integration"
    pass "palaver self-hosted development boundary"
else
    fail "envoy opus authority bridge"
    fail "envoy persona voice integration"
    fail "palaver self-hosted development boundary"
fi

printf '\n%s\n' '=== palaver ==='

check_python \
    "${palaver}/runtime/server.py" \
    "palaver canonical server"

if grep -q \
    'palaver_envoy_synthesize_base64' \
    "${palaver}/runtime/server.py"
then
    pass "palaver envoy synthesis delegation"
else
    fail "palaver envoy synthesis delegation"
fi

if grep -q \
    'DEFAULT_PERSONA_ID' \
    "${palaver}/runtime/server.py"
then
    pass "palaver envoy persona default projection"
else
    fail "palaver envoy persona default projection"
fi

printf '\n%s\n' '=== niche ==='

niche_task_runtime="$(
    grep -RIl \
        --include='*.py' \
        --exclude-dir='__pycache__' \
        -E 'lease|transition|task.*state|task.*queue|masterplan' \
        "${niche}/runtime" \
        2>/dev/null \
        | head -n 1 \
        || true
)"

if [[ -n "$niche_task_runtime" ]]; then
    pass "niche task governance runtime"
else
    fail "niche task governance runtime"
fi

printf '\n%s\n' '=== coda ==='

check_python \
    "${coda}/runtime/mutation.py" \
    "coda mutation runtime"

if [[ -f "${coda}/runtime/mutation.py" ]] \
    && grep -q \
        'def replace_text' \
        "${coda}/runtime/mutation.py"
then
    pass "coda durable mutation surface"
else
    fail "coda durable mutation surface"
fi

printf '\n%s\n' '=== notary ==='

if [[ -f "${notary}/runtime/evidence_admission.py" ]]; then
    check_python \
        "${notary}/runtime/evidence_admission.py" \
        "notary evidence admission"
else
    fail "notary evidence admission"
fi

printf '\n%s\n' '=== migration artifacts ==='

check_file \
    "${root}/canon/nexus-migration/06_ENHANCEMENTS/12_MIGRATION_RECEIPTS.md" \
    "migration receipt canon candidate"

check_file \
    "${envoy}/segue/entity.json" \
    "envoy segue entity"

check_file \
    "${envoy}/segue/graph/edges.json" \
    "envoy segue edges"

check_file \
    "${envoy}/segue/lineage/inheritance.json" \
    "envoy segue lineage"

check_file \
    "${envoy}/segue/registry/contracts.json" \
    "envoy segue contracts"

printf '\n%s\n' '=== json integrity ==='

json_files=(
    "${envoy}/entity.json"
    "${envoy}/graph/node.json"
    "${envoy}/registry/module.json"
    "${envoy}/composition/exports.json"
    "${envoy}/composition/imports.json"
    "${envoy}/interface/capabilities/capabilities.json"
    "${envoy}/interface/contracts/contracts.json"
    "${envoy}/introspection/dependencies.json"
    "${envoy}/introspection/health.json"
    "${envoy}/api/palaver_voice_contract.json"
    "${envoy}/registry/contracts/opus_voice_orchestration_contract.json"
    "${envoy}/registry/contracts/opus_voice_request_contract.json"
    "${envoy}/segue/entity.json"
    "${envoy}/segue/graph/edges.json"
    "${envoy}/segue/lineage/inheritance.json"
    "${envoy}/segue/registry/contracts.json"
)

for file in "${json_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        fail "missing json: $file"
        continue
    fi

    if python3 -m json.tool "$file" >/dev/null; then
        pass "json $(basename "$file")"
    else
        fail "json $(basename "$file")"
    fi
done

printf '\n%s\n' '=== result ==='
printf 'blocking_gap_count=%s\n' "$failures"

if (( failures == 0 )); then
    printf '%s\n' 'migration_gate=ready'
    exit 0
fi

printf '%s\n' 'migration_gate=blocked'
exit 1

#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
EXILES="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"

NICHE="${EXILES}/niche/runtime"
OPUS="${EXILES}/opus/runtime"
CODA="${EXILES}/coda/runtime"
NOTARY="${EXILES}/notary/runtime"
PALAVER="${EXILES}/palaver/runtime"
ENVOY="${EXILES}/envoy/runtime"
LORE="${EXILES}/lore/runtime"

printf '%s\n' '=== SELF-DEVELOPMENT E2E EXACT SURFACE ==='

python3 - \
    "${NICHE}" \
    "${OPUS}" \
    "${CODA}" \
    "${NOTARY}" \
    "${PALAVER}" \
    "${ENVOY}" \
    "${LORE}" <<'PY'
from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOTS = [
    Path(value)
    for value in sys.argv[1:]
]

INTERESTING = {
    "assure",
    "attest",
    "bind_notary",
    "canonical_truth",
    "claim",
    "complete",
    "context",
    "create",
    "execute",
    "execute_text_request",
    "fail",
    "finish",
    "health",
    "lease",
    "recall",
    "replace_text",
    "request",
    "resolve",
    "select_provider",
    "start",
    "status",
    "submit",
    "transition",
    "validate",
    "verify",
}


def signature(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> str:
    return ast.unparse(
        node.args
    )


for root in ROOTS:
    print()
    print(
        f"=== {root} ==="
    )

    if not root.is_dir():
        print("MISSING")
        continue

    files = sorted(
        path
        for path in root.rglob("*.py")
        if "__pycache__"
        not in path.parts
    )

    for path in files:
        try:
            source = path.read_text(
                encoding="utf-8"
            )
            tree = ast.parse(
                source
            )
        except Exception as exc:
            print(
                f"PARSE-ERROR {path}: "
                f"{type(exc).__name__}: {exc}"
            )
            continue

        matches = []

        for node in ast.walk(tree):
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):
                if (
                    node.name in INTERESTING
                    or any(
                        token in node.name.lower()
                        for token in (
                            "task",
                            "lease",
                            "receipt",
                            "evidence",
                            "mutation",
                            "provider",
                            "infer",
                            "persona",
                        )
                    )
                ):
                    matches.append(
                        (
                            node.lineno,
                            node.name,
                            signature(node),
                        )
                    )

        if not matches:
            continue

        print()
        print(
            f"--- {path} ---"
        )

        for lineno, name, args in sorted(
            matches
        ):
            print(
                f"{lineno}: "
                f"{name}({args})"
            )
PY

printf '\n%s\n' \
    '=== PUBLIC PACKAGE EXPORTS ==='

for package in \
    "${ROOT}/runtime/scrybe/__init__.py" \
    "${ROOT}/runtime/pryme/__init__.py" \
    "${ROOT}/runtime/thryce/__init__.py" \
    "${ROOT}/runtime/dryve/__init__.py" \
    "${ROOT}/runtime/cypher/__init__.py" \
    "${ROOT}/runtime/spyral/__init__.py" \
    "${NICHE}/__init__.py" \
    "${OPUS}/__init__.py" \
    "${CODA}/__init__.py" \
    "${NOTARY}/__init__.py" \
    "${PALAVER}/__init__.py" \
    "${ENVOY}/__init__.py" \
    "${LORE}/__init__.py"
do
    if [ ! -f "${package}" ]; then
        continue
    fi

    printf '\n--- %s ---\n' \
        "${package}"

    sed -n '1,240p' \
        "${package}"
done

printf '\n%s\n' \
    '=== OPUS EXECUTION IMPLEMENTATION ==='

for file in \
    "${OPUS}/router.py" \
    "${OPUS}/environment.py"
do
    if [ -f "${file}" ]; then
        printf '\n--- %s ---\n' \
            "${file}"

        grep -nE \
            '^(def|class) |text_inference|provider|credential|execute_text' \
            "${file}" \
            | head -n 180 \
            || true
    fi
done

printf '\n%s\n' \
    '=== NICHE TASK IMPLEMENTATION ==='

find \
    "${NICHE}" \
    -maxdepth 2 \
    -type f \
    -name '*.py' \
    ! -path '*/__pycache__/*' \
    -print \
    | sort

grep -RIn \
    --include='*.py' \
    --exclude-dir='__pycache__' \
    -E \
    'lease|claim|transition|complete|task_id|masterplan|task graph|task_graph' \
    "${NICHE}" \
    | head -n 240 \
    || true

printf '\n%s\n' \
    '=== CODA EXACT MUTATION API ==='

if [ -f "${CODA}/mutation.py" ]; then
    python3 - "${CODA}/mutation.py" <<'PY'
import ast
import sys
from pathlib import Path

path = Path(sys.argv[1])
tree = ast.parse(
    path.read_text(
        encoding="utf-8"
    )
)

for node in ast.walk(tree):
    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    ):
        if node.name in {
            "replace_text",
            "resolve_target",
            "write_receipt",
            "status",
        }:
            print(
                f"{node.name}"
                f"({ast.unparse(node.args)})"
            )
PY
fi

printf '\n%s\n' \
    '=== NOTARY EXACT VERIFICATION API ==='

grep -RIn \
    --include='*.py' \
    --exclude-dir='__pycache__' \
    -E \
    '^(class|def) |assure|verify|attest|evidence|receipt' \
    "${NOTARY}" \
    | head -n 260 \
    || true

printf '\n%s\n' \
    '=== PALAVER EXECUTION / PATCH API ==='

grep -RIn \
    --include='*.py' \
    --exclude-dir='__pycache__' \
    -E \
    '^(class|def) |patch|apply|workspace|opus|envoy|persona|message|chat' \
    "${PALAVER}" \
    | head -n 320 \
    || true

printf '\n%s\n' \
    '=== OROBOUROS EXACT API ==='

grep -RIn \
    --include='*.py' \
    --include='*.json' \
    --exclude-dir='__pycache__' \
    -E \
    'Orobouros|orobouros|trait|persona|baseline|cap' \
    "${ENVOY}" \
    | head -n 300 \
    || true

printf '\n%s\n' \
    '=== LOCAL SELF-DEVELOPMENT PRIMITIVES ==='

find \
    "${ROOT}" \
    -type f \
    \( \
        -iname '*self*develop*' \
        -o -iname '*development*loop*' \
        -o -iname '*agent*loop*' \
        -o -iname '*coding*agent*' \
        -o -iname '*task*executor*' \
    \) \
    ! -path '*/vault/*' \
    ! -path '*/__pycache__/*' \
    ! -path '*/node_modules/*' \
    -print \
    | sort \
    | head -n 160

printf '\n%s\n' \
    '=== RESULT ==='

printf '%s\n' \
    'SELF-DEVELOPMENT E2E EXACT SURFACE INSPECTION: complete'

#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
ENGINE="${ROOT}/runtime/scrybe/engine.py"
INSTANCE="${ROOT}/runtime/scrybe/instance.py"

printf '%s\n' '=== SCRYBE ENGINE SIGNATURES ==='

python3 - "${ENGINE}" <<'PY'
import ast
import sys
from pathlib import Path

path = Path(sys.argv[1])
source = path.read_text(encoding="utf-8")
tree = ast.parse(source)

for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if node.name in {
            "recall",
            "authority_recall",
            "authority_score",
            "health",
            "project",
        }:
            args = ast.unparse(node.args)
            print(f"{path}:{node.lineno}")
            print(f"def {node.name}({args})")
            print()
PY

printf '%s\n' '=== SCRYBE INSTANCE SIGNATURES ==='

python3 - "${INSTANCE}" <<'PY'
import ast
import sys
from pathlib import Path

path = Path(sys.argv[1])
source = path.read_text(encoding="utf-8")
tree = ast.parse(source)

for node in ast.walk(tree):
    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        if isinstance(node, ast.ClassDef):
            if node.name == "ScrybeInstance":
                print(f"{path}:{node.lineno}")
                print(f"class {node.name}")
                print()
        elif node.name in {
            "load_instance",
            "validate_instance",
            "resolve_instance",
        }:
            args = ast.unparse(node.args)
            print(f"{path}:{node.lineno}")
            print(f"def {node.name}({args})")
            print()
PY

printf '%s\n' '=== SCRYBE PUBLIC EXPORTS ==='

python3 - "${ROOT}/runtime/scrybe/__init__.py" <<'PY'
import ast
import sys
from pathlib import Path

path = Path(sys.argv[1])
source = path.read_text(encoding="utf-8")
tree = ast.parse(source)

for node in tree.body:
    if isinstance(node, ast.ImportFrom):
        names = ", ".join(
            alias.name + (f" as {alias.asname}" if alias.asname else "")
            for alias in node.names
        )
        print(f"from {node.module or ''} import {names}")
    elif isinstance(node, ast.Import):
        names = ", ".join(
            alias.name + (f" as {alias.asname}" if alias.asname else "")
            for alias in node.names
        )
        print(f"import {names}")
    elif isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                print("__all__ =", ast.unparse(node.value))
PY

printf '%s\n' '=== RESULT ==='
printf '%s\n' 'SCRYBE SIGNATURE INSPECTION: complete'

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m unittest discover -s tests/constitution -p 'test_*.py' -v
python3 tests/constitution/validate_no_regression.py kindred
python3 tests/constitution/validate_no_regression.py lineage

first="$(python3 -m runtime.constitution.cli runtime | sha256sum | cut -d' ' -f1)"
second="$(python3 -m runtime.constitution.cli runtime | sha256sum | cut -d' ' -f1)"
test "$first" = "$second"

printf 'constitutional projection digest: %s\n' "$first"
printf 'constitutional invariants and existing runtime baseline validated\n'

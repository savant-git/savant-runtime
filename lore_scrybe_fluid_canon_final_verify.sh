#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
LORE_RUNTIME="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/lore/runtime"

python3 -m py_compile \
  "${ROOT}/runtime/scrybe/engine.py" \
  "${ROOT}/runtime/scrybe/instance.py" \
  "${LORE_RUNTIME}/living_canon.py" \
  "${LORE_RUNTIME}/__init__.py"

PYTHONPATH="${ROOT}" \
python3 -c '
import importlib.util
import sys
from pathlib import Path

from runtime.scrybe import Scrybe

root = Path("/root/savant-runtime")

module_path = (
    root
    / "ontology/obelisks/_template/segue/gates/_template/segue/"
      "innates/_template/segue/exiles/lore/runtime/living_canon.py"
)

module_name = "lore_living_canon"

spec = importlib.util.spec_from_file_location(
    module_name,
    module_path,
)

assert spec is not None
assert spec.loader is not None

module = importlib.util.module_from_spec(
    spec
)

sys.modules[module_name] = module

try:
    spec.loader.exec_module(module)
except Exception:
    sys.modules.pop(
        module_name,
        None,
    )
    raise


class FocusedScrybe(Scrybe):
    def __init__(self):
        pass

    def recall(
        self,
        query,
        *,
        limit=9,
        memory_type=None,
        at=None,
    ):
        return (
            {
                "id": "canon:test:one",
                "query": query,
                "status": "accepted",
                "authority": {
                    "state": "accepted",
                },
                "lineage": {
                    "supersedes": [],
                    "superseded_by": [],
                },
                "provenance": {
                    "source": "focused-verification",
                },
                "at": at,
            },
        )[:limit]

    def authority_recall(
        self,
        authority,
    ):
        return (
            {
                "id": "canon:test:authority",
                "authority": authority,
                "status": "accepted",
            },
        )

    def health(self):
        return {
            "healthy": True,
        }


scrybe = FocusedScrybe()

binding = module.bind_scrybe(
    scrybe
)

status = binding.status()

assert status["owner"] == "exile:lore"
assert status["retrieval_owner"] == "living:scrybe"
assert status["canonical_store"] == "fluid-canon"
assert status["scrybe_retrieval_reused"] is True
assert status["independent_ranking_engine"] is False
assert status["independent_memory_store"] is False
assert status["canon_mutation"] is False
assert status["projection_authoritative"] is False
assert status["authority_effect"] == "none"

context = binding.context(
    "canonical truth",
    limit=3,
)

assert context["owner"] == "exile:lore"
assert context["retrieval_owner"] == "living:scrybe"
assert context["canonical_store"] == "fluid-canon"
assert context["bounded"] is True
assert context["independent_memory_store"] is False
assert context["projection_authoritative"] is False
assert context["mutation_performed"] is False
assert context["context"]["record_count"] == 1

current = binding.canonical_truth(
    "canonical truth",
)

assert current["current_only"] is True
assert current["historical"] is False
assert current["mutation_performed"] is False

historical = binding.historical_truth(
    "canonical truth",
    at="2026-07-21T04:20:39Z",
)

assert historical["historical"] is True
assert historical["at"] == "2026-07-21T04:20:39Z"
assert historical["mutation_performed"] is False

authority = binding.authority(
    {
        "state": "accepted",
    }
)

assert authority["record_count"] == 1
assert authority["projection_authoritative"] is False
assert authority["authority_effect"] == "none"

canon_db = (
    root
    / "canon-system/runtime/canon.sqlite3"
)

assert canon_db.is_file()

print({
    "lore_owner": "exile:lore",
    "retrieval_owner": "living:scrybe",
    "canonical_store": "fluid-canon",
    "canon_database_present": True,
    "scrybe_retrieval_reused": True,
    "duplicate_ranking_engine": False,
    "duplicate_memory_store": False,
    "canon_mutation": False,
    "current_recall": True,
    "historical_recall": True,
    "authority_recall": True,
    "context_hydration": True,
    "passed": True,
})
'

printf '%s\n' \
  'LORE / SCRYBE / FLUID CANON FINAL INTEGRATION: valid'

#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(
    "/root/savant-runtime"
).resolve()

RUNTIME = (
    ROOT
    / "ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/"
    "exiles/envoy/runtime"
)

HISTORY_PERSISTENCE_PATH = (
    RUNTIME
    / "trait_persistence.py"
)

CANDIDATE_PERSISTENCE_PATH = (
    RUNTIME
    / "trait_candidate_persistence.py"
)

OWNER = "exile:envoy"
PERSISTENCE_OWNER = "coda"

SCHEMA = (
    "savant://envoy/"
    "orobouros-trait-state/1.0.0"
)


class TraitStateError(
    RuntimeError
):
    pass


def _load_module(
    module_name: str,
    path: Path,
) -> ModuleType:
    existing = sys.modules.get(
        module_name
    )

    if existing is not None:
        return existing

    if not path.is_file():
        raise TraitStateError(
            f"required runtime missing: {path}"
        )

    specification = (
        importlib.util
        .spec_from_file_location(
            module_name,
            path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise TraitStateError(
            f"unable to load runtime: {path}"
        )

    module = (
        importlib.util
        .module_from_spec(
            specification
        )
    )

    sys.modules[
        module_name
    ] = module

    specification.loader.exec_module(
        module
    )

    return module


def history_persistence() -> ModuleType:
    return _load_module(
        "savant_envoy_trait_history_persistence",
        HISTORY_PERSISTENCE_PATH,
    )


def candidate_persistence() -> ModuleType:
    return _load_module(
        "savant_envoy_trait_candidate_persistence",
        CANDIDATE_PERSISTENCE_PATH,
    )


def accepted_projection() -> dict[
    str,
    Any,
]:
    history = history_persistence()
    candidates = candidate_persistence()

    catalog = (
        candidates.candidate_catalog()
    )

    projection = (
        history.accepted_projection(
            catalog
        )
    )

    if (
        projection.get(
            "persona_id"
        )
        != "orobouros"
    ):
        raise TraitStateError(
            "accepted projection persona "
            "identity mismatch"
        )

    if (
        projection.get(
            "authoritative"
        )
        is not False
    ):
        raise TraitStateError(
            "accepted projection became "
            "authoritative"
        )

    if (
        projection.get(
            "authority_effect"
        )
        != "none"
    ):
        raise TraitStateError(
            "accepted projection changed "
            "authority"
        )

    if (
        projection.get(
            "baseline_mutated"
        )
        is not False
    ):
        raise TraitStateError(
            "accepted projection mutated "
            "Orobouros baseline"
        )

    if (
        projection.get(
            "trait_pool_mutated"
        )
        is not False
    ):
        raise TraitStateError(
            "accepted projection mutated "
            "static trait pool"
        )

    return projection


def replay_projection() -> dict[
    str,
    Any,
]:
    history = history_persistence()
    candidates = candidate_persistence()

    history_status = history.status()
    candidate_status = candidates.status()

    accepted = accepted_projection()

    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "persistence_owner": (
            PERSISTENCE_OWNER
        ),
        "persona_id": "orobouros",
        "history_record_count": (
            history_status[
                "record_count"
            ]
        ),
        "candidate_count": (
            candidate_status[
                "candidate_count"
            ]
        ),
        "accepted_trait_count": len(
            accepted[
                "accepted_traits"
            ]
        ),
        "champions": (
            accepted[
                "champions"
            ]
        ),
        "accepted_projection": accepted,
        "history_restart_replay": True,
        "candidate_restart_replay": True,
        "accepted_restart_replay": True,
        "baseline_mutation": False,
        "trait_pool_mutation": False,
        "authoritative": False,
        "authority_effect": "none",
        "rebuildable": True,
    }


def status() -> dict[
    str,
    Any,
]:
    history = history_persistence()
    candidates = candidate_persistence()

    history_status = history.status()
    candidate_status = candidates.status()

    return {
        "schema": (
            "savant://envoy/"
            "orobouros-trait-state-status/"
            "1.0.0"
        ),
        "owner": OWNER,
        "persistence_owner": (
            PERSISTENCE_OWNER
        ),
        "history_state_present": (
            history_status[
                "state_present"
            ]
        ),
        "candidate_state_present": (
            candidate_status[
                "state_present"
            ]
        ),
        "history_record_count": (
            history_status[
                "record_count"
            ]
        ),
        "candidate_count": (
            candidate_status[
                "candidate_count"
            ]
        ),
        "history_append_only": True,
        "candidate_append_only": True,
        "immutable_history": True,
        "immutable_candidates": True,
        "deterministic_replay": True,
        "restart_replay": True,
        "accepted_projection_derived": True,
        "caller_supplied_catalog_required": False,
        "coda_executes_mutation": True,
        "envoy_executes_mutation": False,
        "baseline_mutation": False,
        "trait_pool_mutation": False,
        "automatic_supersession": False,
        "authoritative": False,
        "authority_effect": "none",
        "rebuildable": True,
    }


def selftest() -> dict[
    str,
    Any,
]:
    history = history_persistence()
    candidates = candidate_persistence()

    history_first = (
        history.store_projection(
            ()
        )
    )

    history_second = (
        history.store_projection(
            ()
        )
    )

    if history_first != history_second:
        raise TraitStateError(
            "history empty projection "
            "is not deterministic"
        )

    candidate_first = (
        candidates.store_projection(
            {}
        )
    )

    candidate_second = (
        candidates.store_projection(
            {}
        )
    )

    if (
        candidate_first
        != candidate_second
    ):
        raise TraitStateError(
            "candidate empty projection "
            "is not deterministic"
        )

    history_runtime = (
        history.history_runtime()
    )

    empty_accepted_a = (
        history_runtime
        .accepted_trait_projection(
            (),
            {},
        )
    )

    empty_accepted_b = (
        history_runtime
        .accepted_trait_projection(
            (),
            {},
        )
    )

    if (
        empty_accepted_a
        != empty_accepted_b
    ):
        raise TraitStateError(
            "accepted empty projection "
            "is not deterministic"
        )

    if empty_accepted_a[
        "accepted_traits"
    ]:
        raise TraitStateError(
            "empty history unexpectedly "
            "accepted traits"
        )

    if empty_accepted_a[
        "champions"
    ]:
        raise TraitStateError(
            "empty history unexpectedly "
            "contains champions"
        )

    return {
        "ok": True,
        "owner": OWNER,
        "persistence_owner": (
            PERSISTENCE_OWNER
        ),
        "history_projection_deterministic": (
            True
        ),
        "candidate_projection_deterministic": (
            True
        ),
        "accepted_projection_deterministic": (
            True
        ),
        "restart_replay_bound": True,
        "caller_supplied_catalog_required": (
            False
        ),
        "mutation_performed": False,
        "authoritative": False,
        "authority_effect": "none",
    }


def main() -> int:
    print(
        json.dumps(
            {
                "selftest": selftest(),
                "status": status(),
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

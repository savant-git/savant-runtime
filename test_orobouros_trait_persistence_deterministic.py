#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(
    "/root/savant-runtime"
)

ENVOY_RUNTIME = (
    ROOT
    / "ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/"
    "exiles/envoy/runtime"
)

MODULE_PATH = (
    ENVOY_RUNTIME
    / "trait_persistence.py"
)


def load_module():
    specification = (
        importlib.util
        .spec_from_file_location(
            "orobouros_trait_persistence_test",
            MODULE_PATH,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise RuntimeError(
            "cannot load trait_persistence.py"
        )

    module = (
        importlib.util
        .module_from_spec(
            specification
        )
    )

    sys.modules[
        specification.name
    ] = module

    specification.loader.exec_module(
        module
    )

    return module


def main() -> int:
    module = load_module()

    history = module.history_runtime()
    coda = module.coda_runtime()

    selftest_a = module.selftest()
    selftest_b = module.selftest()

    if selftest_a != selftest_b:
        raise RuntimeError(
            "persistence selftest is "
            "not deterministic"
        )

    if (
        selftest_a[
            "persistence_owner"
        ]
        != "coda"
    ):
        raise RuntimeError(
            "persistence ownership leaked"
        )

    if (
        selftest_a[
            "mutation_performed"
        ]
        is not False
    ):
        raise RuntimeError(
            "selftest unexpectedly "
            "performed mutation"
        )

    empty_a = (
        module.empty_store_projection()
    )

    empty_b = (
        module.empty_store_projection()
    )

    if empty_a != empty_b:
        raise RuntimeError(
            "empty store projection "
            "is not deterministic"
        )

    if (
        empty_a[
            "owner"
        ]
        != "exile:envoy"
    ):
        raise RuntimeError(
            "semantic ownership mismatch"
        )

    if (
        empty_a[
            "persistence_owner"
        ]
        != "coda"
    ):
        raise RuntimeError(
            "durable persistence owner "
            "mismatch"
        )

    if (
        empty_a[
            "authoritative"
        ]
        is not False
    ):
        raise RuntimeError(
            "persistence projection "
            "became authoritative"
        )

    if (
        empty_a[
            "authority_effect"
        ]
        != "none"
    ):
        raise RuntimeError(
            "persistence projection "
            "changed authority"
        )

    validated_empty = (
        history.validate_history(
            ()
        )
    )

    store_a = (
        module.store_projection(
            validated_empty
        )
    )

    store_b = (
        module.store_projection(
            validated_empty
        )
    )

    if store_a != store_b:
        raise RuntimeError(
            "store projection is "
            "not deterministic"
        )

    if (
        store_a
        != empty_a
    ):
        raise RuntimeError(
            "empty canonical store "
            "projection diverged"
        )

    target_a, relative_a = (
        coda.resolve_target(
            module.STATE_RELATIVE_PATH
        )
    )

    target_b, relative_b = (
        coda.resolve_target(
            module.STATE_RELATIVE_PATH
        )
    )

    if (
        target_a != target_b
        or relative_a != relative_b
    ):
        raise RuntimeError(
            "Coda target resolution "
            "is not deterministic"
        )

    if (
        relative_a
        != module.STATE_RELATIVE_PATH
    ):
        raise RuntimeError(
            "Coda changed persisted "
            "state identity"
        )

    if (
        ROOT.resolve()
        not in target_a.parents
    ):
        raise RuntimeError(
            "state target escaped "
            "Savant root"
        )

    status_a = module.status()
    status_b = module.status()

    if status_a != status_b:
        raise RuntimeError(
            "persistence status is "
            "not deterministic"
        )

    required_status = {
        "owner": "exile:envoy",
        "persistence_owner": "coda",
        "append_only_model": True,
        "immutable_history": True,
        "deterministic_replay": True,
        "optimistic_concurrency": True,
        "atomic_mutation": True,
        "mutation_receipts": True,
        "coda_executes_mutation": True,
        "envoy_executes_mutation": False,
        "baseline_mutation": False,
        "trait_pool_mutation": False,
        "authoritative": False,
        "authority_effect": "none",
        "rebuildable": True,
    }

    for key, expected in (
        required_status.items()
    ):
        actual = status_a.get(
            key
        )

        if actual != expected:
            raise RuntimeError(
                f"status mismatch for "
                f"{key}: "
                f"{actual!r} != "
                f"{expected!r}"
            )

    before_exists = (
        module.STATE_PATH.exists()
    )

    module.selftest()

    after_exists = (
        module.STATE_PATH.exists()
    )

    if (
        before_exists
        != after_exists
    ):
        raise RuntimeError(
            "non-mutating verification "
            "changed persistent state"
        )

    print(
        "OROBOUROS TRAIT PERSISTENCE "
        "DETERMINISM: PASS"
    )

    print(
        "semantic_owner="
        + status_a[
            "owner"
        ]
    )

    print(
        "persistence_owner="
        + status_a[
            "persistence_owner"
        ]
    )

    print(
        "state_path="
        + status_a[
            "state_path"
        ]
    )

    print(
        "state_present="
        + str(
            status_a[
                "state_present"
            ]
        ).lower()
    )

    print(
        "record_count="
        + str(
            status_a[
                "record_count"
            ]
        )
    )

    print(
        "coda_executes_mutation="
        + str(
            status_a[
                "coda_executes_mutation"
            ]
        ).lower()
    )

    print(
        "envoy_executes_mutation="
        + str(
            status_a[
                "envoy_executes_mutation"
            ]
        ).lower()
    )

    print(
        "mutation_performed=false"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

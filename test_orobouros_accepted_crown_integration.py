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

PERSONA_PATH = (
    ENVOY_RUNTIME
    / "persona_engine.py"
)

HISTORY_PATH = (
    ENVOY_RUNTIME
    / "trait_history.py"
)

PERSISTENCE_PATH = (
    ENVOY_RUNTIME
    / "trait_persistence.py"
)


def load_module(
    name: str,
    path: Path,
):
    spec = (
        importlib.util
        .spec_from_file_location(
            name,
            path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            f"cannot load {path}"
        )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    sys.modules[
        name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def main() -> int:
    persona = load_module(
        "orobouros_persona_engine_check",
        PERSONA_PATH,
    )

    history = load_module(
        "orobouros_trait_history_check",
        HISTORY_PATH,
    )

    persistence = load_module(
        "orobouros_trait_persistence_check",
        PERSISTENCE_PATH,
    )

    baseline_before = list(
        persona.load_persona(
            "orobouros"
        )[
            "baseline"
        ]
    )

    records = ()

    catalog = {}

    accepted = (
        history
        .accepted_trait_projection(
            records,
            catalog,
        )
    )

    if (
        accepted[
            "accepted_traits"
        ]
        != []
    ):
        raise RuntimeError(
            "empty history produced "
            "accepted traits"
        )

    if (
        accepted[
            "champions"
        ]
        != {}
    ):
        raise RuntimeError(
            "empty history produced "
            "champions"
        )

    persisted = (
        persistence
        .store_projection(
            records
        )
    )

    if (
        persisted[
            "authoritative"
        ]
        is not False
    ):
        raise RuntimeError(
            "persisted trait state "
            "became authoritative"
        )

    if (
        persisted[
            "authority_effect"
        ]
        != "none"
    ):
        raise RuntimeError(
            "persisted trait state "
            "changed authority"
        )

    composed_a = (
        persona.compose_persona(
            persona_id="orobouros",
            domains=(
                "analysis",
                "engineering",
            ),
            signals=(
                "analyze",
                "implement",
                "verify",
            ),
            cap=4,
        )
    )

    composed_b = (
        persona.compose_persona(
            persona_id="orobouros",
            domains=(
                "analysis",
                "engineering",
            ),
            signals=(
                "analyze",
                "implement",
                "verify",
            ),
            cap=4,
        )
    )

    if composed_a != composed_b:
        raise RuntimeError(
            "persona composition "
            "is not deterministic"
        )

    baseline_after = list(
        persona.load_persona(
            "orobouros"
        )[
            "baseline"
        ]
    )

    if (
        baseline_before
        != baseline_after
    ):
        raise RuntimeError(
            "Orobouros baseline mutated"
        )

    if (
        composed_a[
            "baseline"
        ]
        != baseline_before
    ):
        raise RuntimeError(
            "composed baseline diverged "
            "from permanent baseline"
        )

    static_pool = (
        persona.load_trait_pool(
            "orobouros_traits"
        )[
            "traits"
        ]
    )

    static_ids = {
        str(
            trait[
                "id"
            ]
        )
        for trait
        in static_pool
    }

    selected_ids = set(
        composed_a[
            "living_trait_crown"
        ]
    )

    if not selected_ids.issubset(
        static_ids
    ):
        raise RuntimeError(
            "persona selected trait "
            "outside static candidate pool"
        )

    if (
        len(
            selected_ids
        )
        > 4
    ):
        raise RuntimeError(
            "Living Trait Crown "
            "exceeded requested cap"
        )

    persistence_status = (
        persistence.status()
    )

    if (
        persistence_status[
            "persistence_owner"
        ]
        != "coda"
    ):
        raise RuntimeError(
            "Coda persistence ownership "
            "not preserved"
        )

    print(
        "OROBOUROS ACCEPTED CROWN "
        "INTEGRATION BOUNDARY: PASS"
    )

    print(
        "baseline_preserved=true"
    )

    print(
        "accepted_projection_authoritative=false"
    )

    print(
        "persistence_owner="
        + persistence_status[
            "persistence_owner"
        ]
    )

    print(
        "static_trait_pool_count="
        + str(
            len(
                static_ids
            )
        )
    )

    print(
        "selected_crown_count="
        + str(
            len(
                selected_ids
            )
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

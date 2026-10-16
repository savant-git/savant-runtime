#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping


schema = (
    "savant://runtime/envoy/"
    "orobouros-coda-boundary/1.0.0"
)

owner = "exile:envoy"
target_owner = "coda"
persona_id = "orobouros"

authority_effect = "none"

root = Path(
    "/root/savant-runtime"
)

coda_store_path = (
    root
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "coda"
    / "runtime"
    / "orobouros_evolution_store.py"
)


class orobouros_coda_boundary_error(
    RuntimeError
):
    pass


def _mapping(
    value: Any,
    *,
    label: str,
) -> dict[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise (
            orobouros_coda_boundary_error(
                f"{label} must be a mapping"
            )
        )

    return {
        str(key):
            item
        for key, item
        in value.items()
    }


def _load_coda_store():
    if not coda_store_path.is_file():
        raise (
            orobouros_coda_boundary_error(
                "Coda evolution store is missing"
            )
        )

    specification = (
        importlib.util.spec_from_file_location(
            "savant_coda_orobouros_evolution_store",
            coda_store_path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise (
            orobouros_coda_boundary_error(
                "unable to load Coda evolution store"
            )
        )

    module = (
        importlib.util.module_from_spec(
            specification
        )
    )

    specification.loader.exec_module(
        module
    )

    return module


def persist_evolution_lineage(
    *,
    evolution_projection: Mapping[
        str,
        Any,
    ],
    expected_store_digest: str | None = None,
) -> dict[str, Any]:
    projection = _mapping(
        evolution_projection,
        label="evolution_projection",
    )

    if (
        projection.get(
            "owner"
        )
        != owner
    ):
        raise (
            orobouros_coda_boundary_error(
                "evolution projection must remain Envoy-owned"
            )
        )

    if (
        projection.get(
            "persona_id"
        )
        != persona_id
    ):
        raise (
            orobouros_coda_boundary_error(
                "invalid persona identity"
            )
        )

    if (
        projection.get(
            "promotion_executed"
        )
        is not False
    ):
        raise (
            orobouros_coda_boundary_error(
                "Envoy projection cannot claim promotion execution"
            )
        )

    registry = _mapping(
        projection.get(
            "registry"
        ),
        label="registry",
    )

    shadow = _mapping(
        projection.get(
            "shadow"
        ),
        label="shadow",
    )

    gate = _mapping(
        projection.get(
            "promotion_gate"
        ),
        label="promotion_gate",
    )

    request = _mapping(
        projection.get(
            "coda_mutation_request"
        ),
        label="coda_mutation_request",
    )

    if not request:
        raise (
            orobouros_coda_boundary_error(
                "eligible Coda mutation request is required"
            )
        )

    if (
        request.get(
            "target_owner"
        )
        != target_owner
    ):
        raise (
            orobouros_coda_boundary_error(
                "mutation target owner must be Coda"
            )
        )

    coda = _load_coda_store()

    result = coda.append(
        registry_projection=
            registry,
        shadow_evaluation=
            shadow,
        promotion_gate=
            gate,
        mutation_request=
            request,
        expected_store_digest=
            expected_store_digest,
    )

    if (
        result.get(
            "owner"
        )
        != target_owner
    ):
        raise (
            orobouros_coda_boundary_error(
                "durable evolution lineage escaped Coda ownership"
            )
        )

    if result.get(
        "mutation_executed"
    ):
        raise (
            orobouros_coda_boundary_error(
                "lineage persistence unexpectedly mutated Crown"
            )
        )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "target_owner":
            target_owner,
        "persona_id":
            persona_id,
        "coda_receipt":
            result,
        "lineage_persisted":
            bool(
                result.get(
                    "appended",
                    False,
                )
            ),
        "crown_mutated":
            False,
        "trait_history_mutated":
            False,
        "promotion_executed":
            False,
        "authority_effect":
            authority_effect,
    }


def status() -> dict[str, Any]:
    coda = _load_coda_store()

    return {
        "schema":
            schema,
        "owner":
            owner,
        "target_owner":
            target_owner,
        "persona_id":
            persona_id,
        "coda_evolution_store":
            coda.status(),
        "lineage_persistence":
            True,
        "crown_mutation":
            False,
        "trait_history_mutation":
            False,
        "promotion_execution":
            False,
        "authority_effect":
            authority_effect,
    }


def selftest() -> dict[str, Any]:
    coda = _load_coda_store()

    coda_status = (
        coda.selftest()
    )

    if (
        coda_status.get(
            "owner"
        )
        != target_owner
    ):
        raise (
            orobouros_coda_boundary_error(
                "Coda ownership selftest failed"
            )
        )

    if coda_status.get(
        "mutation_executed"
    ):
        raise (
            orobouros_coda_boundary_error(
                "Coda lineage store mutated Crown"
            )
        )

    return {
        "schema":
            schema,
        "ok":
            True,
        "owner":
            owner,
        "target_owner":
            target_owner,
        "lineage_persistence":
            True,
        "promotion_executed":
            False,
        "authority_effect":
            authority_effect,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

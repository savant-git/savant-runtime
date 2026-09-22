#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(
    "/root/savant-runtime"
)

COALESCE_ROOT = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/modus/segue/"
    "prodigals/coalesce"
).resolve()

RUNTIME_ROOT = (
    COALESCE_ROOT
    / "runtime"
)

FILAMENT_PROJECTOR = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/filament/runtime/"
    "projectors/coalesce_view.py"
)

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(RUNTIME_ROOT),
    )


from coalesce_v2 import (
    runtime as v2_runtime,
)
from identity_resolver import (
    resolver,
)
from sliver_migration_projection import (
    project as migration_projection,
)


SCHEMA = (
    "savant://coalesce/"
    "identity-migration-verification/1"
)

OWNER = "prodigal:modus:coalesce"


class IdentityMigrationVerificationError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise IdentityMigrationVerificationError(
            message
        )


def load_filament_projector():
    require(
        FILAMENT_PROJECTOR.is_file(),
        "Filament Coalesce projector missing",
    )

    spec = (
        importlib.util.spec_from_file_location(
            "savant_filament_coalesce_identity_verify",
            FILAMENT_PROJECTOR,
        )
    )

    require(
        spec is not None
        and spec.loader is not None,
        "unable to construct Filament projector import",
    )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    sys.modules[
        spec.name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def verify_identity_surface() -> dict[str, Any]:
    identities = resolver()

    historical = tuple(
        identities.pool.historical_slabs
    )

    slivers = tuple(
        identities.pool.slivers
    )

    require(
        len(historical) == 81,
        "historical 81-piece baseline changed",
    )

    require(
        bool(slivers),
        "canonical Sliver Pool is empty",
    )

    for slab_id in historical:
        result = identities.resolve(
            slab_id
        )

        require(
            result.get(
                "requested_identity"
            )
            == slab_id,
            "historical identity was rewritten",
        )

        require(
            str(
                result.get(
                    "canonical_identity",
                    "",
                )
            ).startswith(
                "sliver:coalesce:"
            ),
            "historical identity failed Sliver resolution",
        )

        require(
            result.get(
                "compatibility",
                {},
            ).get(
                "destructive_migration"
            )
            is False,
            "destructive identity migration detected",
        )

    for sliver in slivers:
        result = identities.resolve(
            sliver.sliver_id
        )

        require(
            result.get(
                "canonical_identity"
            )
            == sliver.sliver_id,
            "canonical Sliver identity failed round trip",
        )

    return {
        "historical_identity_count":
            len(
                historical
            ),
        "canonical_sliver_count":
            len(
                slivers
            ),
        "historical_resolution":
            True,
        "canonical_resolution":
            True,
    }


def verify_migration_projection() -> dict[str, Any]:
    result = migration_projection()

    coverage = result.get(
        "coverage",
        {},
    )

    require(
        result.get(
            "source_piece_count"
        )
        == 81,
        "migration source baseline changed",
    )

    require(
        coverage.get(
            "mapped_piece_count"
        )
        == 81,
        "not every historical piece is mapped",
    )

    require(
        coverage.get(
            "unmapped_piece_count"
        )
        == 0,
        "unmapped historical pieces remain",
    )

    require(
        coverage.get(
            "recipes_within_alloy_limit"
        )
        is True,
        "an Alloy recipe exceeds nine Slivers",
    )

    require(
        result.get(
            "fixed_target_cardinality"
        )
        is False,
        "obsolete fixed cardinality restored",
    )

    compatibility = result.get(
        "compatibility",
        {},
    )

    require(
        compatibility.get(
            "historical_piece_registry_preserved"
        )
        is True,
        "historical registry preservation not established",
    )

    require(
        compatibility.get(
            "historical_recipe_registry_preserved"
        )
        is True,
        "historical recipe preservation not established",
    )

    require(
        compatibility.get(
            "destructive_migration"
        )
        is False,
        "migration projection is destructive",
    )

    return {
        "mapped_piece_count":
            coverage.get(
                "mapped_piece_count"
            ),
        "recipe_count":
            coverage.get(
                "recipes_projected"
            ),
        "migration_digest":
            result.get(
                "digest"
            ),
        "fixed_target_cardinality":
            False,
    }


def verify_v2_surface() -> dict[str, Any]:
    instance = v2_runtime()

    status = instance.dispatch(
        "status",
        {},
    )

    require(
        status.get(
            "ok"
        )
        is True,
        "Coalesce v2 status failed",
    )

    require(
        status.get(
            "historical_identity_compatibility"
        )
        is True,
        "v2 historical identity compatibility absent",
    )

    require(
        status.get(
            "canonical_sliver_identity"
        )
        is True,
        "v2 canonical Sliver identity absent",
    )

    require(
        status.get(
            "legacy_runtime_preserved"
        )
        is True,
        "legacy runtime preservation absent",
    )

    require(
        status.get(
            "maximum_slivers_per_alloy"
        )
        == 9,
        "v2 Alloy Sliver limit changed",
    )

    resolved = instance.dispatch(
        "resolve",
        {
            "identity":
                "slab:coalesce:temporal:date-normalizer",
        },
    )

    require(
        resolved.get(
            "ok"
        )
        is True,
        "v2 historical identity resolution failed",
    )

    canonical = (
        resolved.get(
            "result",
            {},
        ).get(
            "canonical_identity"
        )
    )

    require(
        canonical
        == "sliver:coalesce:temporal",
        "unexpected canonical temporal Sliver identity",
    )

    return {
        "runtime_schema":
            status.get(
                "schema"
            ),
        "historical_identity_compatibility":
            True,
        "legacy_runtime_preserved":
            True,
        "sample_resolution":
            canonical,
    }


def verify_filament_boundary() -> dict[str, Any]:
    module = load_filament_projector()

    derive = getattr(
        module,
        "derive_coalesce_view",
        None,
    )

    require(
        callable(
            derive
        ),
        "Filament Coalesce projection callable missing",
    )

    result = derive(
        "chronology-explorer",
        {},
    )

    require(
        isinstance(
            result,
            dict,
        ),
        "Filament Coalesce projection returned non-object",
    )

    require(
        result.get(
            "owner"
        )
        == "exile:filament",
        "Filament ownership changed",
    )

    require(
        result.get(
            "source"
        )
        == OWNER,
        "Coalesce source identity changed",
    )

    require(
        result.get(
            "recipe"
        )
        == "chronology-explorer",
        "chronology-explorer recipe identity changed",
    )

    require(
        isinstance(
            result.get(
                "records"
            ),
            list,
        ),
        "Filament records projection missing",
    )

    require(
        isinstance(
            result.get(
                "trace"
            ),
            list,
        ),
        "Filament execution trace missing",
    )

    composition = result.get(
        "composition",
        {},
    )

    require(
        isinstance(
            composition,
            dict,
        ),
        "Filament composition projection missing",
    )

    require(
        bool(
            composition.get(
                "digest"
            )
        ),
        "Filament composition digest missing",
    )

    return {
        "owner":
            result.get(
                "owner"
            ),
        "source":
            result.get(
                "source"
            ),
        "recipe":
            result.get(
                "recipe"
            ),
        "record_count":
            len(
                result.get(
                    "records",
                    [],
                )
            ),
        "executed_piece_count":
            len(
                result.get(
                    "trace",
                    [],
                )
            ),
        "composition_digest":
            composition.get(
                "digest"
            ),
    }


def verify() -> dict[str, Any]:
    identity = (
        verify_identity_surface()
    )

    migration = (
        verify_migration_projection()
    )

    runtime = (
        verify_v2_surface()
    )

    filament = (
        verify_filament_boundary()
    )

    return {
        "ok":
            True,
        "schema":
            SCHEMA,
        "owner":
            OWNER,
        "identity":
            identity,
        "migration":
            migration,
        "runtime":
            runtime,
        "filament":
            filament,
        "completion": {
            "identity_migration":
                "verified",
            "historical_81_piece_registry":
                "preserved",
            "canonical_target":
                "extensible-sliver-pool",
            "fixed_27_piece_target":
                "superseded",
            "alloy_sliver_limit":
                9,
            "filament_compatibility":
                "verified",
            "destructive_migration":
                False,
        },
        "authority_effect":
            "none",
    }


def main() -> int:
    print(
        json.dumps(
            verify(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

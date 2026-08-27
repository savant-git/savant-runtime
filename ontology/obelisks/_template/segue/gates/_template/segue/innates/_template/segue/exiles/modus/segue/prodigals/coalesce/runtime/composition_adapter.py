#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable


COALESCE_ROOT = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/modus/segue/"
    "prodigals/coalesce"
).resolve()

RUNTIME_ROOT = (
    COALESCE_ROOT
    / "runtime"
)

LEGACY_RUNTIME = (
    RUNTIME_ROOT
    / "coalesce.py"
)

for value in (
    str(RUNTIME_ROOT),
):
    if value not in sys.path:
        sys.path.insert(
            0,
            value,
        )


from alloy_assembler import (
    AlloyAssembler,
    AlloyAssemblerError,
    assembler,
)
from capability_compiler import (
    CapabilityCompiler,
    CapabilityCompilerError,
    compiler,
)
from sliver_pool import (
    SliverPool,
    SliverPoolError,
    build_pool,
)


OWNER = "prodigal:modus:coalesce"

SCHEMA = (
    "savant://coalesce/"
    "composition-adapter/1"
)

LEGACY_MODULE_NAME = (
    "savant_coalesce_legacy_runtime"
)


class CompositionAdapterError(
    RuntimeError
):
    pass


def load_legacy_runtime() -> ModuleType | None:
    if not LEGACY_RUNTIME.is_file():
        return None

    existing = sys.modules.get(
        LEGACY_MODULE_NAME
    )

    if existing is not None:
        return existing

    spec = (
        importlib.util
        .spec_from_file_location(
            LEGACY_MODULE_NAME,
            LEGACY_RUNTIME,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise CompositionAdapterError(
            "unable to load existing "
            "Coalesce runtime"
        )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    sys.modules[
        LEGACY_MODULE_NAME
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


class CompositionAdapter:
    def __init__(
        self,
        *,
        pool: SliverPool | None = None,
        capability_compiler: (
            CapabilityCompiler
            | None
        ) = None,
        alloy_assembler: (
            AlloyAssembler
            | None
        ) = None,
    ) -> None:
        self.pool = (
            pool
            or build_pool()
        )

        self.compiler = (
            capability_compiler
            or compiler()
        )

        self.assembler = (
            alloy_assembler
            or assembler()
        )

        self.legacy = (
            load_legacy_runtime()
        )

    def list_slivers(
        self,
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "owner": OWNER,
            "schema": (
                "savant://coalesce/"
                "sliver-discovery/1"
            ),
            "slivers": [
                sliver.projection()
                for sliver
                in self.pool.slivers
            ],
            "count": len(
                self.pool.slivers
            ),
            "authoritative": False,
            "rebuildable": True,
            "authority_effect": "none",
        }

    def plan(
        self,
        *,
        alloy_id: str,
        capabilities: Iterable[Any],
    ) -> dict[str, Any]:
        try:
            result = (
                self.compiler
                .compile_requirements(
                    alloy_id=alloy_id,
                    capabilities=capabilities,
                )
            )
        except (
            CapabilityCompilerError,
            SliverPoolError,
        ) as exc:
            raise CompositionAdapterError(
                str(exc)
            ) from exc

        return result.projection()

    def plan_recipe(
        self,
        application_id: str,
    ) -> dict[str, Any]:
        try:
            result = (
                self.compiler
                .compile_recipe(
                    application_id
                )
            )
        except (
            CapabilityCompilerError,
            SliverPoolError,
        ) as exc:
            raise CompositionAdapterError(
                str(exc)
            ) from exc

        return result.projection()

    def assemble(
        self,
        *,
        alloy_id: str,
        capabilities: Iterable[Any],
        configuration: (
            dict[str, Any]
            | None
        ) = None,
        authorized_interfaces: (
            dict[
                str,
                Iterable[str],
            ]
            | None
        ) = None,
        segues: (
            Iterable[
                dict[str, Any]
            ]
            | None
        ) = None,
    ) -> dict[str, Any]:
        try:
            plan = (
                self.compiler
                .compile_requirements(
                    alloy_id=alloy_id,
                    capabilities=capabilities,
                )
            )

            return (
                self.assembler
                .assemble(
                    plan,
                    configuration=configuration,
                    authorized_interfaces=(
                        authorized_interfaces
                    ),
                    segues=segues,
                )
            )

        except (
            CapabilityCompilerError,
            AlloyAssemblerError,
            SliverPoolError,
        ) as exc:
            raise CompositionAdapterError(
                str(exc)
            ) from exc

    def assemble_recipe(
        self,
        application_id: str,
        *,
        configuration: (
            dict[str, Any]
            | None
        ) = None,
        authorized_interfaces: (
            dict[
                str,
                Iterable[str],
            ]
            | None
        ) = None,
        segues: (
            Iterable[
                dict[str, Any]
            ]
            | None
        ) = None,
    ) -> dict[str, Any]:
        try:
            return (
                self.assembler
                .assemble_recipe(
                    application_id,
                    configuration=configuration,
                    authorized_interfaces=(
                        authorized_interfaces
                    ),
                    segues=segues,
                )
            )

        except (
            CapabilityCompilerError,
            AlloyAssemblerError,
            SliverPoolError,
        ) as exc:
            raise CompositionAdapterError(
                str(exc)
            ) from exc

    def legacy_surface(
        self,
    ) -> dict[str, Any]:
        if self.legacy is None:
            return {
                "available": False,
                "path": str(
                    LEGACY_RUNTIME
                ),
                "callables": [],
            }

        callables = tuple(
            sorted(
                name
                for name in dir(
                    self.legacy
                )
                if (
                    not name.startswith(
                        "_"
                    )
                    and callable(
                        getattr(
                            self.legacy,
                            name,
                            None,
                        )
                    )
                )
            )
        )

        return {
            "available": True,
            "path": str(
                LEGACY_RUNTIME
            ),
            "callables": list(
                callables
            ),
        }

    def status(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "owner": OWNER,
            "legacy": (
                self.legacy_surface()
            ),
            "sliver_pool": (
                self.pool
                .projection()
            ),
            "compiler": (
                self.compiler
                .status()
            ),
            "assembler": (
                self.assembler
                .status()
            ),
            "compatibility_preserved": (
                True
            ),
            "legacy_replaced": False,
            "reference_composition": (
                True
            ),
            "minimum_sufficient": True,
            "alloy_sliver_range": [
                1,
                9,
            ],
            "exile_embedding": False,
            "authoritative": False,
            "authority_effect": "none",
        }


def adapter() -> CompositionAdapter:
    return CompositionAdapter()


def main() -> int:
    instance = adapter()

    print(
        json.dumps(
            instance.status(),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

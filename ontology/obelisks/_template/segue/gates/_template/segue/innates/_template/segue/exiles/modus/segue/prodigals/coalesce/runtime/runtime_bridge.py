#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


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

V2_RUNTIME = (
    RUNTIME_ROOT
    / "coalesce_v2.py"
)

LEGACY_MODULE_NAME = (
    "savant_coalesce_runtime_legacy"
)

V2_MODULE_NAME = (
    "savant_coalesce_runtime_v2"
)


class RuntimeBridgeError(
    RuntimeError
):
    pass


def load_module(
    *,
    name: str,
    path: Path,
) -> ModuleType:
    existing = sys.modules.get(
        name
    )

    if existing is not None:
        return existing

    if not path.is_file():
        raise RuntimeBridgeError(
            f"missing runtime: {path}"
        )

    if str(
        path.parent
    ) not in sys.path:
        sys.path.insert(
            0,
            str(
                path.parent
            ),
        )

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
        raise RuntimeBridgeError(
            f"unable to load runtime: {path}"
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


def legacy_runtime() -> ModuleType:
    return load_module(
        name=LEGACY_MODULE_NAME,
        path=LEGACY_RUNTIME,
    )


def v2_runtime() -> ModuleType:
    return load_module(
        name=V2_MODULE_NAME,
        path=V2_RUNTIME,
    )


def legacy_callables() -> tuple[str, ...]:
    module = legacy_runtime()

    return tuple(
        sorted(
            name
            for name in dir(
                module
            )
            if (
                not name.startswith(
                    "_"
                )
                and callable(
                    getattr(
                        module,
                        name,
                        None,
                    )
                )
            )
        )
    )


def v2_dispatch(
    operation: str,
    payload: (
        dict[str, Any]
        | None
    ) = None,
) -> dict[str, Any]:
    module = v2_runtime()

    factory = getattr(
        module,
        "runtime",
        None,
    )

    if not callable(
        factory
    ):
        raise RuntimeBridgeError(
            "Coalesce v2 runtime factory "
            "is unavailable"
        )

    instance = factory()

    dispatch = getattr(
        instance,
        "dispatch",
        None,
    )

    if not callable(
        dispatch
    ):
        raise RuntimeBridgeError(
            "Coalesce v2 dispatch "
            "is unavailable"
        )

    result = dispatch(
        operation,
        payload
        or {},
    )

    if not isinstance(
        result,
        dict,
    ):
        raise RuntimeBridgeError(
            "Coalesce v2 returned "
            "a non-object result"
        )

    return result


def status() -> dict[str, Any]:
    v2 = v2_dispatch(
        "status"
    )

    return {
        "schema": (
            "savant://coalesce/"
            "runtime-bridge/1"
        ),
        "owner": (
            "prodigal:modus:coalesce"
        ),
        "legacy_runtime": str(
            LEGACY_RUNTIME
        ),
        "v2_runtime": str(
            V2_RUNTIME
        ),
        "legacy_preserved": True,
        "legacy_callables": list(
            legacy_callables()
        ),
        "v2_available": bool(
            v2.get(
                "ok",
                True,
            )
        ),
        "replacement_performed": False,
        "composition_extension": True,
        "authoritative": False,
        "authority_effect": "none",
    }


def main() -> int:
    print(
        json.dumps(
            status(),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

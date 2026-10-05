#!/usr/bin/env python3

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


schema = (
    "savant://runtime/envoy/"
    "package-compat/1.0.0"
)

owner = "exile:envoy"

runtime_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/envoy/runtime"
)

package_name = "savant_envoy_runtime"


class envoy_package_compat_error(
    RuntimeError
):
    pass


def _ensure_package() -> ModuleType:
    existing = sys.modules.get(
        package_name
    )

    if existing is not None:
        package_path = list(
            getattr(
                existing,
                "__path__",
                [],
            )
        )

        if str(runtime_root) not in package_path:
            package_path.append(
                str(runtime_root)
            )

            existing.__path__ = (
                package_path
            )

        return existing

    package = ModuleType(
        package_name
    )

    package.__package__ = (
        package_name
    )

    package.__path__ = [
        str(runtime_root)
    ]

    sys.modules[
        package_name
    ] = package

    return package


def package_module(
    name: str,
) -> ModuleType:
    normalized = str(
        name
        or ""
    ).strip()

    if not normalized:
        raise envoy_package_compat_error(
            "module name is required"
        )

    _ensure_package()

    qualified = (
        f"{package_name}.{normalized}"
    )

    return importlib.import_module(
        qualified
    )


def alias(
    bare_name: str,
    package_name_value: str | None = None,
) -> ModuleType:
    normalized_bare = str(
        bare_name
        or ""
    ).strip()

    normalized_package = str(
        package_name_value
        or normalized_bare
    ).strip()

    if not normalized_bare:
        raise envoy_package_compat_error(
            "bare module name is required"
        )

    module = package_module(
        normalized_package
    )

    sys.modules[
        normalized_bare
    ] = module

    return module


def install() -> dict[str, Any]:
    _ensure_package()

    canonical = package_module(
        "canonical_primitives"
    )

    sys.modules[
        "canonical_primitives"
    ] = canonical

    moral = alias(
        "moral_self"
    )

    persona = alias(
        "persona_engine"
    )

    try:
        opus = package_module(
            "opus_bridge"
        )

        sys.modules[
            "opus_bridge"
        ] = opus
    except Exception:
        opus = None

    try:
        psychologist = alias(
            "psychologist"
        )
    except Exception:
        psychologist = None

    try:
        voice = alias(
            "voice_engine"
        )
    except Exception:
        voice = None

    return {
        "schema":
            schema,
        "owner":
            owner,
        "package_name":
            package_name,
        "runtime_root":
            str(runtime_root),
        "canonical_primitives":
            canonical.__name__,
        "moral_self":
            moral.__name__,
        "persona_engine":
            persona.__name__,
        "opus_bridge":
            (
                opus.__name__
                if opus is not None
                else None
            ),
        "psychologist":
            (
                psychologist.__name__
                if psychologist is not None
                else None
            ),
        "voice_engine":
            (
                voice.__name__
                if voice is not None
                else None
            ),
        "source_modified":
            False,
        "authority_effect":
            "none",
    }


def status() -> dict[str, Any]:
    return {
        "schema":
            schema,
        "owner":
            owner,
        "package_name":
            package_name,
        "runtime_root":
            str(runtime_root),
        "installed":
            package_name
            in sys.modules,
        "persona_engine_alias":
            "persona_engine"
            in sys.modules,
        "moral_self_alias":
            "moral_self"
            in sys.modules,
        "canonical_primitives_alias":
            "canonical_primitives"
            in sys.modules,
        "authority_effect":
            "none",
    }


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            install(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=str,
        )
    )

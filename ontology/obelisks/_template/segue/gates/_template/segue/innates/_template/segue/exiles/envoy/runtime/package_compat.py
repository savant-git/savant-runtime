#!/usr/bin/env python3

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


schema = (
    "savant://runtime/envoy/"
    "package-compat/1.0.1"
)

owner = "exile:envoy"

savant_root = Path(
    "/root/savant-runtime"
)

envoy_runtime_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/envoy/runtime"
)

opus_runtime_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/opus/runtime"
)

envoy_package_name = (
    "savant_envoy_runtime"
)

opus_package_name = (
    "savant_opus_runtime"
)


class envoy_package_compat_error(
    RuntimeError
):
    pass


def _ensure_package(
    *,
    package_name: str,
    runtime_root: Path,
) -> ModuleType:
    existing = sys.modules.get(
        package_name
    )

    runtime_value = str(
        runtime_root
    )

    if existing is not None:
        paths = list(
            getattr(
                existing,
                "__path__",
                [],
            )
        )

        if runtime_value not in paths:
            paths.append(
                runtime_value
            )

            existing.__path__ = (
                paths
            )

        return existing

    package = ModuleType(
        package_name
    )

    package.__package__ = (
        package_name
    )

    package.__path__ = [
        runtime_value
    ]

    sys.modules[
        package_name
    ] = package

    return package


def _ensure_envoy_package() -> ModuleType:
    return _ensure_package(
        package_name=
            envoy_package_name,
        runtime_root=
            envoy_runtime_root,
    )


def _ensure_opus_package() -> ModuleType:
    return _ensure_package(
        package_name=
            opus_package_name,
        runtime_root=
            opus_runtime_root,
    )


def _package_module(
    *,
    package_name: str,
    runtime_root: Path,
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

    _ensure_package(
        package_name=
            package_name,
        runtime_root=
            runtime_root,
    )

    qualified = (
        f"{package_name}.{normalized}"
    )

    return importlib.import_module(
        qualified
    )


def envoy_module(
    name: str,
) -> ModuleType:
    return _package_module(
        package_name=
            envoy_package_name,
        runtime_root=
            envoy_runtime_root,
        name=
            name,
    )


def opus_module(
    name: str,
) -> ModuleType:
    return _package_module(
        package_name=
            opus_package_name,
        runtime_root=
            opus_runtime_root,
        name=
            name,
    )


def envoy_alias(
    bare_name: str,
    package_module_name: str | None = None,
) -> ModuleType:
    normalized_bare = str(
        bare_name
        or ""
    ).strip()

    normalized_package = str(
        package_module_name
        or normalized_bare
    ).strip()

    if not normalized_bare:
        raise envoy_package_compat_error(
            "bare Envoy module name is required"
        )

    module = envoy_module(
        normalized_package
    )

    sys.modules[
        normalized_bare
    ] = module

    return module


def opus_alias(
    bare_name: str,
    package_module_name: str | None = None,
) -> ModuleType:
    normalized_bare = str(
        bare_name
        or ""
    ).strip()

    normalized_package = str(
        package_module_name
        or normalized_bare
    ).strip()

    if not normalized_bare:
        raise envoy_package_compat_error(
            "bare Opus module name is required"
        )

    module = opus_module(
        normalized_package
    )

    sys.modules[
        normalized_bare
    ] = module

    return module


def _install_opus_compatibility() -> dict[str, Any]:
    _ensure_opus_package()

    router = opus_alias(
        "router"
    )

    loaded: dict[
        str,
        str | None,
    ] = {
        "router":
            router.__name__,
    }

    for name in (
        "environment",
        "voice_orchestrator",
    ):
        try:
            module = opus_module(
                name
            )

            loaded[
                name
            ] = module.__name__

            if name not in sys.modules:
                sys.modules[
                    name
                ] = module

        except Exception:
            loaded[
                name
            ] = None

    return {
        "package":
            opus_package_name,
        "runtime_root":
            str(
                opus_runtime_root
            ),
        "modules":
            loaded,
        "provider_owner":
            "opus",
        "source_modified":
            False,
        "authority_effect":
            "none",
    }


def install() -> dict[str, Any]:
    _ensure_envoy_package()

    opus_compatibility = (
        _install_opus_compatibility()
    )

    canonical = envoy_module(
        "canonical_primitives"
    )

    sys.modules[
        "canonical_primitives"
    ] = canonical

    moral = envoy_alias(
        "moral_self"
    )

    persona = envoy_alias(
        "persona_engine"
    )

    opus_bridge = envoy_alias(
        "opus_bridge"
    )

    psychologist = envoy_alias(
        "psychologist"
    )

    voice = envoy_alias(
        "voice_engine"
    )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "envoy_package_name":
            envoy_package_name,
        "envoy_runtime_root":
            str(
                envoy_runtime_root
            ),
        "opus_compatibility":
            opus_compatibility,
        "canonical_primitives":
            canonical.__name__,
        "moral_self":
            moral.__name__,
        "persona_engine":
            persona.__name__,
        "opus_bridge":
            opus_bridge.__name__,
        "psychologist":
            psychologist.__name__,
        "voice_engine":
            voice.__name__,
        "historical_bare_imports":
            True,
        "package_relative_imports":
            True,
        "provider_owner":
            "opus",
        "persona_owner":
            "envoy",
        "provider_execution_reimplemented":
            False,
        "opus_source_modified":
            False,
        "envoy_source_modified":
            False,
        "creates_authority":
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
        "envoy_package_name":
            envoy_package_name,
        "opus_package_name":
            opus_package_name,
        "envoy_runtime_root":
            str(
                envoy_runtime_root
            ),
        "opus_runtime_root":
            str(
                opus_runtime_root
            ),
        "envoy_package_installed":
            envoy_package_name
            in sys.modules,
        "opus_package_installed":
            opus_package_name
            in sys.modules,
        "router_alias":
            "router"
            in sys.modules,
        "persona_engine_alias":
            "persona_engine"
            in sys.modules,
        "moral_self_alias":
            "moral_self"
            in sys.modules,
        "opus_bridge_alias":
            "opus_bridge"
            in sys.modules,
        "psychologist_alias":
            "psychologist"
            in sys.modules,
        "voice_engine_alias":
            "voice_engine"
            in sys.modules,
        "canonical_primitives_alias":
            "canonical_primitives"
            in sys.modules,
        "provider_owner":
            "opus",
        "persona_owner":
            "envoy",
        "authority_effect":
            "none",
    }


def selftest() -> dict[str, Any]:
    projection = install()

    if (
        projection[
            "provider_owner"
        ]
        != "opus"
    ):
        raise envoy_package_compat_error(
            "Opus ownership boundary failed"
        )

    if (
        projection[
            "persona_owner"
        ]
        != "envoy"
    ):
        raise envoy_package_compat_error(
            "Envoy ownership boundary failed"
        )

    required = (
        "router",
        "moral_self",
        "persona_engine",
        "opus_bridge",
        "psychologist",
        "voice_engine",
        "canonical_primitives",
    )

    missing = [
        name
        for name in required
        if name not in sys.modules
    ]

    if missing:
        raise envoy_package_compat_error(
            "compatibility aliases missing: "
            + ", ".join(
                missing
            )
        )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "ok":
            True,
        "aliases":
            list(
                required
            ),
        "provider_owner":
            "opus",
        "persona_owner":
            "envoy",
        "authority_effect":
            "none",
    }


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=str,
        )
    )

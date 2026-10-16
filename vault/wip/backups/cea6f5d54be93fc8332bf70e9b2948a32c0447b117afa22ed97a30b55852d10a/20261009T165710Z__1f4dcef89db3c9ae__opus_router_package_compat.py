#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any


schema = (
    "savant://runtime/palaver/"
    "opus-runtime-package-compat/1.1.0"
)

owner = "exile:palaver"
compatibility_target = "exile:opus"
authority_effect = "none"


opus_runtime = Path(
    "/root/savant-runtime/ontology/obelisks/"
    "_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/opus/runtime"
)

package_name = "savant_opus_runtime"

legacy_modules = (
    "router",
    "voice_orchestrator",
)


class opus_runtime_package_compat_error(
    RuntimeError
):
    pass


def _ensure_package() -> ModuleType:
    existing = sys.modules.get(
        package_name
    )

    if existing is not None:
        return existing

    if not opus_runtime.is_dir():
        raise opus_runtime_package_compat_error(
            "Opus runtime directory is missing"
        )

    package = ModuleType(
        package_name
    )

    package.__package__ = package_name
    package.__path__ = [
        str(
            opus_runtime
        )
    ]
    package.__file__ = str(
        opus_runtime
    )

    sys.modules[
        package_name
    ] = package

    return package


def _qualified_name(
    bare_name: str,
) -> str:
    return (
        f"{package_name}.{bare_name}"
    )


def _module_path(
    bare_name: str,
) -> Path:
    return (
        opus_runtime
        / f"{bare_name}.py"
    )


def _load_package_module(
    bare_name: str,
) -> ModuleType:
    qualified_name = (
        _qualified_name(
            bare_name
        )
    )

    existing = sys.modules.get(
        qualified_name
    )

    if existing is not None:
        return existing

    _ensure_package()

    path = _module_path(
        bare_name
    )

    if not path.is_file():
        raise opus_runtime_package_compat_error(
            "required Opus runtime module "
            f"is missing: {path}"
        )

    specification = (
        importlib.util.spec_from_file_location(
            qualified_name,
            path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise opus_runtime_package_compat_error(
            "unable to construct "
            f"Opus import for {bare_name}"
        )

    module = (
        importlib.util.module_from_spec(
            specification
        )
    )

    module.__package__ = package_name

    sys.modules[
        qualified_name
    ] = module

    try:
        specification.loader.exec_module(
            module
        )

    except Exception:
        sys.modules.pop(
            qualified_name,
            None,
        )
        raise

    return module


def _bind_legacy_name(
    bare_name: str,
) -> ModuleType:
    module = _load_package_module(
        bare_name
    )

    sys.modules[
        bare_name
    ] = module

    return module


def install() -> dict[str, Any]:
    bound: dict[
        str,
        str,
    ] = {}

    for bare_name in legacy_modules:
        module = _bind_legacy_name(
            bare_name
        )

        bound[
            bare_name
        ] = getattr(
            module,
            "__name__",
            "",
        )

    router = sys.modules.get(
        "router"
    )

    if not callable(
        getattr(
            router,
            "execute_text_request",
            None,
        )
    ):
        raise opus_runtime_package_compat_error(
            "Opus router does not expose "
            "execute_text_request"
        )

    voice = sys.modules.get(
        "voice_orchestrator"
    )

    if not callable(
        getattr(
            voice,
            "synthesize",
            None,
        )
    ):
        raise opus_runtime_package_compat_error(
            "Opus voice_orchestrator does "
            "not expose synthesize"
        )

    return {
        "schema":
            schema,
        "installed":
            True,
        "owner":
            owner,
        "compatibility_target":
            compatibility_target,
        "package":
            package_name,
        "opus_runtime":
            str(
                opus_runtime
            ),
        "legacy_modules":
            list(
                legacy_modules
            ),
        "bindings":
            bound,
        "authority_effect":
            authority_effect,
    }


def status() -> dict[str, Any]:
    bindings: dict[
        str,
        dict[str, Any],
    ] = {}

    installed = True

    for bare_name in legacy_modules:
        qualified_name = (
            _qualified_name(
                bare_name
            )
        )

        bare = sys.modules.get(
            bare_name
        )

        qualified = sys.modules.get(
            qualified_name
        )

        valid = (
            bare is not None
            and qualified is not None
            and bare is qualified
            and getattr(
                bare,
                "__package__",
                "",
            )
            == package_name
        )

        installed = (
            installed
            and valid
        )

        bindings[
            bare_name
        ] = {
            "qualified_name":
                qualified_name,
            "installed":
                valid,
            "package":
                (
                    getattr(
                        bare,
                        "__package__",
                        None,
                    )
                    if bare is not None
                    else None
                ),
        }

    return {
        "schema":
            schema,
        "installed":
            installed,
        "owner":
            owner,
        "compatibility_target":
            compatibility_target,
        "package":
            package_name,
        "bindings":
            bindings,
        "authority_effect":
            authority_effect,
    }


def selftest() -> dict[str, Any]:
    result = install()

    if not result.get(
        "installed"
    ):
        raise opus_runtime_package_compat_error(
            "Opus runtime package "
            "compatibility installation failed"
        )

    state = status()

    if not state.get(
        "installed"
    ):
        raise opus_runtime_package_compat_error(
            "Opus runtime package "
            "compatibility status failed"
        )

    router = sys.modules[
        "router"
    ]

    voice = sys.modules[
        "voice_orchestrator"
    ]

    if not callable(
        getattr(
            router,
            "execute_text_request",
            None,
        )
    ):
        raise opus_runtime_package_compat_error(
            "router execution contract missing"
        )

    if not callable(
        getattr(
            voice,
            "synthesize",
            None,
        )
    ):
        raise opus_runtime_package_compat_error(
            "voice synthesis contract missing"
        )

    return {
        **state,
        "ok":
            True,
        "router_execution_contract":
            True,
        "voice_synthesis_contract":
            True,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )

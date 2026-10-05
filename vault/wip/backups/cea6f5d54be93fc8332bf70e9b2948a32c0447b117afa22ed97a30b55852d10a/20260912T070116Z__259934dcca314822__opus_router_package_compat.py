#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType


schema = (
    "savant://runtime/palaver/"
    "opus-router-package-compat/1.0.0"
)

owner = "exile:palaver"
compatibility_target = "exile:opus"
authority_effect = "none"


opus_runtime = Path(
    "/root/savant-runtime/ontology/obelisks/"
    "_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/opus/runtime"
)

package_name = (
    "savant_opus_runtime"
)

router_qualified_name = (
    package_name
    + ".router"
)

legacy_router_name = "router"


class opus_router_package_compat_error(
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
        raise opus_router_package_compat_error(
            "Opus runtime directory is missing"
        )

    package = ModuleType(
        package_name
    )

    package.__package__ = (
        package_name
    )

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


def _load_router() -> ModuleType:
    existing = sys.modules.get(
        router_qualified_name
    )

    if existing is not None:
        return existing

    _ensure_package()

    path = (
        opus_runtime
        / "router.py"
    )

    if not path.is_file():
        raise opus_router_package_compat_error(
            "Opus router.py is missing"
        )

    specification = (
        importlib.util.spec_from_file_location(
            router_qualified_name,
            path,
            submodule_search_locations=None,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise opus_router_package_compat_error(
            "unable to construct Opus router import"
        )

    module = (
        importlib.util.module_from_spec(
            specification
        )
    )

    module.__package__ = (
        package_name
    )

    sys.modules[
        router_qualified_name
    ] = module

    try:
        specification.loader.exec_module(
            module
        )

    except Exception:
        sys.modules.pop(
            router_qualified_name,
            None,
        )
        raise

    return module


def install() -> dict[str, object]:
    current = sys.modules.get(
        legacy_router_name
    )

    if (
        current is not None
        and getattr(
            current,
            "__name__",
            "",
        )
        == router_qualified_name
    ):
        return status()

    router = _load_router()

    execute = getattr(
        router,
        "execute_text_request",
        None,
    )

    if not callable(
        execute
    ):
        raise opus_router_package_compat_error(
            "Opus router does not expose "
            "execute_text_request"
        )

    sys.modules[
        legacy_router_name
    ] = router

    return status()


def status() -> dict[str, object]:
    router = sys.modules.get(
        legacy_router_name
    )

    qualified = sys.modules.get(
        router_qualified_name
    )

    installed = (
        router is not None
        and router is qualified
        and getattr(
            router,
            "__package__",
            "",
        )
        == package_name
        and callable(
            getattr(
                router,
                "execute_text_request",
                None,
            )
        )
    )

    return {
        "schema":
            schema,
        "installed":
            installed,
        "owner":
            owner,
        "compatibility_target":
            compatibility_target,
        "legacy_import_name":
            legacy_router_name,
        "qualified_module":
            router_qualified_name,
        "package":
            package_name,
        "opus_runtime":
            str(
                opus_runtime
            ),
        "authority_effect":
            authority_effect,
    }


def selftest() -> dict[str, object]:
    result = install()

    if not result.get(
        "installed"
    ):
        raise opus_router_package_compat_error(
            "Opus router compatibility "
            "installation failed"
        )

    router = sys.modules.get(
        legacy_router_name
    )

    if router is None:
        raise opus_router_package_compat_error(
            "legacy router alias missing"
        )

    if (
        getattr(
            router,
            "__package__",
            "",
        )
        != package_name
    ):
        raise opus_router_package_compat_error(
            "Opus router package context "
            "is incorrect"
        )

    return {
        **result,
        "ok":
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

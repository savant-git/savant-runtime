#!/usr/bin/env python3

from __future__ import annotations

import importlib.abc
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any


schema = (
    "savant://runtime/palaver/"
    "envoy-runtime-package-compat/1.2.0"
)

owner = "exile:palaver"
compatibility_target = "exile:envoy"
authority_effect = "none"

palaver_runtime = Path(
    "/root/savant-runtime/ontology/obelisks/"
    "_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/palaver/runtime"
)

envoy_runtime = Path(
    "/root/savant-runtime/ontology/obelisks/"
    "_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/envoy/runtime"
)

opus_compat_path = (
    palaver_runtime
    / "opus_router_package_compat.py"
)

package_name = "savant_envoy_runtime"

persona_synthetic_name = (
    "savant_envoy_persona_engine"
)

psychologist_synthetic_name = (
    "savant_envoy_psychologist"
)


class envoy_runtime_package_compat_error(
    RuntimeError
):
    pass


def _ensure_package() -> ModuleType:
    existing = sys.modules.get(
        package_name
    )

    if existing is not None:
        return existing

    if not envoy_runtime.is_dir():
        raise envoy_runtime_package_compat_error(
            "Envoy runtime directory missing"
        )

    package = ModuleType(
        package_name
    )

    package.__package__ = package_name
    package.__path__ = [
        str(envoy_runtime)
    ]
    package.__file__ = str(
        envoy_runtime
    )

    sys.modules[
        package_name
    ] = package

    return package


def _load_external_module(
    name: str,
    path: Path,
) -> ModuleType:
    existing = sys.modules.get(
        name
    )

    if existing is not None:
        return existing

    if not path.is_file():
        raise envoy_runtime_package_compat_error(
            f"required compatibility module missing: {path}"
        )

    spec = (
        importlib.util.spec_from_file_location(
            name,
            path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise envoy_runtime_package_compat_error(
            f"unable to construct import: {path}"
        )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    sys.modules[
        name
    ] = module

    try:
        spec.loader.exec_module(
            module
        )
    except Exception:
        if sys.modules.get(
            name
        ) is module:
            sys.modules.pop(
                name,
                None,
            )
        raise

    return module


def _ensure_opus_package_compat() -> None:
    compat = _load_external_module(
        "savant_palaver_opus_runtime_package_compat",
        opus_compat_path,
    )

    install = getattr(
        compat,
        "install",
        None,
    )

    if not callable(
        install
    ):
        raise envoy_runtime_package_compat_error(
            "Opus compatibility installer unavailable"
        )

    status = install()

    if not status.get(
        "installed"
    ):
        raise envoy_runtime_package_compat_error(
            "Opus package compatibility installation failed"
        )


def _package_module(
    bare_name: str,
) -> ModuleType:
    _ensure_package()

    qualified_name = (
        f"{package_name}.{bare_name}"
    )

    existing = sys.modules.get(
        qualified_name
    )

    if existing is not None:
        return existing

    path = (
        envoy_runtime
        / f"{bare_name}.py"
    )

    if not path.is_file():
        raise envoy_runtime_package_compat_error(
            f"Envoy runtime module missing: {path}"
        )

    spec = (
        importlib.util.spec_from_file_location(
            qualified_name,
            path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise envoy_runtime_package_compat_error(
            f"unable to construct Envoy package import: {path}"
        )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    module.__package__ = package_name

    sys.modules[
        qualified_name
    ] = module

    try:
        spec.loader.exec_module(
            module
        )
    except Exception:
        if sys.modules.get(
            qualified_name
        ) is module:
            sys.modules.pop(
                qualified_name,
                None,
            )
        raise

    return module


class _envoy_bare_loader(
    importlib.abc.Loader
):
    def __init__(
        self,
        bare_name: str,
    ) -> None:
        self.bare_name = bare_name

    def create_module(
        self,
        spec,
    ):
        qualified_name = (
            f"{package_name}."
            f"{self.bare_name}"
        )

        return sys.modules.get(
            qualified_name
        )

    def exec_module(
        self,
        module: ModuleType,
    ) -> None:
        qualified_name = (
            f"{package_name}."
            f"{self.bare_name}"
        )

        existing = sys.modules.get(
            qualified_name
        )

        if existing is module:
            sys.modules[
                self.bare_name
            ] = module
            return

        loaded = _package_module(
            self.bare_name
        )

        sys.modules[
            self.bare_name
        ] = loaded


class _envoy_bare_finder(
    importlib.abc.MetaPathFinder
):
    marker = (
        "savant_envoy_runtime_"
        "package_compat_finder"
    )

    def find_spec(
        self,
        fullname: str,
        path=None,
        target=None,
    ):
        if "." in fullname:
            return None

        candidate = (
            envoy_runtime
            / f"{fullname}.py"
        )

        if not candidate.is_file():
            return None

        return importlib.util.spec_from_loader(
            fullname,
            _envoy_bare_loader(
                fullname
            ),
            origin=str(
                candidate
            ),
        )


def _finder_installed() -> bool:
    return any(
        getattr(
            finder,
            "marker",
            None,
        )
        == _envoy_bare_finder.marker
        for finder in sys.meta_path
    )


def _install_finder() -> None:
    if not _finder_installed():
        sys.meta_path.insert(
            0,
            _envoy_bare_finder(),
        )


def _bind_persona_engine() -> ModuleType:
    module = _package_module(
        "persona_engine"
    )

    sys.modules[
        persona_synthetic_name
    ] = module

    return module


def _bind_psychologist() -> ModuleType:
    _ensure_opus_package_compat()

    envoy_opus_bridge = (
        _package_module(
            "opus_bridge"
        )
    )

    infer_with_opus = getattr(
        envoy_opus_bridge,
        "infer_with_opus",
        None,
    )

    if not callable(
        infer_with_opus
    ):
        raise envoy_runtime_package_compat_error(
            "Envoy Opus bridge lacks infer_with_opus()"
        )

    previous_opus_bridge = (
        sys.modules.get(
            "opus_bridge"
        )
    )

    sys.modules[
        "opus_bridge"
    ] = envoy_opus_bridge

    try:
        psychologist = (
            _package_module(
                "psychologist"
            )
        )
    finally:
        if previous_opus_bridge is None:
            sys.modules.pop(
                "opus_bridge",
                None,
            )
        else:
            sys.modules[
                "opus_bridge"
            ] = previous_opus_bridge

    sys.modules[
        psychologist_synthetic_name
    ] = psychologist

    return psychologist


def install() -> dict[str, Any]:
    _ensure_package()
    _ensure_opus_package_compat()

    runtime_value = str(
        envoy_runtime
    )

    if runtime_value not in sys.path:
        sys.path.insert(
            0,
            runtime_value,
        )

    _install_finder()

    persona = _bind_persona_engine()
    psychologist = _bind_psychologist()

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
        "persona_package":
            getattr(
                persona,
                "__package__",
                None,
            ),
        "psychologist_package":
            getattr(
                psychologist,
                "__package__",
                None,
            ),
        "scoped_envoy_opus_bridge":
            True,
        "persistent_opus_bridge_override":
            False,
        "authority_effect":
            authority_effect,
    }


def selftest() -> dict[str, Any]:
    previous_opus_bridge = (
        sys.modules.get(
            "opus_bridge"
        )
    )

    result = install()

    persona = sys.modules.get(
        persona_synthetic_name
    )

    psychologist = sys.modules.get(
        psychologist_synthetic_name
    )

    if persona is None:
        raise envoy_runtime_package_compat_error(
            "persona synthetic alias missing"
        )

    if psychologist is None:
        raise envoy_runtime_package_compat_error(
            "psychologist synthetic alias missing"
        )

    if getattr(
        persona,
        "__package__",
        "",
    ) != package_name:
        raise envoy_runtime_package_compat_error(
            "persona engine lacks package context"
        )

    if getattr(
        psychologist,
        "__package__",
        "",
    ) != package_name:
        raise envoy_runtime_package_compat_error(
            "psychologist lacks package context"
        )

    if not callable(
        getattr(
            persona,
            "load_persona",
            None,
        )
    ):
        raise envoy_runtime_package_compat_error(
            "persona load contract missing"
        )

    if (
        previous_opus_bridge
        is not None
        and sys.modules.get(
            "opus_bridge"
        )
        is not previous_opus_bridge
    ):
        raise envoy_runtime_package_compat_error(
            "bare opus_bridge ownership leaked"
        )

    return {
        **result,
        "ok":
            True,
        "persona_alias":
            persona_synthetic_name,
        "psychologist_alias":
            psychologist_synthetic_name,
        "opus_bridge_restored":
            (
                previous_opus_bridge
                is None
                or sys.modules.get(
                    "opus_bridge"
                )
                is previous_opus_bridge
            ),
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )

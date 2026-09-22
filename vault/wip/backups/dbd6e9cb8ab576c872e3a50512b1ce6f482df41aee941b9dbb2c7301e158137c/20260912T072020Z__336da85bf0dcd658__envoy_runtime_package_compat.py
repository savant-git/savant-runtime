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
    "envoy-runtime-package-compat/1.0.0"
)

owner = "exile:palaver"
compatibility_target = "exile:envoy"
authority_effect = "none"


envoy_runtime = Path(
    "/root/savant-runtime/ontology/obelisks/"
    "_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/envoy/runtime"
)

package_name = "savant_envoy_runtime"


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
            "Envoy runtime directory is missing"
        )

    package = ModuleType(
        package_name
    )

    package.__package__ = package_name
    package.__path__ = [
        str(
            envoy_runtime
        )
    ]
    package.__file__ = str(
        envoy_runtime
    )

    sys.modules[
        package_name
    ] = package

    return package


class _envoy_bare_loader(
    importlib.abc.Loader
):
    def __init__(
        self,
        *,
        bare_name: str,
        path: Path,
    ) -> None:
        self.bare_name = bare_name
        self.path = path

    def create_module(
        self,
        spec,
    ):
        return None

    def exec_module(
        self,
        module: ModuleType,
    ) -> None:
        _ensure_package()

        qualified_name = (
            f"{package_name}.{self.bare_name}"
        )

        module.__package__ = package_name
        module.__file__ = str(
            self.path
        )

        sys.modules[
            qualified_name
        ] = module

        try:
            source = self.path.read_text(
                encoding="utf-8"
            )

            code = compile(
                source,
                str(
                    self.path
                ),
                "exec",
            )

            exec(
                code,
                module.__dict__,
            )

        except Exception:
            if (
                sys.modules.get(
                    qualified_name
                )
                is module
            ):
                sys.modules.pop(
                    qualified_name,
                    None,
                )

            raise


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
                bare_name=fullname,
                path=candidate,
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


def install() -> dict[str, Any]:
    _ensure_package()

    runtime_value = str(
        envoy_runtime
    )

    if runtime_value not in sys.path:
        sys.path.insert(
            0,
            runtime_value,
        )

    if not _finder_installed():
        sys.meta_path.insert(
            0,
            _envoy_bare_finder(),
        )

    return status()


def status() -> dict[str, Any]:
    return {
        "schema":
            schema,
        "installed":
            (
                package_name
                in sys.modules
                and _finder_installed()
            ),
        "owner":
            owner,
        "compatibility_target":
            compatibility_target,
        "package":
            package_name,
        "envoy_runtime":
            str(
                envoy_runtime
            ),
        "bare_import_compatibility":
            True,
        "package_relative_imports":
            True,
        "authority_effect":
            authority_effect,
    }


def selftest() -> dict[str, Any]:
    result = install()

    if not result.get(
        "installed"
    ):
        raise envoy_runtime_package_compat_error(
            "Envoy package compatibility "
            "installation failed"
        )

    import moral_self
    import persona_engine

    moral_package = getattr(
        moral_self,
        "__package__",
        "",
    )

    persona_package = getattr(
        persona_engine,
        "__package__",
        "",
    )

    if moral_package != package_name:
        raise envoy_runtime_package_compat_error(
            "moral_self lacks Envoy "
            "package context"
        )

    if persona_package != package_name:
        raise envoy_runtime_package_compat_error(
            "persona_engine lacks Envoy "
            "package context"
        )

    if not callable(
        getattr(
            persona_engine,
            "load_persona",
            None,
        )
    ):
        raise envoy_runtime_package_compat_error(
            "persona_engine contract missing"
        )

    return {
        **status(),
        "ok":
            True,
        "moral_self_package":
            moral_package,
        "persona_engine_package":
            persona_package,
        "persona_engine_contract":
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

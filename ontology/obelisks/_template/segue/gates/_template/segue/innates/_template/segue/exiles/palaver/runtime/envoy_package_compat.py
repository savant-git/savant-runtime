from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


schema = (
    "savant://runtime/palaver/"
    "envoy-package-compat/1.0.0"
)

owner = "exile:palaver"

savant_root = Path(
    "/root/savant-runtime"
)

envoy_root = (
    savant_root
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
    / "envoy"
)

envoy_runtime = (
    envoy_root
    / "runtime"
)

package_name = (
    "savant_envoy_runtime"
)


class envoy_package_compat_error(
    RuntimeError
):
    pass


def _ensure_package() -> ModuleType:
    existing = sys.modules.get(
        package_name
    )

    if existing is not None:
        return existing

    module = ModuleType(
        package_name
    )

    module.__package__ = (
        package_name
    )

    module.__path__ = [
        str(
            envoy_runtime
        )
    ]

    module.__file__ = str(
        envoy_runtime
        / "__init__.py"
    )

    sys.modules[
        package_name
    ] = module

    return module


def _qualified_name(
    path: Path,
) -> str:
    resolved = path.resolve()

    try:
        relative = resolved.relative_to(
            envoy_runtime.resolve()
        )
    except ValueError as exc:
        raise envoy_package_compat_error(
            "module is outside Envoy runtime"
        ) from exc

    if relative.suffix != ".py":
        raise envoy_package_compat_error(
            "Envoy runtime module must be Python"
        )

    parts = list(
        relative.with_suffix(
            ""
        ).parts
    )

    if parts[-1] == "__init__":
        parts = parts[:-1]

    if not parts:
        return package_name

    return (
        package_name
        + "."
        + ".".join(
            parts
        )
    )


def load_package_module(
    path: Path,
) -> ModuleType:
    _ensure_package()

    qualified = _qualified_name(
        path
    )

    existing = sys.modules.get(
        qualified
    )

    if existing is not None:
        return existing

    if not path.is_file():
        raise envoy_package_compat_error(
            f"required Envoy module missing: {path}"
        )

    spec = (
        importlib.util
        .spec_from_file_location(
            qualified,
            path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise envoy_package_compat_error(
            f"unable to load Envoy module: {path}"
        )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    sys.modules[
        qualified
    ] = module

    try:
        spec.loader.exec_module(
            module
        )
    except Exception:
        sys.modules.pop(
            qualified,
            None,
        )
        raise

    return module


def install_bare_alias(
    name: str,
    path: Path,
) -> ModuleType:
    existing = sys.modules.get(
        name
    )

    if existing is not None:
        existing_file = getattr(
            existing,
            "__file__",
            None,
        )

        if existing_file:
            try:
                if (
                    envoy_runtime.resolve()
                    in Path(
                        existing_file
                    ).resolve().parents
                ):
                    return existing
            except OSError:
                pass

        raise envoy_package_compat_error(
            f"Envoy compatibility alias "
            f"already occupied: {name}"
        )

    module = load_package_module(
        path
    )

    sys.modules[
        name
    ] = module

    return module


def install() -> dict[str, Any]:
    _ensure_package()

    canonical = load_package_module(
        envoy_runtime
        / "canonical_primitives.py"
    )

    moral_self = install_bare_alias(
        "moral_self",
        envoy_runtime
        / "moral_self.py",
    )

    persona_engine = install_bare_alias(
        "persona_engine",
        envoy_runtime
        / "persona_engine.py",
    )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "package":
            package_name,
        "runtime":
            str(
                envoy_runtime
            ),
        "canonical_primitives":
            getattr(
                canonical,
                "__name__",
                None,
            ),
        "bare_aliases": {
            "moral_self":
                getattr(
                    moral_self,
                    "__name__",
                    None,
                ),
            "persona_engine":
                getattr(
                    persona_engine,
                    "__name__",
                    None,
                ),
        },
        "package_relative_imports":
            True,
        "historical_bare_imports":
            True,
        "envoy_source_modified":
            False,
        "authority_effect":
            "none",
    }


def install_bridge_loader(
    bridge: ModuleType,
) -> dict[str, Any]:
    original = getattr(
        bridge,
        "load_module",
        None,
    )

    if not callable(
        original
    ):
        raise envoy_package_compat_error(
            "Palaver Envoy bridge lacks load_module()"
        )

    if getattr(
        bridge,
        "_envoy_package_compat_installed",
        False,
    ):
        return {
            "installed":
                True,
            "already_installed":
                True,
            "authority_effect":
                "none",
        }

    def compatible_load_module(
        name: str,
        path: Path,
    ) -> ModuleType:
        resolved = Path(
            path
        ).resolve()

        try:
            resolved.relative_to(
                envoy_runtime.resolve()
            )
        except ValueError:
            return original(
                name,
                path,
            )

        existing = sys.modules.get(
            name
        )

        if existing is not None:
            return existing

        module = load_package_module(
            resolved
        )

        sys.modules[
            name
        ] = module

        return module

    bridge.load_module = (
        compatible_load_module
    )

    bridge._envoy_package_compat_installed = (
        True
    )

    return {
        "installed":
            True,
        "already_installed":
            False,
        "loader":
            "package-aware-envoy-runtime",
        "envoy_source_modified":
            False,
        "authority_effect":
            "none",
    }

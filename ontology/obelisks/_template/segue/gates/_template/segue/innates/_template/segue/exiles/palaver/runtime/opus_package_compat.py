from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


schema = (
    "savant://runtime/palaver/"
    "opus-package-compat/1.0.0"
)

owner = "exile:palaver"

savant_root = Path(
    "/root/savant-runtime"
)

opus_root = (
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
    / "opus"
)

opus_runtime = (
    opus_root
    / "runtime"
)

package_name = (
    "savant_opus_runtime"
)


class opus_package_compat_error(
    RuntimeError
):
    pass


def _package() -> ModuleType:
    existing = sys.modules.get(
        package_name
    )

    if existing is not None:
        return existing

    init_file = (
        opus_runtime
        / "__init__.py"
    )

    if init_file.is_file():
        spec = (
            importlib.util
            .spec_from_file_location(
                package_name,
                init_file,
                submodule_search_locations=[
                    str(
                        opus_runtime
                    )
                ],
            )
        )
    else:
        spec = (
            importlib.util
            .spec_from_loader(
                package_name,
                loader=None,
                is_package=True,
            )
        )

    if spec is None:
        raise opus_package_compat_error(
            "unable to construct Opus runtime "
            "compatibility package"
        )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    module.__path__ = [
        str(
            opus_runtime
        )
    ]

    module.__package__ = (
        package_name
    )

    sys.modules[
        package_name
    ] = module

    if (
        init_file.is_file()
        and spec.loader is not None
    ):
        try:
            spec.loader.exec_module(
                module
            )
        except Exception:
            sys.modules.pop(
                package_name,
                None,
            )
            raise

    return module


def load_runtime_module(
    module_name: str,
) -> ModuleType:
    normalized = str(
        module_name
        or ""
    ).strip()

    if not normalized:
        raise opus_package_compat_error(
            "Opus runtime module name is required"
        )

    if (
        "/" in normalized
        or "\\"
        in normalized
        or normalized.startswith(
            "."
        )
    ):
        raise opus_package_compat_error(
            "invalid Opus runtime module name"
        )

    _package()

    qualified = (
        f"{package_name}.{normalized}"
    )

    existing = sys.modules.get(
        qualified
    )

    if existing is not None:
        return existing

    source = (
        opus_runtime
        / f"{normalized}.py"
    )

    if not source.is_file():
        raise opus_package_compat_error(
            f"Opus runtime module missing: {source}"
        )

    spec = (
        importlib.util
        .spec_from_file_location(
            qualified,
            source,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise opus_package_compat_error(
            f"unable to load Opus runtime module: "
            f"{source}"
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


def install_alias(
    alias: str,
    module_name: str,
) -> ModuleType:
    normalized_alias = str(
        alias
        or ""
    ).strip()

    if not normalized_alias:
        raise opus_package_compat_error(
            "compatibility alias is required"
        )

    existing = sys.modules.get(
        normalized_alias
    )

    if existing is not None:
        existing_file = getattr(
            existing,
            "__file__",
            None,
        )

        if existing_file:
            try:
                existing_path = (
                    Path(
                        existing_file
                    )
                    .resolve()
                )

                if (
                    opus_runtime
                    in existing_path.parents
                ):
                    return existing
            except OSError:
                pass

        raise opus_package_compat_error(
            f"module alias already occupied: "
            f"{normalized_alias}"
        )

    module = load_runtime_module(
        module_name
    )

    sys.modules[
        normalized_alias
    ] = module

    return module


def install() -> dict[str, Any]:
    runtime_value = str(
        opus_runtime
    )

    if runtime_value not in sys.path:
        sys.path.append(
            runtime_value
        )

    router = install_alias(
        "router",
        "router",
    )

    voice = install_alias(
        "voice_orchestrator",
        "voice_orchestrator",
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
                opus_runtime
            ),
        "aliases": {
            "router":
                getattr(
                    router,
                    "__name__",
                    None,
                ),
            "voice_orchestrator":
                getattr(
                    voice,
                    "__name__",
                    None,
                ),
        },
        "package_context_preserved":
            True,
        "opus_source_modified":
            False,
        "envoy_source_modified":
            False,
        "provider_owner":
            "opus",
        "authority_effect":
            "none",
    }

#!/usr/bin/env python3

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any


savant_root = Path(
    "/root/savant-runtime"
)

savant_runtime = (
    savant_root
    / "runtime"
)

palaver_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/palaver"
)

palaver_runtime = (
    palaver_root
    / "runtime"
)

schema = (
    "savant://runtime/palaver/"
    "enterprise-runtime/1.0.5"
)

owner = "exile:palaver"


class enterprise_runtime_error(
    RuntimeError
):
    pass


def _normalize_import_paths() -> None:
    savant_value = str(
        savant_root
    )

    palaver_value = str(
        palaver_runtime
    )

    filtered = [
        entry
        for entry in sys.path
        if entry not in {
            savant_value,
            palaver_value,
        }
    ]

    sys.path[:] = [
        savant_value,
        palaver_value,
        *filtered,
    ]


def _canonical_runtime_path() -> Path:
    return savant_runtime.resolve()


def _loaded_runtime_path() -> Path | None:
    module = sys.modules.get(
        "runtime"
    )

    if module is None:
        return None

    module_file = getattr(
        module,
        "__file__",
        None,
    )

    if module_file:
        return (
            Path(
                module_file
            )
            .resolve()
            .parent
        )

    module_path = getattr(
        module,
        "__path__",
        None,
    )

    if module_path:
        values = list(
            module_path
        )

        if values:
            return (
                Path(
                    values[0]
                )
                .resolve()
            )

    return None


def _remove_conflicting_runtime_modules() -> None:
    canonical = (
        _canonical_runtime_path()
    )

    loaded = (
        _loaded_runtime_path()
    )

    if (
        loaded is None
        or loaded == canonical
    ):
        return

    for name in tuple(
        sys.modules
    ):
        if (
            name == "runtime"
            or name.startswith(
                "runtime."
            )
        ):
            del sys.modules[
                name
            ]


def _preload_canonical_runtime() -> Any:
    _normalize_import_paths()

    _remove_conflicting_runtime_modules()

    runtime_module = (
        importlib.import_module(
            "runtime"
        )
    )

    loaded = (
        _loaded_runtime_path()
    )

    expected = (
        _canonical_runtime_path()
    )

    if loaded != expected:
        raise enterprise_runtime_error(
            "canonical Savant runtime namespace "
            f"did not resolve correctly: "
            f"expected={expected} loaded={loaded}"
        )

    constitution = (
        importlib.import_module(
            "runtime.constitution"
        )
    )

    if not hasattr(
        constitution,
        "ConstitutionalRegistry",
    ):
        raise enterprise_runtime_error(
            "runtime.constitution does not expose "
            "ConstitutionalRegistry"
        )

    return runtime_module


canonical_runtime = (
    _preload_canonical_runtime()
)


from opus_package_compat import (
    install as install_opus_package_compat,
)

from envoy_package_compat import (
    install as install_envoy_package_compat,
    install_bridge_loader,
)


opus_compatibility = (
    install_opus_package_compat()
)

envoy_compatibility = (
    install_envoy_package_compat()
)


import envoy_bridge


envoy_bridge_compatibility = (
    install_bridge_loader(
        envoy_bridge
    )
)


import server

from chat_session_bridge import (
    install as install_chat_session_bridge,
)

from deployment import (
    load_config,
)

from session_runtime import (
    install as install_session_runtime,
    status as session_status,
)

from transport_integration import (
    install as install_transport,
    integration_status,
)


def _namespace_projection() -> dict[str, Any]:
    loaded = (
        _loaded_runtime_path()
    )

    canonical = (
        _canonical_runtime_path()
    )

    return {
        "canonical_runtime":
            str(
                canonical
            ),
        "loaded_runtime":
            (
                str(
                    loaded
                )
                if loaded is not None
                else None
            ),
        "canonical_runtime_active":
            loaded == canonical,
        "constitution_available":
            (
                "runtime.constitution"
                in sys.modules
            ),
        "palaver_runtime":
            str(
                palaver_runtime
            ),
        "namespace_collision":
            (
                loaded is not None
                and loaded != canonical
            ),
        "authority_effect":
            "none",
    }


def _install_runtime_layers() -> tuple[
    Any,
    dict[str, Any],
]:
    config = load_config()

    sessions = (
        install_session_runtime(
            server
        )
    )

    chat_bridge = (
        install_chat_session_bridge(
            server,
            runtime=sessions,
        )
    )

    install_transport(
        server,
        config=config,
    )

    return (
        sessions,
        chat_bridge,
    )


def bootstrap() -> tuple[
    Any,
    Any,
    dict[str, Any],
]:
    namespace = (
        _namespace_projection()
    )

    if not namespace[
        "canonical_runtime_active"
    ]:
        raise enterprise_runtime_error(
            "canonical runtime namespace "
            "was displaced before bootstrap"
        )

    sessions, chat_bridge = (
        _install_runtime_layers()
    )

    legacy = (
        server.bootstrap()
    )

    return (
        legacy,
        sessions,
        chat_bridge,
    )


def inspection() -> dict[str, Any]:
    (
        legacy,
        sessions,
        chat_bridge,
    ) = bootstrap()

    return {
        "schema":
            schema,
        "owner":
            owner,
        "canonical_server":
            str(
                palaver_runtime
                / "server.py"
            ),
        "execution_mode":
            "enterprise-composed-runtime",
        "namespace":
            _namespace_projection(),
        "opus_package_compatibility":
            opus_compatibility,
        "envoy_package_compatibility":
            envoy_compatibility,
        "envoy_bridge_compatibility":
            envoy_bridge_compatibility,
        "chat_session_bridge":
            chat_bridge,
        "session_runtime":
            session_status(
                sessions
            ),
        "transport":
            integration_status(
                server
            ),
        "palaver":
            server.compatibility_status(
                legacy
            ),
        "boundaries": {
            "conversation_owner":
                "palaver",
            "provider_owner":
                "opus",
            "persona_owner":
                "envoy",
            "task_owner":
                "niche",
            "mutation_owner":
                "coda",
            "root_runtime_owner":
                "savant",
            "palaver_replaces_root_runtime":
                False,
            "chat_contract_modified":
                False,
            "provider_execution_modified":
                False,
            "opus_source_modified":
                False,
            "envoy_source_modified":
                False,
            "creates_authority":
                False,
        },
        "authority_effect":
            "none",
    }


def serve() -> int:
    namespace = (
        _namespace_projection()
    )

    if not namespace[
        "canonical_runtime_active"
    ]:
        raise enterprise_runtime_error(
            "canonical runtime namespace "
            "was displaced before serve"
        )

    _install_runtime_layers()

    result = (
        server.main()
    )

    if result is None:
        return 0

    return int(
        result
    )


def main() -> int:
    arguments = set(
        sys.argv[1:]
    )

    if "--inspect" in arguments:
        print(
            json.dumps(
                inspection(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            )
        )

        return 0

    return serve()


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

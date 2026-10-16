#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
from types import ModuleType
from typing import Any


schema = (
    "savant://runtime/palaver/"
    "enterprise-server-entrypoint/1.0.0"
)

owner = "exile:palaver"
authority_effect = "none"


palaver_root = Path(
    "/root/savant-runtime/ontology/obelisks/"
    "_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/palaver"
)

runtime_root = (
    palaver_root
    / "runtime"
)

server_path = (
    runtime_root
    / "server.py"
)

live_execution_path = (
    runtime_root
    / "live_chat_execution.py"
)

server_module_name = (
    "savant_palaver_canonical_server"
)

live_execution_module_name = (
    "savant_palaver_live_chat_execution"
)


class enterprise_server_error(
    RuntimeError
):
    pass


def _load_module(
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
        raise enterprise_server_error(
            f"required module is missing: {path}"
        )

    specification = (
        importlib.util.spec_from_file_location(
            name,
            path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise enterprise_server_error(
            f"unable to load module: {path}"
        )

    module = (
        importlib.util.module_from_spec(
            specification
        )
    )

    sys.modules[
        name
    ] = module

    try:
        specification.loader.exec_module(
            module
        )
    except Exception:
        sys.modules.pop(
            name,
            None,
        )
        raise

    return module


def _server() -> ModuleType:
    return _load_module(
        name=
            server_module_name,
        path=
            server_path,
    )


def _live_execution() -> ModuleType:
    return _load_module(
        name=
            live_execution_module_name,
        path=
            live_execution_path,
    )


def bootstrap() -> tuple[
    ModuleType,
    ModuleType,
    dict[str, Any],
]:
    server = _server()

    bootstrap_target = getattr(
        server,
        "bootstrap",
        None,
    )

    if not callable(
        bootstrap_target
    ):
        raise enterprise_server_error(
            "canonical Palaver bootstrap "
            "is not callable"
        )

    legacy = bootstrap_target()

    if not isinstance(
        legacy,
        ModuleType,
    ):
        raise enterprise_server_error(
            "canonical bootstrap did not "
            "return the legacy compatibility module"
        )

    selected_persona = getattr(
        server,
        "_selected_persona_id",
        None,
    )

    if not callable(
        selected_persona
    ):
        raise enterprise_server_error(
            "canonical persona selector "
            "is not callable"
        )

    live_execution = (
        _live_execution()
    )

    install_target = getattr(
        live_execution,
        "install",
        None,
    )

    if not callable(
        install_target
    ):
        raise enterprise_server_error(
            "live chat execution installer "
            "is not callable"
        )

    live_status = install_target(
        legacy,
        selected_persona=
            selected_persona,
    )

    if not isinstance(
        live_status,
        dict,
    ):
        raise enterprise_server_error(
            "live chat execution installer "
            "returned invalid status"
        )

    if not live_status.get(
        "installed"
    ):
        raise enterprise_server_error(
            "live chat execution was not installed"
        )

    return (
        server,
        legacy,
        live_status,
    )


def status(
    server: ModuleType,
    legacy: ModuleType,
    live_status: dict[
        str,
        Any,
    ],
) -> dict[str, Any]:
    compatibility_target = getattr(
        server,
        "compatibility_status",
        None,
    )

    canonical_status: dict[
        str,
        Any,
    ] = {}

    if callable(
        compatibility_target
    ):
        value = compatibility_target(
            legacy
        )

        if isinstance(
            value,
            dict,
        ):
            canonical_status = dict(
                value
            )

    live_execution = (
        _live_execution()
    )

    live_state_target = getattr(
        live_execution,
        "status",
        None,
    )

    live_state: dict[
        str,
        Any,
    ] = dict(
        live_status
    )

    if callable(
        live_state_target
    ):
        value = live_state_target(
            legacy
        )

        if isinstance(
            value,
            dict,
        ):
            live_state = dict(
                value
            )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "canonical_server":
            str(
                server_path
            ),
        "canonical_server_preserved":
            True,
        "canonical":
            canonical_status,
        "live_chat_execution":
            live_state,
        "conversation_owner":
            "palaver",
        "persona_owner":
            "envoy",
        "provider_owner":
            "opus",
        "verification_owner":
            "notary",
        "mutation_owner":
            "coda",
        "session_identity_binding":
            bool(
                live_state.get(
                    "contract_session_binding"
                )
            ),
        "request_identity_binding":
            bool(
                live_state.get(
                    "request_header_binding"
                )
            ),
        "outcome_capture":
            bool(
                live_state.get(
                    "installed"
                )
            ),
        "synthetic_streaming":
            False,
        "synthetic_provider_cancellation":
            False,
        "authority_effect":
            authority_effect,
    }


def main() -> int:
    (
        server,
        legacy,
        live_status,
    ) = bootstrap()

    if (
        os.environ.get(
            "PALAVER_BOOTSTRAP_INSPECT"
        )
        == "1"
    ):
        print(
            json.dumps(
                status(
                    server,
                    legacy,
                    live_status,
                ),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    legacy_main = getattr(
        legacy,
        "main",
        None,
    )

    if not callable(
        legacy_main
    ):
        raise enterprise_server_error(
            "Palaver canonical main "
            "is not callable"
        )

    legacy_main()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

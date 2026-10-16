#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


savant_root = Path(
    "/root/savant-runtime"
)

palaver_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/palaver"
)

palaver_runtime = (
    palaver_root
    / "runtime"
)


def _ensure_import_paths() -> None:
    savant_value = str(
        savant_root
    )

    palaver_value = str(
        palaver_runtime
    )

    if savant_value in sys.path:
        sys.path.remove(
            savant_value
        )

    sys.path.insert(
        0,
        savant_value,
    )

    if palaver_value in sys.path:
        sys.path.remove(
            palaver_value
        )

    sys.path.insert(
        1,
        palaver_value,
    )


_ensure_import_paths()


import server

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


schema = (
    "savant://runtime/palaver/"
    "enterprise-runtime/1.0.1"
)

owner = "exile:palaver"


def bootstrap() -> tuple[
    Any,
    Any,
]:
    config = load_config()

    sessions = (
        install_session_runtime(
            server
        )
    )

    install_transport(
        server,
        config=config,
    )

    legacy = server.bootstrap()

    return (
        legacy,
        sessions,
    )


def inspection() -> dict[str, Any]:
    legacy, sessions = bootstrap()

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
        "root_runtime_namespace":
            str(
                savant_root
                / "runtime"
            ),
        "palaver_runtime":
            str(
                palaver_runtime
            ),
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
            "creates_authority":
                False,
        },
        "authority_effect":
            "none",
    }


def serve() -> int:
    config = load_config()

    install_session_runtime(
        server
    )

    install_transport(
        server,
        config=config,
    )

    result = server.main()

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

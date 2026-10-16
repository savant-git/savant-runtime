#!/usr/bin/env python3

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any


runtime_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/envoy/runtime"
)

runtime_value = str(
    runtime_root
)

if runtime_value not in sys.path:
    sys.path.insert(
        0,
        runtime_value,
    )


from package_compat import (
    install as install_package_compat,
)


schema = (
    "savant://runtime/envoy/"
    "orobouros-entrypoint/1.0.0"
)

owner = "exile:envoy"


class orobouros_entrypoint_error(
    RuntimeError
):
    pass


def load() -> tuple[
    Any,
    dict[str, Any],
]:
    compatibility = (
        install_package_compat()
    )

    runtime = importlib.import_module(
        "savant_envoy_runtime.orobouros_enterprise"
    )

    if not hasattr(
        runtime,
        "project",
    ):
        raise orobouros_entrypoint_error(
            "Orobouros enterprise runtime "
            "does not expose project()"
        )

    if not hasattr(
        runtime,
        "selftest",
    ):
        raise orobouros_entrypoint_error(
            "Orobouros enterprise runtime "
            "does not expose selftest()"
        )

    return (
        runtime,
        compatibility,
    )


def inspection() -> dict[str, Any]:
    runtime, compatibility = (
        load()
    )

    runtime_status = (
        runtime.status()
        if hasattr(
            runtime,
            "status",
        )
        else {}
    )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "persona":
            "orobouros",
        "runtime":
            runtime.__name__,
        "package_compatibility":
            compatibility,
        "runtime_status":
            runtime_status,
        "persona_owner":
            "envoy",
        "provider_owner":
            "opus",
        "conversation_owner":
            "palaver",
        "source_modified":
            False,
        "authority_effect":
            "none",
    }


def selftest() -> dict[str, Any]:
    runtime, compatibility = (
        load()
    )

    result = runtime.selftest()

    if not isinstance(
        result,
        dict,
    ):
        raise orobouros_entrypoint_error(
            "Orobouros selftest did not "
            "return a projection"
        )

    if result.get(
        "ok"
    ) is not True:
        raise orobouros_entrypoint_error(
            "Orobouros selftest failed"
        )

    if result.get(
        "authority_effect"
    ) != "none":
        raise orobouros_entrypoint_error(
            "Orobouros selftest changed authority"
        )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "ok":
            True,
        "orobouros":
            result,
        "package_compatibility":
            compatibility,
        "authority_effect":
            "none",
    }


def main() -> int:
    arguments = set(
        sys.argv[1:]
    )

    if "--inspect" in arguments:
        payload = inspection()
    else:
        payload = selftest()

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=str,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any


schema = (
    "savant://runtime/palaver/"
    "opus-streaming-capability/1.0.0"
)

owner = "exile:palaver"
provider_owner = "exile:opus"
authority_effect = "none"


runtime_root = Path(
    "/root/savant-runtime/ontology/obelisks/"
    "_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/palaver/runtime"
)

compatibility_path = (
    runtime_root
    / "opus_router_package_compat.py"
)

compatibility_module_name = (
    "savant_palaver_opus_runtime_package_compat"
)


class opus_streaming_capability_error(
    RuntimeError
):
    pass


def _load_compatibility() -> ModuleType:
    existing = sys.modules.get(
        compatibility_module_name
    )

    if existing is not None:
        return existing

    if not compatibility_path.is_file():
        raise opus_streaming_capability_error(
            "Opus runtime package compatibility "
            "module is missing"
        )

    specification = (
        importlib.util.spec_from_file_location(
            compatibility_module_name,
            compatibility_path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise opus_streaming_capability_error(
            "unable to load Opus runtime "
            "package compatibility"
        )

    module = (
        importlib.util.module_from_spec(
            specification
        )
    )

    sys.modules[
        compatibility_module_name
    ] = module

    try:
        specification.loader.exec_module(
            module
        )
    except Exception:
        sys.modules.pop(
            compatibility_module_name,
            None,
        )
        raise

    return module


def _callable_signature(
    module: ModuleType,
    name: str,
) -> str | None:
    target = getattr(
        module,
        name,
        None,
    )

    if not callable(
        target
    ):
        return None

    try:
        return str(
            inspect.signature(
                target
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        return "unknown"


def _stream_contracts(
    router: ModuleType,
) -> dict[str, str]:
    candidates = (
        "execute_text_stream",
        "stream_text_request",
        "execute_streaming_text_request",
        "stream_text",
    )

    result: dict[
        str,
        str,
    ] = {}

    for name in candidates:
        signature = (
            _callable_signature(
                router,
                name,
            )
        )

        if signature is not None:
            result[
                name
            ] = signature

    return result


def _callback_support(
    router: ModuleType,
) -> dict[str, Any]:
    execute = getattr(
        router,
        "execute_text_request",
        None,
    )

    if not callable(
        execute
    ):
        return {
            "execute_text_request":
                False,
            "signature":
                None,
            "stream_parameter":
                False,
            "delta_callback_parameter":
                False,
            "cancel_parameter":
                False,
        }

    try:
        signature = inspect.signature(
            execute
        )
    except (
        TypeError,
        ValueError,
    ):
        return {
            "execute_text_request":
                True,
            "signature":
                "unknown",
            "stream_parameter":
                False,
            "delta_callback_parameter":
                False,
            "cancel_parameter":
                False,
        }

    names = set(
        signature.parameters
    )

    stream_parameter = bool(
        names
        & {
            "stream",
            "streaming",
        }
    )

    delta_callback_parameter = bool(
        names
        & {
            "on_delta",
            "delta_callback",
            "stream_callback",
            "on_token",
            "token_callback",
        }
    )

    cancel_parameter = bool(
        names
        & {
            "cancel",
            "cancel_hook",
            "cancel_event",
            "cancellation",
            "cancellation_token",
        }
    )

    return {
        "execute_text_request":
            True,
        "signature":
            str(
                signature
            ),
        "stream_parameter":
            stream_parameter,
        "delta_callback_parameter":
            delta_callback_parameter,
        "cancel_parameter":
            cancel_parameter,
    }


def project() -> dict[str, Any]:
    compatibility = (
        _load_compatibility()
    )

    install = getattr(
        compatibility,
        "install",
        None,
    )

    if not callable(
        install
    ):
        raise opus_streaming_capability_error(
            "Opus compatibility installer "
            "is unavailable"
        )

    installation = install()

    if not installation.get(
        "installed"
    ):
        raise opus_streaming_capability_error(
            "Opus compatibility installation "
            "did not succeed"
        )

    router = sys.modules.get(
        "router"
    )

    if not isinstance(
        router,
        ModuleType,
    ):
        raise opus_streaming_capability_error(
            "Opus router is unavailable"
        )

    explicit_stream_contracts = (
        _stream_contracts(
            router
        )
    )

    callback_support = (
        _callback_support(
            router
        )
    )

    genuine_streaming = bool(
        explicit_stream_contracts
        or (
            callback_support[
                "stream_parameter"
            ]
            and callback_support[
                "delta_callback_parameter"
            ]
        )
    )

    genuine_cancellation = bool(
        callback_support[
            "cancel_parameter"
        ]
    )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "provider_owner":
            provider_owner,
        "router_module":
            getattr(
                router,
                "__name__",
                "",
            ),
        "execute_text_request":
            callback_support[
                "execute_text_request"
            ],
        "execute_text_request_signature":
            callback_support[
                "signature"
            ],
        "explicit_stream_contracts":
            explicit_stream_contracts,
        "stream_parameter":
            callback_support[
                "stream_parameter"
            ],
        "delta_callback_parameter":
            callback_support[
                "delta_callback_parameter"
            ],
        "cancel_parameter":
            callback_support[
                "cancel_parameter"
            ],
        "genuine_streaming_supported":
            genuine_streaming,
        "genuine_provider_cancellation_supported":
            genuine_cancellation,
        "synthetic_streaming_permitted":
            False,
        "synthetic_provider_cancellation_permitted":
            False,
        "binding_required":
            genuine_streaming,
        "authority_effect":
            authority_effect,
    }


def selftest() -> dict[str, Any]:
    result = project()

    if not result.get(
        "execute_text_request"
    ):
        raise opus_streaming_capability_error(
            "verified Opus text execution "
            "surface is unavailable"
        )

    if result.get(
        "synthetic_streaming_permitted"
    ):
        raise opus_streaming_capability_error(
            "synthetic streaming became permitted"
        )

    if result.get(
        "synthetic_provider_cancellation_permitted"
    ):
        raise opus_streaming_capability_error(
            "synthetic provider cancellation "
            "became permitted"
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

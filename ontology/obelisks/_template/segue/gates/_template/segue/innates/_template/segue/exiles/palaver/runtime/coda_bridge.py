from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


CODA_MUTATION = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/coda/"
    "runtime/mutation.py"
)

MODULE_NAME = "savant_coda_mutation"


def load_coda() -> ModuleType:
    existing = sys.modules.get(
        MODULE_NAME
    )

    if existing is not None:
        return existing

    if not CODA_MUTATION.is_file():
        raise RuntimeError(
            "Coda mutation runtime missing: "
            f"{CODA_MUTATION}"
        )

    spec = (
        importlib.util
        .spec_from_file_location(
            MODULE_NAME,
            CODA_MUTATION,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            "unable to load Coda mutation runtime"
        )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    sys.modules[
        MODULE_NAME
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def current_digest(
    path: str,
) -> str | None:
    coda = load_coda()

    target, _ = coda.resolve_target(
        path
    )

    return coda.digest_file(
        target
    )


def save_file(
    path: str,
    content: str,
    *,
    expected_digest: str | None = None,
    intent: str = "Palaver file save",
) -> dict[str, Any]:
    coda = load_coda()

    return coda.replace_text(
        path,
        content,
        expected_digest=expected_digest,
        requester="palaver",
        intent=intent,
    )


def integration_status() -> dict[str, Any]:
    coda = load_coda()

    return {
        "owner": "palaver",
        "delegates_to": "coda",
        "operation": "replace_text",
        "coda": coda.status(),
        "direct_durable_mutation": False,
        "authority_effect": "none",
    }

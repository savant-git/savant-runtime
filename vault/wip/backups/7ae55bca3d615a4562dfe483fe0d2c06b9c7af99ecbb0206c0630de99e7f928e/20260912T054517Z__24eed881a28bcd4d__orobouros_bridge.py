#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Iterable, Mapping


schema = (
    "savant://runtime/palaver/"
    "orobouros-bridge/1.1.0"
)

owner = "exile:palaver"

savant_root = Path(
    "/root/savant-runtime"
)

envoy_runtime = (
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
    / "runtime"
)

orobouros_runtime = (
    envoy_runtime
    / "orobouros_runtime.py"
)

package_name = (
    "savant_envoy_runtime"
)


class orobouros_bridge_error(
    RuntimeError
):
    pass


def _ensure_package() -> ModuleType:
    existing = sys.modules.get(
        package_name
    )

    if existing is not None:
        paths = list(
            getattr(
                existing,
                "__path__",
                [],
            )
        )

        runtime_value = str(
            envoy_runtime
        )

        if runtime_value not in paths:
            paths.append(
                runtime_value
            )

            existing.__path__ = (
                paths
            )

        return existing

    package = ModuleType(
        package_name
    )

    package.__path__ = [
        str(
            envoy_runtime
        )
    ]

    package.__package__ = (
        package_name
    )

    sys.modules[
        package_name
    ] = package

    return package


def _load() -> ModuleType:
    _ensure_package()

    qualified = (
        package_name
        + ".orobouros_runtime"
    )

    existing = sys.modules.get(
        qualified
    )

    if existing is not None:
        return existing

    if not orobouros_runtime.is_file():
        raise (
            orobouros_bridge_error(
                "Envoy Orobouros runtime "
                "is unavailable"
            )
        )

    spec = (
        importlib.util
        .spec_from_file_location(
            qualified,
            orobouros_runtime,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise (
            orobouros_bridge_error(
                "unable to load Envoy "
                "Orobouros runtime"
            )
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


def project(
    *,
    domains: Iterable[Any] = (),
    signals: Iterable[Any] = (),
    required_capabilities: Iterable[Any] = (),
    preferred_capabilities: Iterable[Any] = (),
    previous_traits: Iterable[Any] = (),
    unavailable_providers: Iterable[Any] = (),
    maximum_latency_ms: float | None = None,
    maximum_cost: float | None = None,
    cap: int | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    runtime = _load()

    result = runtime.project(
        domains=
            domains,
        signals=
            signals,
        required_capabilities=
            required_capabilities,
        preferred_capabilities=
            preferred_capabilities,
        previous_traits=
            previous_traits,
        unavailable_providers=
            unavailable_providers,
        maximum_latency_ms=
            maximum_latency_ms,
        maximum_cost=
            maximum_cost,
        cap=
            cap,
        actor=
            actor,
    )

    if not isinstance(
        result,
        dict,
    ):
        raise (
            orobouros_bridge_error(
                "Envoy Orobouros projection "
                "must be an object"
            )
        )

    if (
        result.get(
            "owner"
        )
        != "envoy"
    ):
        raise (
            orobouros_bridge_error(
                "Envoy ownership boundary violated"
            )
        )

    if (
        result.get(
            "persona_id"
        )
        != "orobouros"
    ):
        raise (
            orobouros_bridge_error(
                "unexpected persona identity"
            )
        )

    return result


def context_from_message(
    message: str,
) -> dict[str, tuple[str, ...]]:
    normalized = str(
        message
        or ""
    ).strip().lower()

    tokens = {
        token.strip(
            ".,:;!?()[]{}\"'"
        )
        for token in normalized.split()
    }

    domains: set[str] = {
        "conversation"
    }

    signals: set[str] = set()

    mappings = {
        "engineering": {
            "code",
            "coding",
            "implement",
            "implementation",
            "runtime",
            "server",
            "api",
            "python",
            "typescript",
        },
        "analysis": {
            "analyze",
            "analysis",
            "evaluate",
            "compare",
            "reason",
            "architecture",
        },
        "research": {
            "research",
            "source",
            "sources",
            "evidence",
            "verify",
            "citation",
        },
        "literary": {
            "novel",
            "story",
            "scene",
            "character",
            "prose",
            "dialogue",
            "literary",
        },
        "planning": {
            "plan",
            "roadmap",
            "sequence",
            "dependency",
            "schedule",
        },
    }

    for (
        domain,
        keywords,
    ) in mappings.items():
        hits = (
            tokens.intersection(
                keywords
            )
        )

        if hits:
            domains.add(
                domain
            )

            signals.update(
                hits
            )

    signals.update(
        token
        for token in tokens
        if token in {
            "authority",
            "uncertain",
            "unknown",
            "verify",
            "implement",
            "context",
            "canon",
            "failure",
            "risk",
            "tool",
        }
    )

    return {
        "domains":
            tuple(
                sorted(
                    domains
                )
            ),
        "signals":
            tuple(
                sorted(
                    signals
                )
            ),
    }


def project_for_message(
    message: str,
    *,
    previous_traits: Iterable[Any] = (),
    provider_state: Mapping[
        str,
        Any,
    ] | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    context = (
        context_from_message(
            message
        )
    )

    unavailable: tuple[
        str,
        ...,
    ] = ()

    if provider_state:
        raw = provider_state.get(
            "unavailable"
        )

        if isinstance(
            raw,
            (
                list,
                tuple,
                set,
            ),
        ):
            unavailable = tuple(
                str(
                    value
                )
                for value in raw
            )

    return project(
        domains=
            context[
                "domains"
            ],
        signals=
            context[
                "signals"
            ],
        previous_traits=
            previous_traits,
        unavailable_providers=
            unavailable,
        actor=
            actor,
    )


def status() -> dict[str, Any]:
    runtime = _load()

    runtime_status = (
        runtime.status()
    )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "persona_owner":
            "envoy",
        "provider_owner":
            "opus",
        "conversation_owner":
            "palaver",
        "default_persona":
            "orobouros",
        "envoy_runtime":
            runtime_status,
        "reflection_boundary":
            True,
        "psychologist_authoritative":
            False,
        "moral_self_mutation":
            False,
        "palaver_defines_persona":
            False,
        "palaver_executes_provider":
            False,
        "authority_effect":
            "none",
    }


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            status(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )

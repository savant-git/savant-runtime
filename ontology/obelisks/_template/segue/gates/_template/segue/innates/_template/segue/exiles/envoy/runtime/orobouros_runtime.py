#!/usr/bin/env python3

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Iterable, Mapping


try:
    from . import orobouros_enterprise
    from . import orobouros_reflection
except ImportError:
    import orobouros_enterprise
    import orobouros_reflection


schema = (
    "savant://envoy/"
    "orobouros-runtime/1.0.0"
)

owner = "envoy"
persona_id = "orobouros"


class orobouros_runtime_error(
    RuntimeError
):
    pass


def canonical_json(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        default=str,
    ).encode(
        "utf-8"
    )


def digest(
    value: Any,
) -> str:
    return sha256(
        canonical_json(
            value
        )
    ).hexdigest()


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
    composition = (
        orobouros_enterprise.project(
            domains=domains,
            signals=signals,
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
        )
    )

    reflection = (
        orobouros_reflection.project(
            actor=actor
        )
    )

    if (
        composition.get(
            "owner"
        )
        != owner
    ):
        raise (
            orobouros_runtime_error(
                "composition ownership violation"
            )
        )

    if (
        reflection.get(
            "owner"
        )
        != owner
    ):
        raise (
            orobouros_runtime_error(
                "reflection ownership violation"
            )
        )

    semantic = {
        "persona_id":
            persona_id,
        "composition_digest":
            composition.get(
                "composition_digest"
            ),
        "reflection_digest":
            reflection.get(
                "reflection_digest"
            ),
        "expression_policy":
            reflection.get(
                "expression_policy"
            ),
        "expression_directives":
            reflection.get(
                "expression_directives"
            ),
    }

    result = dict(
        composition
    )

    result[
        "schema"
    ] = schema

    result[
        "composition_schema"
    ] = composition.get(
        "schema"
    )

    result[
        "reflection"
    ] = reflection

    result[
        "expression_policy"
    ] = reflection.get(
        "expression_policy"
    )

    result[
        "expression_directives"
    ] = reflection.get(
        "expression_directives"
    )

    result[
        "reflection_digest"
    ] = reflection.get(
        "reflection_digest"
    )

    result[
        "runtime_digest"
    ] = digest(
        semantic
    )

    result[
        "moral_self_mutated"
    ] = False

    result[
        "psychologist_authoritative"
    ] = False

    result[
        "psychologist_live_inference"
    ] = False

    result[
        "expression_is_authority"
    ] = False

    result[
        "provider_execution"
    ] = False

    result[
        "conversation_ownership"
    ] = False

    result[
        "authority_effect"
    ] = "none"

    return result


def public_projection(
    value: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    return {
        "schema":
            schema,
        "owner":
            owner,
        "persona_id":
            persona_id,
        "composition_digest":
            value.get(
                "composition_digest"
            ),
        "reflection_digest":
            value.get(
                "reflection_digest"
            ),
        "runtime_digest":
            value.get(
                "runtime_digest"
            ),
        "living_trait_crown":
            list(
                value.get(
                    "living_trait_crown"
                )
                or ()
            ),
        "expression_policy":
            dict(
                value.get(
                    "expression_policy"
                )
                or {}
            ),
        "capability_gap":
            bool(
                value.get(
                    "capability_gap",
                    False,
                )
            ),
        "degraded_mode":
            bool(
                value.get(
                    "degraded_mode",
                    False,
                )
            ),
        "authority_effect":
            "none",
    }


def status() -> dict[str, Any]:
    return {
        "schema":
            schema,
        "owner":
            owner,
        "persona_id":
            persona_id,
        "composition":
            orobouros_enterprise.status(),
        "reflection":
            orobouros_reflection.status(),
        "expression_authoritative":
            False,
        "psychologist_authoritative":
            False,
        "provider_owner":
            "opus",
        "conversation_owner":
            "palaver",
        "authority_effect":
            "none",
    }


def selftest() -> dict[str, Any]:
    first = project(
        domains=(
            "analysis",
        ),
        signals=(
            "verify",
        ),
        actor="selftest",
    )

    second = project(
        domains=(
            "analysis",
        ),
        signals=(
            "verify",
        ),
        actor="selftest",
    )

    if (
        first[
            "runtime_digest"
        ]
        != second[
            "runtime_digest"
        ]
    ):
        raise (
            orobouros_runtime_error(
                "runtime replay failed"
            )
        )

    if (
        first[
            "psychologist_authoritative"
        ]
        is not False
    ):
        raise (
            orobouros_runtime_error(
                "psychologist authority boundary failed"
            )
        )

    return {
        "schema":
            schema,
        "ok":
            True,
        "runtime_digest":
            first[
                "runtime_digest"
            ],
        "authority_effect":
            "none",
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

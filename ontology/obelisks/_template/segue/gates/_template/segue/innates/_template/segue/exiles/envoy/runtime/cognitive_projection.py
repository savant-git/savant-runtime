#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable


SCHEMA = "savant.envoy.cognitive-projection.v1"

OWNER = "envoy"
EXECUTION_OWNER = "opus"

DEFAULT_PERSONA_ID = "orobouros"

LAYER_ORDER = (
    "general",
    "reasoning",
    "instruction",
    "writing",
    "code",
    "tool",
)

DOMAIN_LAYERS = {
    "analysis": (
        "reasoning",
    ),
    "engineering": (
        "reasoning",
        "code",
        "tool",
    ),
    "code": (
        "code",
        "reasoning",
    ),
    "coding": (
        "code",
        "reasoning",
    ),
    "implementation": (
        "code",
        "reasoning",
        "tool",
    ),
    "writing": (
        "writing",
        "instruction",
    ),
    "creative": (
        "writing",
    ),
    "literature": (
        "writing",
        "reasoning",
    ),
    "research": (
        "reasoning",
        "instruction",
    ),
    "conversation": (
        "general",
        "instruction",
    ),
    "agent": (
        "reasoning",
        "tool",
        "instruction",
    ),
}

SIGNAL_LAYERS = {
    "analyze": (
        "reasoning",
    ),
    "analyse": (
        "reasoning",
    ),
    "reason": (
        "reasoning",
    ),
    "verify": (
        "reasoning",
    ),
    "compare": (
        "reasoning",
    ),
    "infer": (
        "reasoning",
    ),
    "implement": (
        "code",
        "reasoning",
        "tool",
    ),
    "code": (
        "code",
    ),
    "debug": (
        "code",
        "reasoning",
    ),
    "refactor": (
        "code",
        "reasoning",
    ),
    "write": (
        "writing",
    ),
    "rewrite": (
        "writing",
        "instruction",
    ),
    "compose": (
        "writing",
    ),
    "story": (
        "writing",
    ),
    "prose": (
        "writing",
    ),
    "follow": (
        "instruction",
    ),
    "obey": (
        "instruction",
    ),
    "tool": (
        "tool",
    ),
    "function": (
        "tool",
    ),
    "execute": (
        "tool",
        "instruction",
    ),
}

TRAIT_LAYER_HINTS = {
    "analytical": (
        "reasoning",
    ),
    "reasoning": (
        "reasoning",
    ),
    "precise": (
        "instruction",
        "reasoning",
    ),
    "disciplined": (
        "instruction",
    ),
    "creative": (
        "writing",
    ),
    "literary": (
        "writing",
    ),
    "technical": (
        "code",
        "reasoning",
    ),
    "engineering": (
        "code",
        "reasoning",
        "tool",
    ),
    "agentic": (
        "tool",
        "reasoning",
    ),
}


class CognitiveProjectionError(
    RuntimeError
):
    pass


def _normalize_terms(
    values: Iterable[Any],
) -> tuple[str, ...]:
    result: set[str] = set()

    for value in values:
        text = str(
            value or ""
        ).strip().lower()

        if text:
            result.add(text)

    return tuple(
        sorted(result)
    )


def _digest(
    value: Any,
) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


def _add_layers(
    selected: set[str],
    layers: Iterable[Any],
) -> None:
    for layer in layers:
        normalized = str(
            layer or ""
        ).strip().lower()

        if normalized not in LAYER_ORDER:
            raise CognitiveProjectionError(
                "unsupported cognitive layer: "
                f"{normalized!r}"
            )

        selected.add(normalized)


def _trait_terms(
    persona_projection: dict[str, Any],
) -> tuple[str, ...]:
    result: set[str] = set()

    traits = persona_projection.get(
        "traits"
    )

    if not isinstance(traits, list):
        return ()

    for trait in traits:
        if not isinstance(trait, dict):
            continue

        for field in (
            "id",
            "trait_id",
            "candidate_id",
        ):
            value = str(
                trait.get(field) or ""
            ).strip().lower()

            if value:
                result.add(value)

        for field in (
            "domains",
            "signals",
        ):
            values = trait.get(field)

            if isinstance(values, list):
                result.update(
                    _normalize_terms(values)
                )

    return tuple(
        sorted(result)
    )


def project_cognitive_layers(
    persona_projection: dict[str, Any],
    *,
    domains: Iterable[Any] = (),
    signals: Iterable[Any] = (),
    requested_layers: Iterable[Any] = (),
) -> dict[str, Any]:
    if not isinstance(
        persona_projection,
        dict,
    ):
        raise CognitiveProjectionError(
            "persona projection must "
            "be an object"
        )

    persona_id = str(
        persona_projection.get(
            "persona_id"
        )
        or ""
    ).strip()

    if not persona_id:
        raise CognitiveProjectionError(
            "persona projection lacks "
            "persona_id"
        )

    normalized_domains = (
        _normalize_terms(domains)
    )

    normalized_signals = (
        _normalize_terms(signals)
    )

    normalized_requested = (
        _normalize_terms(
            requested_layers
        )
    )

    trait_terms = _trait_terms(
        persona_projection
    )

    selected: set[str] = set()

    evidence: dict[
        str,
        list[str],
    ] = {
        layer: []
        for layer in LAYER_ORDER
    }

    def apply(
        source: str,
        layers: Iterable[Any],
    ) -> None:
        materialized = tuple(layers)

        _add_layers(
            selected,
            materialized,
        )

        for layer in materialized:
            normalized = str(
                layer
            ).strip().lower()

            evidence[
                normalized
            ].append(source)

    for layer in normalized_requested:
        apply(
            f"explicit:{layer}",
            (layer,),
        )

    for domain in normalized_domains:
        layers = DOMAIN_LAYERS.get(
            domain,
            (),
        )

        if layers:
            apply(
                f"domain:{domain}",
                layers,
            )

    for signal in normalized_signals:
        layers = SIGNAL_LAYERS.get(
            signal,
            (),
        )

        if layers:
            apply(
                f"signal:{signal}",
                layers,
            )

    for term in trait_terms:
        layers = TRAIT_LAYER_HINTS.get(
            term,
            (),
        )

        if layers:
            apply(
                f"trait:{term}",
                layers,
            )

    if not selected:
        apply(
            "default",
            ("general",),
        )

    ordered_layers = [
        layer
        for layer in LAYER_ORDER
        if layer in selected
    ]

    compact_evidence = {
        layer: sorted(
            set(
                evidence[layer]
            )
        )
        for layer in ordered_layers
    }

    canonical = {
        "schema": SCHEMA,
        "owner": OWNER,
        "persona_id": persona_id,
        "persona_composition_digest": (
            persona_projection.get(
                "composition_digest"
            )
        ),
        "domains": list(
            normalized_domains
        ),
        "signals": list(
            normalized_signals
        ),
        "requested_layers": list(
            normalized_requested
        ),
        "layers": ordered_layers,
        "evidence": compact_evidence,
    }

    return {
        **canonical,
        "projection_digest": (
            _digest(canonical)
        ),
        "execution_owner": (
            EXECUTION_OWNER
        ),
        "provider_selection_owner": (
            EXECUTION_OWNER
        ),
        "model_selection_owner": (
            EXECUTION_OWNER
        ),
        "envoy_may_select_provider": False,
        "envoy_may_select_model": False,
        "envoy_may_access_credentials": False,
        "authority_effect": "none",
        "projection_only": True,
    }


def opus_request_projection(
    cognitive_projection: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        cognitive_projection,
        dict,
    ):
        raise CognitiveProjectionError(
            "cognitive projection must "
            "be an object"
        )

    if cognitive_projection.get(
        "schema"
    ) != SCHEMA:
        raise CognitiveProjectionError(
            "unsupported cognitive "
            "projection schema"
        )

    if cognitive_projection.get(
        "owner"
    ) != OWNER:
        raise CognitiveProjectionError(
            "cognitive projection owner "
            "must be envoy"
        )

    layers = cognitive_projection.get(
        "layers"
    )

    if not isinstance(
        layers,
        list,
    ):
        raise CognitiveProjectionError(
            "cognitive projection layers "
            "must be a list"
        )

    _add_layers(
        set(),
        layers,
    )

    return {
        "required_layers": list(
            layers
        ),
        "cognitive_projection": {
            "schema": (
                cognitive_projection[
                    "schema"
                ]
            ),
            "owner": OWNER,
            "persona_id": (
                cognitive_projection[
                    "persona_id"
                ]
            ),
            "projection_digest": (
                cognitive_projection[
                    "projection_digest"
                ]
            ),
            "authority_effect": "none",
        },
    }


def selftest() -> dict[str, Any]:
    persona = {
        "persona_id": DEFAULT_PERSONA_ID,
        "composition_digest": "test",
        "traits": [],
    }

    writing = project_cognitive_layers(
        persona,
        domains=("writing",),
    )

    if writing["layers"] != [
        "instruction",
        "writing",
    ]:
        raise CognitiveProjectionError(
            "writing layer projection failed"
        )

    code = project_cognitive_layers(
        persona,
        domains=("engineering",),
        signals=("implement",),
    )

    expected_code = [
        "reasoning",
        "code",
        "tool",
    ]

    if code["layers"] != expected_code:
        raise CognitiveProjectionError(
            "engineering layer "
            "projection failed"
        )

    first = project_cognitive_layers(
        persona,
        domains=("analysis",),
        signals=("verify",),
    )

    second = project_cognitive_layers(
        persona,
        domains=("analysis",),
        signals=("verify",),
    )

    if first != second:
        raise CognitiveProjectionError(
            "cognitive projection "
            "is not deterministic"
        )

    request = opus_request_projection(
        code
    )

    if request[
        "required_layers"
    ] != expected_code:
        raise CognitiveProjectionError(
            "opus request layer "
            "projection failed"
        )

    for field in (
        "envoy_may_select_provider",
        "envoy_may_select_model",
        "envoy_may_access_credentials",
    ):
        if code[field] is not False:
            raise CognitiveProjectionError(
                "authority boundary failed: "
                f"{field}"
            )

    if (
        code["execution_owner"]
        != EXECUTION_OWNER
        or code[
            "provider_selection_owner"
        ]
        != EXECUTION_OWNER
        or code[
            "model_selection_owner"
        ]
        != EXECUTION_OWNER
    ):
        raise CognitiveProjectionError(
            "opus execution authority "
            "was not preserved"
        )

    return {
        "ok": True,
        "schema": SCHEMA,
        "owner": OWNER,
        "execution_owner": (
            EXECUTION_OWNER
        ),
        "deterministic": True,
        "provider_authority_preserved": True,
        "model_authority_preserved": True,
        "persona_authority_preserved": True,
        "projection_only": True,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )

#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence


SCHEMA = "opus.cognitive.request.v1"

STRATEGIES = (
    "single",
    "fallback",
    "parallel",
    "specialist",
    "adversarial",
    "consensus",
    "refinement",
)


def normalize_request(
    request: Mapping[str, Any],
) -> Dict[str, Any]:
    output = dict(
        request
    )

    text = str(
        output.get("text")
        or output.get("prompt")
        or output.get("message")
        or ""
    ).strip()

    if not text:
        raise ValueError(
            "Opus cognitive request requires text"
        )

    output["text"] = text

    capabilities = output.get(
        "required_capabilities"
    )

    if not capabilities:
        capabilities = [
            "text",
        ]

    elif isinstance(
        capabilities,
        str,
    ):
        capabilities = [
            capabilities,
        ]

    elif not isinstance(
        capabilities,
        Sequence,
    ):
        raise ValueError(
            "required_capabilities must be a sequence"
        )

    normalized_capabilities = sorted(
        {
            str(value).strip().lower()
            for value in capabilities
            if str(value).strip()
        }
    )

    if not normalized_capabilities:
        normalized_capabilities = [
            "text",
        ]

    output[
        "required_capabilities"
    ] = normalized_capabilities

    strategy = output.get(
        "cognitive_strategy"
    )

    if strategy is not None:
        strategy = str(
            strategy
        ).strip().lower()

        if strategy not in STRATEGIES:
            raise ValueError(
                f"Unsupported cognitive strategy: {strategy}"
            )

        output[
            "cognitive_strategy"
        ] = strategy

    output[
        "cognitive_orchestration"
    ] = bool(
        output.get(
            "cognitive_orchestration",
            True,
        )
    )

    output[
        "cognitive_schema"
    ] = SCHEMA

    return output


def validate_result(
    result: Mapping[str, Any],
) -> Dict[str, Any]:
    output = dict(
        result
    )

    if not output.get("ok"):
        raise RuntimeError(
            str(
                output.get("error")
                or "Opus cognitive execution failed"
            )
        )

    text = str(
        output.get("text")
        or ""
    ).strip()

    if not text:
        raise RuntimeError(
            "Opus cognitive execution returned no text"
        )

    output["text"] = text

    lineage = output.get(
        "lineage"
    )

    if not isinstance(
        lineage,
        Mapping,
    ):
        raise RuntimeError(
            "Opus cognitive execution returned no lineage"
        )

    output[
        "cognitive_schema"
    ] = "opus.cognitive.result.v1"

    return output

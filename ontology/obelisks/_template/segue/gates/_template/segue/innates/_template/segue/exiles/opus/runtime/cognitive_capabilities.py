from __future__ import annotations

from typing import Any, Iterable, Mapping


CAPABILITY_ALIASES = {
    "text": "text_inference",
    "text_generation": "text_inference",
    "generate_text": "text_inference",
    "chat": "text_inference",
    "inference": "text_inference",
}


def canonical_capability(
    value: Any,
) -> str:
    capability = str(
        value or ""
    ).strip().lower()

    return CAPABILITY_ALIASES.get(
        capability,
        capability,
    )


def normalized_capabilities(
    values: Iterable[Any] | None,
) -> set[str]:
    if values is None:
        return set()

    if isinstance(
        values,
        str,
    ):
        values = (
            values,
        )

    return {
        canonical_capability(
            value
        )
        for value in values
        if canonical_capability(
            value
        )
    }


def provider_capabilities(
    provider_data: Mapping[str, Any],
) -> set[str]:
    raw = provider_data.get(
        "capabilities"
    )

    if not isinstance(
        raw,
        (list, tuple, set),
    ):
        return set()

    return normalized_capabilities(
        raw
    )


def supports(
    provider_data: Mapping[str, Any],
    required_capabilities: Iterable[Any] | None,
) -> bool:
    required = normalized_capabilities(
        required_capabilities
    )

    if not required:
        return True

    available = provider_capabilities(
        provider_data
    )

    return required.issubset(
        available
    )


def canonical_list(
    values: Iterable[Any] | None,
) -> list[str]:
    return sorted(
        normalized_capabilities(
            values
        )
    )

from __future__ import annotations

from typing import Any, Iterable


schema = "savant.opus.runtime-normalization.v1"


def normalized_strings(
    values: Iterable[Any] | None,
) -> set[str]:
    if values is None:
        return set()

    return {
        str(value).strip().lower()
        for value in values
        if str(value).strip()
    }

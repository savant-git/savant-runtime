from __future__ import annotations

from typing import Any, Callable, Dict, Type


schema = "savant.opus.provider-tool-normalization.v1"


def normalize_tools(
    value: Any,
    *,
    error_type: Type[Exception],
) -> list[Dict[str, Any]]:
    if value is None:
        return []

    if not isinstance(value, list):
        raise error_type(
            "text inference tools must be a list"
        )

    result: list[Dict[str, Any]] = []

    for row in value:
        if not isinstance(row, dict):
            raise error_type(
                "text inference tool definition "
                "must be object"
            )

        name = str(
            row.get("name") or ""
        ).strip()

        if not name:
            raise error_type(
                "text inference tool requires name"
            )

        parameters = row.get("parameters")

        if parameters is None:
            parameters = {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            }

        if not isinstance(parameters, dict):
            raise error_type(
                "text inference tool parameters "
                "must be object"
            )

        result.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": str(
                        row.get("description") or ""
                    ).strip(),
                    "parameters": parameters,
                },
            }
        )

    return result


def make_tool_normalizer(
    error_type: Type[Exception],
) -> Callable[
    [Any],
    list[Dict[str, Any]],
]:
    def bound_normalize_tools(
        value: Any,
    ) -> list[Dict[str, Any]]:
        return normalize_tools(
            value,
            error_type=error_type,
        )

    return bound_normalize_tools

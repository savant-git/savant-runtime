from __future__ import annotations

from typing import Any, Dict


schema = "savant.opus.provider-response-text.v1"


def response_text(
    data: Dict[str, Any],
) -> str:
    direct = data.get(
        "output_text"
    )

    if (
        isinstance(
            direct,
            str,
        )
        and direct.strip()
    ):
        return direct.strip()

    texts: list[str] = []

    for item in data.get(
        "output",
        [],
    ):
        if not isinstance(
            item,
            dict,
        ):
            continue

        for content in item.get(
            "content",
            [],
        ):
            if not isinstance(
                content,
                dict,
            ):
                continue

            text = content.get(
                "text"
            )

            if (
                isinstance(
                    text,
                    str,
                )
                and text
            ):
                texts.append(
                    text
                )

    return "\n".join(
        texts
    ).strip()

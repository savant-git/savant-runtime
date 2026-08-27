#!/usr/bin/env python3

from __future__ import annotations

import json
from typing import Any

from EXILE_DISCOVERY import (
    discover_records,
    validate_discovery,
)


def load(
) -> list[str]:
    """
    Compatibility API.

    Returns canonical Exile names in the
    accepted registry order.
    """
    return [
        record.name
        for record
        in discover_records()
        if record.exists
    ]


def load_projection(
) -> dict[str, Any]:
    discovery = (
        validate_discovery()
    )

    loaded = load()

    payload = {
        "schema": (
            "savant://runtime/"
            "exile-loader/2.0.0"
        ),
        "loaded":
            loaded,
        "loaded_count":
            len(
                loaded
            ),
        "registry_source":
            discovery[
                "registry_source"
            ],
        "registry_digest":
            discovery[
                "registry_digest"
            ],
        "filesystem_defines_population":
            False,
        "mutation_performed":
            False,
        "valid": (
            discovery[
                "valid"
            ]
            and len(
                loaded
            )
            == discovery[
                "expected_count"
            ]
        ),
    }

    return payload


def main() -> int:
    report = (
        load_projection()
    )

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if report[
            "valid"
        ]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

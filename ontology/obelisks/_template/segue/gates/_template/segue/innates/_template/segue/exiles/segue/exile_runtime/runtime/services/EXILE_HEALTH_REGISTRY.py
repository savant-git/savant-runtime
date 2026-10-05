#!/usr/bin/env python3

from __future__ import annotations

import json

from EXILE_RESOURCE_REGISTRY import (
    collect_direct_area,
)


def collect_health():
    return collect_direct_area(
        "health"
    )


def collect():
    return collect_health()


if __name__ == "__main__":
    print(
        json.dumps(
            collect_health(),
            indent=2,
            sort_keys=True,
        )
    )

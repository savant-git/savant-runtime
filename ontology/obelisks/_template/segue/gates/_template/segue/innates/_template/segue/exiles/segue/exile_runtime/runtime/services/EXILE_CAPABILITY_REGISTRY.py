#!/usr/bin/env python3

from __future__ import annotations

import json

from EXILE_RESOURCE_REGISTRY import (
    collect_registry_area,
)


def collect_capabilities():
    return collect_registry_area(
        "capabilities"
    )


def collect():
    return collect_capabilities()


if __name__ == "__main__":
    print(
        json.dumps(
            collect_capabilities(),
            indent=2,
            sort_keys=True,
        )
    )

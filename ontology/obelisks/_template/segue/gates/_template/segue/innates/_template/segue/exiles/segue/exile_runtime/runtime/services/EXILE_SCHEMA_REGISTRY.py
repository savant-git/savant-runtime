#!/usr/bin/env python3

from __future__ import annotations

import json

from EXILE_RESOURCE_REGISTRY import (
    collect_registry_area,
)


def collect():
    return collect_registry_area(
        "schemas"
    )


def collect_schemas():
    return collect()


if __name__ == "__main__":
    print(
        json.dumps(
            collect(),
            indent=2,
            sort_keys=True,
        )
    )

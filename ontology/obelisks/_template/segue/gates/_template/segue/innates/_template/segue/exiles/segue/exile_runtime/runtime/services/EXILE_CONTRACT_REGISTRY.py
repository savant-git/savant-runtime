#!/usr/bin/env python3

from __future__ import annotations

import json

from EXILE_RESOURCE_REGISTRY import (
    collect_registry_area,
)


def collect_contracts():
    return collect_registry_area(
        "contracts"
    )


def collect():
    return collect_contracts()


if __name__ == "__main__":
    print(
        json.dumps(
            collect_contracts(),
            indent=2,
            sort_keys=True,
        )
    )

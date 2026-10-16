#!/usr/bin/env python3

from __future__ import annotations

import json

from EXILE_RESOURCE_REGISTRY import (
    collect_direct_area,
)


def collect_canon():
    return collect_direct_area(
        "canon"
    )


def collect():
    return collect_canon()


if __name__ == "__main__":
    print(
        json.dumps(
            collect_canon(),
            indent=2,
            sort_keys=True,
        )
    )

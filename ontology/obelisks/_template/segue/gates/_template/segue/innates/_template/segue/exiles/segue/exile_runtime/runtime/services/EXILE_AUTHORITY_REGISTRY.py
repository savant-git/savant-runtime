#!/usr/bin/env python3

from __future__ import annotations

import json

from EXILE_RESOURCE_REGISTRY import (
    collect_direct_area,
)


def collect_authority():
    return collect_direct_area(
        "authority"
    )


def collect():
    return collect_authority()


if __name__ == "__main__":
    print(
        json.dumps(
            collect_authority(),
            indent=2,
            sort_keys=True,
        )
    )

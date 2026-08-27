#!/usr/bin/env python3

from __future__ import annotations

import json

from EXILE_RESOURCE_REGISTRY import (
    collect_direct_area,
)


def collect_lineage():
    return collect_direct_area(
        "lineage"
    )


def collect():
    return collect_lineage()


if __name__ == "__main__":
    print(
        json.dumps(
            collect_lineage(),
            indent=2,
            sort_keys=True,
        )
    )

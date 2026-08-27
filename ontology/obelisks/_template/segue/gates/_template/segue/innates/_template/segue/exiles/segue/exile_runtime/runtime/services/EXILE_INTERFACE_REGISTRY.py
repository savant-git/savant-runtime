#!/usr/bin/env python3

from __future__ import annotations

import json

from EXILE_RESOURCE_REGISTRY import (
    collect_direct_area,
)


def collect_interfaces():
    return collect_direct_area(
        "interface"
    )


def collect_interface():
    return collect_interfaces()


def collect():
    return collect_interfaces()


if __name__ == "__main__":
    print(
        json.dumps(
            collect_interfaces(),
            indent=2,
            sort_keys=True,
        )
    )

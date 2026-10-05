#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


canonical_path = Path(
    "/root/savant-runtime/edifices/utility/runtime/"
    "utility_hierarchy.py"
)

if not canonical_path.is_file():
    raise ImportError(
        "canonical utility hierarchy unavailable: "
        f"{canonical_path}"
    )

spec = importlib.util.spec_from_file_location(
    "savant_utility_hierarchy",
    canonical_path,
)

if (
    spec is None
    or spec.loader is None
):
    raise ImportError(
        "cannot load canonical utility hierarchy: "
        f"{canonical_path}"
    )

module = importlib.util.module_from_spec(
    spec
)

sys.modules[
    spec.name
] = module

spec.loader.exec_module(
    module
)

for name in dir(module):
    if name.startswith("__"):
        continue

    globals()[name] = getattr(
        module,
        name,
    )

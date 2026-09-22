#!/usr/bin/env python3
"""
Stable controller for the Savant dimensional archive system.

The controller installs the bounded lexical audit before dispatching into the
dimensional scaffold implementation.
"""

from __future__ import annotations

import sys
from pathlib import Path


SYS_ROOT = Path(
    "/root/savant-runtime/vault/dimensions/sys"
)

if str(SYS_ROOT) not in sys.path:
    sys.path.insert(0, str(SYS_ROOT))

import scaffold
from lexeme_audit import kinship_occurrences


scaffold.kinship_occurrences = kinship_occurrences


if __name__ == "__main__":
    raise SystemExit(scaffold.main())

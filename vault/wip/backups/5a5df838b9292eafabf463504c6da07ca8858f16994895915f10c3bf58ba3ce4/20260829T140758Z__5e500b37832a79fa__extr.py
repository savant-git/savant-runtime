#!/usr/bin/env python3

from __future__ import annotations

import os
from pathlib import Path
import runpy
import sys


program = "extr"
version = "3.0.0"

runtime_root = Path(
    "/root/savant-runtime"
)

legacy_entrypoint = (
    runtime_root
    / "bin"
    / "extract_savant_jsonl.py"
)


def main() -> int:
    if not legacy_entrypoint.is_file():
        print(
            (
                "extr: verified extraction "
                "entrypoint unavailable: "
                f"{legacy_entrypoint}"
            ),
            file=sys.stderr,
        )
        return 1

    os.environ.setdefault(
        "SAVANT_ROOT",
        str(runtime_root),
    )

    sys.argv[0] = "extr"

    runpy.run_path(
        str(legacy_entrypoint),
        run_name="__main__",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

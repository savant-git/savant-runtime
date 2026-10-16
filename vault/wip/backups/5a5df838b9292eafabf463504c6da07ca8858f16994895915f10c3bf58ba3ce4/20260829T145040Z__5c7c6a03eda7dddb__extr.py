#!/usr/bin/env python3

from __future__ import annotations

import json
import os
from pathlib import Path
import runpy
import sys


runtime_root = Path(
    "/root/savant-runtime"
)

verified_chatgpt = (
    runtime_root
    / "bin"
    / "extract_savant_jsonl.py"
)

universal = (
    runtime_root
    / "tools"
    / "extr-enterprise"
    / "runtime"
    / "universal.py"
)


def probable_chatgpt_export(
    path: Path,
) -> bool:
    if path.name.casefold() == (
        "conversations.json"
    ):
        return True

    if path.suffix.casefold() != ".json":
        return False

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            prefix = handle.read(
                262144
            )
    except Exception:
        return False

    lowered = prefix.casefold()

    return (
        '"mapping"'
        in lowered
        and (
            '"current_node"'
            in lowered
            or '"conversation_id"'
            in lowered
        )
    )


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "usage: extr <input> [output] [options...]",
            file=sys.stderr,
        )
        return 2

    input_path = Path(
        os.path.expanduser(
            os.path.expandvars(
                sys.argv[1]
            )
        )
    ).resolve()

    if not input_path.is_file():
        print(
            f"extr: input unavailable: {input_path}",
            file=sys.stderr,
        )
        return 1

    if probable_chatgpt_export(
        input_path
    ):
        if not verified_chatgpt.is_file():
            print(
                "extr: verified ChatGPT "
                "extractor unavailable",
                file=sys.stderr,
            )
            return 1

        os.environ.setdefault(
            "SAVANT_ROOT",
            str(runtime_root),
        )

        sys.argv[0] = "extr"

        runpy.run_path(
            str(
                verified_chatgpt
            ),
            run_name="__main__",
        )

        return 0

    if not universal.is_file():
        print(
            "extr: universal ingestion "
            "substrate unavailable",
            file=sys.stderr,
        )
        return 1

    if len(sys.argv) < 3:
        output_path = (
            input_path.parent
            / (
                input_path.stem
                + ".extr.jsonl"
            )
        )

        sys.argv.insert(
            2,
            str(output_path),
        )

    sys.argv[0] = (
        "extr-universal"
    )

    runpy.run_path(
        str(universal),
        run_name="__main__",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

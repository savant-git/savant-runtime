#!/usr/bin/env python3

from __future__ import annotations

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

extr_runtime = (
    runtime_root
    / "tools"
    / "extr-enterprise"
    / "runtime"
)

universal = (
    extr_runtime
    / "universal.py"
)

pipeline = (
    extr_runtime
    / "pipeline.py"
)


def probable_chatgpt_export(
    path: Path,
) -> bool:
    if (
        path.name.casefold()
        == "conversations.json"
    ):
        return True

    if (
        path.suffix.casefold()
        != ".json"
    ):
        return False

    try:
        with path.open(
            "r",
            encoding="utf-8",
            errors="replace",
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


def execute(
    path: Path,
    program: str,
) -> int:
    if not path.is_file():
        print(
            (
                "extr: runtime "
                f"unavailable: {path}"
            ),
            file=sys.stderr,
        )

        return 1

    sys.argv[0] = program

    try:
        runpy.run_path(
            str(
                path
            ),
            run_name="__main__",
        )

    except SystemExit as error:
        code = error.code

        if code is None:
            return 0

        if isinstance(
            code,
            int,
        ):
            return code

        print(
            str(code),
            file=sys.stderr,
        )

        return 1

    return 0


def main() -> int:
    if len(
        sys.argv
    ) < 2:
        print(
            (
                "usage: extr <input> "
                "[output] [options...]"
            ),
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

    if input_path.is_dir():
        return execute(
            pipeline,
            "extr-pipeline",
        )

    if not input_path.is_file():
        print(
            (
                "extr: input unavailable: "
                f"{input_path}"
            ),
            file=sys.stderr,
        )

        return 1

    if probable_chatgpt_export(
        input_path
    ):
        os.environ.setdefault(
            "SAVANT_ROOT",
            str(
                runtime_root
            ),
        )

        return execute(
            verified_chatgpt,
            "extr",
        )

    if len(
        sys.argv
    ) < 3:
        output = (
            input_path.parent
            / (
                input_path.stem
                + ".extr.jsonl"
            )
        )

        sys.argv.insert(
            2,
            str(
                output
            ),
        )

    return execute(
        universal,
        "extr-universal",
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )ó

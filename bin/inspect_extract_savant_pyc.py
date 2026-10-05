#!/usr/bin/env python3

from __future__ import annotations

import marshal
from pathlib import Path


PYC = Path(
    "/root/savant-runtime/bin/__pycache__/"
    "extract_savant_jsonl.cpython-312.pyc"
)


def main() -> int:
    if not PYC.is_file():
        raise SystemExit(
            f"missing bytecode: {PYC}"
        )

    data = PYC.read_bytes()

    if len(data) < 17:
        raise SystemExit(
            f"invalid or truncated bytecode: {PYC}"
        )

    code = marshal.loads(
        data[16:]
    )

    print(
        "filename:",
        code.co_filename,
    )

    print("\nnames:")

    for name in sorted(
        set(code.co_names)
    ):
        print(name)

    print("\nrelevant constants:")

    found = False

    for value in code.co_consts:
        if not isinstance(
            value,
            str,
        ):
            continue

        if any(
            needle in value
            for needle in (
                "extract_savant",
                "2.0.0",
                "3.0.0",
                "ScoreResult",
                "savant-jsonl",
            )
        ):
            found = True
            print(repr(value))

    if not found:
        print("(none)")

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

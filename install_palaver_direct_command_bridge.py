#!/usr/bin/env python3

from __future__ import annotations

import os
import tempfile
from pathlib import Path


SERVER = Path(
    "/root/savant-runtime/ontology/obelisks/"
    "_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/palaver/"
    "runtime/server.py"
)


def atomic_write(
    path: Path,
    text: str,
) -> None:
    descriptor, temporary = (
        tempfile.mkstemp(
            prefix=(
                path.name
                + "."
            ),
            dir=str(
                path.parent
            ),
        )
    )

    temporary_path = Path(
        temporary
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(
                text
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.chmod(
            temporary_path,
            path.stat().st_mode,
        )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def replace_once(
    text: str,
    old: str,
    new: str,
    label: str,
) -> str:
    count = text.count(
        old
    )

    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly "
            f"one anchor, found {count}"
        )

    return text.replace(
        old,
        new,
        1,
    )


def main() -> int:
    text = SERVER.read_text(
        encoding="utf-8"
    )

    if (
        "install_direct_command_bridge"
        in text
    ):
        print(
            "PALAVER DIRECT COMMAND BRIDGE: "
            "already installed"
        )

        return 0

    function_anchor = '''def install_opus_inference(
    legacy: ModuleType,
) -> None:
'''

    function_replacement = '''def install_direct_command_bridge(
    legacy: ModuleType,
) -> None:
    from direct_command_bridge import (
        install,
    )

    install(
        legacy
    )


def install_opus_inference(
    legacy: ModuleType,
) -> None:
'''

    text = replace_once(
        text,
        function_anchor,
        function_replacement,
        "direct command installer",
    )

    bootstrap_anchor = '''    install_scrybe_context(
        legacy
    )

    install_opus_inference(
        legacy
    )
'''

    bootstrap_replacement = '''    install_scrybe_context(
        legacy
    )

    install_direct_command_bridge(
        legacy
    )

    install_opus_inference(
        legacy
    )
'''

    text = replace_once(
        text,
        bootstrap_anchor,
        bootstrap_replacement,
        "bootstrap direct command bridge",
    )

    atomic_write(
        SERVER,
        text,
    )

    print(
        "PALAVER DIRECT COMMAND BRIDGE: installed"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

#!/usr/bin/env python3

from __future__ import annotations

import os
import tempfile
from pathlib import Path


SERVER = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/palaver/runtime/server.py"
)

MARKER = "PALAVER_SCRYBE_CONTEXT_V1"


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
            f"{label}: expected one anchor, found {count}"
        )

    return text.replace(
        old,
        new,
        1,
    )


def atomic_write(
    path: Path,
    text: str,
) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.scrybe-",
        dir=str(
            path.parent
        ),
    )

    temporary = Path(
        temporary_name
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
            temporary,
            path.stat().st_mode,
        )

        os.replace(
            temporary,
            path,
        )

    except Exception:
        temporary.unlink(
            missing_ok=True
        )
        raise


def main() -> int:
    text = SERVER.read_text(
        encoding="utf-8"
    )

    if MARKER in text:
        print(
            "PALAVER SCRYBE CONTEXT: already installed"
        )
        return 0

    anchor = '''def install_opus_inference(
    legacy: ModuleType,
) -> None:
'''

    replacement = '''# PALAVER_SCRYBE_CONTEXT_V1
def install_scrybe_context(
    legacy: ModuleType,
) -> None:
    from scrybe_bridge import (
        prompt_block,
    )

    def memory_block_through_scrybe(
        message: str,
        limit: int = 8,
    ) -> str:
        return prompt_block(
            message,
            limit=limit,
        )

    legacy.memory_block_for_prompt = (
        memory_block_through_scrybe
    )


def install_opus_inference(
    legacy: ModuleType,
) -> None:
'''

    text = replace_once(
        text,
        anchor,
        replacement,
        "install_scrybe_context",
    )

    bootstrap_anchor = '''    install_envoy(
        legacy
    )

    install_opus_inference(
        legacy
    )
'''

    bootstrap_replacement = '''    install_envoy(
        legacy
    )

    install_scrybe_context(
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
        "bootstrap Scrybe installation",
    )

    status_anchor = '''        "niche_task_context_installed": (
'''

    status_replacement = '''        "scrybe_context_installed": (
            callable(
                getattr(
                    legacy,
                    "memory_block_for_prompt",
                    None,
                )
            )
            and getattr(
                legacy.memory_block_for_prompt,
                "__name__",
                "",
            )
            == "memory_block_through_scrybe"
        ),
        "memory_context_owner": "scrybe",
        "canonical_memory_store": "fluid-canon",
        "niche_task_context_installed": (
'''

    text = replace_once(
        text,
        status_anchor,
        status_replacement,
        "compatibility status",
    )

    atomic_write(
        SERVER,
        text,
    )

    print(
        "PALAVER SCRYBE CONTEXT: installed"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

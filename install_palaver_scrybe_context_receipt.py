#!/usr/bin/env python3

from __future__ import annotations

import os
import tempfile
from pathlib import Path


PALAVER_ROOT = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/palaver"
)

BRIDGE = (
    PALAVER_ROOT
    / "runtime"
    / "scrybe_bridge.py"
)

SERVER = (
    PALAVER_ROOT
    / "runtime"
    / "server.py"
)

MARKER = "PALAVER_SCRYBE_CONTEXT_RECEIPT_V1"


def replace_once(
    text: str,
    old: str,
    new: str,
    label: str,
) -> str:
    count = text.count(old)

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
        prefix=f".{path.name}.context-receipt-",
        dir=str(path.parent),
    )

    temporary = Path(temporary_name)

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())

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


def patch_bridge(
    text: str,
) -> str:
    import_anchor = """import json
import sys
from pathlib import Path
"""

    import_replacement = """import json
import sys
from contextvars import ContextVar
from pathlib import Path
"""

    text = replace_once(
        text,
        import_anchor,
        import_replacement,
        "bridge imports",
    )

    constants_anchor = """DEFAULT_INSTANCE = "lore"
DEFAULT_LIMIT = 8
"""

    constants_replacement = """DEFAULT_INSTANCE = "lore"
DEFAULT_LIMIT = 8

# PALAVER_SCRYBE_CONTEXT_RECEIPT_V1
_LAST_CONTEXT_RECEIPT: ContextVar[
    dict[str, Any] | None
] = ContextVar(
    "palaver_scrybe_context_receipt",
    default=None,
)
"""

    text = replace_once(
        text,
        constants_anchor,
        constants_replacement,
        "context receipt state",
    )

    hydrate_return_anchor = """    return packet


def _memory_line(
"""

    hydrate_return_replacement = """    _LAST_CONTEXT_RECEIPT.set(
        {
            "owner": "scrybe",
            "instance_id": packet.get(
                "instance_id"
            ),
            "canonical_memory_store": (
                "fluid-canon"
            ),
            "digest": packet.get(
                "digest"
            ),
            "memory_count": int(
                packet.get(
                    "memory_count",
                    0,
                )
            ),
            "limit": int(
                packet.get(
                    "limit",
                    limit,
                )
            ),
            "authoritative": False,
            "rebuildable": True,
        }
    )

    return packet


def context_receipt() -> dict[str, Any] | None:
    value = _LAST_CONTEXT_RECEIPT.get()

    if value is None:
        return None

    return dict(value)


def clear_context_receipt() -> None:
    _LAST_CONTEXT_RECEIPT.set(
        None
    )


def _memory_line(
"""

    return replace_once(
        text,
        hydrate_return_anchor,
        hydrate_return_replacement,
        "context receipt capture",
    )


def patch_server(
    text: str,
) -> str:
    import_anchor = """    from scrybe_bridge import (
        prompt_block,
    )
"""

    import_replacement = """    from scrybe_bridge import (
        clear_context_receipt,
        context_receipt,
        prompt_block,
    )
"""

    text = replace_once(
        text,
        import_anchor,
        import_replacement,
        "Scrybe bridge imports",
    )

    install_anchor = """    legacy.memory_block_for_prompt = (
        memory_block_through_scrybe
    )
"""

    install_replacement = """    legacy.memory_block_for_prompt = (
        memory_block_through_scrybe
    )

    legacy.palaver_scrybe_context_receipt = (
        context_receipt
    )

    legacy.palaver_scrybe_clear_context_receipt = (
        clear_context_receipt
    )
"""

    text = replace_once(
        text,
        install_anchor,
        install_replacement,
        "Scrybe receipt bridge installation",
    )

    chat_anchor = """                    try:
                        result = legacy.chat(
                            message
                        )
                    finally:
                        REQUEST_PERSONA_ID.reset(
                            token
                        )
"""

    chat_replacement = """                    legacy.palaver_scrybe_clear_context_receipt()

                    try:
                        result = legacy.chat(
                            message
                        )
                    finally:
                        REQUEST_PERSONA_ID.reset(
                            token
                        )

                    context_receipt = (
                        legacy
                        .palaver_scrybe_context_receipt()
                    )

                    if (
                        isinstance(
                            result,
                            dict,
                        )
                        and isinstance(
                            context_receipt,
                            dict,
                        )
                    ):
                        trace = str(
                            result.get(
                                "trace",
                                "",
                            )
                            or ""
                        ).strip()

                        receipt_trace = (
                            "scrybe context "
                            f"digest={context_receipt.get('digest')} "
                            f"memory_count={context_receipt.get('memory_count')} "
                            f"limit={context_receipt.get('limit')} "
                            "authoritative=false "
                            "rebuildable=true"
                        )

                        result[
                            "trace"
                        ] = "\\n".join(
                            part
                            for part in (
                                trace,
                                receipt_trace,
                            )
                            if part
                        )

                        result[
                            "context_receipt"
                        ] = context_receipt
"""

    text = replace_once(
        text,
        chat_anchor,
        chat_replacement,
        "chat context receipt",
    )

    status_anchor = '''        "memory_context_owner": "scrybe",
'''

    status_replacement = '''        "memory_context_owner": "scrybe",
        "scrybe_context_receipt_installed": (
            callable(
                getattr(
                    legacy,
                    "palaver_scrybe_context_receipt",
                    None,
                )
            )
            and callable(
                getattr(
                    legacy,
                    "palaver_scrybe_clear_context_receipt",
                    None,
                )
            )
        ),
'''

    return replace_once(
        text,
        status_anchor,
        status_replacement,
        "compatibility receipt status",
    )


def main() -> int:
    bridge_text = BRIDGE.read_text(
        encoding="utf-8"
    )

    server_text = SERVER.read_text(
        encoding="utf-8"
    )

    if MARKER in bridge_text:
        print(
            "PALAVER SCRYBE CONTEXT RECEIPT: already installed"
        )
        return 0

    patched_bridge = patch_bridge(
        bridge_text
    )

    patched_server = patch_server(
        server_text
    )

    atomic_write(
        BRIDGE,
        patched_bridge,
    )

    atomic_write(
        SERVER,
        patched_server,
    )

    print(
        "PALAVER SCRYBE CONTEXT RECEIPT: installed"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

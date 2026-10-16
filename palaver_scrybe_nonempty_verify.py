#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(
    "/root/savant-runtime"
).resolve()

PALAVER_RUNTIME = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/palaver/runtime"
)

PALAVER_SERVER = (
    PALAVER_RUNTIME
    / "server.py"
)

TOKEN = (
    "SCRYBE_LIVE_CONTEXT_7F3C91A2"
)

QUERY = (
    "Return only the exact verification token "
    "contained in the retrieved memory context. "
    "Do not add punctuation or explanation."
)


for path in (
    ROOT,
    PALAVER_RUNTIME,
):
    value = str(
        path
    )

    if value not in sys.path:
        sys.path.insert(
            0,
            value,
        )


from runtime.constitution import (
    ConstitutionalRegistry,
)
from runtime.memory import (
    MemoryAssertion,
)
from runtime.scrybe import (
    Scrybe,
)

import scrybe_bridge


def load_palaver_server() -> ModuleType:
    name = (
        "palaver_scrybe_nonempty_test_server"
    )

    spec = (
        importlib.util
        .spec_from_file_location(
            name,
            PALAVER_SERVER,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            "unable to load canonical "
            "Palaver server"
        )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    sys.modules[
        name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def build_test_scrybe() -> Scrybe:
    registry = (
        ConstitutionalRegistry.load(
            ROOT
        )
    )

    base = Scrybe.install(
        registry,
        instance="lore",
    )

    assertion = MemoryAssertion.create(
        identity=(
            "memory:test:palaver:"
            "scrybe-nonempty"
        ),
        memory_type="semantic",
        subject=(
            "Palaver Scrybe integration "
            "verification"
        ),
        content=(
            "The exact verification token is "
            f"{TOKEN}"
        ),
        asserted_by="verification",
        source=(
            "palaver_scrybe_nonempty_verify"
        ),
        occurred_at=(
            "2026-08-12T21:28:00Z"
        ),
        confidence=1.0,
    )

    contributed = (
        base.memory.contribute(
            (
                assertion,
            )
        )
    )

    return Scrybe(
        contributed,
        base.instance,
    )


def main() -> int:
    test_scrybe = (
        build_test_scrybe()
    )

    original_hydrate = (
        scrybe_bridge.hydrate
    )

    def hydrate_from_test_snapshot(
        query: str,
        *,
        limit: int = (
            scrybe_bridge.DEFAULT_LIMIT
        ),
        at: str | None = None,
    ):
        packet = (
            test_scrybe.hydrate(
                query,
                limit=limit,
                at=at,
            )
        )

        if packet.get(
            "authoritative"
        ) is not False:
            raise RuntimeError(
                "test context became authoritative"
            )

        if packet.get(
            "rebuildable"
        ) is not True:
            raise RuntimeError(
                "test context is not rebuildable"
            )

        return packet

    scrybe_bridge.hydrate = (
        hydrate_from_test_snapshot
    )

    try:
        server = (
            load_palaver_server()
        )

        legacy = server.bootstrap()

        context = (
            legacy.memory_block_for_prompt(
                QUERY,
                limit=8,
            )
        )

        if TOKEN not in context:
            raise RuntimeError(
                "verification token missing "
                "from Scrybe prompt context"
            )

        if (
            "SCRYBE MEMORY CONTEXT"
            not in context
        ):
            raise RuntimeError(
                "production Scrybe prompt "
                "formatter was not used"
            )

        if (
            "authority: non-authoritative projection"
            not in context
        ):
            raise RuntimeError(
                "Scrybe authority marker missing"
            )

        result = legacy.chat(
            QUERY
        )

        if not isinstance(
            result,
            dict,
        ):
            raise RuntimeError(
                "Palaver returned invalid "
                "chat result"
            )

        trace = str(
            result.get(
                "trace"
            )
            or ""
        )

        answer = str(
            result.get(
                "answer"
            )
            or ""
        ).strip()

        if (
            "memory attached"
            not in trace
        ):
            raise RuntimeError(
                "Palaver did not attach "
                "Scrybe memory context: "
                f"{trace!r}"
            )

        if (
            "openai ok"
            not in trace
        ):
            raise RuntimeError(
                "Opus inference did not "
                "complete successfully: "
                f"{trace!r}"
            )

        if TOKEN not in answer:
            raise RuntimeError(
                "provider response did not "
                "recover verification token: "
                f"{answer!r}"
            )

        current_registry = (
            ConstitutionalRegistry.load(
                ROOT
            )
        )

        persistent_identity_present = (
            "memory:test:palaver:"
            "scrybe-nonempty"
            in current_registry.ids
        )

        if persistent_identity_present:
            raise RuntimeError(
                "verification memory leaked "
                "into persistent authority"
            )

        print(
            json.dumps(
                {
                    "ok": True,
                    "token": TOKEN,
                    "context_contains_token": (
                        True
                    ),
                    "production_formatter": (
                        True
                    ),
                    "context_authoritative": (
                        False
                    ),
                    "context_rebuildable": (
                        True
                    ),
                    "trace": trace,
                    "answer": answer,
                    "memory_attached": True,
                    "opus_inference": True,
                    "persistent_mutation": (
                        False
                    ),
                    "persistent_identity_present": (
                        False
                    ),
                    "canonical_memory_store": (
                        test_scrybe
                        .instance
                        .canonical_memory_store
                    ),
                    "independent_memory_store": (
                        test_scrybe
                        .instance
                        .independent_memory_store
                    ),
                    "path": [
                        "palaver",
                        "scrybe",
                        "fluid-canon",
                        "opus",
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    finally:
        scrybe_bridge.hydrate = (
            original_hydrate
        )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


runtime = Path(
    "/root/savant-runtime/ontology/obelisks/_template/"
    "segue/gates/_template/segue/innates/_template/segue/"
    "exiles/niche/runtime"
)

sys.path.insert(
    0,
    str(runtime),
)

from task_engine import engine


task_id = (
    "masterplan:lore-fluid-canon-scrybe-integration"
)

terminal_states = {
    "completed",
    "rejected",
    "superseded",
}

verification = Path(
    "/root/savant-runtime/"
    "lore_scrybe_fluid_canon_final_verify.sh"
)

implementation_references = [
    (
        "/root/savant-runtime/ontology/obelisks/_template/"
        "segue/gates/_template/segue/innates/_template/segue/"
        "exiles/lore/runtime/living_canon.py"
    ),
    "/root/savant-runtime/runtime/scrybe/engine.py",
    "/root/savant-runtime/runtime/scrybe/instance.py",
    "/root/savant-runtime/runtime/scrybe/instances/lore.json",
    "/root/savant-runtime/runtime/fluid_canon/engine.py",
    "/root/savant-runtime/runtime/fluid_canon/model.py",
    str(verification),
]

receipts = [
    (
        "focused final verification passed for Lore, Scrybe, "
        "and fluid-canon integration"
    ),
    (
        "Lore retains ownership of canonical-context projection "
        "while Scrybe retains retrieval ownership"
    ),
    (
        "fluid-canon remains the singular canonical store"
    ),
    (
        "Lore reuses Scrybe retrieval rather than creating an "
        "independent ranking engine"
    ),
    (
        "Lore creates no independent memory store"
    ),
    (
        "current, historical, authority, and bounded context "
        "recall are verified"
    ),
    (
        "integration performs no canon mutation and creates no "
        "authority"
    ),
    (
        "canon-system runtime database is present"
    ),
]


def run_verification() -> str:
    if not verification.is_file():
        raise RuntimeError(
            "missing final verification script: "
            + str(verification)
        )

    result = subprocess.run(
        [str(verification)],
        cwd="/root/savant-runtime",
        text=True,
        capture_output=True,
        check=False,
    )

    output = "\n".join(
        part.strip()
        for part in (
            result.stdout,
            result.stderr,
        )
        if part.strip()
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Lore/Scrybe/fluid-canon verification failed:\n"
            + output
        )

    marker = (
        "LORE / SCRYBE / FLUID CANON FINAL INTEGRATION: valid"
    )

    if marker not in result.stdout:
        raise RuntimeError(
            "verification exited successfully but did not emit "
            "the required completion marker"
        )

    return output


def main() -> int:
    verification_output = run_verification()

    task_engine = engine()

    current = task_engine.public_task(
        task_id
    )

    if current["status"] not in terminal_states:
        task_engine.amend(
            task_id,
            {
                "implementation_references":
                    implementation_references,
            },
        )

        current = task_engine.transition(
            task_id,
            "completed",
            receipts=receipts,
            reason=(
                "Lore, fluid-canon, and Scrybe integration is "
                "operational with singular authority-preserving "
                "canonical storage, reused Scrybe retrieval, no "
                "duplicate memory store, and focused final "
                "verification passing."
            ),
        )

    dashboard = task_engine.dashboard()

    ready = dashboard.get(
        "ready_queue",
        [],
    )

    print(
        json.dumps(
            {
                "task": current,
                "verification": {
                    "passed": True,
                    "script": str(verification),
                    "output": verification_output,
                },
                "next": (
                    ready[0]
                    if ready
                    else None
                ),
            },
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

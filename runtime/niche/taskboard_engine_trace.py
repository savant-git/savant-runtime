#!/usr/bin/env python3
"""
savant / niche
bounded task-engine blocking trace

owner: exile:niche
authority_effect: none
mutation_effect: none

Captures the Python stack while the proven-blocking tasks() read path is
executing. The call runs in an isolated child process and is terminated
after the trace is emitted.

No task mutation method is invoked.
"""

from __future__ import annotations

import faulthandler
import importlib.util
import multiprocessing
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any


SAVANT_ROOT = Path("/root/savant-runtime")

NICHE_ROOT = (
    SAVANT_ROOT
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "niche"
)

TASK_ENGINE = (
    NICHE_ROOT
    / "runtime"
    / "task_engine.py"
)

TASKBOARD_ROOT = (
    NICHE_ROOT
    / "apps"
    / "taskboard"
)

TRACE_AFTER_SECONDS = 3.0
KILL_AFTER_SECONDS = 6.0


def prepare_imports() -> None:
    for directory in (
        str(TASK_ENGINE.parent),
        str(TASKBOARD_ROOT),
        str(NICHE_ROOT),
        str(SAVANT_ROOT),
    ):
        if directory not in sys.path:
            sys.path.insert(
                0,
                directory,
            )


def load_module() -> Any:
    prepare_imports()

    spec = importlib.util.spec_from_file_location(
        "savant_niche_task_engine_trace",
        TASK_ENGINE,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"unable to load {TASK_ENGINE}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[spec.name] = module

    spec.loader.exec_module(
        module
    )

    return module


def trace_tasks() -> None:
    faulthandler.enable(
        file=sys.stderr,
        all_threads=True,
    )

    module = load_module()

    factory = getattr(
        module,
        "engine",
    )

    engine = (
        factory()
        if callable(factory)
        else factory
    )

    print(
        "savant niche trace: "
        "engine resolved; entering tasks()",
        file=sys.stderr,
        flush=True,
    )

    faulthandler.dump_traceback_later(
        TRACE_AFTER_SECONDS,
        repeat=False,
        file=sys.stderr,
        exit=False,
    )

    started = time.monotonic()

    try:
        result = engine.tasks()

        faulthandler.cancel_dump_traceback_later()

        print(
            "savant niche trace: "
            f"tasks() returned in "
            f"{time.monotonic() - started:.6f}s; "
            f"type={type(result).__name__}; "
            f"size="
            f"{len(result) if hasattr(result, '__len__') else 'unknown'}",
            file=sys.stderr,
            flush=True,
        )

    finally:
        faulthandler.cancel_dump_traceback_later()


def main() -> int:
    if not TASK_ENGINE.is_file():
        print(
            f"task engine absent: {TASK_ENGINE}",
            file=sys.stderr,
        )

        return 2

    process = multiprocessing.Process(
        target=trace_tasks,
        name="niche-task-read-trace",
        daemon=True,
    )

    process.start()

    process.join(
        KILL_AFTER_SECONDS
    )

    if process.is_alive():
        print(
            "savant niche trace: "
            "tasks() remained blocked after "
            f"{KILL_AFTER_SECONDS:.1f}s; "
            "terminating isolated diagnostic child",
            file=sys.stderr,
            flush=True,
        )

        process.terminate()
        process.join(2.0)

        if process.is_alive():
            os.kill(
                process.pid,
                signal.SIGKILL,
            )

            process.join(2.0)

        return 1

    return (
        process.exitcode
        if process.exitcode is not None
        else 1
    )


if __name__ == "__main__":
    multiprocessing.set_start_method(
        "fork"
    )

    raise SystemExit(
        main()
    )

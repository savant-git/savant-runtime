#!/usr/bin/env python3
"""
savant / niche
task-engine bounded call diagnostic

owner: exile:niche
authority_effect: none
mutation_effect: none

The HTTP evidence shows the server remains responsive while health,
tasks, dashboard, and state calls exceed five seconds. History,
living, living-fabric, and static command delivery complete normally.

This diagnostic imports the current Niche task engine and measures
read-only engine calls independently of HTTP so the blocking call can
be isolated without changing authoritative task state.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import multiprocessing
import os
import sys
import time
import traceback
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

TASKBOARD_ROOT = (
    NICHE_ROOT
    / "apps"
    / "taskboard"
)

TASK_ENGINE = (
    NICHE_ROOT
    / "runtime"
    / "task_engine.py"
)

ALTERNATE_TASK_ENGINE = (
    TASKBOARD_ROOT
    / "task_engine.py"
)

DEFAULT_TIMEOUT = 5.0

READ_ONLY_CANDIDATES = (
    "health",
    "dashboard",
    "state",
    "list_tasks",
    "tasks",
    "get_tasks",
    "snapshot",
    "status",
)


def engine_path() -> Path:
    if TASK_ENGINE.is_file():
        return TASK_ENGINE

    if ALTERNATE_TASK_ENGINE.is_file():
        return ALTERNATE_TASK_ENGINE

    raise FileNotFoundError(
        "current task_engine.py was not found "
        "at either known Niche location"
    )


def load_module(
    path: Path,
):
    module_name = (
        "savant_niche_task_engine_diagnostic"
    )

    spec = (
        importlib.util
        .spec_from_file_location(
            module_name,
            path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            f"unable to load module spec: {path}"
        )

    module = (
        importlib.util
        .module_from_spec(spec)
    )

    sys.modules[module_name] = module

    spec.loader.exec_module(
        module
    )

    return module


def safe_summary(
    value: Any,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": (
            type(value).__name__
        )
    }

    if value is None:
        result["value"] = None
        return result

    if isinstance(
        value,
        (str, int, float, bool),
    ):
        text = str(value)

        result["value"] = (
            text[:1000]
        )

        return result

    if isinstance(
        value,
        dict,
    ):
        result["size"] = len(value)

        result["keys"] = [
            str(key)
            for key in list(
                value.keys()
            )[:50]
        ]

        return result

    if isinstance(
        value,
        (list, tuple, set),
    ):
        result["size"] = len(value)

        return result

    result["repr"] = (
        repr(value)[:1000]
    )

    return result


def callable_inventory(
    target: Any,
) -> list[str]:
    names: list[str] = []

    for name in dir(target):
        if name.startswith("_"):
            continue

        try:
            value = getattr(
                target,
                name,
            )
        except Exception:
            continue

        if callable(value):
            names.append(name)

    return sorted(names)


def resolve_engine(
    module: Any,
) -> tuple[str, Any]:
    if hasattr(
        module,
        "engine",
    ):
        return (
            "module.engine",
            getattr(
                module,
                "engine",
            ),
        )

    return (
        "module",
        module,
    )


def child_call(
    path_text: str,
    method_name: str,
    queue: multiprocessing.Queue,
) -> None:
    started = time.monotonic()

    try:
        path = Path(path_text)

        for directory in (
            str(path.parent),
            str(TASKBOARD_ROOT),
            str(NICHE_ROOT),
            str(SAVANT_ROOT),
        ):
            if (
                directory
                not in sys.path
            ):
                sys.path.insert(
                    0,
                    directory,
                )

        module = load_module(
            path
        )

        owner_name, target = (
            resolve_engine(
                module
            )
        )

        method = getattr(
            target,
            method_name,
        )

        result = method()

        queue.put(
            {
                "ok": True,
                "method": method_name,
                "owner": owner_name,
                "elapsed_ms": round(
                    (
                        time.monotonic()
                        - started
                    )
                    * 1000,
                    3,
                ),
                "result": (
                    safe_summary(
                        result
                    )
                ),
            }
        )

    except Exception as exc:
        queue.put(
            {
                "ok": False,
                "method": method_name,
                "elapsed_ms": round(
                    (
                        time.monotonic()
                        - started
                    )
                    * 1000,
                    3,
                ),
                "error_type": (
                    type(exc).__name__
                ),
                "error": str(exc),
                "traceback": (
                    traceback.format_exc()
                ),
            }
        )


def timed_call(
    path: Path,
    method_name: str,
    timeout: float,
) -> dict[str, Any]:
    queue: multiprocessing.Queue = (
        multiprocessing.Queue(
            maxsize=1
        )
    )

    process = (
        multiprocessing.Process(
            target=child_call,
            args=(
                str(path),
                method_name,
                queue,
            ),
            daemon=True,
        )
    )

    started = time.monotonic()

    process.start()

    process.join(
        timeout
    )

    elapsed_ms = round(
        (
            time.monotonic()
            - started
        )
        * 1000,
        3,
    )

    if process.is_alive():
        process.terminate()
        process.join(2)

        if process.is_alive():
            process.kill()
            process.join(2)

        return {
            "ok": False,
            "method": method_name,
            "timed_out": True,
            "elapsed_ms": elapsed_ms,
            "process_returncode": (
                process.exitcode
            ),
        }

    try:
        result = queue.get_nowait()
    except Exception:
        result = {
            "ok": False,
            "method": method_name,
            "timed_out": False,
            "elapsed_ms": elapsed_ms,
            "process_returncode": (
                process.exitcode
            ),
            "error": (
                "child exited without "
                "returning diagnostic data"
            ),
        }

    return result


def inspect_engine(
    path: Path,
) -> dict[str, Any]:
    for directory in (
        str(path.parent),
        str(TASKBOARD_ROOT),
        str(NICHE_ROOT),
        str(SAVANT_ROOT),
    ):
        if directory not in sys.path:
            sys.path.insert(
                0,
                directory,
            )

    started = time.monotonic()

    module = load_module(
        path
    )

    owner_name, target = (
        resolve_engine(
            module
        )
    )

    return {
        "import_elapsed_ms": round(
            (
                time.monotonic()
                - started
            )
            * 1000,
            3,
        ),
        "owner": owner_name,
        "module_callables": (
            callable_inventory(
                module
            )
        ),
        "engine_callables": (
            callable_inventory(
                target
            )
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
    )

    args = parser.parse_args()

    report: dict[str, Any] = {
        "schema": (
            "savant.niche."
            "task-engine-diagnostic.v1"
        ),
        "authority_effect": "none",
        "mutation_effect": "none",
        "pid": os.getpid(),
        "timeout_seconds": (
            args.timeout
        ),
        "calls": [],
    }

    try:
        path = engine_path()

        report["task_engine"] = (
            str(path)
        )

        inspection = (
            inspect_engine(
                path
            )
        )

        report["inspection"] = (
            inspection
        )

        available = set(
            inspection[
                "engine_callables"
            ]
        )

        candidates = [
            name
            for name
            in READ_ONLY_CANDIDATES
            if name in available
        ]

        report[
            "read_only_candidates"
        ] = candidates

        for name in candidates:
            report["calls"].append(
                timed_call(
                    path,
                    name,
                    args.timeout,
                )
            )

        timed_out = [
            result["method"]
            for result
            in report["calls"]
            if result.get(
                "timed_out"
            )
        ]

        errors = [
            result["method"]
            for result
            in report["calls"]
            if (
                not result.get("ok")
                and not result.get(
                    "timed_out"
                )
            )
        ]

        report["summary"] = {
            "candidate_count": (
                len(candidates)
            ),
            "timed_out": timed_out,
            "errors": errors,
        }

        report["ok"] = (
            not timed_out
            and not errors
        )

    except Exception as exc:
        report["ok"] = False

        report["fatal"] = {
            "error_type": (
                type(exc).__name__
            ),
            "error": str(exc),
            "traceback": (
                traceback.format_exc()
            ),
        }

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if report.get("ok")
        else 1
    )


if __name__ == "__main__":
    multiprocessing.set_start_method(
        "fork"
    )

    raise SystemExit(
        main()
    )

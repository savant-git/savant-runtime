#!/usr/bin/env python3
"""
savant / niche
task-engine resolver diagnostic

owner: exile:niche
authority_effect: none
mutation_effect: none

The previous diagnostic established that module.engine is itself callable,
not an already-instantiated engine object. This diagnostic resolves that
factory in an isolated child process, inventories the returned object, and
times only zero-required-argument read-oriented methods.

No transition, create, update, delete, lease, release, completion, blocking,
deferral, admission, or other mutation method is invoked.
"""

from __future__ import annotations

import argparse
import importlib.util
import inspect
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

DEFAULT_TIMEOUT = 5.0

READ_NAMES = {
    "health",
    "dashboard",
    "state",
    "list_tasks",
    "tasks",
    "get_tasks",
    "snapshot",
    "status",
    "taskboard_meta",
}

MUTATION_TOKENS = (
    "create",
    "update",
    "delete",
    "remove",
    "transition",
    "complete",
    "block",
    "defer",
    "lease",
    "release",
    "admit",
    "accept",
    "reject",
    "write",
    "save",
    "append",
    "mutate",
    "set_",
    "start",
    "claim",
)


def prepare_imports() -> None:
    for directory in (
        str(TASK_ENGINE.parent),
        str(TASKBOARD_ROOT),
        str(NICHE_ROOT),
        str(SAVANT_ROOT),
    ):
        if directory not in sys.path:
            sys.path.insert(0, directory)


def load_module() -> Any:
    prepare_imports()

    spec = importlib.util.spec_from_file_location(
        "savant_niche_task_engine_resolver",
        TASK_ENGINE,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"unable to load {TASK_ENGINE}"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    return module


def signature_text(value: Any) -> str:
    try:
        return str(inspect.signature(value))
    except Exception as exc:
        return f"<unavailable: {type(exc).__name__}: {exc}>"


def zero_required_arguments(value: Any) -> bool:
    try:
        signature = inspect.signature(value)
    except Exception:
        return False

    for parameter in signature.parameters.values():
        if parameter.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        if parameter.name in (
            "self",
            "cls",
        ):
            continue

        if parameter.default is inspect.Parameter.empty:
            return False

    return True


def safe_summary(value: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": type(value).__name__,
    }

    if value is None:
        result["value"] = None
        return result

    if isinstance(value, (str, int, float, bool)):
        result["value"] = str(value)[:1000]
        return result

    if isinstance(value, dict):
        result["size"] = len(value)
        result["keys"] = [
            str(key)
            for key in list(value.keys())[:50]
        ]
        return result

    if isinstance(value, (list, tuple, set)):
        result["size"] = len(value)
        return result

    result["repr"] = repr(value)[:1000]
    return result


def resolve_child(
    queue: multiprocessing.Queue,
) -> None:
    started = time.monotonic()

    try:
        module = load_module()

        factory = getattr(
            module,
            "engine",
            None,
        )

        if factory is None:
            raise RuntimeError(
                "task_engine module has no engine attribute"
            )

        report: dict[str, Any] = {
            "factory_type": type(factory).__name__,
            "factory_callable": callable(factory),
            "factory_signature": signature_text(factory),
        }

        if not callable(factory):
            resolved = factory
        else:
            if not zero_required_arguments(factory):
                report["resolved"] = False
                report["reason"] = (
                    "engine callable requires arguments; "
                    "diagnostic will not invent them"
                )
                queue.put(report)
                return

            factory_started = time.monotonic()
            resolved = factory()

            report["factory_elapsed_ms"] = round(
                (time.monotonic() - factory_started) * 1000,
                3,
            )

        report["resolved"] = True
        report["resolved_type"] = type(resolved).__name__

        methods: list[dict[str, Any]] = []

        for name in sorted(dir(resolved)):
            if name.startswith("_"):
                continue

            try:
                value = getattr(resolved, name)
            except Exception as exc:
                methods.append(
                    {
                        "name": name,
                        "attribute_error": (
                            f"{type(exc).__name__}: {exc}"
                        ),
                    }
                )
                continue

            if not callable(value):
                continue

            lowered = name.lower()

            methods.append(
                {
                    "name": name,
                    "signature": signature_text(value),
                    "zero_required_arguments": (
                        zero_required_arguments(value)
                    ),
                    "mutation_name_guard": any(
                        token in lowered
                        for token in MUTATION_TOKENS
                    ),
                    "read_candidate": (
                        name in READ_NAMES
                    ),
                }
            )

        report["methods"] = methods
        report["elapsed_ms"] = round(
            (time.monotonic() - started) * 1000,
            3,
        )

        queue.put(report)

    except Exception as exc:
        queue.put(
            {
                "resolved": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "elapsed_ms": round(
                    (time.monotonic() - started) * 1000,
                    3,
                ),
            }
        )


def resolve(
    timeout: float,
) -> dict[str, Any]:
    queue: multiprocessing.Queue = multiprocessing.Queue(maxsize=1)

    process = multiprocessing.Process(
        target=resolve_child,
        args=(queue,),
        daemon=True,
    )

    process.start()
    process.join(timeout)

    if process.is_alive():
        process.terminate()
        process.join(2)

        if process.is_alive():
            process.kill()
            process.join(2)

        return {
            "resolved": False,
            "timed_out": True,
            "phase": "engine_factory_resolution",
            "timeout_seconds": timeout,
        }

    try:
        return queue.get_nowait()
    except Exception:
        return {
            "resolved": False,
            "timed_out": False,
            "process_returncode": process.exitcode,
            "error": (
                "resolver child exited without diagnostic output"
            ),
        }


def call_child(
    method_name: str,
    queue: multiprocessing.Queue,
) -> None:
    started = time.monotonic()

    try:
        module = load_module()
        factory = getattr(module, "engine")

        resolved = (
            factory()
            if callable(factory)
            else factory
        )

        method = getattr(
            resolved,
            method_name,
        )

        result = method()

        queue.put(
            {
                "method": method_name,
                "ok": True,
                "elapsed_ms": round(
                    (time.monotonic() - started) * 1000,
                    3,
                ),
                "result": safe_summary(result),
            }
        )

    except Exception as exc:
        queue.put(
            {
                "method": method_name,
                "ok": False,
                "elapsed_ms": round(
                    (time.monotonic() - started) * 1000,
                    3,
                ),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
        )


def timed_call(
    method_name: str,
    timeout: float,
) -> dict[str, Any]:
    queue: multiprocessing.Queue = multiprocessing.Queue(maxsize=1)

    process = multiprocessing.Process(
        target=call_child,
        args=(
            method_name,
            queue,
        ),
        daemon=True,
    )

    started = time.monotonic()
    process.start()
    process.join(timeout)

    elapsed_ms = round(
        (time.monotonic() - started) * 1000,
        3,
    )

    if process.is_alive():
        process.terminate()
        process.join(2)

        if process.is_alive():
            process.kill()
            process.join(2)

        return {
            "method": method_name,
            "ok": False,
            "timed_out": True,
            "elapsed_ms": elapsed_ms,
        }

    try:
        return queue.get_nowait()
    except Exception:
        return {
            "method": method_name,
            "ok": False,
            "timed_out": False,
            "elapsed_ms": elapsed_ms,
            "process_returncode": process.exitcode,
            "error": (
                "call child exited without diagnostic output"
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
            "task-engine-resolver-diagnostic.v1"
        ),
        "authority_effect": "none",
        "mutation_effect": "none",
        "task_engine": str(TASK_ENGINE),
        "pid": os.getpid(),
        "timeout_seconds": args.timeout,
        "calls": [],
    }

    if not TASK_ENGINE.is_file():
        report["ok"] = False
        report["error"] = "task_engine.py absent"

        print(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
            )
        )

        return 2

    resolution = resolve(
        args.timeout
    )

    report["resolution"] = resolution

    if not resolution.get("resolved"):
        report["ok"] = False

        print(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    safe_methods: list[str] = []

    for method in resolution.get(
        "methods",
        [],
    ):
        if (
            method.get("read_candidate")
            and method.get(
                "zero_required_arguments"
            )
            and not method.get(
                "mutation_name_guard"
            )
        ):
            safe_methods.append(
                method["name"]
            )

    report["read_only_candidates"] = safe_methods

    for method_name in safe_methods:
        report["calls"].append(
            timed_call(
                method_name,
                args.timeout,
            )
        )

    report["summary"] = {
        "resolved_type": resolution.get(
            "resolved_type"
        ),
        "candidate_count": len(
            safe_methods
        ),
        "timed_out": [
            call["method"]
            for call in report["calls"]
            if call.get("timed_out")
        ],
        "errors": [
            call["method"]
            for call in report["calls"]
            if (
                not call.get("ok")
                and not call.get(
                    "timed_out"
                )
            )
        ],
    }

    report["ok"] = (
        not report["summary"]["timed_out"]
        and not report["summary"]["errors"]
    )

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    multiprocessing.set_start_method(
        "fork"
    )

    raise SystemExit(
        main()
    )

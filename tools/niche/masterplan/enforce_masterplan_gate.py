#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

GRAPH_PATH = (
    ROOT
    / "authority"
    / "task-graph"
    / "masterplan.json"
)

MASTERPLANCTL = (
    ROOT
    / "bin"
    / "masterplanctl"
)

RUNTIME_ROOT = (
    ROOT
    / "runtime"
    / "masterplan"
    / "gate"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "gate"
)

AGENT_CONTEXT_PATH = (
    RUNTIME_ROOT
    / "agent-context.json"
)

LEASE_PATH = (
    RUNTIME_ROOT
    / "active-lease.json"
)

VOLATILE_FIELDS = {
    "generated_at",
    "issued_at",
    "expires_at",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
    "timestamp",
}


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")


def canonical_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(value)
    ).hexdigest()


def deterministic_projection(
    value: Any,
) -> Any:
    if isinstance(value, dict):
        return {
            key: deterministic_projection(child)
            for key, child in sorted(
                value.items(),
                key=lambda item: item[0],
            )
            if key not in VOLATILE_FIELDS
        }

    if isinstance(value, list):
        return [
            deterministic_projection(child)
            for child in value
        ]

    if isinstance(value, tuple):
        return tuple(
            deterministic_projection(child)
            for child in value
        )

    return value


def sha256_path(
    path: Path,
) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def load_json(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(value, dict):
        raise ValueError(
            f"Expected JSON object: {path}"
        )

    return value


def atomic_write_text(
    path: Path,
    value: str,
    mode: int = 0o644,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )

    temporary_path = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(value)
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.chmod(
            temporary_path,
            mode,
        )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_write_json(
    path: Path,
    value: Any,
    mode: int = 0o644,
) -> None:
    atomic_write_text(
        path,
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        mode,
    )


def relative_path(
    path: Path,
) -> str:
    try:
        return path.relative_to(
            ROOT
        ).as_posix()

    except ValueError:
        return str(path)


def resolve_path(
    value: str,
) -> Path:
    path = Path(value).expanduser()

    if not path.is_absolute():
        path = ROOT / path

    return path.resolve()


def normalize_task_id(
    value: str,
) -> str:
    normalized = re.sub(
        r"[^A-Za-z0-9._-]+",
        "-",
        value.strip(),
    ).upper()

    normalized = re.sub(
        r"-+",
        "-",
        normalized,
    ).strip("-")

    if not normalized.startswith("SAV-"):
        normalized = "SAV-" + normalized

    return normalized


def task_map(
    graph: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    records = graph.get(
        "records",
        [],
    )

    if not isinstance(records, list):
        raise ValueError(
            "Task graph records are invalid."
        )

    return {
        record["id"]: record
        for record in records
        if (
            isinstance(record, dict)
            and isinstance(
                record.get("id"),
                str,
            )
        )
    }


def dependency_map(
    graph: dict[str, Any],
) -> dict[str, tuple[str, ...]]:
    values: dict[str, set[str]] = {}

    for segue in graph.get(
        "segues",
        [],
    ):
        if not isinstance(segue, dict):
            continue

        if segue.get("type") != "depends_on":
            continue

        source = segue.get("source")
        target = segue.get("target")

        if (
            isinstance(source, str)
            and isinstance(target, str)
        ):
            values.setdefault(
                source,
                set(),
            ).add(target)

    return {
        key: tuple(sorted(children))
        for key, children in sorted(
            values.items()
        )
    }


def completion_status(
    record: dict[str, Any],
) -> bool:
    return record.get("status") in {
        "completed",
        "archived",
        "superseded",
    }


def executable(
    graph: dict[str, Any],
    record: dict[str, Any],
) -> tuple[bool, tuple[str, ...]]:
    records = task_map(graph)

    authority = record.get(
        "authority"
    )

    authority_state = (
        authority.get("state")
        if isinstance(authority, dict)
        else None
    )

    if authority_state not in {
        "accepted",
        "authoritative",
    }:
        return False, (
            "task authority is not accepted",
        )

    if record.get("status") not in {
        "accepted",
        "ready",
        "active",
        "reopened",
    }:
        return False, (
            (
                "task status is not executable: "
                f"{record.get('status')}"
            ),
        )

    unmet: list[str] = []

    for dependency in dependency_map(
        graph
    ).get(
        record["id"],
        (),
    ):
        dependency_record = records.get(
            dependency
        )

        if (
            dependency_record is None
            or not completion_status(
                dependency_record
            )
        ):
            unmet.append(dependency)

    if unmet:
        return False, tuple(
            f"unmet dependency: {value}"
            for value in sorted(unmet)
        )

    return True, ()


def priority_key(
    record: dict[str, Any],
) -> tuple[int, int, str]:
    priority = record.get(
        "priority"
    )

    if not isinstance(priority, dict):
        return 999, 999999, str(
            record.get(
                "id",
                "",
            )
        )

    band = str(
        priority.get(
            "band",
            "P999",
        )
    )

    match = re.match(
        r"^P([0-9]+)([A-Z]*)$",
        band,
    )

    if match:
        number = int(
            match.group(1)
        )

        suffix = match.group(2)

        suffix_value = sum(
            (
                ord(character)
                - ord("A")
                + 1
            )
            * (index + 1)
            for index, character in enumerate(
                suffix
            )
        )

    else:
        number = 999
        suffix_value = 999

    ordinal = int(
        priority.get(
            "ordinal",
            999999,
        )
    )

    return (
        number * 1000 + suffix_value,
        ordinal,
        str(
            record.get(
                "id",
                "",
            )
        ),
    )


def selected_task(
    graph: dict[str, Any],
) -> dict[str, Any] | None:
    records = task_map(graph)

    candidates: list[
        dict[str, Any]
    ] = []

    for record in records.values():
        passed, _ = executable(
            graph,
            record,
        )

        if passed:
            candidates.append(record)

    if not candidates:
        return None

    return sorted(
        candidates,
        key=priority_key,
    )[0]


def task_closure(
    graph: dict[str, Any],
    task_id: str,
) -> tuple[str, ...]:
    dependencies = dependency_map(
        graph
    )

    visited: set[str] = set()
    pending = [
        task_id
    ]

    while pending:
        current = pending.pop()

        if current in visited:
            continue

        visited.add(current)

        for dependency in dependencies.get(
            current,
            (),
        ):
            pending.append(dependency)

    return tuple(sorted(visited))


def derive_allowed_paths(
    record: dict[str, Any],
) -> tuple[str, ...]:
    values: set[str] = set()

    for output in record.get(
        "outputs",
        [],
    ):
        if not isinstance(output, str):
            continue

        path = resolve_path(output)

        try:
            values.add(
                path.relative_to(
                    ROOT
                ).as_posix()
            )

        except ValueError:
            continue

    extensions = record.get(
        "extensions"
    )

    if isinstance(extensions, dict):
        source_record = extensions.get(
            "source_record"
        )

        if isinstance(
            source_record,
            dict,
        ):
            for output in source_record.get(
                "outputs",
                [],
            ):
                if not isinstance(
                    output,
                    str,
                ):
                    continue

                path = resolve_path(output)

                try:
                    values.add(
                        path.relative_to(
                            ROOT
                        ).as_posix()
                    )

                except ValueError:
                    continue

    return tuple(sorted(values))


def build_context(
    graph: dict[str, Any],
) -> dict[str, Any]:
    selected = selected_task(
        graph
    )

    graph_value_digest = digest(
        deterministic_projection(
            graph
        )
    )

    if selected is None:
        return {
            "schema": (
                "savant://niche/masterplan/"
                "agent-context/1.0.0"
            ),
            "generated_at": utc_now(),
            "graph": {
                "path": relative_path(
                    GRAPH_PATH
                ),
                "sha256": sha256_path(
                    GRAPH_PATH
                ),
                "digest": graph_value_digest,
            },
            "selected_task": None,
            "allowed_task_ids": [],
            "allowed_paths": [],
            "passed": False,
            "failure": {
                "code": (
                    "masterplan.no_executable_task"
                ),
                "message": (
                    "No accepted executable task exists."
                ),
            },
        }

    closure = task_closure(
        graph,
        selected["id"],
    )

    records = task_map(graph)

    allowed_paths: set[str] = set()

    for task_id in closure:
        record = records.get(task_id)

        if record is None:
            continue

        allowed_paths.update(
            derive_allowed_paths(
                record
            )
        )

    context: dict[str, Any] = {
        "schema": (
            "savant://niche/masterplan/"
            "agent-context/1.0.0"
        ),
        "generated_at": utc_now(),
        "graph": {
            "path": relative_path(
                GRAPH_PATH
            ),
            "sha256": sha256_path(
                GRAPH_PATH
            ),
            "digest": graph_value_digest,
        },
        "governing_rule": (
            "Work only on the selected task, its explicit "
            "dependencies, and declared output paths unless "
            "an accepted override decision exists."
        ),
        "selected_task": selected,
        "allowed_task_ids": list(
            closure
        ),
        "allowed_paths": sorted(
            allowed_paths
        ),
        "prohibited": [
            "silent priority override",
            "silent task completion",
            "authority mutation through projection",
            "editing unrelated subsystem files",
            "deleting task history",
            "converting observed work into accepted authority",
        ],
        "passed": True,
    }

    context["digest"] = digest(
        deterministic_projection(
            context
        )
    )

    return context


def path_within(
    child: str,
    parent: str,
) -> bool:
    child_path = resolve_path(child)
    parent_path = resolve_path(parent)

    try:
        child_path.relative_to(
            parent_path
        )

        return True

    except ValueError:
        return False


def authorize_paths(
    context: dict[str, Any],
    requested_paths: list[str],
) -> dict[str, Any]:
    allowed_paths = [
        str(value)
        for value in context.get(
            "allowed_paths",
            [],
        )
    ]

    results: list[
        dict[str, Any]
    ] = []

    for requested in requested_paths:
        resolved = resolve_path(
            requested
        )

        try:
            relative = resolved.relative_to(
                ROOT
            ).as_posix()

        except ValueError:
            results.append(
                {
                    "requested": requested,
                    "resolved": str(
                        resolved
                    ),
                    "passed": False,
                    "reason": (
                        "path escapes Savant root"
                    ),
                }
            )

            continue

        matched = [
            allowed
            for allowed in allowed_paths
            if (
                relative == allowed
                or path_within(
                    relative,
                    allowed,
                )
                or path_within(
                    allowed,
                    relative,
                )
            )
        ]

        results.append(
            {
                "requested": requested,
                "resolved": relative,
                "matched": matched,
                "passed": bool(matched),
                "reason": (
                    ""
                    if matched
                    else (
                        "path is outside selected task outputs"
                    )
                ),
            }
        )

    return {
        "passed": all(
            result["passed"]
            for result in results
        ),
        "results": results,
    }


def build_lease(
    context: dict[str, Any],
    *,
    agent: str,
    requested_paths: list[str],
    ttl_minutes: int,
) -> dict[str, Any]:
    authorization = authorize_paths(
        context,
        requested_paths,
    )

    issued = dt.datetime.now(
        dt.timezone.utc
    ).replace(
        microsecond=0
    )

    expires = issued + dt.timedelta(
        minutes=ttl_minutes
    )

    selected = context.get(
        "selected_task"
    )

    lease: dict[str, Any] = {
        "schema": (
            "savant://niche/masterplan/"
            "execution-lease/1.0.0"
        ),
        "issued_at": issued.isoformat(),
        "expires_at": expires.isoformat(),
        "agent": agent,
        "graph_digest": context.get(
            "graph",
            {},
        ).get(
            "digest"
        ),
        "context_digest": context.get(
            "digest"
        ),
        "task_id": (
            selected.get("id")
            if isinstance(
                selected,
                dict,
            )
            else None
        ),
        "requested_paths": requested_paths,
        "authorization": authorization,
        "passed": (
            context.get("passed")
            is True
            and authorization["passed"]
        ),
    }

    lease["lease_id"] = (
        "lease-"
        + digest(
            deterministic_projection(
                lease
            )
        )[:24]
    )

    lease["digest"] = digest(
        deterministic_projection(
            lease
        )
    )

    return lease


def validate_lease(
    lease: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    now = dt.datetime.now(
        dt.timezone.utc
    )

    try:
        expires = dt.datetime.fromisoformat(
            str(
                lease["expires_at"]
            )
        )

    except Exception:
        return {
            "passed": False,
            "reason": (
                "lease expiration is invalid"
            ),
        }

    selected = context.get(
        "selected_task"
    )

    current_task_id = (
        selected.get("id")
        if isinstance(
            selected,
            dict,
        )
        else None
    )

    checks = {
        "lease_passed": (
            lease.get("passed")
            is True
        ),
        "not_expired": (
            expires > now
        ),
        "graph_matches": (
            lease.get(
                "graph_digest"
            )
            == context.get(
                "graph",
                {},
            ).get(
                "digest"
            )
        ),
        "context_matches": (
            lease.get(
                "context_digest"
            )
            == context.get(
                "digest"
            )
        ),
        "task_matches": (
            lease.get("task_id")
            == current_task_id
        ),
    }

    return {
        "passed": all(
            checks.values()
        ),
        "checks": checks,
        "lease_id": lease.get(
            "lease_id"
        ),
        "task_id": lease.get(
            "task_id"
        ),
    }


def emit_report(
    operation: str,
    payload: dict[str, Any],
) -> None:
    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = timestamp()

    report = {
        "operation": operation,
        "generated_at": utc_now(),
        **payload,
    }

    report["digest"] = digest(
        deterministic_projection(
            report
        )
    )

    atomic_write_json(
        REPORT_ROOT
        / f"{run_id}__{operation}.json",
        report,
    )

    atomic_write_json(
        REPORT_ROOT
        / "latest.json",
        report,
    )


def load_graph() -> dict[str, Any]:
    if not GRAPH_PATH.is_file():
        raise FileNotFoundError(
            GRAPH_PATH
        )

    return load_json(
        GRAPH_PATH
    )


def command_context() -> int:
    graph = load_graph()

    context = build_context(
        graph
    )

    atomic_write_json(
        AGENT_CONTEXT_PATH,
        context,
    )

    emit_report(
        "context",
        {
            "passed": context.get(
                "passed",
                False,
            ),
            "context": {
                "path": relative_path(
                    AGENT_CONTEXT_PATH
                ),
                "digest": context.get(
                    "digest"
                ),
            },
            "selected_task": context.get(
                "selected_task"
            ),
        },
    )

    print(
        json.dumps(
            context,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if context.get("passed")
        else 1
    )


def command_authorize(
    paths: list[str],
) -> int:
    graph = load_graph()

    context = build_context(
        graph
    )

    result = authorize_paths(
        context,
        paths,
    )

    payload = {
        "passed": result["passed"],
        "selected_task": context.get(
            "selected_task"
        ),
        "authorization": result,
    }

    emit_report(
        "authorize",
        payload,
    )

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if result["passed"]
        else 1
    )


def command_lease(
    agent: str,
    paths: list[str],
    ttl_minutes: int,
) -> int:
    graph = load_graph()

    context = build_context(
        graph
    )

    atomic_write_json(
        AGENT_CONTEXT_PATH,
        context,
    )

    lease = build_lease(
        context,
        agent=agent,
        requested_paths=paths,
        ttl_minutes=ttl_minutes,
    )

    atomic_write_json(
        LEASE_PATH,
        lease,
    )

    emit_report(
        "lease",
        {
            "passed": lease["passed"],
            "lease": {
                "path": relative_path(
                    LEASE_PATH
                ),
                "lease_id": lease[
                    "lease_id"
                ],
                "digest": lease["digest"],
            },
            "authorization": lease[
                "authorization"
            ],
        },
    )

    print(
        json.dumps(
            lease,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if lease["passed"]
        else 1
    )


def command_validate() -> int:
    graph = load_graph()

    context = build_context(
        graph
    )

    if not LEASE_PATH.is_file():
        result = {
            "passed": False,
            "reason": (
                "active lease does not exist"
            ),
        }

    else:
        lease = load_json(
            LEASE_PATH
        )

        result = validate_lease(
            lease,
            context,
        )

    emit_report(
        "validate",
        result,
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if result["passed"]
        else 1
    )


def command_revoke() -> int:
    existed = LEASE_PATH.is_file()

    if existed:
        LEASE_PATH.unlink()

    result = {
        "passed": (
            not LEASE_PATH.exists()
        ),
        "revoked": existed,
        "lease_path": relative_path(
            LEASE_PATH
        ),
    }

    emit_report(
        "revoke",
        result,
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if result["passed"]
        else 1
    )


def command_status() -> int:
    graph = load_graph()

    context = build_context(
        graph
    )

    lease = (
        load_json(
            LEASE_PATH
        )
        if LEASE_PATH.is_file()
        else None
    )

    validation = (
        validate_lease(
            lease,
            context,
        )
        if isinstance(
            lease,
            dict,
        )
        else {
            "passed": False,
            "reason": (
                "active lease does not exist"
            ),
        }
    )

    result = {
        "passed": context.get(
            "passed",
            False,
        ),
        "graph": context.get(
            "graph"
        ),
        "selected_task": context.get(
            "selected_task"
        ),
        "allowed_task_ids": context.get(
            "allowed_task_ids"
        ),
        "allowed_paths": context.get(
            "allowed_paths"
        ),
        "context_path": relative_path(
            AGENT_CONTEXT_PATH
        ),
        "lease_path": relative_path(
            LEASE_PATH
        ),
        "lease_exists": (
            LEASE_PATH.is_file()
        ),
        "lease_validation": validation,
    }

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if result["passed"]
        else 1
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Enforce the authoritative Masterplan before "
            "an execution agent edits Savant."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "context"
    )

    authorize_parser = (
        subparsers.add_parser(
            "authorize"
        )
    )

    authorize_parser.add_argument(
        "paths",
        nargs="+",
    )

    lease_parser = subparsers.add_parser(
        "lease"
    )

    lease_parser.add_argument(
        "--agent",
        required=True,
    )

    lease_parser.add_argument(
        "--ttl-minutes",
        type=int,
        default=60,
    )

    lease_parser.add_argument(
        "paths",
        nargs="+",
    )

    subparsers.add_parser(
        "validate"
    )

    subparsers.add_parser(
        "revoke"
    )

    subparsers.add_parser(
        "status"
    )

    arguments = parser.parse_args()

    try:
        if arguments.command == "context":
            return command_context()

        if arguments.command == "authorize":
            return command_authorize(
                arguments.paths
            )

        if arguments.command == "lease":
            if arguments.ttl_minutes < 1:
                raise ValueError(
                    "Lease TTL must be at least one minute."
                )

            return command_lease(
                arguments.agent,
                arguments.paths,
                arguments.ttl_minutes,
            )

        if arguments.command == "validate":
            return command_validate()

        if arguments.command == "revoke":
            return command_revoke()

        if arguments.command == "status":
            return command_status()

        return 2

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "enforce_masterplan_gate"
                    ),
                    "passed": False,
                    "error": {
                        "type": type(
                            exc
                        ).__name__,
                        "message": str(
                            exc
                        ),
                    },
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

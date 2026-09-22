#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(
    "/root/savant-runtime"
).resolve()

SEARCH_FABRIC = (
    ROOT
    / "runtime"
    / "palaver"
    / "search"
    / "search_fabric.py"
)

_BOUND_LEGACY: ModuleType | None = None


class PalaverToolBrokerError(
    RuntimeError
):
    pass


def bind(
    legacy: ModuleType,
) -> None:
    global _BOUND_LEGACY

    if not isinstance(
        legacy,
        ModuleType,
    ):
        raise PalaverToolBrokerError(
            "Palaver tool broker requires "
            "legacy module binding"
        )

    required = (
        "list_directory_payload",
        "read_file_payload",
        "graph_snapshot",
        "patch_review_pending_payload",
        "patch_review_create_payload",
        "patch_review_apply_payload",
    )

    missing = tuple(
        name
        for name in required
        if not callable(
            getattr(
                legacy,
                name,
                None,
            )
        )
    )

    if missing:
        raise PalaverToolBrokerError(
            "Palaver tool broker missing "
            "required surfaces: "
            + ", ".join(
                missing
            )
        )

    _BOUND_LEGACY = legacy


def is_bound() -> bool:
    return (
        _BOUND_LEGACY
        is not None
    )


def _legacy() -> ModuleType:
    if _BOUND_LEGACY is None:
        raise PalaverToolBrokerError(
            "Palaver tool broker "
            "is not bound"
        )

    return _BOUND_LEGACY


def _inside_root(
    value: str,
) -> Path:
    text = str(
        value
        or ""
    ).strip()

    if not text:
        raise PalaverToolBrokerError(
            "path is required"
        )

    candidate = Path(
        text
    )

    if not candidate.is_absolute():
        candidate = (
            ROOT
            / candidate
        )

    candidate = candidate.resolve()

    if (
        candidate != ROOT
        and ROOT not in candidate.parents
    ):
        raise PalaverToolBrokerError(
            "path escapes Savant root"
        )

    return candidate


def _relative(
    path: Path,
) -> str:
    return str(
        path.relative_to(
            ROOT
        )
    )


def _sha256(
    path: Path,
) -> str:
    value = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        while True:
            block = handle.read(
                1024 * 1024
            )

            if not block:
                break

            value.update(
                block
            )

    return value.hexdigest()


def tool_schemas() -> list[
    dict[str, Any]
]:
    return [
        {
            "name": "list_files",
            "description": (
                "List files and directories inside "
                "the Savant runtime through Palaver's "
                "bounded filesystem surface."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Path relative to "
                            "/root/savant-runtime. "
                            "Empty means the root."
                        ),
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "read_file",
            "description": (
                "Read a Savant runtime file through "
                "Palaver's bounded file reader."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                    },
                },
                "required": [
                    "path",
                ],
                "additionalProperties": False,
            },
        },
        {
            "name": "stat_file",
            "description": (
                "Read bounded metadata and SHA-256 "
                "for one Savant runtime file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                    },
                },
                "required": [
                    "path",
                ],
                "additionalProperties": False,
            },
        },
        {
            "name": "search_runtime",
            "description": (
                "Search Savant using the existing "
                "Palaver search fabric."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                    },
                },
                "required": [
                    "query",
                ],
                "additionalProperties": False,
            },
        },
        {
            "name": "retrieve_memory",
            "description": (
                "Retrieve relevant canonical context "
                "through Scrybe."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 30,
                    },
                },
                "required": [
                    "query",
                ],
                "additionalProperties": False,
            },
        },
        {
            "name": "graph_snapshot",
            "description": (
                "Read Palaver's current runtime "
                "graph projection."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
        {
            "name": "list_pending_patches",
            "description": (
                "List pending Palaver patch-review "
                "proposals."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
        {
            "name": "propose_file_patch",
            "description": (
                "Create a Palaver patch-review "
                "proposal containing the complete "
                "replacement text for one Savant "
                "runtime file. Proposal creation "
                "does not directly mutate the target."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                    },
                    "after": {
                        "type": "string",
                    },
                },
                "required": [
                    "path",
                    "after",
                ],
                "additionalProperties": False,
            },
        },
        {
            "name": "apply_patch",
            "description": (
                "Apply an existing Palaver patch "
                "proposal through Coda's durable "
                "mutation path."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "patch_id": {
                        "type": "string",
                    },
                },
                "required": [
                    "patch_id",
                ],
                "additionalProperties": False,
            },
        },
        {
            "name": "run_validation",
            "description": (
                "Run one bounded Savant validation "
                "operation. Supported operations are "
                "python_compile, bash_syntax, "
                "bash_execute, and execute_file. "
                "No shell expression evaluation, "
                "pipelines, redirection, command "
                "substitution, or arbitrary shell "
                "command execution is available."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": [
                            "python_compile",
                            "bash_syntax",
                            "bash_execute",
                            "execute_file",
                        ],
                    },
                    "paths": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                        "maxItems": 24,
                    },
                    "path": {
                        "type": "string",
                    },
                    "arguments": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                        "maxItems": 24,
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 180,
                    },
                },
                "required": [
                    "operation",
                ],
                "additionalProperties": False,
            },
        },
    ]


def _require_string(
    arguments: dict[str, Any],
    name: str,
) -> str:
    value = str(
        arguments.get(
            name
        )
        or ""
    ).strip()

    if not value:
        raise PalaverToolBrokerError(
            f"{name} is required"
        )

    return value


def _search_runtime(
    query: str,
) -> dict[str, Any]:
    if not SEARCH_FABRIC.is_file():
        raise PalaverToolBrokerError(
            "Palaver search fabric missing: "
            + str(
                SEARCH_FABRIC
            )
        )

    process = subprocess.run(
        [
            sys.executable,
            str(
                SEARCH_FABRIC
            ),
            query,
        ],
        cwd=str(
            ROOT
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=False,
    )

    if process.returncode != 0:
        raise PalaverToolBrokerError(
            "search fabric failed: "
            + process.stderr[
                -2000:
            ].strip()
        )

    output = process.stdout.strip()

    if not output:
        return {
            "query": query,
            "count": 0,
            "results": [],
        }

    try:
        payload = json.loads(
            output
        )
    except json.JSONDecodeError as exc:
        raise PalaverToolBrokerError(
            "search fabric returned "
            "invalid JSON"
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise PalaverToolBrokerError(
            "search fabric returned "
            "non-object payload"
        )

    return payload


def _stat_file(
    value: str,
) -> dict[str, Any]:
    path = _inside_root(
        value
    )

    if not path.is_file():
        raise PalaverToolBrokerError(
            "file does not exist: "
            + str(
                path
            )
        )

    stat = path.stat()

    return {
        "path": _relative(
            path
        ),
        "absolute_path": str(
            path
        ),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "mode": oct(
            stat.st_mode
            & 0o7777
        ),
        "executable": bool(
            stat.st_mode
            & 0o111
        ),
        "sha256": _sha256(
            path
        ),
    }


def _bounded_arguments(
    arguments: dict[str, Any],
) -> list[str]:
    raw_arguments = arguments.get(
        "arguments",
        [],
    )

    if not isinstance(
        raw_arguments,
        list,
    ):
        raise PalaverToolBrokerError(
            "execution arguments must "
            "be a list"
        )

    if len(
        raw_arguments
    ) > 24:
        raise PalaverToolBrokerError(
            "execution argument bound "
            "exceeded"
        )

    return [
        str(
            value
        )
        for value
        in raw_arguments
    ]


def _run_validation(
    arguments: dict[str, Any],
) -> dict[str, Any]:
    operation = _require_string(
        arguments,
        "operation",
    )

    timeout = int(
        arguments.get(
            "timeout_seconds",
            60,
        )
    )

    if (
        timeout < 1
        or timeout > 180
    ):
        raise PalaverToolBrokerError(
            "validation timeout must be "
            "between 1 and 180 seconds"
        )

    if operation == "python_compile":
        raw_paths = arguments.get(
            "paths"
        )

        if (
            not isinstance(
                raw_paths,
                list,
            )
            or not raw_paths
        ):
            raise PalaverToolBrokerError(
                "python_compile requires "
                "non-empty paths"
            )

        if len(
            raw_paths
        ) > 24:
            raise PalaverToolBrokerError(
                "python_compile path bound "
                "exceeded"
            )

        paths = [
            _inside_root(
                str(
                    value
                )
            )
            for value in raw_paths
        ]

        for path in paths:
            if not path.is_file():
                raise PalaverToolBrokerError(
                    "compile target missing: "
                    + str(
                        path
                    )
                )

        command = [
            sys.executable,
            "-m",
            "py_compile",
            *[
                str(
                    path
                )
                for path in paths
            ],
        ]

    elif operation == "bash_syntax":
        path = _inside_root(
            _require_string(
                arguments,
                "path",
            )
        )

        if not path.is_file():
            raise PalaverToolBrokerError(
                "bash syntax target missing: "
                + str(
                    path
                )
            )

        command = [
            "bash",
            "-n",
            str(
                path
            ),
        ]

    elif operation == "bash_execute":
        path = _inside_root(
            _require_string(
                arguments,
                "path",
            )
        )

        if not path.is_file():
            raise PalaverToolBrokerError(
                "bash execution target missing: "
                + str(
                    path
                )
            )

        command = [
            "bash",
            str(
                path
            ),
            *_bounded_arguments(
                arguments
            ),
        ]

    elif operation == "execute_file":
        path = _inside_root(
            _require_string(
                arguments,
                "path",
            )
        )

        if not path.is_file():
            raise PalaverToolBrokerError(
                "execution target missing: "
                + str(
                    path
                )
            )

        if not os.access(
            path,
            os.X_OK,
        ):
            raise PalaverToolBrokerError(
                "execution target is not "
                "executable: "
                + str(
                    path
                )
            )

        command = [
            str(
                path
            ),
            *_bounded_arguments(
                arguments
            ),
        ]

    else:
        raise PalaverToolBrokerError(
            "unsupported validation "
            "operation: "
            + operation
        )

    process = subprocess.run(
        command,
        cwd=str(
            ROOT
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )

    return {
        "operation": operation,
        "command": command,
        "returncode": (
            process.returncode
        ),
        "stdout": (
            process.stdout[
                -50000:
            ]
        ),
        "stderr": (
            process.stderr[
                -50000:
            ]
        ),
        "passed": (
            process.returncode
            == 0
        ),
    }


def execute(
    legacy: ModuleType,
    name: str,
    arguments: dict[str, Any] | None,
) -> dict[str, Any]:
    tool_name = str(
        name
    ).strip()

    values = dict(
        arguments
        or {}
    )

    if tool_name == "list_files":
        path = str(
            values.get(
                "path"
            )
            or ""
        ).strip()

        result = (
            legacy
            .list_directory_payload(
                path
            )
        )

    elif tool_name == "read_file":
        result = (
            legacy
            .read_file_payload(
                _require_string(
                    values,
                    "path",
                )
            )
        )

    elif tool_name == "stat_file":
        result = _stat_file(
            _require_string(
                values,
                "path",
            )
        )

    elif tool_name == "search_runtime":
        result = _search_runtime(
            _require_string(
                values,
                "query",
            )
        )

    elif tool_name == "retrieve_memory":
        from scrybe_bridge import (
            hydrate,
        )

        limit = int(
            values.get(
                "limit",
                8,
            )
        )

        if (
            limit < 0
            or limit > 30
        ):
            raise PalaverToolBrokerError(
                "retrieval limit must be "
                "between 0 and 30"
            )

        result = hydrate(
            _require_string(
                values,
                "query",
            ),
            limit=limit,
        )

    elif tool_name == "graph_snapshot":
        result = (
            legacy
            .graph_snapshot()
        )

    elif tool_name == "list_pending_patches":
        result = (
            legacy
            .patch_review_pending_payload()
        )

    elif tool_name == "propose_file_patch":
        result = (
            legacy
            .patch_review_create_payload(
                _require_string(
                    values,
                    "path",
                ),
                str(
                    values.get(
                        "after"
                    )
                    or ""
                ),
            )
        )

    elif tool_name == "apply_patch":
        result = (
            legacy
            .patch_review_apply_payload(
                _require_string(
                    values,
                    "patch_id",
                )
            )
        )

    elif tool_name == "run_validation":
        result = _run_validation(
            values
        )

    else:
        raise PalaverToolBrokerError(
            "unknown Palaver tool: "
            + tool_name
        )

    return {
        "ok": True,
        "tool": tool_name,
        "arguments": values,
        "result": result,
        "owner": "palaver",
        "mutation_owner": (
            "coda"
            if tool_name
            == "apply_patch"
            else None
        ),
        "authority_effect": "none",
    }


def execute_bound(
    name: str,
    arguments: dict[str, Any] | None,
) -> dict[str, Any]:
    try:
        return execute(
            _legacy(),
            name,
            arguments,
        )

    except Exception as exc:
        return {
            "ok": False,
            "tool": str(
                name
            ),
            "arguments": dict(
                arguments
                or {}
            ),
            "error": str(
                exc
            ),
            "owner": "palaver",
            "authority_effect": "none",
        }


def status() -> dict[str, Any]:
    schemas = tool_schemas()

    return {
        "schema": (
            "savant://palaver/"
            "tool-broker/1.2.0"
        ),
        "owner": "palaver",
        "bound": is_bound(),
        "tool_count": len(
            schemas
        ),
        "tools": [
            row["name"]
            for row in schemas
        ],
        "filesystem_bounded": True,
        "validation_bounded": True,
        "bash_execution_bounded": True,
        "shell_expression_execution": False,
        "search_owner": "palaver",
        "retrieval_owner": "scrybe",
        "patch_review_owner": "palaver",
        "mutation_owner": "coda",
        "unrestricted_shell": False,
        "authoritative": False,
        "authority_effect": "none",
    }


def main() -> int:
    print(
        json.dumps(
            status(),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

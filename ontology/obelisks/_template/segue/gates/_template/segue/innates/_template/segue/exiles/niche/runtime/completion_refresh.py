#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


owner = "exile:niche"

schema = (
    "savant://runtime/niche/"
    "completion-refresh/1.0.0"
)

root = Path(
    "/root/savant-runtime"
)

niche_runtime = (
    root
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
    / "runtime"
)

completion_engine = (
    niche_runtime
    / "completion_engine.py"
)

decomposition_reconciler = (
    niche_runtime
    / "decomposition_reconciler.py"
)


class CompletionRefreshError(
    RuntimeError
):
    pass


def run_json(
    command: Sequence[str],
) -> dict[str, Any]:
    completed = subprocess.run(
        list(command),
        check=False,
        capture_output=True,
        text=True,
    )

    stdout = (
        completed.stdout
        or ""
    ).strip()

    stderr = (
        completed.stderr
        or ""
    ).strip()

    if completed.returncode != 0:
        raise CompletionRefreshError(
            json.dumps(
                {
                    "command":
                        list(command),

                    "returncode":
                        completed.returncode,

                    "stdout":
                        stdout,

                    "stderr":
                        stderr,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )

    if not stdout:
        raise CompletionRefreshError(
            "component returned no json output: "
            + " ".join(command)
        )

    try:
        payload = json.loads(
            stdout
        )

    except json.JSONDecodeError as exc:
        raise CompletionRefreshError(
            "component returned invalid json: "
            + " ".join(command)
            + f": {exc}"
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise CompletionRefreshError(
            "component returned non-object json: "
            + " ".join(command)
        )

    return payload


def completion_command(
    action: str,
    *,
    depth: int,
    discover: bool = False,
) -> list[str]:
    command = [
        sys.executable,
        str(
            completion_engine
        ),
        action,
        "--depth",
        str(depth),
    ]

    if discover:
        command.append(
            "--discover"
        )

    return command


def decomposition_command(
    action: str,
) -> list[str]:
    return [
        sys.executable,
        str(
            decomposition_reconciler
        ),
        action,
    ]


def preview(
    *,
    depth: int,
    discover: bool,
) -> dict[str, Any]:
    completion = run_json(
        completion_command(
            "preview",
            depth=depth,
            discover=discover,
        )
    )

    decomposition = run_json(
        decomposition_command(
            "preview"
        )
    )

    return {
        "schema":
            schema,

        "owner":
            owner,

        "authority_effect":
            "none",

        "depth":
            depth,

        "discover":
            discover,

        "completion":
            completion,

        "decomposition":
            decomposition,

        "refresh_order": [
            "completion-apply",
            "decomposition-apply",
            "completion-project",
            "completion-health",
            "decomposition-health",
        ],
    }


def refresh(
    *,
    depth: int,
    discover: bool,
) -> dict[str, Any]:
    completion_apply = run_json(
        completion_command(
            "apply",
            depth=depth,
            discover=discover,
        )
    )

    decomposition_apply = run_json(
        decomposition_command(
            "apply"
        )
    )

    completion_project = run_json(
        completion_command(
            "project",
            depth=depth,
            discover=False,
        )
    )

    completion_health = run_json(
        completion_command(
            "health",
            depth=depth,
            discover=False,
        )
    )

    decomposition_health = run_json(
        decomposition_command(
            "health"
        )
    )

    completion_healthy = bool(
        completion_health.get(
            "healthy",
            False,
        )
    )

    decomposition_healthy = bool(
        decomposition_health.get(
            "healthy",
            False,
        )
    )

    lineage_reconciled = bool(
        decomposition_health.get(
            "lineage_reconciled",
            False,
        )
    )

    failed_count = int(
        completion_apply.get(
            "apply",
            {},
        ).get(
            "failed_count",
            0,
        )
    )

    healthy = (
        completion_healthy
        and decomposition_healthy
        and lineage_reconciled
        and failed_count == 0
    )

    return {
        "schema":
            schema,

        "owner":
            owner,

        "authority_effect":
            "authoritative-task-refresh",

        "depth":
            depth,

        "discover":
            discover,

        "healthy":
            healthy,

        "completion_apply":
            completion_apply,

        "decomposition_apply":
            decomposition_apply,

        "completion_project":
            completion_project,

        "completion_health":
            completion_health,

        "decomposition_health":
            decomposition_health,

        "invariants": {
            "completion_healthy":
                completion_healthy,

            "decomposition_healthy":
                decomposition_healthy,

            "lineage_reconciled":
                lineage_reconciled,

            "completion_failures":
                failed_count,

            "projection_after_reconciliation":
                True,
        },
    }


def health(
    *,
    depth: int,
) -> dict[str, Any]:
    completion = run_json(
        completion_command(
            "health",
            depth=depth,
            discover=False,
        )
    )

    decomposition = run_json(
        decomposition_command(
            "health"
        )
    )

    completion_healthy = bool(
        completion.get(
            "healthy",
            False,
        )
    )

    decomposition_healthy = bool(
        decomposition.get(
            "healthy",
            False,
        )
    )

    lineage_reconciled = bool(
        decomposition.get(
            "lineage_reconciled",
            False,
        )
    )

    return {
        "schema":
            schema,

        "owner":
            owner,

        "authority_effect":
            "none",

        "depth":
            depth,

        "healthy": (
            completion_healthy
            and decomposition_healthy
            and lineage_reconciled
        ),

        "completion_healthy":
            completion_healthy,

        "decomposition_healthy":
            decomposition_healthy,

        "lineage_reconciled":
            lineage_reconciled,

        "completion":
            completion,

        "decomposition":
            decomposition,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Deterministic Niche completion "
            "refresh orchestration."
        )
    )

    parser.add_argument(
        "command",
        choices=(
            "preview",
            "refresh",
            "health",
        ),
    )

    parser.add_argument(
        "--depth",
        type=int,
        choices=(
            1,
            2,
            3,
            4,
        ),
        default=3,
    )

    parser.add_argument(
        "--discover",
        action="store_true",
        help=(
            "permit completion_engine marker "
            "discovery during authoritative refresh"
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        if args.command == "preview":
            payload = preview(
                depth=args.depth,
                discover=args.discover,
            )

            exit_code = 0

        elif args.command == "refresh":
            payload = refresh(
                depth=args.depth,
                discover=args.discover,
            )

            exit_code = (
                0
                if payload[
                    "healthy"
                ]
                else 1
            )

        elif args.command == "health":
            payload = health(
                depth=args.depth,
            )

            exit_code = (
                0
                if payload[
                    "healthy"
                ]
                else 1
            )

        else:
            return 2

    except CompletionRefreshError as exc:
        payload = {
            "schema":
                schema,

            "owner":
                owner,

            "healthy":
                False,

            "error":
                str(exc),
        }

        exit_code = 1

    print(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    return exit_code


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

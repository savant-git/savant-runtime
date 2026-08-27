#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

VERIFY = (
    ROOT
    / "bin"
    / "masterplan-verify"
)


def execute() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(VERIFY),
            "--strict",
        ],
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )


def parse_payload(
    completed: subprocess.CompletedProcess[str],
) -> dict[str, Any]:
    try:
        value = json.loads(
            completed.stdout
        )
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            json.dumps(
                {
                    "returncode": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise RuntimeError(
            "Verification output is not a JSON object."
        )

    return value


def failed_stage(
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    stages = payload.get(
        "stages",
        [],
    )

    if not isinstance(
        stages,
        list,
    ):
        return None

    for stage in stages:
        if (
            isinstance(
                stage,
                dict,
            )
            and stage.get(
                "passed"
            )
            is False
        ):
            return stage

    return None


def main() -> int:
    try:
        completed = execute()
        payload = parse_payload(
            completed
        )

        stage = failed_stage(
            payload
        )

        result = {
            "operation": (
                "show_masterplan_verification_failure"
            ),
            "passed": payload.get(
                "passed"
            )
            is True,
            "verification_returncode": (
                completed.returncode
            ),
            "statistics": payload.get(
                "statistics"
            ),
            "failed_stage": stage,
            "files": payload.get(
                "files"
            ),
            "tests": payload.get(
                "tests"
            ),
        }

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "show_masterplan_verification_failure"
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
        if result[
            "passed"
        ]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

#!/usr/bin/env python3

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from runtime_engine import (
    EXECUTION_ORDER,
    RuntimeEngine,
)


ROOT = Path(
    __file__
).resolve().parent

LEXICON_ROOT = ROOT.parent

REQUIRED_PATHS = [
    LEXICON_ROOT
    / "bin"
    / "lexiconctl",
    LEXICON_ROOT
    / "bin"
    / "ontologyctl",
    LEXICON_ROOT
    / "bin"
    / "kindredctl",
    LEXICON_ROOT
    / "bin"
    / "instancectl",
    LEXICON_ROOT
    / "bin"
    / "seguectl",
    LEXICON_ROOT
    / "bin"
    / "projectionctl",
    LEXICON_ROOT
    / "bin"
    / "constitutionctl",
]


def add_issue(
    issues: list[dict[str, Any]],
    code: str,
    message: str,
    severity: str = "error",
    reference: str | None = None,
    value: Any = None,
) -> None:

    issue: dict[str, Any] = {
        "code": code,
        "message": message,
        "severity": severity,
    }

    if reference:

        issue[
            "reference"
        ] = reference

    if value is not None:

        issue[
            "value"
        ] = value

    issues.append(
        issue
    )


def validate() -> list[dict[str, Any]]:

    issues: list[
        dict[str, Any]
    ] = []

    for path in REQUIRED_PATHS:

        if not path.exists():

            add_issue(
                issues,
                "runtime.path.missing",
                "Required runtime executable is missing",
                reference=str(
                    path
                ),
            )

            continue

        if not path.is_file():

            add_issue(
                issues,
                "runtime.path.not_file",
                "Runtime executable path is not a file",
                reference=str(
                    path
                ),
            )

        if not os.access(
            path,
            os.X_OK,
        ):

            add_issue(
                issues,
                "runtime.path.not_executable",
                "Runtime executable is not executable",
                reference=str(
                    path
                ),
            )

    engine = RuntimeEngine()

    status = engine.status()

    if not status[
        "ready"
    ]:

        add_issue(
            issues,
            "runtime.status.not_ready",
            "Runtime subsystem status is not ready",
            value=status,
        )

    if status[
        "execution_order"
    ] != EXECUTION_ORDER:

        add_issue(
            issues,
            "runtime.order.invalid",
            "Runtime execution order differs from authority",
            value={
                "expected": EXECUTION_ORDER,
                "actual": status[
                    "execution_order"
                ],
            },
        )

    validation = engine.validate(
        stop_on_failure=False
    )

    if not validation[
        "passed"
    ]:

        for subsystem, result in (
            validation[
                "results"
            ].items()
        ):

            if result[
                "passed"
            ]:

                continue

            add_issue(
                issues,
                "runtime.subsystem.validation_failure",
                "Subsystem validation failed",
                reference=subsystem,
                value={
                    "returncode": result[
                        "returncode"
                    ],
                    "stdout": result[
                        "stdout"
                    ],
                    "stderr": result[
                        "stderr"
                    ],
                },
            )

    return issues


def main() -> int:

    try:

        issues = validate()

    except Exception as error:

        print(
            json.dumps(
                {
                    "valid": False,
                    "error_count": 1,
                    "warning_count": 0,
                    "issues": [
                        {
                            "code": (
                                "runtime_validator."
                                "runtime_failure"
                            ),
                            "severity": "error",
                            "message": str(
                                error
                            ),
                            "exception": type(
                                error
                            ).__name__,
                        }
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    errors = [
        issue
        for issue in issues
        if issue.get(
            "severity"
        ) == "error"
    ]

    warnings = [
        issue
        for issue in issues
        if issue.get(
            "severity"
        ) == "warning"
    ]

    print(
        json.dumps(
            {
                "valid": not errors,
                "error_count": len(
                    errors
                ),
                "warning_count": len(
                    warnings
                ),
                "issues": issues,
            },
            indent=2,
            sort_keys=True,
        )
    )

    return (
        1
        if errors
        else 0
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )

#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

PYTHON = ROOT / "bin" / "identity-quality-python"

INSPECTOR = (
    ROOT
    / "tools"
    / "niche"
    / "masterplan"
    / "inspect_duplicate_segues.py"
)

PLANNER = (
    ROOT
    / "tools"
    / "niche"
    / "masterplan"
    / "plan_duplicate_segue_reconciliation.py"
)

PROPOSER = (
    ROOT
    / "tools"
    / "niche"
    / "masterplan"
    / "propose_duplicate_segue_reconciliation_decision.py"
)

ACCEPTER = (
    ROOT
    / "tools"
    / "niche"
    / "masterplan"
    / "accept_duplicate_segue_reconciliation_decision.py"
)

APPLIER = (
    ROOT
    / "tools"
    / "niche"
    / "masterplan"
    / "apply_duplicate_segue_reconciliation.py"
)

STATE_CHECKER = (
    ROOT
    / "tools"
    / "niche"
    / "masterplan"
    / "check_segue_reconciliation_state.py"
)

ACCEPTANCE_REPORT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "decision-acceptance"
    / "latest.json"
)

COMMANDS_AFTER_APPLY = (
    (
        ROOT
        / "bin"
        / "masterplan-replay",
        "strict",
    ),
    (
        ROOT
        / "bin"
        / "masterplan-integrity-tree",
        "refresh-verify",
    ),
    (
        ROOT
        / "bin"
        / "masterplan-manifest",
        "persist-all",
    ),
    (
        ROOT
        / "bin"
        / "masterplan-policy",
        "verify",
    ),
    (
        ROOT
        / "bin"
        / "masterplan-verify",
        "--strict",
    ),
)


class ReconciliationWorkflowError(RuntimeError):
    pass


def execute(
    command: list[str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )


def run_json(
    command: list[str],
    *,
    require_success: bool = True,
) -> dict[str, Any]:
    completed = execute(
        command
    )

    try:
        payload = json.loads(
            completed.stdout
        )

    except json.JSONDecodeError as exc:
        raise ReconciliationWorkflowError(
            json.dumps(
                {
                    "command": command,
                    "returncode": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise ReconciliationWorkflowError(
            f"Command returned non-object JSON: {command}"
        )

    if (
        require_success
        and (
            completed.returncode != 0
            or payload.get("passed") is False
        )
    ):
        raise ReconciliationWorkflowError(
            json.dumps(
                {
                    "command": command,
                    "returncode": completed.returncode,
                    "payload": payload,
                    "stderr": completed.stderr,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )

    return payload


def load_json(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(
        value,
        dict,
    ):
        raise ReconciliationWorkflowError(
            f"Expected JSON object: {path}"
        )

    return value


def resolve_decision_id() -> str:
    if not ACCEPTANCE_REPORT.is_file():
        raise FileNotFoundError(
            ACCEPTANCE_REPORT
        )

    report = load_json(
        ACCEPTANCE_REPORT
    )

    candidates = (
        report.get("decision_id"),
        report.get("id"),
    )

    for candidate in candidates:
        if isinstance(
            candidate,
            str,
        ) and candidate:
            return candidate

    nested = report.get(
        "decision"
    )

    if isinstance(
        nested,
        dict,
    ):
        candidate = nested.get(
            "id"
        )

        if isinstance(
            candidate,
            str,
        ) and candidate:
            return candidate

    raise ReconciliationWorkflowError(
        "Accepted decision report contains no decision identifier."
    )


def duplicate_count(
    inspection: dict[str, Any],
) -> int:
    value = inspection.get(
        "duplicate_relationship_count"
    )

    if not isinstance(
        value,
        int,
    ):
        raise ReconciliationWorkflowError(
            "Inspection contains no duplicate relationship count."
        )

    return value


def run_post_apply_verification() -> list[dict[str, Any]]:
    results: list[
        dict[str, Any]
    ] = []

    for command in COMMANDS_AFTER_APPLY:
        completed = execute(
            [
                str(command[0]),
                *command[1:],
            ]
        )

        result = {
            "command": [
                str(command[0]),
                *command[1:],
            ],
            "returncode": completed.returncode,
            "passed": completed.returncode == 0,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

        results.append(
            result
        )

        if not result[
            "passed"
        ]:
            break

    return results


def main() -> int:
    try:
        initial = run_json(
            [
                str(PYTHON),
                str(INSPECTOR),
            ]
        )

        initial_duplicates = duplicate_count(
            initial
        )

        if initial_duplicates == 0:
            verification = run_post_apply_verification()

            result = {
                "operation": (
                    "reconcile_duplicate_segues_current"
                ),
                "passed": all(
                    stage["passed"]
                    for stage in verification
                ),
                "changed": False,
                "initial": initial,
                "final": initial,
                "verification": verification,
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

        plan = run_json(
            [
                str(PYTHON),
                str(PLANNER),
            ]
        )

        proposal = run_json(
            [
                str(PYTHON),
                str(PROPOSER),
            ]
        )

        acceptance = run_json(
            [
                str(PYTHON),
                str(ACCEPTER),
                "--accept",
            ]
        )

        decision_id = resolve_decision_id()

        preview = run_json(
            [
                str(PYTHON),
                str(APPLIER),
                decision_id,
                "--plan",
            ]
        )

        application = run_json(
            [
                str(PYTHON),
                str(APPLIER),
                decision_id,
            ]
        )

        final = run_json(
            [
                str(PYTHON),
                str(INSPECTOR),
            ]
        )

        final_duplicates = duplicate_count(
            final
        )

        state = run_json(
            [
                str(PYTHON),
                str(STATE_CHECKER),
            ],
            require_success=False,
        )

        verification = run_post_apply_verification()

        passed = all(
            (
                final_duplicates == 0,
                application.get(
                    "applied"
                )
                is True,
                all(
                    stage["passed"]
                    for stage in verification
                ),
            )
        )

        result = {
            "operation": (
                "reconcile_duplicate_segues_current"
            ),
            "passed": passed,
            "changed": True,
            "decision_id": decision_id,
            "initial": initial,
            "plan": plan,
            "proposal": proposal,
            "acceptance": acceptance,
            "preview": preview,
            "application": application,
            "final": final,
            "state": state,
            "verification": verification,
        }

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "reconcile_duplicate_segues_current"
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
        if result["passed"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

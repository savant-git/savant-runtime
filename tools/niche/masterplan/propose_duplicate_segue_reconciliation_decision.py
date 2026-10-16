#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

PLAN_PATH = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "segue-reconciliation"
    / "latest.json"
)

PROPOSAL_ROOT = (
    ROOT
    / "runtime"
    / "masterplan"
    / "decision-proposals"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "decision-proposals"
)

VOLATILE_FIELDS = {
    "generated_at",
    "created_at",
    "captured_at",
    "accepted_at",
    "occurred_at",
    "issued_at",
    "expires_at",
    "timestamp",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
}


class DecisionProposalError(RuntimeError):
    pass


def utc_now() -> str:
    return (
        dt.datetime.now(
            dt.timezone.utc
        )
        .replace(
            microsecond=0
        )
        .isoformat()
    )


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def canonical_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


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


def semantic_digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(
            deterministic_projection(value)
        )
    ).hexdigest()


def load_json(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(value, dict):
        raise DecisionProposalError(
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


def validate_plan(
    plan: dict[str, Any],
) -> list[str]:
    if plan.get("passed") is not True:
        raise DecisionProposalError(
            "Segue reconciliation plan did not pass."
        )

    removals = plan.get(
        "proposed_removal_ids"
    )

    if not isinstance(removals, list):
        raise DecisionProposalError(
            "Plan removal identifiers are invalid."
        )

    if any(
        not isinstance(value, str)
        for value in removals
    ):
        raise DecisionProposalError(
            "Plan contains a non-string removal identifier."
        )

    if len(removals) != len(
        set(removals)
    ):
        raise DecisionProposalError(
            "Plan contains duplicate removal identifiers."
        )

    statistics = plan.get(
        "statistics",
        {},
    )

    if not isinstance(statistics, dict):
        raise DecisionProposalError(
            "Plan statistics are invalid."
        )

    planned_count = statistics.get(
        "proposed_removal_count"
    )

    if planned_count != len(removals):
        raise DecisionProposalError(
            "Plan removal count does not match its removal set."
        )

    return sorted(removals)


def build_proposal(
    plan: dict[str, Any],
    removal_ids: list[str],
) -> dict[str, Any]:
    authorization = {
        "plan_semantic_digest": plan[
            "semantic_digest"
        ],
        "graph_semantic_digest": (
            plan.get(
                "graph",
                {},
            )
            or {}
        ).get(
            "semantic_digest"
        ),
        "removal_ids": removal_ids,
        "removal_count": len(
            removal_ids
        ),
        "proposed_segue_count": (
            plan.get(
                "statistics",
                {},
            )
            or {}
        ).get(
            "proposed_segue_count"
        ),
    }

    decision_seed = {
        "subject": "SAV-P4A-003",
        "decision": (
            "approve_duplicate_segue_reconciliation"
        ),
        "authorization": authorization,
    }

    decision_id = (
        "decision-"
        + semantic_digest(
            decision_seed
        )[:24]
    )

    proposal: dict[str, Any] = {
        "schema": (
            "savant://niche/masterplan/"
            "decision-proposal/1.0.0"
        ),
        "id": decision_id,
        "subject": "SAV-P4A-003",
        "decision": (
            "approve_duplicate_segue_reconciliation"
        ),
        "authority": {
            "state": "proposed",
            "authority_class": (
                "project-owner-decision-required"
            ),
            "tier": 1,
            "source": relative_path(
                PLAN_PATH
            ),
            "accepted_by": None,
            "accepted_at": None,
            "confidence": 1.0,
        },
        "rationale": (
            "Remove only the explicitly identified "
            "duplicate segue records while retaining "
            "one authoritative segue for every unique "
            "semantic relationship. Preserve all "
            "lineage through the accepted decision, "
            "transaction backup, event, receipt, and "
            "post-application snapshot."
        ),
        "occurred_at": utc_now(),
        "provenance": {
            "sources": [
                {
                    "source_id": plan[
                        "semantic_digest"
                    ],
                    "source_kind": (
                        "segue-reconciliation-plan"
                    ),
                    "source_path": relative_path(
                        PLAN_PATH
                    ),
                    "authority_state": "proposed",
                }
            ],
            "transformations": [
                "validate_reconciliation_plan",
                "bind_exact_plan_digest",
                "bind_exact_graph_digest",
                "bind_exact_removal_set",
                "project_decision_proposal",
            ],
            "generated_by": (
                "prodigal.niche.masterplan."
                "propose_duplicate_"
                "segue_reconciliation_decision"
            ),
            "generated_at": utc_now(),
            "contract_version": "1.0.0",
        },
        "extensions": {
            "payload": authorization,
            "acceptance_required": True,
            "application_tool": (
                "bin/masterplan-segue-reconcile"
            ),
            "application_command": (
                "masterplan-segue-reconcile "
                f"apply {decision_id}"
            ),
        },
    }

    proposal[
        "semantic_digest"
    ] = semantic_digest(
        proposal
    )

    return proposal


def persist(
    proposal: dict[str, Any],
) -> dict[str, str]:
    PROPOSAL_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    proposal_path = (
        PROPOSAL_ROOT
        / f"{proposal['id']}.json"
    )

    latest_proposal = (
        PROPOSAL_ROOT
        / "latest.json"
    )

    report_path = (
        REPORT_ROOT
        / (
            f"{timestamp()}__"
            "duplicate-segue-decision-proposal.json"
        )
    )

    latest_report = (
        REPORT_ROOT
        / "latest.json"
    )

    if proposal_path.exists():
        existing = load_json(
            proposal_path
        )

        if (
            semantic_digest(existing)
            != semantic_digest(proposal)
        ):
            raise DecisionProposalError(
                "Decision proposal identity collision."
            )

    else:
        atomic_write_json(
            proposal_path,
            proposal,
        )

    atomic_write_json(
        latest_proposal,
        proposal,
    )

    atomic_write_json(
        report_path,
        proposal,
    )

    atomic_write_json(
        latest_report,
        proposal,
    )

    return {
        "proposal": relative_path(
            proposal_path
        ),
        "latest_proposal": relative_path(
            latest_proposal
        ),
        "report": relative_path(
            report_path
        ),
        "latest_report": relative_path(
            latest_report
        ),
    }


def main() -> int:
    try:
        if not PLAN_PATH.is_file():
            raise FileNotFoundError(
                PLAN_PATH
            )

        plan = load_json(
            PLAN_PATH
        )

        removals = validate_plan(
            plan
        )

        proposal = build_proposal(
            plan,
            removals,
        )

        files = persist(
            proposal
        )

        result = {
            "operation": (
                "propose_duplicate_"
                "segue_reconciliation_decision"
            ),
            "passed": True,
            "accepted": False,
            "decision_id": proposal[
                "id"
            ],
            "proposal": proposal,
            "files": files,
        }

        result[
            "semantic_digest"
        ] = semantic_digest(
            result
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "propose_duplicate_"
                        "segue_reconciliation_decision"
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

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

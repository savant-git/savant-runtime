#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

PROPOSAL_PATH = (
    ROOT
    / "runtime"
    / "masterplan"
    / "decision-proposals"
    / "latest.json"
)

DECISION_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "decisions"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "decision-acceptance"
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


class DecisionAcceptanceError(RuntimeError):
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
        raise DecisionAcceptanceError(
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


def validate_proposal(
    proposal: dict[str, Any],
) -> None:
    required = {
        "id",
        "subject",
        "decision",
        "authority",
        "rationale",
        "occurred_at",
        "provenance",
        "extensions",
        "semantic_digest",
    }

    missing = sorted(
        required
        - set(proposal)
    )

    if missing:
        raise DecisionAcceptanceError(
            "Proposal is missing fields: "
            + ", ".join(missing)
        )

    if proposal.get(
        "decision"
    ) != (
        "approve_duplicate_"
        "segue_reconciliation"
    ):
        raise DecisionAcceptanceError(
            "Proposal is not a duplicate segue reconciliation decision."
        )

    authority = proposal.get(
        "authority"
    )

    if not isinstance(
        authority,
        dict,
    ):
        raise DecisionAcceptanceError(
            "Proposal authority is invalid."
        )

    if authority.get(
        "state"
    ) != "proposed":
        raise DecisionAcceptanceError(
            "Only proposed decisions may be accepted."
        )

    expected_digest = proposal.get(
        "semantic_digest"
    )

    actual_digest = semantic_digest(
        {
            key: value
            for key, value
            in proposal.items()
            if key != "semantic_digest"
        }
    )

    if expected_digest != actual_digest:
        raise DecisionAcceptanceError(
            "Proposal semantic digest is invalid."
        )

    extensions = proposal.get(
        "extensions"
    )

    if not isinstance(
        extensions,
        dict,
    ):
        raise DecisionAcceptanceError(
            "Proposal extensions are invalid."
        )

    payload = extensions.get(
        "payload"
    )

    if not isinstance(
        payload,
        dict,
    ):
        raise DecisionAcceptanceError(
            "Proposal authorization payload is invalid."
        )

    required_payload = {
        "plan_semantic_digest",
        "graph_semantic_digest",
        "removal_ids",
        "removal_count",
    }

    missing_payload = sorted(
        required_payload
        - set(payload)
    )

    if missing_payload:
        raise DecisionAcceptanceError(
            "Proposal payload is missing fields: "
            + ", ".join(
                missing_payload
            )
        )

    removal_ids = payload.get(
        "removal_ids"
    )

    if (
        not isinstance(
            removal_ids,
            list,
        )
        or any(
            not isinstance(
                identifier,
                str,
            )
            for identifier in removal_ids
        )
    ):
        raise DecisionAcceptanceError(
            "Proposal removal set is invalid."
        )

    if payload.get(
        "removal_count"
    ) != len(removal_ids):
        raise DecisionAcceptanceError(
            "Proposal removal count is invalid."
        )


def accept_proposal(
    proposal: dict[str, Any],
    *,
    accepted_by: str,
    acceptance_basis: str,
) -> dict[str, Any]:
    accepted = json.loads(
        json.dumps(proposal)
    )

    accepted_at = utc_now()

    accepted[
        "authority"
    ] = {
        "state": "accepted",
        "authority_class": (
            "project-owner-directed"
        ),
        "tier": 1,
        "source": relative_path(
            PROPOSAL_PATH
        ),
        "accepted_by": accepted_by,
        "accepted_at": accepted_at,
        "confidence": 1.0,
    }

    accepted[
        "occurred_at"
    ] = accepted_at

    extensions = accepted.setdefault(
        "extensions",
        {},
    )

    extensions[
        "acceptance"
    ] = {
        "accepted_by": accepted_by,
        "accepted_at": accepted_at,
        "basis": acceptance_basis,
        "proposal_path": relative_path(
            PROPOSAL_PATH
        ),
        "proposal_sha256": sha256_path(
            PROPOSAL_PATH
        ),
        "proposal_semantic_digest": (
            proposal[
                "semantic_digest"
            ]
        ),
    }

    provenance = accepted.setdefault(
        "provenance",
        {},
    )

    sources = provenance.setdefault(
        "sources",
        [],
    )

    if not isinstance(
        sources,
        list,
    ):
        raise DecisionAcceptanceError(
            "Proposal provenance sources are invalid."
        )

    sources.append(
        {
            "source_id": proposal[
                "semantic_digest"
            ],
            "source_kind": (
                "decision-proposal"
            ),
            "source_path": relative_path(
                PROPOSAL_PATH
            ),
            "authority_state": "proposed",
        }
    )

    transformations = provenance.setdefault(
        "transformations",
        [],
    )

    if not isinstance(
        transformations,
        list,
    ):
        raise DecisionAcceptanceError(
            "Proposal provenance transformations are invalid."
        )

    transformations.extend(
        [
            "validate_proposal_digest",
            "validate_authorization_payload",
            "record_explicit_project_owner_acceptance",
            "promote_proposed_decision_to_accepted",
        ]
    )

    provenance[
        "generated_by"
    ] = (
        "prodigal.niche.masterplan."
        "accept_duplicate_"
        "segue_reconciliation_decision"
    )

    provenance[
        "generated_at"
    ] = accepted_at

    accepted.pop(
        "semantic_digest",
        None,
    )

    accepted[
        "semantic_digest"
    ] = semantic_digest(
        accepted
    )

    return accepted


def persist_decision(
    decision: dict[str, Any],
) -> dict[str, str]:
    DECISION_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    decision_path = (
        DECISION_ROOT
        / f"{decision['id']}.json"
    )

    report_path = (
        REPORT_ROOT
        / (
            f"{timestamp()}__"
            f"{decision['id']}.json"
        )
    )

    latest_report = (
        REPORT_ROOT
        / "latest.json"
    )

    if decision_path.exists():
        existing = load_json(
            decision_path
        )

        if (
            semantic_digest(existing)
            != semantic_digest(decision)
        ):
            raise DecisionAcceptanceError(
                "Accepted decision identity collision."
            )

    else:
        atomic_write_json(
            decision_path,
            decision,
        )

    atomic_write_json(
        report_path,
        decision,
    )

    atomic_write_json(
        latest_report,
        decision,
    )

    return {
        "decision": relative_path(
            decision_path
        ),
        "report": relative_path(
            report_path
        ),
        "latest_report": relative_path(
            latest_report
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Accept the exact current duplicate "
            "segue reconciliation proposal."
        )
    )

    parser.add_argument(
        "--accept",
        action="store_true",
    )

    parser.add_argument(
        "--accepted-by",
        default="project-owner",
    )

    parser.add_argument(
        "--basis",
        default=(
            "Explicit project-owner instruction "
            "to continue the governed Masterplan "
            "implementation sequence."
        ),
    )

    arguments = parser.parse_args()

    try:
        if not arguments.accept:
            raise DecisionAcceptanceError(
                "Explicit --accept authorization is required."
            )

        if not PROPOSAL_PATH.is_file():
            raise FileNotFoundError(
                PROPOSAL_PATH
            )

        proposal = load_json(
            PROPOSAL_PATH
        )

        validate_proposal(
            proposal
        )

        decision = accept_proposal(
            proposal,
            accepted_by=(
                arguments.accepted_by
            ),
            acceptance_basis=(
                arguments.basis
            ),
        )

        files = persist_decision(
            decision
        )

        result = {
            "operation": (
                "accept_duplicate_"
                "segue_reconciliation_decision"
            ),
            "passed": True,
            "accepted": True,
            "decision_id": decision[
                "id"
            ],
            "decision": decision,
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
                        "accept_duplicate_"
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

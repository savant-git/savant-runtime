#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
import uuid

from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]

AUTHORITY_ROOT = ROOT / "authority"
PROPOSAL_ROOT = ROOT / "proposals"
PENDING_ROOT = PROPOSAL_ROOT / "pending"
APPROVED_ROOT = PROPOSAL_ROOT / "approved"
REJECTED_ROOT = PROPOSAL_ROOT / "rejected"
HISTORY_ROOT = ROOT / "history" / "proposals"
SCHEMA_PATH = ROOT / "schemas" / "canon-record.schema.json"
CANONCTL_PATH = ROOT / "runtime" / "canonctl.py"


def now_iso() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def now_stamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")


def safe_slug(value: str) -> str:
    output = []

    for character in value.lower():
        if character.isalnum():
            output.append(character)
        elif character in {":", "-", "_", ".", "/"}:
            output.append("-")
        else:
            output.append("-")

    slug = "".join(output)

    while "--" in slug:
        slug = slug.replace("--", "-")

    return slug.strip("-") or "proposal"


def load_yaml(path: Path) -> dict[str, Any]:
    content = yaml.safe_load(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(content, dict):
        raise ValueError(
            f"expected YAML mapping: {path}"
        )

    return content


def write_yaml(
    path: Path,
    value: dict[str, Any]
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        yaml.safe_dump(
            value,
            sort_keys=False,
            allow_unicode=True
        ),
        encoding="utf-8"
    )


def load_schema() -> dict[str, Any]:
    return json.loads(
        SCHEMA_PATH.read_text(
            encoding="utf-8"
        )
    )


def validate_record(
    record: dict[str, Any]
) -> list[str]:
    validator = Draft202012Validator(
        load_schema()
    )

    errors = []

    for error in validator.iter_errors(
        record
    ):
        location = "/".join(
            str(part)
            for part in error.path
        )

        errors.append(
            f"{location or '<root>'}: "
            f"{error.message}"
        )

    return errors


def iter_authority_records():
    for path in sorted(
        AUTHORITY_ROOT.rglob("*.yaml")
    ):
        try:
            record = load_yaml(path)
        except Exception:
            continue

        yield path, record


def find_authority_record(
    record_id: str
) -> tuple[Path, dict[str, Any]] | None:
    for path, record in iter_authority_records():
        if record.get("id") == record_id:
            return path, record

    return None


def find_latest_semantic_record(
    semantic_id: str
) -> tuple[Path, dict[str, Any]] | None:
    matches = []

    for path, record in iter_authority_records():
        candidate_semantic_id = (
            record.get("semantic_id")
            or record.get("id")
        )

        if candidate_semantic_id != semantic_id:
            continue

        matches.append(
            (
                int(
                    record.get(
                        "version",
                        1
                    )
                ),
                path,
                record
            )
        )

    if not matches:
        return None

    matches.sort(
        key=lambda item: item[0],
        reverse=True
    )

    _, path, record = matches[0]

    return path, record


def authority_directory_for(
    record: dict[str, Any]
) -> Path:
    kind = str(
        record.get(
            "kind",
            "record"
        )
    ).strip().lower()

    plural = {
        "edifice": "edifices",
        "exile": "exiles",
        "foundation": "foundation",
        "policy": "policies",
        "record": "records"
    }.get(
        kind,
        f"{kind}s"
    )

    return AUTHORITY_ROOT / plural


def authority_filename_for(
    record: dict[str, Any]
) -> str:
    semantic_id = str(
        record.get("semantic_id")
        or record.get("id")
    )

    version = int(
        record.get(
            "version",
            1
        )
    )

    return (
        f"{safe_slug(semantic_id)}"
        f"__v{version:04d}.yaml"
    )


def proposal_filename(
    proposal: dict[str, Any]
) -> str:
    proposal_id = proposal["proposal_id"]

    return (
        f"{safe_slug(proposal_id)}.yaml"
    )


def proposal_path(
    proposal_id: str
) -> Path | None:
    filename = (
        f"{safe_slug(proposal_id)}.yaml"
    )

    for root in (
        PENDING_ROOT,
        APPROVED_ROOT,
        REJECTED_ROOT
    ):
        candidate = root / filename

        if candidate.exists():
            return candidate

    return None


def canonical_record_template(
    semantic_id: str,
    kind: str,
    title: str,
    status: str,
    purpose: list[str],
    source: str | None,
    open_questions: list[str],
    future_slots: list[str]
) -> dict[str, Any]:
    record = {
        "id": semantic_id,
        "semantic_id": semantic_id,
        "kind": kind,
        "status": status,
        "version": 1,
        "title": title,
        "authority": {
            "state": status,
            "tier": 2,
            "confidence": 0.5
        },
        "purpose": {
            "current": purpose,
            "status": status
        },
        "future_slots": future_slots,
        "open_questions": open_questions,
        "lineage": {
            "parents": [],
            "supersedes": [],
            "superseded_by": []
        },
        "provenance": {
            "created_at": now_iso(),
            "created_by": "canon_proposal",
            "sources": (
                [source]
                if source
                else []
            )
        },
        "dependencies": [],
        "relationships": [],
        "attachments": []
    }

    return record


def cmd_create(
    args: argparse.Namespace
) -> int:
    PENDING_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    semantic_id = args.id.strip()

    existing = find_latest_semantic_record(
        semantic_id
    )

    if args.from_record:
        source_path = Path(
            args.from_record
        ).expanduser().resolve()

        candidate = load_yaml(
            source_path
        )

    elif existing:
        _, current_record = existing

        candidate = json.loads(
            json.dumps(
                current_record
            )
        )

        candidate["semantic_id"] = (
            current_record.get(
                "semantic_id"
            )
            or semantic_id
        )

        candidate["version"] = int(
            current_record.get(
                "version",
                1
            )
        ) + 1

        candidate["id"] = (
            f"{semantic_id}:"
            f"v{candidate['version']}"
        )

        candidate["status"] = (
            args.status
            or "candidate"
        )

        candidate.setdefault(
            "authority",
            {}
        )

        candidate["authority"][
            "state"
        ] = candidate["status"]

        candidate.setdefault(
            "lineage",
            {}
        )

        candidate["lineage"].setdefault(
            "supersedes",
            []
        )

        previous_id = current_record[
            "id"
        ]

        if previous_id not in candidate[
            "lineage"
        ]["supersedes"]:
            candidate[
                "lineage"
            ]["supersedes"].append(
                previous_id
            )

        candidate["lineage"][
            "superseded_by"
        ] = []

        candidate.setdefault(
            "provenance",
            {}
        )

        candidate["provenance"][
            "created_at"
        ] = now_iso()

        candidate["provenance"][
            "created_by"
        ] = "canon_proposal"

    else:
        candidate = canonical_record_template(
            semantic_id=semantic_id,
            kind=args.kind,
            title=(
                args.title
                or semantic_id
            ),
            status=(
                args.status
                or "candidate"
            ),
            purpose=(
                args.purpose
                or []
            ),
            source=args.source,
            open_questions=(
                args.open_question
                or []
            ),
            future_slots=(
                args.future_slot
                or []
            )
        )

    proposal_id = (
        f"proposal:"
        f"{safe_slug(semantic_id)}:"
        f"{now_stamp()}:"
        f"{uuid.uuid4().hex[:8]}"
    )

    proposal = {
        "proposal_id": proposal_id,
        "proposal_status": "pending",
        "created_at": now_iso(),
        "created_by": (
            args.actor
            or "operator"
        ),
        "reason": args.reason,
        "target_semantic_id": semantic_id,
        "candidate_record": candidate,
        "review": {
            "reviewed_at": None,
            "reviewed_by": None,
            "decision": None,
            "notes": []
        }
    }

    output = (
        PENDING_ROOT
        / proposal_filename(
            proposal
        )
    )

    write_yaml(
        output,
        proposal
    )

    print(
        output
    )

    return 0


def cmd_list(
    args: argparse.Namespace
) -> int:
    roots = []

    if args.status == "all":
        roots = [
            PENDING_ROOT,
            APPROVED_ROOT,
            REJECTED_ROOT
        ]
    elif args.status == "pending":
        roots = [
            PENDING_ROOT
        ]
    elif args.status == "approved":
        roots = [
            APPROVED_ROOT
        ]
    elif args.status == "rejected":
        roots = [
            REJECTED_ROOT
        ]

    found = 0

    for root in roots:
        for path in sorted(
            root.glob("*.yaml")
        ):
            proposal = load_yaml(
                path
            )

            print(
                "\t".join(
                    [
                        proposal.get(
                            "proposal_id",
                            ""
                        ),
                        proposal.get(
                            "proposal_status",
                            ""
                        ),
                        proposal.get(
                            "target_semantic_id",
                            ""
                        ),
                        proposal.get(
                            "created_at",
                            ""
                        )
                    ]
                )
            )

            found += 1

    print(
        f"count: {found}",
        file=sys.stderr
    )

    return 0


def cmd_show(
    args: argparse.Namespace
) -> int:
    path = proposal_path(
        args.proposal_id
    )

    if path is None:
        print(
            f"not found: "
            f"{args.proposal_id}",
            file=sys.stderr
        )

        return 1

    print(
        path.read_text(
            encoding="utf-8"
        ),
        end=""
    )

    return 0


def run_projection_pipeline() -> None:
    python = sys.executable

    commands = [
        [
            python,
            str(CANONCTL_PATH),
            "validate"
        ],
        [
            python,
            str(CANONCTL_PATH),
            "project"
        ],
        [
            python,
            str(CANONCTL_PATH),
            "build-db"
        ]
    ]

    for command in commands:
        subprocess.run(
            command,
            check=True,
            cwd=ROOT
        )


def cmd_approve(
    args: argparse.Namespace
) -> int:
    source_path = (
        PENDING_ROOT
        / f"{safe_slug(args.proposal_id)}.yaml"
    )

    if not source_path.exists():
        print(
            f"pending proposal not found: "
            f"{args.proposal_id}",
            file=sys.stderr
        )

        return 1

    proposal = load_yaml(
        source_path
    )

    candidate = proposal.get(
        "candidate_record"
    )

    if not isinstance(
        candidate,
        dict
    ):
        print(
            "proposal has no valid "
            "candidate_record",
            file=sys.stderr
        )

        return 1

    semantic_id = (
        candidate.get(
            "semantic_id"
        )
        or proposal.get(
            "target_semantic_id"
        )
        or candidate.get("id")
    )

    candidate[
        "semantic_id"
    ] = semantic_id

    current = find_latest_semantic_record(
        semantic_id
    )

    if current:
        current_path, current_record = current

        current_version = int(
            current_record.get(
                "version",
                1
            )
        )

        candidate_version = int(
            candidate.get(
                "version",
                current_version + 1
            )
        )

        if candidate_version <= current_version:
            candidate_version = (
                current_version + 1
            )

        candidate[
            "version"
        ] = candidate_version

        candidate[
            "id"
        ] = (
            f"{semantic_id}:"
            f"v{candidate_version}"
        )

        candidate.setdefault(
            "lineage",
            {}
        )

        candidate["lineage"].setdefault(
            "supersedes",
            []
        )

        current_id = current_record[
            "id"
        ]

        if current_id not in candidate[
            "lineage"
        ]["supersedes"]:
            candidate[
                "lineage"
            ]["supersedes"].append(
                current_id
            )

        candidate["lineage"][
            "superseded_by"
        ] = []

        current_record[
            "status"
        ] = "superseded"

        current_record.setdefault(
            "authority",
            {}
        )

        current_record["authority"][
            "state"
        ] = "superseded"

        current_record.setdefault(
            "lineage",
            {}
        )

        current_record["lineage"].setdefault(
            "superseded_by",
            []
        )

        if candidate["id"] not in current_record[
            "lineage"
        ]["superseded_by"]:
            current_record[
                "lineage"
            ]["superseded_by"].append(
                candidate["id"]
            )

        write_yaml(
            current_path,
            current_record
        )

    candidate[
        "status"
    ] = (
        args.authority_status
        or "accepted"
    )

    candidate.setdefault(
        "authority",
        {}
    )

    candidate["authority"][
        "state"
    ] = candidate["status"]

    candidate["authority"][
        "confidence"
    ] = args.confidence

    candidate.setdefault(
        "provenance",
        {}
    )

    candidate["provenance"][
        "approved_at"
    ] = now_iso()

    candidate["provenance"][
        "approved_by"
    ] = (
        args.actor
        or "operator"
    )

    errors = validate_record(
        candidate
    )

    if errors:
        print(
            "candidate validation failed:",
            file=sys.stderr
        )

        for error in errors:
            print(
                f"- {error}",
                file=sys.stderr
            )

        return 1

    destination_directory = (
        authority_directory_for(
            candidate
        )
    )

    destination_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    destination_path = (
        destination_directory
        / authority_filename_for(
            candidate
        )
    )

    if destination_path.exists():
        print(
            f"authority destination exists: "
            f"{destination_path}",
            file=sys.stderr
        )

        return 1

    write_yaml(
        destination_path,
        candidate
    )

    proposal[
        "proposal_status"
    ] = "approved"

    proposal["review"] = {
        "reviewed_at": now_iso(),
        "reviewed_by": (
            args.actor
            or "operator"
        ),
        "decision": "approved",
        "notes": (
            args.note
            or []
        )
    }

    approved_path = (
        APPROVED_ROOT
        / source_path.name
    )

    write_yaml(
        approved_path,
        proposal
    )

    source_path.unlink()

    event = {
        "event_id": (
            f"event:"
            f"{uuid.uuid4().hex}"
        ),
        "event_type": (
            "canon_proposal_approved"
        ),
        "occurred_at": now_iso(),
        "proposal_id": proposal[
            "proposal_id"
        ],
        "authority_record_id": (
            candidate["id"]
        ),
        "semantic_id": semantic_id,
        "authority_path": str(
            destination_path.relative_to(
                ROOT
            )
        ),
        "actor": (
            args.actor
            or "operator"
        ),
        "notes": (
            args.note
            or []
        )
    }

    event_path = (
        HISTORY_ROOT
        / (
            f"{now_stamp()}__"
            f"{safe_slug(proposal['proposal_id'])}"
            f"__approved.json"
        )
    )

    event_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    event_path.write_text(
        json.dumps(
            event,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    run_projection_pipeline()

    print(
        f"approved: "
        f"{proposal['proposal_id']}"
    )

    print(
        f"authority: "
        f"{destination_path}"
    )

    print(
        f"event: "
        f"{event_path}"
    )

    return 0


def cmd_reject(
    args: argparse.Namespace
) -> int:
    source_path = (
        PENDING_ROOT
        / f"{safe_slug(args.proposal_id)}.yaml"
    )

    if not source_path.exists():
        print(
            f"pending proposal not found: "
            f"{args.proposal_id}",
            file=sys.stderr
        )

        return 1

    proposal = load_yaml(
        source_path
    )

    proposal[
        "proposal_status"
    ] = "rejected"

    proposal["review"] = {
        "reviewed_at": now_iso(),
        "reviewed_by": (
            args.actor
            or "operator"
        ),
        "decision": "rejected",
        "notes": (
            args.note
            or []
        )
    }

    destination = (
        REJECTED_ROOT
        / source_path.name
    )

    write_yaml(
        destination,
        proposal
    )

    source_path.unlink()

    event = {
        "event_id": (
            f"event:"
            f"{uuid.uuid4().hex}"
        ),
        "event_type": (
            "canon_proposal_rejected"
        ),
        "occurred_at": now_iso(),
        "proposal_id": proposal[
            "proposal_id"
        ],
        "actor": (
            args.actor
            or "operator"
        ),
        "notes": (
            args.note
            or []
        )
    }

    event_path = (
        HISTORY_ROOT
        / (
            f"{now_stamp()}__"
            f"{safe_slug(proposal['proposal_id'])}"
            f"__rejected.json"
        )
    )

    event_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    event_path.write_text(
        json.dumps(
            event,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print(
        f"rejected: "
        f"{proposal['proposal_id']}"
    )

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="canon-proposal",
        description=(
            "create, inspect, approve, and reject "
            "dynamic canon proposals"
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True
    )

    create = subparsers.add_parser(
        "create"
    )

    create.add_argument(
        "id"
    )

    create.add_argument(
        "--kind",
        default="record"
    )

    create.add_argument(
        "--title"
    )

    create.add_argument(
        "--status",
        default="candidate"
    )

    create.add_argument(
        "--purpose",
        action="append"
    )

    create.add_argument(
        "--source"
    )

    create.add_argument(
        "--open-question",
        action="append"
    )

    create.add_argument(
        "--future-slot",
        action="append"
    )

    create.add_argument(
        "--reason",
        required=True
    )

    create.add_argument(
        "--actor"
    )

    create.add_argument(
        "--from-record"
    )

    create.set_defaults(
        function=cmd_create
    )

    listing = subparsers.add_parser(
        "list"
    )

    listing.add_argument(
        "--status",
        choices=[
            "pending",
            "approved",
            "rejected",
            "all"
        ],
        default="pending"
    )

    listing.set_defaults(
        function=cmd_list
    )

    show = subparsers.add_parser(
        "show"
    )

    show.add_argument(
        "proposal_id"
    )

    show.set_defaults(
        function=cmd_show
    )

    approve = subparsers.add_parser(
        "approve"
    )

    approve.add_argument(
        "proposal_id"
    )

    approve.add_argument(
        "--actor"
    )

    approve.add_argument(
        "--authority-status",
        choices=[
            "accepted",
            "canonical",
            "axiomatic",
            "immutable"
        ],
        default="accepted"
    )

    approve.add_argument(
        "--confidence",
        type=float,
        default=0.9
    )

    approve.add_argument(
        "--note",
        action="append"
    )

    approve.set_defaults(
        function=cmd_approve
    )

    reject = subparsers.add_parser(
        "reject"
    )

    reject.add_argument(
        "proposal_id"
    )

    reject.add_argument(
        "--actor"
    )

    reject.add_argument(
        "--note",
        action="append",
        required=True
    )

    reject.set_defaults(
        function=cmd_reject
    )

    return parser


def main() -> int:
    parser = build_parser()

    args = parser.parse_args()

    return int(
        args.function(
            args
        )
        or 0
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

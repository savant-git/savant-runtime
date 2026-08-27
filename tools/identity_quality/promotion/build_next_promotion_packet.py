#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

PROMOTION_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
)

QUEUE_PATH = (
    PROMOTION_ROOT
    / "latest.json"
)

SUBJECT_REPORT_ROOT = (
    PROMOTION_ROOT
    / "subjects"
)

NOCTURNE_ROOT = (
    ROOT
    / "hierarchies"
    / "identity"
    / "exiles"
    / "opus"
    / "prodigals"
    / "nocturne"
)

REFERENCE_FILES = {
    "prodigal_definition": (
        NOCTURNE_ROOT
        / "definition.json"
    ),
    "prodigal_runtime": (
        NOCTURNE_ROOT
        / "runtime"
        / "nocturne_runtime.py"
    ),
    "prodigal_tests": (
        NOCTURNE_ROOT
        / "tests"
        / "test_nocturne_runtime.py"
    ),
    "prodigal_controller": (
        ROOT
        / "bin"
        / "nocturnectl"
    ),
    "quirk_definition": (
        NOCTURNE_ROOT
        / "quirks"
        / "veil"
        / "definition.json"
    ),
    "quirk_runtime": (
        NOCTURNE_ROOT
        / "quirks"
        / "veil"
        / "runtime"
        / "veil_runtime.py"
    ),
    "quirk_tests": (
        NOCTURNE_ROOT
        / "quirks"
        / "veil"
        / "tests"
        / "test_veil_runtime.py"
    ),
    "quirk_controller": (
        ROOT
        / "bin"
        / "veilctl"
    ),
    "exile_definition": (
        ROOT
        / "hierarchies"
        / "identity"
        / "exiles"
        / "opus"
        / "definition.json"
    ),
}

TEXT_SUFFIXES = {
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".sh",
    ".md",
    ".txt",
    ".toml",
}

VOLATILE_FIELDS = {
    "generated_at",
    "timestamp",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
}

KINSHIP_TERM = "kin" + "ship"


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
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


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(value)
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


def deterministic_projection(
    value: Any,
) -> Any:
    if isinstance(value, dict):
        return {
            key: deterministic_projection(
                child
            )
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


def write_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def write_text(
    path: Path,
    value: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        value,
        encoding="utf-8",
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


def inspect_file(
    path: Path,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": relative_path(path),
        "exists": path.is_file(),
    }

    if path.is_file():
        stat = path.stat()

        record.update(
            {
                "size": stat.st_size,
                "mode": oct(
                    stat.st_mode
                    & 0o777
                ),
                "sha256": sha256_path(
                    path
                ),
            }
        )

    return record


def first_queue_subject(
    queue_document: dict[str, Any],
) -> dict[str, Any]:
    queue = queue_document.get(
        "queue"
    )

    if (
        not isinstance(queue, list)
        or not queue
    ):
        raise RuntimeError(
            "Identity promotion queue is empty."
        )

    subject = queue[0]

    if not isinstance(subject, dict):
        raise RuntimeError(
            "First queue subject is invalid."
        )

    return subject


def load_subject_definition(
    subject: dict[str, Any],
) -> tuple[
    Path,
    dict[str, Any],
]:
    declared = subject.get(
        "path"
    )

    if not isinstance(declared, str):
        raise RuntimeError(
            "Promotion subject has no definition path."
        )

    path = (
        ROOT
        / declared
    ).resolve()

    if not path.is_file():
        raise FileNotFoundError(path)

    return path, load_json(path)


def discover_subject_files(
    directory: Path,
) -> list[dict[str, Any]]:
    records: list[
        dict[str, Any]
    ] = []

    for path in sorted(
        directory.rglob("*")
    ):
        if not path.is_file():
            continue

        records.append(
            inspect_file(path)
        )

    return records


def search_mentions(
    identifier: str,
    name: str,
    definition_path: Path,
) -> list[dict[str, Any]]:
    search_terms = tuple(
        sorted(
            {
                identifier.lower(),
                name.lower(),
            }
        )
    )

    roots = (
        ROOT
        / "hierarchies",
        ROOT
        / "ontology",
        ROOT
        / "runtime",
        ROOT
        / "tools",
        ROOT
        / "bin",
        ROOT
        / "docs",
    )

    findings: list[
        dict[str, Any]
    ] = []

    for search_root in roots:
        if not search_root.is_dir():
            continue

        for path in sorted(
            search_root.rglob("*")
        ):
            if (
                not path.is_file()
                or path.suffix.lower()
                not in TEXT_SUFFIXES
            ):
                continue

            if path == definition_path:
                continue

            try:
                text = path.read_text(
                    encoding="utf-8",
                )

            except (
                OSError,
                UnicodeDecodeError,
            ):
                continue

            lowered = text.lower()

            matched = [
                term
                for term in search_terms
                if term
                and term in lowered
            ]

            if not matched:
                continue

            findings.append(
                {
                    "path": relative_path(
                        path
                    ),
                    "matched_terms": matched,
                    "sha256": sha256_path(
                        path
                    ),
                }
            )

            if len(findings) >= 500:
                return findings

    return findings


def forbidden_term_findings(
    directory: Path,
) -> list[dict[str, Any]]:
    pattern = re.compile(
        rf"\b{re.escape(KINSHIP_TERM)}\b",
        re.IGNORECASE,
    )

    findings: list[
        dict[str, Any]
    ] = []

    for path in sorted(
        directory.rglob("*")
    ):
        if (
            not path.is_file()
            or path.suffix.lower()
            not in TEXT_SUFFIXES
        ):
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
            )

        except (
            OSError,
            UnicodeDecodeError,
        ):
            continue

        for line_number, line in enumerate(
            text.splitlines(),
            start=1,
        ):
            if pattern.search(line):
                findings.append(
                    {
                        "path": relative_path(
                            path
                        ),
                        "line": line_number,
                        "value": KINSHIP_TERM,
                    }
                )

    return findings


def reference_selection(
    kind: str,
) -> dict[str, dict[str, Any]]:
    if kind == "quirk":
        keys = (
            "quirk_definition",
            "quirk_runtime",
            "quirk_tests",
            "quirk_controller",
        )

    elif kind == "prodigal":
        keys = (
            "prodigal_definition",
            "prodigal_runtime",
            "prodigal_tests",
            "prodigal_controller",
        )

    else:
        keys = (
            "exile_definition",
            "prodigal_definition",
            "prodigal_runtime",
            "prodigal_tests",
            "prodigal_controller",
        )

    return {
        key: inspect_file(
            REFERENCE_FILES[key]
        )
        for key in keys
    }


def infer_name(
    subject: dict[str, Any],
    definition_path: Path,
    definition: dict[str, Any],
) -> str:
    identity = definition.get(
        "identity"
    )

    if isinstance(identity, dict):
        for field in (
            "name",
            "canonical_name",
            "slug",
        ):
            value = identity.get(
                field
            )

            if (
                isinstance(value, str)
                and value.strip()
            ):
                return value.strip()

    identifier = subject.get(
        "id"
    )

    if isinstance(identifier, str):
        return identifier.rsplit(
            ".",
            1,
        )[-1]

    return definition_path.parent.name


def expected_layout(
    kind: str,
    definition_path: Path,
    name: str,
) -> dict[str, str]:
    directory = definition_path.parent

    controller_name = (
        f"{name.lower()}ctl"
    )

    return {
        "definition": relative_path(
            definition_path
        ),
        "contracts": relative_path(
            directory
            / "contracts"
            / f"{name.lower()}_contracts.py"
        ),
        "runtime": relative_path(
            directory
            / "runtime"
            / f"{name.lower()}_runtime.py"
        ),
        "tests": relative_path(
            directory
            / "tests"
            / f"test_{name.lower()}_runtime.py"
        ),
        "controller": relative_path(
            ROOT
            / "bin"
            / controller_name
        ),
        "reports": relative_path(
            ROOT
            / "reports"
            / "identity_quality"
            / name.lower()
        ),
    }


def classify_existing(
    layout: dict[str, str],
) -> dict[str, dict[str, Any]]:
    result: dict[
        str,
        dict[str, Any]
    ] = {}

    for key, declared in layout.items():
        path = ROOT / declared

        if key == "reports":
            result[key] = {
                "path": declared,
                "exists": path.is_dir(),
                "kind": "directory",
            }

        else:
            result[key] = inspect_file(
                path
            )

    return result


def authoritative_primitives(
    definition: dict[str, Any],
) -> dict[str, Any]:
    fields = (
        "id",
        "kind",
        "version",
        "status",
        "identity",
        "purpose",
        "authority",
        "composition",
        "contracts",
        "capabilities",
        "dependencies",
        "relationships",
        "lineage",
        "provenance",
        "runtime",
        "security",
        "observability",
        "validation",
        "lifecycle",
        "apertures",
    )

    return {
        field: definition.get(
            field
        )
        for field in fields
        if field in definition
    }


def build_packet() -> dict[str, Any]:
    if not QUEUE_PATH.is_file():
        raise FileNotFoundError(
            QUEUE_PATH
        )

    queue_document = load_json(
        QUEUE_PATH
    )

    subject = first_queue_subject(
        queue_document
    )

    definition_path, definition = (
        load_subject_definition(
            subject
        )
    )

    directory = definition_path.parent

    kind = str(
        subject.get(
            "kind",
            definition.get(
                "kind",
                "unknown",
            ),
        )
    ).lower()

    name = infer_name(
        subject,
        definition_path,
        definition,
    )

    identifier = str(
        subject.get(
            "id",
            definition.get(
                "id",
                name,
            ),
        )
    )

    layout = expected_layout(
        kind,
        definition_path,
        name,
    )

    packet: dict[str, Any] = {
        "schema": (
            "savant://identity-quality/"
            "promotion-packet/1.1.0"
        ),
        "operation": (
            "build_next_promotion_packet"
        ),
        "generated_at": utc_now(),
        "queue": {
            "path": relative_path(
                QUEUE_PATH
            ),
            "sha256": sha256_path(
                QUEUE_PATH
            ),
            "digest": queue_document.get(
                "digest"
            ),
            "position": subject.get(
                "queue_position"
            ),
        },
        "subject": {
            "id": identifier,
            "name": name,
            "kind": kind,
            "path": relative_path(
                definition_path
            ),
            "parent": subject.get(
                "parent"
            ),
            "score": subject.get(
                "score"
            ),
            "runtime_state": subject.get(
                "runtime_state"
            ),
            "issue_count": subject.get(
                "issue_count"
            ),
            "reference_subject": subject.get(
                "reference_subject",
                False,
            ),
            "tasks": subject.get(
                "tasks",
                [],
            ),
        },
        "authority": {
            "definition": inspect_file(
                definition_path
            ),
            "primitives": (
                authoritative_primitives(
                    definition
                )
            ),
            "definition_digest": digest(
                deterministic_projection(
                    definition
                )
            ),
        },
        "existing": {
            "layout": classify_existing(
                layout
            ),
            "subtree": discover_subject_files(
                directory
            ),
            "mentions": search_mentions(
                identifier,
                name,
                definition_path,
            ),
            "forbidden_terms": (
                forbidden_term_findings(
                    directory
                )
            ),
        },
        "reference": {
            "subject": (
                "prodigal.nocturne"
                if kind == "prodigal"
                else (
                    "quirk.nocturne.veil"
                    if kind == "quirk"
                    else "exile.opus"
                )
            ),
            "files": reference_selection(
                kind
            ),
            "usage": (
                "Reference structure and quality only. "
                "Do not duplicate Nocturne-specific behavior."
            ),
        },
        "target_layout": layout,
        "promotion_constraints": [
            (
                "Extend authoritative primitives; "
                "do not replace them without explicit migration."
            ),
            (
                "Store only authoritative primitives."
            ),
            (
                "Generate reports, indexes, manifests, "
                "and attestations as deterministic projections."
            ),
            (
                "Expose authority, lineage, provenance, "
                "dependencies, and typed relationships."
            ),
            (
                "Preserve parent and child authority boundaries."
            ),
            (
                "Implement independently useful bounded behavior."
            ),
            (
                "Fail closed when implementation, dependency, "
                "authority, or evidence is unavailable."
            ),
            (
                "Exclude volatile telemetry from deterministic identity."
            ),
            (
                "Add versioned contracts before runtime composition."
            ),
            (
                "Add unit, property, security, integration, "
                "recovery, and determinism tests."
            ),
            (
                "Create one canonical controller."
            ),
            (
                "Create reversible parent attachment."
            ),
            (
                "Create deterministic verification and attestation."
            ),
            (
                "Use kindred exclusively; forbidden terminology "
                "must not remain in authoritative or projected files."
            ),
            (
                "Do not invent capability absent from source authority."
            ),
        ],
        "execution_order": [
            "preserve_authority_backup",
            "inspect_authoritative_definition",
            "inspect_existing_subtree",
            "reconcile_existing_runtime_and_contracts",
            "define_bounded_capability_contract",
            "extend_runtime_without_replacement",
            "add_canonical_controller",
            "add_complete_validation_matrix",
            "attach_runtime_evidence_to_definition",
            "attach_to_parent_without_authority_transfer",
            "build_verification_controller",
            "build_deterministic_attestation",
            "rerun_identity_audit",
            "rebuild_promotion_queue",
        ],
    }

    packet["digest"] = digest(
        deterministic_projection(
            packet
        )
    )

    return packet


def markdown(
    packet: dict[str, Any],
) -> str:
    subject = packet[
        "subject"
    ]

    lines = [
        "# Identity Promotion Packet",
        "",
        (
            f"- Generated: "
            f"`{packet['generated_at']}`"
        ),
        (
            f"- Digest: "
            f"`{packet['digest']}`"
        ),
        (
            f"- Subject: "
            f"`{subject['id']}`"
        ),
        (
            f"- Kind: "
            f"`{subject['kind']}`"
        ),
        (
            f"- Parent: "
            f"`{subject['parent']}`"
        ),
        (
            f"- Runtime: "
            f"`{subject['runtime_state']}`"
        ),
        (
            f"- Reference subject: "
            f"`{subject['reference_subject']}`"
        ),
        (
            f"- Score: "
            f"**{subject['score']}**"
        ),
        "",
        "## Authority",
        "",
        (
            f"- Definition: "
            f"`{packet['authority']['definition']['path']}`"
        ),
        (
            f"- Definition SHA-256: "
            f"`{packet['authority']['definition']['sha256']}`"
        ),
        (
            f"- Deterministic authority digest: "
            f"`{packet['authority']['definition_digest']}`"
        ),
        "",
        "## Promotion Tasks",
        "",
    ]

    for task in subject.get(
        "tasks",
        []
    ):
        lines.append(
            (
                f"{task.get('priority', '-')}. "
                f"`{task.get('code', 'unknown')}` — "
                f"{task.get('action', '')}"
            )
        )

    lines.extend(
        [
            "",
            "## Target Layout",
            "",
        ]
    )

    for key, value in packet[
        "target_layout"
    ].items():
        lines.append(
            f"- {key}: `{value}`"
        )

    lines.extend(
        [
            "",
            "## Execution Order",
            "",
        ]
    )

    for index, stage in enumerate(
        packet["execution_order"],
        start=1,
    ):
        lines.append(
            f"{index}. `{stage}`"
        )

    lines.extend(
        [
            "",
            "## Existing Subtree",
            "",
            (
                f"- Files: "
                f"**{len(packet['existing']['subtree'])}**"
            ),
            (
                f"- External mentions: "
                f"**{len(packet['existing']['mentions'])}**"
            ),
            (
                f"- Forbidden-term findings: "
                f"**{len(packet['existing']['forbidden_terms'])}**"
            ),
            "",
        ]
    )

    return "\n".join(
        lines
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build an authoritative implementation packet "
            "for the highest-priority identity promotion subject."
        )
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=SUBJECT_REPORT_ROOT,
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    arguments = parser.parse_args()

    try:
        packet = build_packet()

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "build_next_promotion_packet"
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

    subject_id = (
        packet["subject"]["id"]
        .replace(":", "_")
        .replace("/", "_")
    )

    output_root = (
        arguments.output_root
        .resolve()
        / subject_id
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = timestamp()

    json_path = (
        output_root
        / (
            f"{run_id}__"
            "promotion-packet.json"
        )
    )

    markdown_path = (
        output_root
        / (
            f"{run_id}__"
            "promotion-packet.md"
        )
    )

    latest_json = (
        output_root
        / "latest.json"
    )

    latest_markdown = (
        output_root
        / "latest.md"
    )

    write_json(
        json_path,
        packet,
    )

    write_json(
        latest_json,
        packet,
    )

    rendered = markdown(
        packet
    )

    write_text(
        markdown_path,
        rendered,
    )

    write_text(
        latest_markdown,
        rendered,
    )

    manifest = {
        "generated_at": (
            packet["generated_at"]
        ),
        "subject": (
            packet["subject"]["id"]
        ),
        "packet_digest": (
            packet["digest"]
        ),
        "files": {
            json_path.name: (
                sha256_path(
                    json_path
                )
            ),
            markdown_path.name: (
                sha256_path(
                    markdown_path
                )
            ),
            latest_json.name: (
                sha256_path(
                    latest_json
                )
            ),
            latest_markdown.name: (
                sha256_path(
                    latest_markdown
                )
            ),
        },
    }

    manifest_path = (
        output_root
        / (
            f"{run_id}__manifest.json"
        )
    )

    write_json(
        manifest_path,
        manifest,
    )

    passed = (
        packet["authority"][
            "definition"
        ]["exists"]
        and packet["subject"][
            "kind"
        ] in {
            "exile",
            "prodigal",
            "quirk",
        }
    )

    print(
        json.dumps(
            {
                "operation": (
                    "build_next_promotion_packet"
                ),
                "passed": passed,
                "subject": (
                    packet["subject"]
                ),
                "digest": (
                    packet["digest"]
                ),
                "reports": {
                    "json": str(
                        json_path
                    ),
                    "markdown": str(
                        markdown_path
                    ),
                    "latest_json": str(
                        latest_json
                    ),
                    "latest_markdown": str(
                        latest_markdown
                    ),
                    "manifest": str(
                        manifest_path
                    ),
                },
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    if (
        arguments.strict
        and not passed
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

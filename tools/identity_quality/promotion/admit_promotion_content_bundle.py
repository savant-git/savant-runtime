#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

CONTENT_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
    / "content"
)

ADMISSION_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
    / "admissions"
)

TRANSACTION_ROOT = (
    ROOT
    / "runtime"
    / "identity-promotion"
    / "content-admissions"
)

BACKUP_ROOT = (
    ROOT
    / "backups"
    / "identity-quality"
    / "promotion-content"
)

ALLOWED_ROLES = {
    "contracts",
    "runtime",
    "tests",
    "controller",
}

EXECUTABLE_ROLES = {
    "contracts",
    "runtime",
    "tests",
    "controller",
}

VOLATILE_FIELDS = {
    "generated_at",
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


def sha256_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def sha256_text(
    value: str,
) -> str:
    return sha256_bytes(
        value.encode("utf-8")
    )


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


def atomic_write_bytes(
    path: Path,
    value: bytes,
    mode: int,
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
            "wb",
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


def atomic_write_text(
    path: Path,
    value: str,
    mode: int = 0o644,
) -> None:
    atomic_write_bytes(
        path,
        value.encode("utf-8"),
        mode,
    )


def atomic_write_json(
    path: Path,
    value: Any,
    mode: int = 0o644,
) -> None:
    rendered = (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    atomic_write_text(
        path,
        rendered,
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


def safe_key(
    value: str,
) -> str:
    return "".join(
        character
        if (
            character.isalnum()
            or character in {
                ".",
                "_",
                "-",
            }
        )
        else "_"
        for character in value
    ).strip("_")


def latest_bundle_paths() -> list[Path]:
    if not CONTENT_ROOT.is_dir():
        return []

    return sorted(
        (
            path
            for path in CONTENT_ROOT.glob(
                "*/latest.json"
            )
            if path.is_file()
        ),
        key=lambda path: (
            path.stat().st_mtime_ns,
            path.as_posix(),
        ),
        reverse=True,
    )


def latest_bundle_path() -> Path:
    paths = latest_bundle_paths()

    if not paths:
        raise FileNotFoundError(
            "No promotion content bundle exists."
        )

    return paths[0]


def resolve_bundle_path(
    declared: Path | None,
) -> Path:
    if declared is None:
        return latest_bundle_path()

    path = declared.expanduser()

    if not path.is_absolute():
        path = ROOT / path

    path = path.resolve()

    if not path.is_file():
        raise FileNotFoundError(path)

    return path


def ensure_within_root(
    path: Path,
) -> Path:
    resolved = path.resolve()

    try:
        resolved.relative_to(ROOT)

    except ValueError as exc:
        raise ValueError(
            f"Path escapes runtime root: {resolved}"
        ) from exc

    return resolved


def validate_bundle(
    bundle: dict[str, Any],
) -> None:
    subject = bundle.get(
        "subject"
    )

    if not isinstance(subject, dict):
        raise ValueError(
            "Bundle has no subject."
        )

    identifier = subject.get(
        "id"
    )

    if (
        not isinstance(identifier, str)
        or not identifier.strip()
    ):
        raise ValueError(
            "Bundle subject has no identifier."
        )

    admission = bundle.get(
        "admission"
    )

    if not isinstance(admission, dict):
        raise ValueError(
            "Bundle has no admission data."
        )

    if admission.get(
        "automatic_overwrite_allowed"
    ) is not False:
        raise ValueError(
            "Bundle permits automatic overwrite."
        )

    files = bundle.get(
        "files"
    )

    if (
        not isinstance(files, list)
        or not files
    ):
        raise ValueError(
            "Bundle has no files."
        )

    seen_roles: set[str] = set()
    seen_paths: set[str] = set()

    for record in files:
        if not isinstance(record, dict):
            raise ValueError(
                "Bundle contains an invalid file record."
            )

        role = record.get(
            "role"
        )

        if role not in ALLOWED_ROLES:
            raise ValueError(
                f"Unsupported content role: {role}"
            )

        if role in seen_roles:
            raise ValueError(
                f"Duplicate content role: {role}"
            )

        seen_roles.add(role)

        declared_path = record.get(
            "path"
        )

        if (
            not isinstance(declared_path, str)
            or not declared_path.strip()
        ):
            raise ValueError(
                f"Missing path for role: {role}"
            )

        if declared_path in seen_paths:
            raise ValueError(
                f"Duplicate target path: {declared_path}"
            )

        seen_paths.add(declared_path)

        target = ensure_within_root(
            ROOT / declared_path
        )

        if target == ROOT:
            raise ValueError(
                "Target cannot be runtime root."
            )

        content = record.get(
            "content"
        )

        if not isinstance(content, str):
            raise ValueError(
                f"Missing content for role: {role}"
            )

        expected = record.get(
            "content_sha256"
        )

        actual = sha256_text(
            content
        )

        if expected != actual:
            raise ValueError(
                f"Content digest mismatch for role: {role}"
            )

        existing = target.is_file()

        declared_existing = bool(
            record.get(
                "existing",
                False,
            )
        )

        if existing != declared_existing:
            raise ValueError(
                f"Target state changed for role: {role}"
            )

        if existing:
            expected_existing = record.get(
                "existing_sha256"
            )

            actual_existing = sha256_path(
                target
            )

            if expected_existing != actual_existing:
                raise ValueError(
                    f"Existing file changed for role: {role}"
                )

            if record.get(
                "requires_review"
            ) is not True:
                raise ValueError(
                    f"Existing file lacks review requirement: {role}"
                )

            if record.get(
                "replace_existing"
            ) is not False:
                raise ValueError(
                    f"Existing file permits replacement: {role}"
                )


def preflight_records(
    bundle: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[
        dict[str, Any]
    ] = []

    for file_record in bundle[
        "files"
    ]:
        role = file_record[
            "role"
        ]

        target = ensure_within_root(
            ROOT
            / file_record[
                "path"
            ]
        )

        content = file_record[
            "content"
        ]

        current_exists = target.is_file()

        current_sha256 = (
            sha256_path(target)
            if current_exists
            else None
        )

        expected_existing = file_record.get(
            "existing_sha256"
        )

        expected_content = file_record[
            "content_sha256"
        ]

        content_sha256 = sha256_text(
            content
        )

        passed = all(
            (
                content_sha256
                == expected_content,
                current_exists
                == bool(
                    file_record.get(
                        "existing",
                        False,
                    )
                ),
                (
                    not current_exists
                    or current_sha256
                    == expected_existing
                ),
            )
        )

        records.append(
            {
                "role": role,
                "path": relative_path(
                    target
                ),
                "passed": passed,
                "current_exists": (
                    current_exists
                ),
                "current_sha256": (
                    current_sha256
                ),
                "expected_existing_sha256": (
                    expected_existing
                ),
                "content_sha256": (
                    content_sha256
                ),
                "expected_content_sha256": (
                    expected_content
                ),
                "requires_review": bool(
                    file_record.get(
                        "requires_review",
                        False,
                    )
                ),
            }
        )

    return records


def backup_file(
    target: Path,
    backup_root: Path,
) -> dict[str, Any]:
    if not target.is_file():
        return {
            "source": relative_path(
                target
            ),
            "exists": False,
            "backed_up": False,
            "passed": True,
        }

    relative = target.relative_to(
        ROOT
    )

    destination = (
        backup_root
        / relative
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        target,
        destination,
    )

    source_sha256 = sha256_path(
        target
    )

    backup_sha256 = sha256_path(
        destination
    )

    return {
        "source": relative_path(
            target
        ),
        "destination": relative_path(
            destination
        ),
        "exists": True,
        "backed_up": True,
        "source_sha256": source_sha256,
        "backup_sha256": backup_sha256,
        "passed": (
            source_sha256
            == backup_sha256
        ),
    }


def backup_targets(
    bundle: dict[str, Any],
    backup_root: Path,
) -> list[dict[str, Any]]:
    return [
        backup_file(
            ensure_within_root(
                ROOT
                / record[
                    "path"
                ]
            ),
            backup_root,
        )
        for record in bundle[
            "files"
        ]
    ]


def target_mode(
    role: str,
    target: Path,
) -> int:
    if target.is_file():
        current = stat.S_IMODE(
            target.stat().st_mode
        )

        if role in EXECUTABLE_ROLES:
            return current | 0o755

        return current

    if role in EXECUTABLE_ROLES:
        return 0o755

    return 0o644


def write_target(
    record: dict[str, Any],
) -> dict[str, Any]:
    role = record[
        "role"
    ]

    target = ensure_within_root(
        ROOT
        / record[
            "path"
        ]
    )

    content = record[
        "content"
    ]

    before_exists = target.is_file()

    before_sha256 = (
        sha256_path(target)
        if before_exists
        else None
    )

    mode = target_mode(
        role,
        target,
    )

    atomic_write_text(
        target,
        content,
        mode,
    )

    after_sha256 = sha256_path(
        target
    )

    expected = record[
        "content_sha256"
    ]

    return {
        "role": role,
        "path": relative_path(
            target
        ),
        "before_exists": before_exists,
        "before_sha256": before_sha256,
        "after_sha256": after_sha256,
        "expected_sha256": expected,
        "mode": oct(mode),
        "passed": (
            after_sha256
            == expected
        ),
    }


def restore_from_backup(
    bundle: dict[str, Any],
    backup_root: Path,
) -> dict[str, Any]:
    results: list[
        dict[str, Any]
    ] = []

    for record in bundle[
        "files"
    ]:
        target = ensure_within_root(
            ROOT
            / record[
                "path"
            ]
        )

        relative = target.relative_to(
            ROOT
        )

        backup = (
            backup_root
            / relative
        )

        originally_existed = bool(
            record.get(
                "existing",
                False,
            )
        )

        if originally_existed:
            if not backup.is_file():
                results.append(
                    {
                        "path": relative_path(
                            target
                        ),
                        "passed": False,
                        "code": (
                            "rollback.backup_missing"
                        ),
                    }
                )
                continue

            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copy2(
                backup,
                target,
            )

            expected = record.get(
                "existing_sha256"
            )

            actual = sha256_path(
                target
            )

            results.append(
                {
                    "path": relative_path(
                        target
                    ),
                    "operation": "restore",
                    "expected_sha256": (
                        expected
                    ),
                    "actual_sha256": (
                        actual
                    ),
                    "passed": (
                        expected == actual
                    ),
                }
            )

        else:
            if target.exists():
                target.unlink()

            results.append(
                {
                    "path": relative_path(
                        target
                    ),
                    "operation": "remove",
                    "passed": (
                        not target.exists()
                    ),
                }
            )

    return {
        "passed": all(
            result.get(
                "passed",
                False,
            )
            for result in results
        ),
        "results": results,
    }


def markdown(
    result: dict[str, Any],
) -> str:
    lines = [
        "# Identity Promotion Content Admission",
        "",
        (
            f"- Generated: "
            f"`{result['generated_at']}`"
        ),
        (
            f"- Subject: "
            f"`{result['subject']['id']}`"
        ),
        (
            f"- Mode: "
            f"`{result['mode']}`"
        ),
        (
            f"- Passed: "
            f"**{result['passed']}**"
        ),
        (
            f"- Digest: "
            f"`{result['digest']}`"
        ),
        "",
        "## Files",
        "",
    ]

    for record in result[
        "files"
    ]:
        lines.extend(
            [
                (
                    f"### `{record['role']}`"
                ),
                "",
                (
                    f"- Path: "
                    f"`{record['path']}`"
                ),
                (
                    f"- State: "
                    f"`{record['state']}`"
                ),
                (
                    f"- Passed: "
                    f"**{record['passed']}**"
                ),
                "",
            ]
        )

    if result.get(
        "rollback"
    ):
        lines.extend(
            [
                "## Rollback",
                "",
                (
                    f"- Passed: "
                    f"**{result['rollback']['passed']}**"
                ),
                "",
            ]
        )

    return "\n".join(
        lines
    )


def admit_bundle(
    bundle_path: Path,
    *,
    apply: bool,
    approve_existing: bool,
    rollback_on_failure: bool,
) -> dict[str, Any]:
    bundle = load_json(
        bundle_path
    )

    validate_bundle(
        bundle
    )

    subject = bundle[
        "subject"
    ]

    subject_id = subject[
        "id"
    ]

    run_id = (
        f"admission-{timestamp()}-"
        f"{digest(bundle)[:16]}"
    )

    transaction_root = (
        TRANSACTION_ROOT
        / safe_key(
            subject_id
        )
        / run_id
    )

    transaction_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    snapshot_path = (
        transaction_root
        / "bundle.json"
    )

    atomic_write_json(
        snapshot_path,
        bundle,
    )

    preflight = preflight_records(
        bundle
    )

    preflight_passed = all(
        record[
            "passed"
        ]
        for record in preflight
    )

    review_required = [
        record
        for record in bundle[
            "files"
        ]
        if record.get(
            "requires_review"
        )
    ]

    review_admitted = (
        not review_required
        or approve_existing
    )

    backup_root = (
        BACKUP_ROOT
        / safe_key(
            subject_id
        )
        / run_id
    )

    backups: list[
        dict[str, Any]
    ] = []

    file_results: list[
        dict[str, Any]
    ] = []

    rollback_result: dict[
        str,
        Any
    ] | None = None

    passed = (
        preflight_passed
        and review_admitted
    )

    if apply and passed:
        backups = backup_targets(
            bundle,
            backup_root,
        )

        backup_passed = all(
            record[
                "passed"
            ]
            for record in backups
        )

        passed = (
            passed
            and backup_passed
        )

        if passed:
            for record in bundle[
                "files"
            ]:
                write_result = write_target(
                    record
                )

                file_results.append(
                    {
                        "role": record[
                            "role"
                        ],
                        "path": record[
                            "path"
                        ],
                        "state": (
                            "written"
                            if write_result[
                                "passed"
                            ]
                            else "failed"
                        ),
                        "passed": (
                            write_result[
                                "passed"
                            ]
                        ),
                        "details": write_result,
                    }
                )

                if not write_result[
                    "passed"
                ]:
                    passed = False
                    break

        if (
            not passed
            and rollback_on_failure
        ):
            rollback_result = (
                restore_from_backup(
                    bundle,
                    backup_root,
                )
            )

    else:
        for record in bundle[
            "files"
        ]:
            file_results.append(
                {
                    "role": record[
                        "role"
                    ],
                    "path": record[
                        "path"
                    ],
                    "state": (
                        "planned"
                        if passed
                        else "blocked"
                    ),
                    "passed": passed,
                    "details": {
                        "requires_review": bool(
                            record.get(
                                "requires_review",
                                False,
                            )
                        ),
                        "approved": (
                            approve_existing
                            if record.get(
                                "requires_review"
                            )
                            else True
                        ),
                    },
                }
            )

    result: dict[str, Any] = {
        "schema": (
            "savant://identity-quality/"
            "promotion-content-admission/1.0.0"
        ),
        "operation": (
            "admit_promotion_content_bundle"
        ),
        "generated_at": utc_now(),
        "mode": (
            "apply"
            if apply
            else "plan"
        ),
        "bundle": {
            "path": relative_path(
                bundle_path
            ),
            "sha256": sha256_path(
                bundle_path
            ),
            "digest": bundle.get(
                "digest"
            ),
        },
        "subject": subject,
        "transaction": {
            "id": run_id,
            "root": relative_path(
                transaction_root
            ),
            "bundle_snapshot": (
                relative_path(
                    snapshot_path
                )
            ),
            "backup_root": (
                relative_path(
                    backup_root
                )
            ),
        },
        "preflight": {
            "passed": preflight_passed,
            "records": preflight,
        },
        "review": {
            "required_count": len(
                review_required
            ),
            "approved": approve_existing,
            "admitted": review_admitted,
        },
        "backups": backups,
        "files": file_results,
        "rollback": rollback_result,
        "passed": passed,
        "statistics": {
            "file_count": len(
                bundle[
                    "files"
                ]
            ),
            "existing_file_count": len(
                review_required
            ),
            "preflight_passed_count": sum(
                record[
                    "passed"
                ]
                for record in preflight
            ),
            "written_count": sum(
                record[
                    "state"
                ]
                == "written"
                for record in file_results
            ),
            "failed_count": sum(
                not record[
                    "passed"
                ]
                for record in file_results
            ),
        },
    }

    result[
        "digest"
    ] = digest(
        deterministic_projection(
            result
        )
    )

    atomic_write_json(
        transaction_root
        / "result.json",
        result,
    )

    atomic_write_text(
        transaction_root
        / "result.md",
        markdown(
            result
        ),
    )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Plan or apply a transaction-safe "
            "identity promotion content bundle."
        )
    )

    parser.add_argument(
        "--bundle",
        type=Path,
    )

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    parser.add_argument(
        "--approve-existing",
        action="store_true",
    )

    parser.add_argument(
        "--no-rollback",
        action="store_true",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=ADMISSION_ROOT,
    )

    arguments = parser.parse_args()

    try:
        bundle_path = resolve_bundle_path(
            arguments.bundle
        )

        result = admit_bundle(
            bundle_path,
            apply=arguments.apply,
            approve_existing=(
                arguments.approve_existing
            ),
            rollback_on_failure=(
                not arguments.no_rollback
            ),
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "admit_promotion_content_bundle"
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

    subject_key = safe_key(
        result[
            "subject"
        ][
            "id"
        ]
    )

    output_root = (
        arguments.output_root
        .expanduser()
        .resolve()
        / subject_key
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
            "content-admission.json"
        )
    )

    markdown_path = (
        output_root
        / (
            f"{run_id}__"
            "content-admission.md"
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

    atomic_write_json(
        json_path,
        result,
    )

    atomic_write_json(
        latest_json,
        result,
    )

    rendered = markdown(
        result
    )

    atomic_write_text(
        markdown_path,
        rendered,
    )

    atomic_write_text(
        latest_markdown,
        rendered,
    )

    manifest = {
        "generated_at": (
            result[
                "generated_at"
            ]
        ),
        "subject": (
            result[
                "subject"
            ][
                "id"
            ]
        ),
        "mode": result[
            "mode"
        ],
        "passed": result[
            "passed"
        ],
        "admission_digest": (
            result[
                "digest"
            ]
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

    atomic_write_json(
        manifest_path,
        manifest,
    )

    print(
        json.dumps(
            {
                "operation": (
                    "admit_promotion_content_bundle"
                ),
                "passed": result[
                    "passed"
                ],
                "mode": result[
                    "mode"
                ],
                "subject": result[
                    "subject"
                ],
                "digest": result[
                    "digest"
                ],
                "review": result[
                    "review"
                ],
                "statistics": result[
                    "statistics"
                ],
                "transaction": result[
                    "transaction"
                ],
                "rollback": result[
                    "rollback"
                ],
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
        and not result[
            "passed"
        ]
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

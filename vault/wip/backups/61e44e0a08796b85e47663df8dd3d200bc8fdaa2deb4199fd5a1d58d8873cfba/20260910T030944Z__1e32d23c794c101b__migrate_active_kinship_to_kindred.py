#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


schema = "savant.assurance.migrate-active-kinship-to-kindred.v1"
authority_effect = "none"

root = Path(
    "/root/savant-runtime"
)

legacy_term = "kinship"
canonical_term = "kindred"


excluded_directory_names = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "node_modules",
}

immutable_or_historical_roots = (
    root / "vault" / "wip" / "backups",
    root / "runtime" / "reports",
)

historical_name_fragments = (
    "backup",
    "snapshot",
    "sdump",
    "archive",
    "historical",
    "history",
)

candidate_suffixes = {
    ".py",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".service",
    ".socket",
    ".path",
    ".target",
    ".sh",
    ".bash",
    ".zsh",
    ".md",
    ".txt",
    ".html",
    ".css",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".jsx",
    ".sql",
    ".graphql",
}

candidate_names_without_suffix = {
    "makefile",
    "dockerfile",
}

term_pattern = re.compile(
    r"kinship",
    flags=re.IGNORECASE,
)


class MigrationError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
)
class Change:
    path: Path
    before_sha256: str
    after_sha256: str
    occurrence_count: int


def sha256(
    data: bytes,
) -> str:
    return hashlib.sha256(
        data
    ).hexdigest()


def is_under(
    path: Path,
    parent: Path,
) -> bool:
    try:
        path.relative_to(
            parent
        )

        return True

    except ValueError:
        return False


def is_historical_or_immutable(
    path: Path,
) -> bool:
    resolved = path.resolve()

    for excluded_root in (
        immutable_or_historical_roots
    ):
        if is_under(
            resolved,
            excluded_root.resolve(),
        ):
            return True

    relative = resolved.relative_to(
        root.resolve()
    )

    lowered_parts = tuple(
        part.lower()
        for part in relative.parts
    )

    for part in lowered_parts:
        if any(
            fragment in part
            for fragment
            in historical_name_fragments
        ):
            return True

    return False


def is_candidate(
    path: Path,
) -> bool:
    if not path.is_file():
        return False

    lowered_name = path.name.lower()

    if (
        lowered_name
        in candidate_names_without_suffix
    ):
        return True

    return (
        path.suffix.lower()
        in candidate_suffixes
    )


def iter_candidates() -> Iterable[
    Path
]:
    for directory, dirs, files in os.walk(
        root
    ):
        dirs[:] = [
            item
            for item in dirs
            if item
            not in excluded_directory_names
        ]

        directory_path = Path(
            directory
        )

        for filename in files:
            path = (
                directory_path
                / filename
            )

            if not is_candidate(
                path
            ):
                continue

            yield path


def decode_text(
    data: bytes,
) -> str | None:
    if b"\x00" in data:
        return None

    try:
        return data.decode(
            "utf-8"
        )

    except UnicodeDecodeError:
        return None


def replacement_for(
    match: re.Match[str],
) -> str:
    value = match.group(
        0
    )

    if value.isupper():
        return canonical_term.upper()

    if value[:1].isupper():
        return canonical_term.capitalize()

    return canonical_term


def migrate_text(
    text: str,
) -> tuple[
    str,
    int,
]:
    return term_pattern.subn(
        replacement_for,
        text,
    )


def atomic_write(
    path: Path,
    data: bytes,
) -> None:
    stat = path.stat()

    fd, temporary_name = tempfile.mkstemp(
        prefix=(
            "."
            + path.name
            + "."
        ),
        suffix=".tmp",
        dir=str(
            path.parent
        ),
    )

    temporary = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            fd,
            "wb",
        ) as handle:
            handle.write(
                data
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.chmod(
            temporary,
            stat.st_mode,
        )

        try:
            os.chown(
                temporary,
                stat.st_uid,
                stat.st_gid,
            )

        except PermissionError:
            pass

        os.replace(
            temporary,
            path,
        )

    finally:
        if temporary.exists():
            temporary.unlink()


def backup_path(
    source: Path,
    run_id: str,
) -> Path:
    relative = source.relative_to(
        root
    )

    return (
        root
        / "vault"
        / "wip"
        / "backups"
        / "kindred-terminology-migration"
        / run_id
        / relative
    )


def backup(
    source: Path,
    run_id: str,
) -> Path:
    destination = backup_path(
        source,
        run_id,
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source,
        destination,
    )

    return destination


def scan() -> tuple[
    list[tuple[Path, bytes, bytes, int]],
    list[dict[str, object]],
]:
    mutable_matches = []
    preserved_matches = []

    for path in iter_candidates():
        try:
            before = path.read_bytes()

        except OSError:
            continue

        text = decode_text(
            before
        )

        if text is None:
            continue

        if not term_pattern.search(
            text
        ):
            continue

        after_text, count = migrate_text(
            text
        )

        if count < 1:
            continue

        if is_historical_or_immutable(
            path
        ):
            preserved_matches.append(
                {
                    "path":
                        str(
                            path
                        ),
                    "occurrences":
                        count,
                    "disposition":
                        "preserved-history-or-backup",
                }
            )

            continue

        after = after_text.encode(
            "utf-8"
        )

        mutable_matches.append(
            (
                path,
                before,
                after,
                count,
            )
        )

    mutable_matches.sort(
        key=lambda item: str(
            item[
                0
            ]
        )
    )

    preserved_matches.sort(
        key=lambda item: str(
            item[
                "path"
            ]
        )
    )

    return (
        mutable_matches,
        preserved_matches,
    )


def run(
    apply: bool,
) -> dict[str, object]:
    mutable_matches, preserved = (
        scan()
    )

    run_id = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    changes = []

    for (
        path,
        before,
        after,
        count,
    ) in mutable_matches:
        before_digest = sha256(
            before
        )

        after_digest = sha256(
            after
        )

        backup_location = None

        if apply:
            backup_location = backup(
                path,
                run_id,
            )

            atomic_write(
                path,
                after,
            )

            observed = path.read_bytes()

            if observed != after:
                raise MigrationError(
                    "post-write verification failed: "
                    + str(
                        path
                    )
                )

        changes.append(
            {
                "path":
                    str(
                        path
                    ),
                "occurrences":
                    count,
                "before_sha256":
                    before_digest,
                "after_sha256":
                    after_digest,
                "backup":
                    (
                        str(
                            backup_location
                        )
                        if backup_location
                        is not None
                        else None
                    ),
            }
        )

    remaining_active = []

    if apply:
        rescanned, _ = scan()

        remaining_active = [
            {
                "path":
                    str(
                        path
                    ),
                "occurrences":
                    count,
            }
            for (
                path,
                _before,
                _after,
                count,
            ) in rescanned
        ]

        if remaining_active:
            raise MigrationError(
                "active SAVANT-owned kinship "
                "terminology remains after migration"
            )

    return {
        "schema":
            schema,
        "authority_effect":
            authority_effect,
        "status":
            "passed",
        "apply":
            apply,
        "canonical_term":
            canonical_term,
        "deprecated_active_term":
            legacy_term,
        "active_files_changed":
            (
                len(
                    changes
                )
                if apply
                else 0
            ),
        "active_files_would_change":
            len(
                changes
            ),
        "active_occurrences":
            sum(
                int(
                    item[
                        "occurrences"
                    ]
                )
                for item in changes
            ),
        "changes":
            changes,
        "preserved_historical_matches":
            preserved,
        "remaining_active_matches":
            remaining_active,
        "historical_evidence_mutated":
            False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    args = parser.parse_args()

    try:
        result = run(
            apply=args.apply
        )

        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema,
                    "authority_effect":
                        authority_effect,
                    "status":
                        "failed",
                    "error":
                        str(
                            exc
                        ),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

#!/usr/bin/env python3

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Iterable


root = Path(
    "/root/savant-runtime"
)

schema = (
    "savant://runtime/edifices/"
    "terminology-migration/1.0.0"
)

source_term = "hierarchy"
target_term = "edifice"

immutable_roots = (
    root / "authority"
    / "accepted-decisions",
)

historical_roots = (
    root / "vault",
    root / "imports",
    root / "evolution"
    / "structure-migration"
    / "backups",
    root / "evolution"
    / "structure-migration"
    / "baseline-captures",
)

external_directory_names = {
    ".git",
    "__pycache__",
    "node_modules",
    "site-packages",
    "dist-packages",
    ".venv",
    "venv",
}

binary_suffixes = {
    ".7z",
    ".a",
    ".bin",
    ".bz2",
    ".class",
    ".db",
    ".dll",
    ".dylib",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".jar",
    ".jpeg",
    ".jpg",
    ".lock",
    ".mp3",
    ".mp4",
    ".o",
    ".pdf",
    ".png",
    ".pyc",
    ".pyo",
    ".so",
    ".sqlite",
    ".sqlite3",
    ".tar",
    ".tgz",
    ".webp",
    ".woff",
    ".woff2",
    ".xz",
    ".zip",
}


class migration_error(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class change:
    kind: str
    before: str
    after: str
    digest_before: str | None
    digest_after: str | None

    def projection(
        self,
    ) -> dict[str, str | None]:
        return {
            "kind":
                self.kind,
            "before":
                self.before,
            "after":
                self.after,
            "digest_before":
                self.digest_before,
            "digest_after":
                self.digest_after,
        }


def digest_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def relative(
    path: Path,
) -> str:
    try:
        return str(
            path.relative_to(
                root
            )
        )
    except ValueError:
        return str(
            path
        )


def is_under(
    path: Path,
    parents: Iterable[Path],
) -> bool:
    resolved = (
        path.resolve(
            strict=False
        )
    )

    for parent in parents:
        parent_resolved = (
            parent.resolve(
                strict=False
            )
        )

        try:
            resolved.relative_to(
                parent_resolved
            )
            return True
        except ValueError:
            continue

    return False


def is_external(
    path: Path,
) -> bool:
    try:
        parts = (
            path.relative_to(
                root
            ).parts
        )
    except ValueError:
        return True

    for part in parts:
        if (
            part
            in external_directory_names
        ):
            return True

        if (
            part.startswith(
                ".venv"
            )
        ):
            return True

    return False


def protected(
    path: Path,
) -> bool:
    return (
        is_under(
            path,
            immutable_roots,
        )
        or is_under(
            path,
            historical_roots,
        )
        or is_external(
            path
        )
    )


def textual(
    path: Path,
) -> bool:
    if (
        path.suffix.lower()
        in binary_suffixes
    ):
        return False

    try:
        sample = path.read_bytes()[
            :8192
        ]
    except OSError:
        return False

    if b"\x00" in sample:
        return False

    try:
        sample.decode(
            "utf-8"
        )
    except UnicodeDecodeError:
        return False

    return True


def replace_term(
    value: str,
) -> str:
    substitutions = (
        (
            re.compile(
                r"HIERARCHIES"
            ),
            "EDIFICES",
        ),
        (
            re.compile(
                r"HIERARCHY"
            ),
            "EDIFICE",
        ),
        (
            re.compile(
                r"Hierarchies"
            ),
            "Edifices",
        ),
        (
            re.compile(
                r"Hierarchy"
            ),
            "Edifice",
        ),
        (
            re.compile(
                r"hierarchies"
            ),
            "edifices",
        ),
        (
            re.compile(
                r"hierarchy"
            ),
            "edifice",
        ),
    )

    projected = value

    for pattern, replacement in (
        substitutions
    ):
        projected = (
            pattern.sub(
                replacement,
                projected,
            )
        )

    return projected


def content_changes(
) -> list[change]:
    changes: list[
        change
    ] = []

    for path in sorted(
        root.rglob("*"),
        key=lambda item:
            str(item),
    ):
        if (
            not path.is_file()
            or protected(
                path
            )
            or not textual(
                path
            )
        ):
            continue

        try:
            before_bytes = (
                path.read_bytes()
            )
            before = (
                before_bytes.decode(
                    "utf-8"
                )
            )
        except (
            OSError,
            UnicodeDecodeError,
        ):
            continue

        after = replace_term(
            before
        )

        if after == before:
            continue

        after_bytes = (
            after.encode(
                "utf-8"
            )
        )

        changes.append(
            change(
                kind="content",
                before=
                    relative(
                        path
                    ),
                after=
                    relative(
                        path
                    ),
                digest_before=
                    digest_bytes(
                        before_bytes
                    ),
                digest_after=
                    digest_bytes(
                        after_bytes
                    ),
            )
        )

    return changes


def renamed_path(
    path: Path,
) -> Path:
    return path.with_name(
        replace_term(
            path.name
        )
    )


def path_changes(
) -> list[change]:
    changes: list[
        change
    ] = []

    candidates = sorted(
        (
            path
            for path
            in root.rglob("*")
            if (
                not protected(
                    path
                )
                and replace_term(
                    path.name
                )
                != path.name
            )
        ),
        key=lambda item: (
            len(
                item.parts
            ),
            str(item),
        ),
        reverse=True,
    )

    for path in candidates:
        destination = (
            renamed_path(
                path
            )
        )

        changes.append(
            change(
                kind="path",
                before=
                    relative(
                        path
                    ),
                after=
                    relative(
                        destination
                    ),
                digest_before=None,
                digest_after=None,
            )
        )

    return changes


def apply_content(
    changes: list[change],
) -> None:
    for item in changes:
        if item.kind != "content":
            continue

        path = (
            root
            / item.before
        )

        before_bytes = (
            path.read_bytes()
        )

        if (
            digest_bytes(
                before_bytes
            )
            != item.digest_before
        ):
            raise migration_error(
                "content changed during "
                "migration: "
                f"{path}"
            )

        before = (
            before_bytes.decode(
                "utf-8"
            )
        )

        after = replace_term(
            before
        )

        after_bytes = (
            after.encode(
                "utf-8"
            )
        )

        if (
            digest_bytes(
                after_bytes
            )
            != item.digest_after
        ):
            raise migration_error(
                "non-deterministic content "
                "projection: "
                f"{path}"
            )

        temporary = (
            path.with_name(
                f".{path.name}."
                "edifice-migration.tmp"
            )
        )

        temporary.write_bytes(
            after_bytes
        )

        os.replace(
            temporary,
            path,
        )


def apply_paths(
) -> list[change]:
    applied: list[
        change
    ] = []

    candidates = sorted(
        (
            path
            for path
            in root.rglob("*")
            if (
                not protected(
                    path
                )
                and replace_term(
                    path.name
                )
                != path.name
            )
        ),
        key=lambda item: (
            len(
                item.parts
            ),
            str(item),
        ),
        reverse=True,
    )

    for path in candidates:
        if not path.exists():
            continue

        destination = (
            renamed_path(
                path
            )
        )

        if destination.exists():
            raise migration_error(
                "rename destination already "
                "exists: "
                f"{destination}"
            )

        before = relative(
            path
        )

        path.rename(
            destination
        )

        applied.append(
            change(
                kind="path",
                before=before,
                after=
                    relative(
                        destination
                    ),
                digest_before=None,
                digest_after=None,
            )
        )

    return applied


def remaining_current(
) -> list[str]:
    remaining: list[
        str
    ] = []

    for path in sorted(
        root.rglob("*"),
        key=lambda item:
            str(item),
    ):
        if protected(
            path
        ):
            continue

        if (
            source_term
            in path.name.lower()
        ):
            remaining.append(
                "path:"
                + relative(
                    path
                )
            )

        if (
            path.is_file()
            and textual(
                path
            )
        ):
            try:
                content = (
                    path.read_text(
                        encoding="utf-8"
                    )
                )
            except (
                OSError,
                UnicodeDecodeError,
            ):
                continue

            if re.search(
                r"hierarch(?:y|ies)",
                content,
                flags=re.IGNORECASE,
            ):
                remaining.append(
                    "content:"
                    + relative(
                        path
                    )
                )

    return sorted(
        set(
            remaining
        )
    )


def projection(
    *,
    mode: str,
    content: list[change],
    paths: list[change],
    remaining: list[str],
) -> dict[str, object]:
    payload: dict[
        str,
        object,
    ] = {
        "schema":
            schema,
        "authority_effect":
            "none",
        "mode":
            mode,
        "source_term":
            source_term,
        "target_term":
            target_term,
        "immutable_accepted_decisions":
            True,
        "historical_evidence_preserved":
            True,
        "external_dependencies_preserved":
            True,
        "content_changes": [
            item.projection()
            for item
            in content
        ],
        "path_changes": [
            item.projection()
            for item
            in paths
        ],
        "remaining_current":
            remaining,
        "ok":
            (
                mode != "apply"
                or not remaining
            ),
    }

    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode(
        "utf-8"
    )

    payload[
        "projection_digest"
    ] = digest_bytes(
        encoded
    )

    return payload


def main() -> int:
    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    arguments = (
        parser.parse_args()
    )

    if not root.is_dir():
        raise migration_error(
            "savant runtime root "
            "unavailable"
        )

    planned_content = (
        content_changes()
    )

    planned_paths = (
        path_changes()
    )

    if not arguments.apply:
        result = projection(
            mode="plan",
            content=
                planned_content,
            paths=
                planned_paths,
            remaining=
                remaining_current(),
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
        )

        return 0

    apply_content(
        planned_content
    )

    applied_paths = (
        apply_paths()
    )

    remaining = (
        remaining_current()
    )

    result = projection(
        mode="apply",
        content=
            planned_content,
        paths=
            applied_paths,
        remaining=
            remaining,
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return (
        0
        if not remaining
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


root = Path(
    "/root/savant-runtime"
)

schema = (
    "savant://runtime/edifices/"
    "terminology-repair/2.1.1"
)

backup_root = (
    root
    / "evolution"
    / "structure-migration"
    / "backups"
    / "20260927-edifice-terminology-repair"
)

canonical = {
    (
        root
        / "edifices"
        / "utility"
        / "runtime"
        / "utility_edifice.py"
    ): (
        "bcd2bbdceef8b3eb2ff37989b3d8ddf0"
        "e0067bc98b2c1c5e2d04cac55bce777b"
    ),
    (
        root
        / "tools"
        / "extr-enterprise"
        / "runtime"
        / "utility_edifice.py"
    ): (
        "862633cb635fb53d991ff59e4870db234"
        "570198158becd7c5520d1024974dac1"
    ),
}

legacy = {
    (
        root
        / "edifices"
        / "utility"
        / "runtime"
        / "utility_hierarchy.py"
    ): (
        "0573ec87fe4149f0bb458d00ff19d7e7"
        "a5e8b47e43fdd4438c75e25d1e251460"
    ),
    (
        root
        / "tools"
        / "extr-enterprise"
        / "runtime"
        / "utility_hierarchy.py"
    ): (
        "85aa4ed5dd86cb0b1d60146cd7e86f51"
        "ae5bea6de5f8cc4fc1370992af1d8239"
    ),
}

historical_wrong = (
    root
    / "runtime"
    / "identity-promotion"
    / "transactions"
    / "quirk.nocturne.veil"
    / "promotion-20260801T031644Z-ad7be0812595f48d"
    / "backup"
    / "edifices"
)

historical_original = (
    historical_wrong.parent
    / "hierarchies"
)

scan_roots = (
    root
    / "edifices"
    / "utility",
    root
    / "tools"
    / "extr-enterprise",
)


class repair_error(
    RuntimeError
):
    pass


def sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                chunk
            )

    return digest.hexdigest()


def relative(
    path: Path,
) -> str:
    return str(
        path.relative_to(
            root
        )
    )


def backup_path(
    path: Path,
) -> Path:
    return (
        backup_root
        / path.relative_to(
            root
        )
    )


def verify_digest(
    path: Path,
    expected: str,
    label: str,
) -> str:
    if not path.is_file():
        raise repair_error(
            f"missing {label}: "
            f"{path}"
        )

    actual = sha256(
        path
    )

    if actual != expected:
        raise repair_error(
            f"{label} changed since "
            "audited snapshot: "
            f"{path}\n"
            f"expected={expected}\n"
            f"actual={actual}"
        )

    return actual


def active_references(
) -> list[str]:
    needle = (
        "utility_"
        + "hierarchy"
    )

    findings: list[str] = []

    skipped = set(
        legacy
    )

    suffixes = {
        ".py",
        ".json",
        ".md",
        ".txt",
        ".yaml",
        ".yml",
        ".toml",
        ".sh",
        ".service",
        ".timer",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
    }

    for base in scan_roots:
        if not base.exists():
            continue

        for path in base.rglob(
            "*"
        ):
            if (
                path in skipped
                or path.is_symlink()
                or not path.is_file()
                or "__pycache__"
                in path.parts
            ):
                continue

            if (
                path.suffix.lower()
                not in suffixes
            ):
                continue

            try:
                with path.open(
                    "r",
                    encoding="utf-8",
                ) as handle:
                    for line_number, line in enumerate(
                        handle,
                        1,
                    ):
                        if needle in line:
                            findings.append(
                                f"{relative(path)}:"
                                f"{line_number}"
                            )

            except (
                OSError,
                UnicodeDecodeError,
            ):
                continue

    return sorted(
        set(
            findings
        )
    )


def preflight(
) -> dict[str, object]:
    state: dict[
        str,
        object,
    ] = {
        "canonical": {},
        "legacy": {},
        "references":
            active_references(),
    }

    if state[
        "references"
    ]:
        raise repair_error(
            "active legacy utility "
            "references remain:\n"
            + "\n".join(
                state[
                    "references"
                ]
            )
        )

    canonical_state = {}

    for (
        path,
        expected,
    ) in canonical.items():
        canonical_state[
            relative(
                path
            )
        ] = verify_digest(
            path,
            expected,
            "canonical file",
        )

    state[
        "canonical"
    ] = canonical_state

    legacy_state = {}

    for (
        path,
        expected,
    ) in legacy.items():
        archived = backup_path(
            path
        )

        if path.exists():
            legacy_state[
                relative(
                    path
                )
            ] = (
                "active:"
                + verify_digest(
                    path,
                    expected,
                    "legacy file",
                )
            )

        elif archived.exists():
            legacy_state[
                relative(
                    path
                )
            ] = (
                "archived:"
                + verify_digest(
                    archived,
                    expected,
                    "legacy backup",
                )
            )

        else:
            raise repair_error(
                "legacy file missing "
                "without verified archive: "
                f"{path}"
            )

    state[
        "legacy"
    ] = legacy_state

    wrong_exists = (
        historical_wrong.exists()
    )

    original_exists = (
        historical_original.exists()
    )

    if (
        wrong_exists
        == original_exists
    ):
        raise repair_error(
            "historical path state "
            "invalid; exactly one path "
            "variant must exist"
        )

    state[
        "historical"
    ] = {
        "wrong_exists":
            wrong_exists,
        "original_exists":
            original_exists,
    }

    return state


def archive_legacy(
    path: Path,
    expected: str,
) -> str | None:
    if not path.exists():
        return None

    verify_digest(
        path,
        expected,
        "legacy file",
    )

    destination = backup_path(
        path
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if destination.exists():
        verify_digest(
            destination,
            expected,
            "legacy backup",
        )

    else:
        shutil.copy2(
            path,
            destination,
        )

        verify_digest(
            destination,
            expected,
            "legacy backup",
        )

    path.unlink()

    return relative(
        destination
    )


def apply_repairs(
) -> list[
    dict[str, str]
]:
    operations: list[
        dict[str, str]
    ] = []

    if historical_wrong.exists():
        if historical_original.exists():
            raise repair_error(
                "historical destination "
                "already exists"
            )

        historical_wrong.rename(
            historical_original
        )

        operations.append(
            {
                "operation":
                    "restore_historical_path",
                "from":
                    relative(
                        historical_wrong
                    ),
                "to":
                    relative(
                        historical_original
                    ),
            }
        )

    for (
        path,
        expected,
    ) in legacy.items():
        archived = archive_legacy(
            path,
            expected,
        )

        if archived is not None:
            operations.append(
                {
                    "operation":
                        "archive_and_remove_legacy_path",
                    "path":
                        relative(
                            path
                        ),
                    "backup":
                        archived,
                }
            )

    return operations


def postcheck(
) -> dict[str, object]:
    for (
        path,
        expected,
    ) in canonical.items():
        verify_digest(
            path,
            expected,
            "canonical file",
        )

    for (
        path,
        expected,
    ) in legacy.items():
        if path.exists():
            raise repair_error(
                "legacy active path "
                "remains: "
                f"{path}"
            )

        verify_digest(
            backup_path(
                path
            ),
            expected,
            "legacy backup",
        )

    if (
        historical_wrong.exists()
        or not historical_original.is_dir()
    ):
        raise repair_error(
            "historical provenance "
            "path was not restored"
        )

    references = (
        active_references()
    )

    if references:
        raise repair_error(
            "active legacy references "
            "remain after repair:\n"
            + "\n".join(
                references
            )
        )

    return {
        "historical_path":
            relative(
                historical_original
            ),
        "legacy_active_paths":
            [],
        "active_legacy_references":
            [],
    }


def main(
) -> int:
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
        raise repair_error(
            "runtime root unavailable: "
            f"{root}"
        )

    before = preflight()

    if not arguments.apply:
        print(
            json.dumps(
                {
                    "schema":
                        schema,
                    "mode":
                        "plan",
                    "global_text_replacement":
                        False,
                    "preflight":
                        before,
                    "ok":
                        True,
                },
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
        )

        return 0

    operations = (
        apply_repairs()
    )

    after = (
        postcheck()
    )

    print(
        json.dumps(
            {
                "schema":
                    schema,
                "mode":
                    "apply",
                "global_text_replacement":
                    False,
                "operations":
                    operations,
                "post":
                    after,
                "ok":
                    True,
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

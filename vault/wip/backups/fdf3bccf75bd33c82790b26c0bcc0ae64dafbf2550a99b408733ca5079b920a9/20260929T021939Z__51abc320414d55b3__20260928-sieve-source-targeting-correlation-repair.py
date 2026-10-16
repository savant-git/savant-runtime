#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat


schema = (
    "savant://migration/sieve/"
    "source-targeting-correlation-repair/1.0.0"
)

canonical_root = Path(
    "/root/savant-runtime"
)

target_relative = Path(
    "tools/extr-enterprise/runtime/source_targeting.py"
)

backup_relative = Path(
    "evolution/structure-migration/backups/"
    "20260928-sieve-source-targeting-correlation-repair/"
    "tools/extr-enterprise/runtime/source_targeting.py"
)

before_sha256 = (
    "0d64e110d5d16286aedd3aa71cc7f869"
    "87865aaec7d515222aed8ae661967927"
)

after_sha256 = (
    "b12761d4d4f34b9f9004d6f3b8ec81a0"
    "ea3de1f221c5918bb77570c1ccc474f6"
)

old_block = '''    prioritized = (
        set(
            signals
        )
        or set(
            candidate_tokens
        )
    )
'''

new_block = '''    correlation_signals = (
        set(
            signals
        )
        - {
            "savant"
        }
    )

    prioritized = (
        correlation_signals
        if signals
        else set(
            candidate_tokens
        )
    )
'''


class repair_error(RuntimeError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(
        data
    ).hexdigest()


def read_regular(
    path: Path,
) -> tuple[bytes, int]:
    info = path.lstat()

    if (
        stat.S_ISLNK(
            info.st_mode
        )
        or not stat.S_ISREG(
            info.st_mode
        )
    ):
        raise repair_error(
            f"refusing non-regular target: {path}"
        )

    return (
        path.read_bytes(),
        stat.S_IMODE(
            info.st_mode
        ),
    )


def transform(
    source: bytes,
) -> bytes:
    text = source.decode(
        "utf-8"
    )

    count = text.count(
        old_block
    )

    if count != 1:
        raise repair_error(
            "expected exactly one runtime "
            "correlation block; "
            f"found {count}"
        )

    projected = text.replace(
        old_block,
        new_block,
        1,
    ).encode(
        "utf-8"
    )

    actual = digest(
        projected
    )

    if actual != after_sha256:
        raise repair_error(
            "projected digest mismatch: "
            f"expected {after_sha256}, "
            f"found {actual}"
        )

    return projected


def build_plan(
    root: Path,
) -> dict:
    path = (
        root
        / target_relative
    )

    source, mode = (
        read_regular(
            path
        )
    )

    source_digest = digest(
        source
    )

    if (
        source_digest
        == after_sha256
    ):
        projected = source
        state = "already_repaired"

    elif (
        source_digest
        == before_sha256
    ):
        projected = transform(
            source
        )

        state = "repair_required"

    else:
        raise repair_error(
            "unexpected source digest: "
            f"expected {before_sha256} "
            f"or {after_sha256}, "
            f"found {source_digest}"
        )

    checks = {
        "generic_savant_not_runtime_evidence":
            (
                b"correlation_signals"
                in projected
                and (
                    b'- {\n'
                    b'            "savant"\n'
                    b'        }'
                    in projected
                )
            ),

        "candidate_fallback_preserved":
            (
                b'else set(\n'
                b'            candidate_tokens\n'
                b'        )'
                in projected
            ),

        "authority_effect_unchanged":
            (
                b'authority_effect = "none"'
                in projected
            ),
    }

    if not all(
        checks.values()
    ):
        failed = [
            name
            for name, ok
            in checks.items()
            if not ok
        ]

        raise repair_error(
            "projection checks failed: "
            + ", ".join(
                failed
            )
        )

    return {
        "path":
            path,
        "source":
            source,
        "projected":
            projected,
        "mode":
            mode,
        "state":
            state,
        "checks":
            checks,
    }


def atomic_write(
    path: Path,
    data: bytes,
    mode: int,
) -> None:
    temporary = path.with_name(
        f".{path.name}."
        "correlation-repair.tmp"
    )

    if (
        temporary.exists()
        or temporary.is_symlink()
    ):
        raise repair_error(
            "temporary path already exists: "
            f"{temporary}"
        )

    descriptor = os.open(
        temporary,
        (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
        ),
        mode,
    )

    try:
        with os.fdopen(
            descriptor,
            "wb",
            closefd=True,
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
            mode,
        )

        os.replace(
            temporary,
            path,
        )

        directory = os.open(
            path.parent,
            os.O_RDONLY,
        )

        try:
            os.fsync(
                directory
            )

        finally:
            os.close(
                directory
            )

    finally:
        if temporary.exists():
            temporary.unlink()


def apply_plan(
    root: Path,
    plan: dict,
) -> None:
    if (
        plan[
            "state"
        ]
        == "already_repaired"
    ):
        return

    path = plan[
        "path"
    ]

    backup = (
        root
        / backup_relative
    )

    current, _ = (
        read_regular(
            path
        )
    )

    if (
        digest(
            current
        )
        != digest(
            plan[
                "source"
            ]
        )
    ):
        raise repair_error(
            "source changed before backup"
        )

    backup.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if (
        backup.exists()
        or backup.is_symlink()
    ):
        existing, _ = (
            read_regular(
                backup
            )
        )

        if (
            digest(
                existing
            )
            != digest(
                plan[
                    "source"
                ]
            )
        ):
            raise repair_error(
                "conflicting backup: "
                f"{backup}"
            )

    else:
        shutil.copy2(
            path,
            backup,
            follow_symlinks=False,
        )

        copied, _ = (
            read_regular(
                backup
            )
        )

        if (
            digest(
                copied
            )
            != digest(
                plan[
                    "source"
                ]
            )
        ):
            raise repair_error(
                "backup verification "
                f"failed: {backup}"
            )

    current, _ = (
        read_regular(
            path
        )
    )

    if (
        digest(
            current
        )
        != digest(
            plan[
                "source"
            ]
        )
    ):
        raise repair_error(
            "source changed "
            "before mutation"
        )

    atomic_write(
        path,
        plan[
            "projected"
        ],
        plan[
            "mode"
        ],
    )

    written, _ = (
        read_regular(
            path
        )
    )

    if (
        digest(
            written
        )
        != after_sha256
    ):
        atomic_write(
            path,
            plan[
                "source"
            ],
            plan[
                "mode"
            ],
        )

        raise repair_error(
            "post-write verification "
            "failed; source restored"
        )


def result(
    plan: dict,
    apply_mode: bool,
) -> dict:
    return {
        "schema":
            schema,
        "ok":
            True,
        "mode":
            (
                "apply"
                if apply_mode
                else "plan"
            ),
        "path":
            str(
                target_relative
            ),
        "state":
            plan[
                "state"
            ],
        "source_sha256":
            digest(
                plan[
                    "source"
                ]
            ),
        "projected_sha256":
            digest(
                plan[
                    "projected"
                ]
            ),
        "checks":
            plan[
                "checks"
            ],
    }


def main() -> int:
    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=canonical_root,
    )

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    arguments = (
        parser.parse_args()
    )

    try:
        plan = build_plan(
            arguments.root
        )

        if arguments.apply:
            apply_plan(
                arguments.root,
                plan,
            )

            plan = build_plan(
                arguments.root
            )

        print(
            json.dumps(
                result(
                    plan,
                    arguments.apply,
                ),
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
                    "ok":
                        False,
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

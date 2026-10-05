#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile


schema = (
    "savant://migration/sieve/"
    "source-targeting-correlation-repair/1.0.1"
)

root = Path(
    "/root/savant-runtime"
)

target = (
    root
    / "tools/extr-enterprise/runtime/"
    "source_targeting.py"
)

backup = (
    root
    / "evolution/structure-migration/backups/"
    "20260928-sieve-source-targeting-correlation-repair/"
    "source_targeting.py"
)

before_sha256 = (
    "c52571ae75f189496be453b346eab7e8"
    "80349a0bcd53b1c97f009218121725"
)

after_sha256 = (
    "595ce6b34a6fe2d6e30be86c5d59c37"
    "cdaa8991c37a4f988cd6ea9281b091f22"
)

old = b'''    prioritized = (
        set(
            signals
        )
        or set(
            candidate_tokens
        )
    )
'''

new = b'''    correlation_signals = (
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


def sha256(
    data: bytes,
) -> str:
    return hashlib.sha256(
        data
    ).hexdigest()


def read_regular(
    path: Path,
) -> tuple[
    bytes,
    int,
]:
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
            f"refusing non-regular file: {path}"
        )

    return (
        path.read_bytes(),
        stat.S_IMODE(
            info.st_mode
        ),
    )


def projected(
    source: bytes,
) -> bytes:
    count = source.count(
        old
    )

    if count != 1:
        raise repair_error(
            "expected one runtime-correlation "
            f"block; found {count}"
        )

    result = source.replace(
        old,
        new,
        1,
    )

    actual = sha256(
        result
    )

    if actual != after_sha256:
        raise repair_error(
            "projected digest mismatch: "
            f"expected {after_sha256}, "
            f"found {actual}"
        )

    return result


def inspect() -> dict:
    source, mode = read_regular(
        target
    )

    actual = sha256(
        source
    )

    if actual == after_sha256:
        return {
            "source":
                source,
            "projected":
                source,
            "mode":
                mode,
            "state":
                "already_repaired",
        }

    if actual != before_sha256:
        raise repair_error(
            "unexpected source digest: "
            f"expected {before_sha256} "
            f"or {after_sha256}, "
            f"found {actual}"
        )

    result = projected(
        source
    )

    return {
        "source":
            source,
        "projected":
            result,
        "mode":
            mode,
        "state":
            "repair_required",
    }


def atomic_write(
    path: Path,
    data: bytes,
    mode: int,
) -> None:
    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=(
                ".source-targeting-"
                "repair-"
            ),
            dir=str(
                path.parent
            ),
        )
    )

    temporary = Path(
        temporary_name
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
        temporary.unlink(
            missing_ok=True
        )


def apply(
    plan: dict,
) -> None:
    if (
        plan[
            "state"
        ]
        == "already_repaired"
    ):
        return

    current, _ = read_regular(
        target
    )

    if (
        sha256(
            current
        )
        != before_sha256
    ):
        raise repair_error(
            "target changed before backup"
        )

    backup.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if backup.exists():
        existing, _ = read_regular(
            backup
        )

        if (
            sha256(
                existing
            )
            != before_sha256
        ):
            raise repair_error(
                "conflicting backup exists: "
                f"{backup}"
            )

    else:
        shutil.copy2(
            target,
            backup,
            follow_symlinks=False,
        )

        copied, _ = read_regular(
            backup
        )

        if (
            sha256(
                copied
            )
            != before_sha256
        ):
            raise repair_error(
                "backup verification failed"
            )

    current, _ = read_regular(
        target
    )

    if (
        sha256(
            current
        )
        != before_sha256
    ):
        raise repair_error(
            "target changed before mutation"
        )

    atomic_write(
        target,
        plan[
            "projected"
        ],
        plan[
            "mode"
        ],
    )

    written, _ = read_regular(
        target
    )

    if (
        sha256(
            written
        )
        != after_sha256
    ):
        atomic_write(
            target,
            plan[
                "source"
            ],
            plan[
                "mode"
            ],
        )

        raise repair_error(
            "post-write verification failed; "
            "original restored"
        )


def output(
    mode: str,
    plan: dict,
) -> None:
    print(
        json.dumps(
            {
                "schema":
                    schema,
                "ok":
                    True,
                "mode":
                    mode,
                "state":
                    plan[
                        "state"
                    ],
                "source_sha256":
                    sha256(
                        plan[
                            "source"
                        ]
                    ),
                "projected_sha256":
                    sha256(
                        plan[
                            "projected"
                        ]
                    ),
            },
            indent=2,
            sort_keys=True,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    arguments = parser.parse_args()

    try:
        plan = inspect()

        if arguments.apply:
            apply(
                plan
            )

            plan = inspect()

        output(
            (
                "apply"
                if arguments.apply
                else "plan"
            ),
            plan,
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

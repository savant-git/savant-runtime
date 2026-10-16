#!/usr/bin/env python3

from __future__ import annotations

import ast
import os
import shutil
import tempfile
from pathlib import Path


TARGET = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/niche/runtime/"
    "living_task.py"
)

OLD = '''        connection.execute(
            "PRAGMA journal_mode = WAL"
        )

        connection.execute(
            "PRAGMA busy_timeout = 5000"
        )
'''

NEW = '''        connection.execute(
            "PRAGMA busy_timeout = 5000"
        )
'''


def main() -> int:
    source = TARGET.read_text(
        encoding="utf-8"
    )

    count = source.count(OLD)

    if count != 1:
        raise SystemExit(
            "repair refused: expected exactly one "
            "verified _connect WAL block; found "
            + str(count)
        )

    repaired = source.replace(
        OLD,
        NEW,
        1,
    )

    ast.parse(
        repaired,
        filename=str(TARGET),
    )

    target_stat = TARGET.stat()

    backup = TARGET.with_name(
        TARGET.name
        + ".pre-wal-connect-repair"
    )

    if not backup.exists():
        shutil.copy2(
            TARGET,
            backup,
        )

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=TARGET.name + ".",
            suffix=".tmp",
            dir=str(TARGET.parent),
            text=True,
        )
    )

    temporary = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(
                repaired
            )
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.chmod(
            temporary,
            target_stat.st_mode & 0o7777,
        )

        os.replace(
            temporary,
            TARGET,
        )

    finally:
        if temporary.exists():
            temporary.unlink()

    print(
        "repaired: "
        + str(TARGET)
    )

    print(
        "preserved backup: "
        + str(backup)
    )

    print(
        "change: journal_mode=WAL remains "
        "database initialization responsibility; "
        "ordinary _connect calls no longer renegotiate it"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

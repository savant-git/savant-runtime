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

OLD = '''    def tasks(
        self,
    ) -> tuple[Task, ...]:
        with self._connect() as connection:
            ids = [
                row["task_id"]
                for row
                in connection.execute(
                    """
                    SELECT task_id
                    FROM tasks
                    ORDER BY task_id
                    """
                )
            ]

        return tuple(
            self.get(task_id)
            for task_id in ids
        )
'''

NEW = '''    def tasks(
        self,
    ) -> tuple[Task, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM tasks
                ORDER BY task_id
                """
            ).fetchall()

            dependency_rows = (
                connection.execute(
                    """
                    SELECT
                        task_id,
                        dependency_id
                    FROM dependencies
                    ORDER BY
                        task_id,
                        dependency_id
                    """
                ).fetchall()
            )

        dependencies: dict[
            str,
            list[str],
        ] = {
            row["task_id"]: []
            for row in rows
        }

        for dependency_row in (
            dependency_rows
        ):
            dependencies.setdefault(
                dependency_row["task_id"],
                [],
            ).append(
                dependency_row[
                    "dependency_id"
                ]
            )

        return tuple(
            self._row_to_task(
                row,
                dependencies.get(
                    row["task_id"],
                    (),
                ),
            )
            for row in rows
        )
'''


def main() -> int:
    source = TARGET.read_text(
        encoding="utf-8"
    )

    count = source.count(OLD)

    if count != 1:
        raise SystemExit(
            "repair refused: expected exactly "
            "one verified tasks() implementation; "
            f"found {count}"
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

    backup = TARGET.with_name(
        TARGET.name
        + ".pre-task-snapshot-repair"
    )

    if not backup.exists():
        shutil.copy2(
            TARGET,
            backup,
        )

    target_stat = TARGET.stat()

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
            target_stat.st_mode
            & 0o7777,
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
        "change: tasks() now hydrates the "
        "authoritative task snapshot and direct "
        "dependency edges in two deterministic "
        "queries instead of reopening SQLite "
        "once per task"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

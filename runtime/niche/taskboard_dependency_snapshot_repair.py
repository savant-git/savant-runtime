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

OLD = '''    def dependency_map(
        self,
    ) -> dict[
        str,
        tuple[str, ...],
    ]:
        tasks = {
            task.task_id
            for task in self.tasks()
        }

        result: dict[
            str,
            set[str],
        ] = {
            task_id: set()
            for task_id in tasks
        }

        with self._connect() as connection:
            for row in connection.execute(
                """
                SELECT task_id, dependency_id
                FROM dependencies
                ORDER BY task_id, dependency_id
                """
            ):
                result.setdefault(
                    row["task_id"],
                    set(),
                ).add(
                    row[
                        "dependency_id"
                    ]
                )

                result.setdefault(
                    row[
                        "dependency_id"
                    ],
                    set(),
                )

        return {
            key: tuple(
                sorted(value)
            )
            for key, value
            in sorted(
                result.items()
            )
        }
'''

NEW = '''    def dependency_map(
        self,
    ) -> dict[
        str,
        tuple[str, ...],
    ]:
        with self._connect() as connection:
            task_ids = [
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

        result: dict[
            str,
            set[str],
        ] = {
            task_id: set()
            for task_id in task_ids
        }

        for row in dependency_rows:
            result.setdefault(
                row["task_id"],
                set(),
            ).add(
                row[
                    "dependency_id"
                ]
            )

            result.setdefault(
                row[
                    "dependency_id"
                ],
                set(),
            )

        return {
            key: tuple(
                sorted(value)
            )
            for key, value
            in sorted(
                result.items()
            )
        }
'''


def main() -> int:
    source = TARGET.read_text(
        encoding="utf-8"
    )

    count = source.count(
        OLD
    )

    if count != 1:
        raise SystemExit(
            "repair refused: expected exactly "
            "one verified dependency_map() "
            f"implementation; found {count}"
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
        + ".pre-dependency-snapshot-repair"
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
        "change: dependency_map() now "
        "projects task identities and direct "
        "dependency edges from one SQLite "
        "snapshot without hydrating every task"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

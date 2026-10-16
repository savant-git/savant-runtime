#!/usr/bin/env python3

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


DATABASE = Path(
    "/root/savant-runtime/audit/archive-rule-extraction/"
    "ae2420cc26989b23f18f3dd579c69f2c9c8d9d107d90793173cf4f8fe74af1af/"
    "reduced/reduction.sqlite3"
)


def main() -> int:
    if not DATABASE.is_file():
        print(
            f"database does not exist: {DATABASE}",
            file=sys.stderr,
        )
        return 1

    connection = sqlite3.connect(
        str(DATABASE)
    )

    try:
        rows = connection.execute(
            """
            SELECT
                representative_path,
                COUNT(*) AS groups,
                SUM(occurrence_count) AS occurrences
            FROM groups
            WHERE strength = 'explicit_normative'
            GROUP BY representative_path
            ORDER BY
                groups DESC,
                occurrences DESC,
                representative_path ASC
            """
        )

        total_sources = 0
        total_groups = 0
        total_occurrences = 0

        print(
            "groups\toccurrences\trepresentative_path"
        )

        for path, groups, occurrences in rows:
            groups = int(groups or 0)
            occurrences = int(occurrences or 0)

            total_sources += 1
            total_groups += groups
            total_occurrences += occurrences

            print(
                f"{groups}\t"
                f"{occurrences}\t"
                f"{path}"
            )

        print()
        print(
            f"source_paths={total_sources}"
        )
        print(
            f"explicit_normative_groups={total_groups}"
        )
        print(
            "representative_occurrences="
            f"{total_occurrences}"
        )

    except sqlite3.Error as exc:
        print(
            "query failed: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    finally:
        connection.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

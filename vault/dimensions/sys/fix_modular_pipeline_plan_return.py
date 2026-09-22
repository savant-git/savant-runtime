#!/usr/bin/env python3

from __future__ import annotations

import json
import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path


TARGET = Path(
    "/root/savant-runtime/vault/dimensions/sys/run_modular_pipeline.py"
)

BACKUP_ROOT = Path(
    "/root/savant-runtime/vault/dimensions/sys/backups/"
    "modular-pipeline-plan-return"
)

OLD = """\
    Stage(
        ordinal=2,
        key="plan",
        script=SYS_ROOT / "plan_modular_migration.py",
        operation="plan",
        output=REPORT_ROOT / "modular-migration" / "latest.json",
        acceptable_return_codes=(0, 2),
    ),
"""

NEW = """\
    Stage(
        ordinal=2,
        key="plan",
        script=SYS_ROOT / "plan_modular_migration.py",
        operation="plan",
        output=REPORT_ROOT / "modular-migration" / "latest.json",
        acceptable_return_codes=(0, 1),
    ),
"""


def timestamp() -> str:
    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def main() -> int:
    if not TARGET.is_file():
        raise FileNotFoundError(
            f"missing target: {TARGET}"
        )

    source = TARGET.read_text(
        encoding="utf-8"
    )

    if NEW in source:
        py_compile.compile(
            str(TARGET),
            doraise=True,
        )

        print(
            json.dumps(
                {
                    "operation": (
                        "fix_modular_pipeline_plan_return"
                    ),
                    "passed": True,
                    "mutation_performed": False,
                    "state": "already-correct",
                    "target": str(TARGET),
                    "plan_return_codes": [0, 1],
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    if OLD not in source:
        raise RuntimeError(
            "Plan stage does not match the "
            "expected verified pre-change form."
        )

    if source.count(OLD) != 1:
        raise RuntimeError(
            "Expected exactly one old plan-stage contract."
        )

    updated = source.replace(
        OLD,
        NEW,
        1,
    )

    backup_dir = (
        BACKUP_ROOT
        / timestamp()
    )

    backup_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    backup_path = (
        backup_dir
        / "run_modular_pipeline.py"
    )

    shutil.copy2(
        TARGET,
        backup_path,
    )

    try:
        TARGET.write_text(
            updated,
            encoding="utf-8",
        )

        py_compile.compile(
            str(TARGET),
            doraise=True,
        )

        installed = TARGET.read_text(
            encoding="utf-8"
        )

        if installed.count(NEW) != 1:
            raise RuntimeError(
                "New plan-stage contract was not installed exactly once."
            )

        audit_index = installed.index(
            'key="audit"'
        )

        plan_index = installed.index(
            'key="plan"'
        )

        classification_index = installed.index(
            'key="classification"'
        )

        audit_block = installed[
            audit_index:plan_index
        ]

        plan_block = installed[
            plan_index:classification_index
        ]

        if (
            "acceptable_return_codes=(0, 1, 2)"
            not in audit_block
        ):
            raise RuntimeError(
                "Audit-stage return contract changed unexpectedly."
            )

        if (
            "acceptable_return_codes=(0, 1)"
            not in plan_block
        ):
            raise RuntimeError(
                "Plan-stage return contract was not installed."
            )

    except BaseException:
        shutil.copy2(
            backup_path,
            TARGET,
        )
        raise

    print(
        json.dumps(
            {
                "operation": (
                    "fix_modular_pipeline_plan_return"
                ),
                "passed": True,
                "mutation_performed": True,
                "target": str(TARGET),
                "backup": str(
                    backup_path
                ),
                "previous_plan_return_codes": [
                    0,
                    2,
                ],
                "current_plan_return_codes": [
                    0,
                    1,
                ],
                "audit_return_codes_preserved": [
                    0,
                    1,
                    2,
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

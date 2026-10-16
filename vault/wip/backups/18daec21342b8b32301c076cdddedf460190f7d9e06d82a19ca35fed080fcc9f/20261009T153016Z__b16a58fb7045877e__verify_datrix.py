#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from ontology.obelisks._template.segue.gates._template.segue.innates._template.segue.exiles.niche.runtime.living_task import (
    LivingTaskEngine,
)


def main() -> None:
    with TemporaryDirectory() as directory:
        path = (
            Path(directory)
            / "niche-test.datrix"
        )

        engine = LivingTaskEngine(
            path
        )

        created = engine.create(
            task_id=(
                "datrix-functional-check"
            ),
            purpose=(
                "verify niche datrix "
                "persistence"
            ),
            owner="exile:niche",
            jurisdiction="niche",
            authority_basis=(
                "migration-verification",
            ),
            completion_condition=(
                "task survives datrix "
                "checkpoint and reload"
            ),
        )

        updated = engine.update(
            created.task_id,
            priority="high",
        )

        reloaded = LivingTaskEngine(
            path
        )
        persisted = reloaded.get(
            created.task_id
        )
        history = reloaded.history(
            created.task_id
        )
        history_valid = (
            reloaded.validate_history_chain()[
                0
            ]
        )

        assert (
            persisted.priority
            == "high"
        )
        assert len(history) == 2
        assert history_valid is True

        print(
            "created:",
            created.task_id,
        )
        print(
            "updated_priority:",
            updated.priority,
        )
        print(
            "reloaded_priority:",
            persisted.priority,
        )
        print(
            "history_events:",
            len(history),
        )
        print(
            "history_chain_valid:",
            history_valid,
        )
        print(
            "focused_functional_check: PASS"
        )


if __name__ == "__main__":
    main()

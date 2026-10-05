#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Mapping


root = Path("/root/savant-runtime").resolve()

palaver_runtime = (
    root
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "palaver"
    / "runtime"
)

grounded_development_path = (
    palaver_runtime
    / "grounded_development.py"
)

niche_bridge_path = (
    palaver_runtime
    / "niche_bridge.py"
)

owner = "palaver"
task_owner = "exile:niche"
persona_owner = "envoy"
execution_owner = "opus"
mutation_owner = "coda"

plan_schema = (
    "savant://palaver/"
    "task-grounded-development-plan/1.0.0"
)

run_schema = (
    "savant://palaver/"
    "task-grounded-development-run/1.0.0"
)


class TaskGroundedDevelopmentError(
    RuntimeError
):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def load_module(
    name: str,
    path: Path,
) -> ModuleType:
    existing = sys.modules.get(
        name
    )

    if existing is not None:
        return existing

    if not path.is_file():
        raise TaskGroundedDevelopmentError(
            "required runtime missing: "
            + str(path)
        )

    spec = (
        importlib.util.spec_from_file_location(
            name,
            path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise TaskGroundedDevelopmentError(
            "unable to load runtime: "
            + str(path)
        )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    sys.modules[
        name
    ] = module

    try:
        spec.loader.exec_module(
            module
        )
    except Exception:
        sys.modules.pop(
            name,
            None,
        )
        raise

    return module


def load_grounded_development() -> ModuleType:
    return load_module(
        "savant_palaver_task_grounded_base",
        grounded_development_path,
    )


def load_niche_bridge() -> ModuleType:
    return load_module(
        "savant_palaver_task_niche_bridge",
        niche_bridge_path,
    )


def compose_instruction(
    *,
    task_projection: Mapping[str, Any],
    instruction: str | None = None,
) -> str:
    niche = load_niche_bridge()

    task_instruction = (
        niche.task_system_instruction(
            task_projection
        )
    )

    user_instruction = str(
        instruction
        or (
            "Implement the next actionable Niche task "
            "using the minimum complete implementation "
            "required by its accepted authority."
        )
    ).strip()

    return (
        user_instruction
        + "\n\n"
        + task_instruction
    )


def select_task() -> dict[str, Any]:
    niche = load_niche_bridge()

    projection = (
        niche.select_next_task()
    )

    if projection is None:
        raise TaskGroundedDevelopmentError(
            "no actionable Niche task "
            "is available"
        )

    if not isinstance(
        projection,
        dict,
    ):
        raise TaskGroundedDevelopmentError(
            "Niche task selection returned "
            "non-object"
        )

    if (
        projection.get(
            "owner"
        )
        != task_owner
    ):
        raise TaskGroundedDevelopmentError(
            "Niche task ownership "
            "boundary failed"
        )

    task = projection.get(
        "task"
    )

    if not isinstance(
        task,
        Mapping,
    ):
        raise TaskGroundedDevelopmentError(
            "selected Niche task missing"
        )

    if not task.get(
        "task_id"
    ):
        raise TaskGroundedDevelopmentError(
            "selected Niche task "
            "has no task_id"
        )

    return projection


def plan_next_task_development(
    *,
    instruction: str | None = None,
    persona_id: str = "orobouros",
    domains: Iterable[Any] = (),
    signals: Iterable[Any] = (),
    cap: int | None = None,
) -> dict[str, Any]:
    grounded = (
        load_grounded_development()
    )

    niche = load_niche_bridge()

    task_projection = (
        select_task()
    )

    final_instruction = (
        compose_instruction(
            task_projection=(
                task_projection
            ),
            instruction=instruction,
        )
    )

    plan = (
        grounded.plan_development(
            instruction=(
                final_instruction
            ),
            persona_id=(
                persona_id
            ),
            cap=cap,
        )
    )

    if not isinstance(
        plan,
        dict,
    ):
        raise TaskGroundedDevelopmentError(
            "grounded development plan "
            "returned non-object"
        )

    task_context = (
        niche.task_context(
            task_projection
        )
    )

    result = dict(
        plan
    )

    result.update(
        {
            "schema": plan_schema,
            "owner": owner,
            "task_owner": (
                task_owner
            ),
            "persona_owner": (
                persona_owner
            ),
            "execution_owner": (
                execution_owner
            ),
            "mutation_owner": (
                mutation_owner
            ),
            "niche_task": (
                task_context
            ),
            "task_selected": True,
            "authority_effect": (
                "none"
            ),
        }
    )

    result[
        "task_digest"
    ] = digest(
        {
            "task_id": (
                task_projection.get(
                    "task",
                    {}
                ).get(
                    "task_id"
                )
            ),
            "task_projection_digest": (
                task_projection.get(
                    "digest"
                )
            ),
            "development_plan_digest": (
                plan.get(
                    "digest"
                )
            ),
        }
    )

    return result


def reconciliation_hint(
    *,
    task_projection: Mapping[str, Any],
    committed: bool,
    commit_result: Mapping[str, Any] | None,
) -> dict[str, Any]:
    task = task_projection.get(
        "task",
        {}
    )

    selection = (
        task_projection.get(
            "selection",
            {},
        )
    )

    return {
        "owner": task_owner,
        "task_id": (
            task.get(
                "task_id"
            )
        ),
        "task_digest": (
            task_projection.get(
                "digest"
            )
        ),
        "dependencies_satisfied": (
            selection.get(
                "dependencies_satisfied",
                False,
            )
        ),
        "committed": committed,
        "successful_coda_mutation": (
            bool(
                committed
                and commit_result
            )
        ),
        "recommended_transition": (
            "completed"
            if (
                committed
                and commit_result
            )
            else "unchanged"
        ),
        "evidence_required": True,
        "authority_effect": "none",
    }


def develop_next_task(
    *,
    instruction: str | None = None,
    persona_id: str = "orobouros",
    cap: int | None = None,
    commit: bool = False,
) -> dict[str, Any]:
    grounded = (
        load_grounded_development()
    )

    niche = load_niche_bridge()

    task_projection = (
        select_task()
    )

    final_instruction = (
        compose_instruction(
            task_projection=(
                task_projection
            ),
            instruction=instruction,
        )
    )

    run = grounded.develop(
        instruction=(
            final_instruction
        ),
        persona_id=(
            persona_id
        ),
        cap=cap,
        commit=commit,
    )

    if not isinstance(
        run,
        dict,
    ):
        raise TaskGroundedDevelopmentError(
            "grounded development run "
            "returned non-object"
        )

    committed = bool(
        run.get(
            "committed"
        )
    )

    commit_result = (
        run.get(
            "commit"
        )
        if isinstance(
            run.get(
                "commit"
            ),
            Mapping,
        )
        else None
    )

    task_context = (
        niche.task_context(
            task_projection
        )
    )

    result = {
        "schema": run_schema,
        "owner": owner,
        "task_owner": (
            task_owner
        ),
        "persona_owner": (
            persona_owner
        ),
        "execution_owner": (
            execution_owner
        ),
        "mutation_owner": (
            mutation_owner
        ),
        "committed": committed,
        "plan": run.get(
            "plan"
        ),
        "commit": commit_result,
        "niche_task": (
            task_context
        ),
        "reconciliation_hint": (
            reconciliation_hint(
                task_projection=(
                    task_projection
                ),
                committed=committed,
                commit_result=(
                    commit_result
                ),
            )
        ),
        "authority_effect": "none",
    }

    result[
        "digest"
    ] = digest(
        {
            "task_id": (
                task_projection.get(
                    "task",
                    {}
                ).get(
                    "task_id"
                )
            ),
            "task_digest": (
                task_projection.get(
                    "digest"
                )
            ),
            "committed": committed,
            "commit_digest": (
                commit_result.get(
                    "plan_digest"
                )
                if commit_result
                else None
            ),
        }
    )

    return result


def status() -> dict[str, Any]:
    grounded = (
        load_grounded_development()
    )

    niche = load_niche_bridge()

    base_status = (
        grounded.status()
    )

    selected = (
        niche.select_next_task()
    )

    checks = {
        "grounded_development_ready": (
            base_status.get(
                "ready"
            )
            is True
        ),
        "niche_bridge_available": (
            callable(
                getattr(
                    niche,
                    "select_next_task",
                    None,
                )
            )
        ),
        "niche_task_instruction_available": (
            callable(
                getattr(
                    niche,
                    "task_system_instruction",
                    None,
                )
            )
        ),
        "niche_task_context_available": (
            callable(
                getattr(
                    niche,
                    "task_context",
                    None,
                )
            )
        ),
        "task_owner_preserved": (
            selected is None
            or selected.get(
                "owner"
            )
            == task_owner
        ),
        "palaver_owner_preserved": (
            owner
            == "palaver"
        ),
        "envoy_owner_preserved": (
            persona_owner
            == "envoy"
        ),
        "opus_owner_preserved": (
            execution_owner
            == "opus"
        ),
        "coda_owner_preserved": (
            mutation_owner
            == "coda"
        ),
    }

    return {
        "schema": (
            "savant://palaver/"
            "task-grounded-development-status/1.0.0"
        ),
        "owner": owner,
        "task_owner": (
            task_owner
        ),
        "persona_owner": (
            persona_owner
        ),
        "execution_owner": (
            execution_owner
        ),
        "mutation_owner": (
            mutation_owner
        ),
        "actionable_task_present": (
            selected is not None
        ),
        "selected_task_id": (
            selected.get(
                "task",
                {}
            ).get(
                "task_id"
            )
            if selected
            else None
        ),
        "checks": checks,
        "ready": all(
            checks.values()
        ),
        "authority_effect": "none",
    }


if __name__ == "__main__":
    print(
        json.dumps(
            status(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )

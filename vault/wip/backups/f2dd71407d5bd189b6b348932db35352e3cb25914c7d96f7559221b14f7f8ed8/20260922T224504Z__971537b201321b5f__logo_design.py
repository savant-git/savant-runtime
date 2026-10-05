from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .iteration import criterion, job, policy
from .iteration_composition import project
from .job_adapter import adapter, execution_boundary


schema = "savant://runtime/urge/jobs/logo-design/1.0.0"
owner = "exile:urge"


class logo_design_error(ValueError):
    pass


_default_criteria = (
    criterion(
        id="conceptual_fit",
        weight=1.25,
        target=0.90,
        required=True,
    ),
    criterion(
        id="distinctiveness",
        weight=1.20,
        target=0.88,
    ),
    criterion(
        id="legibility",
        weight=1.15,
        target=0.92,
        required=True,
    ),
    criterion(
        id="scalability",
        weight=1.10,
        target=0.92,
        required=True,
    ),
    criterion(
        id="silhouette_strength",
        weight=1.00,
        target=0.86,
    ),
    criterion(
        id="reproduction_resilience",
        weight=1.00,
        target=0.90,
        required=True,
    ),
    criterion(
        id="memorability",
        weight=1.10,
        target=0.86,
    ),
    criterion(
        id="system_extensibility",
        weight=0.90,
        target=0.82,
    ),
)


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise logo_design_error(
            "logo design specification must be "
            "canonical-json serializable"
        ) from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def create_job(
    *,
    job_id: str,
    objective: str,
    initial_candidate: Any,
    brief: Mapping[str, Any],
    constraints: tuple[str, ...] = (),
    provenance: tuple[str, ...] = (),
    dependencies: tuple[str, ...] = (),
) -> job:
    if not isinstance(brief, Mapping):
        raise logo_design_error(
            "brief must be a mapping"
        )

    metadata = {
        "schema": schema,
        "domain": "logo-design",
        "brief": dict(brief),
        "brief_digest": _digest(
            dict(brief)
        ),
        "iteration_owner": owner,
        "execution_owner": "external",
    }

    return job(
        id=job_id,
        objective=objective,
        payload=initial_candidate,
        criteria=_default_criteria,
        constraints=constraints,
        provenance=provenance,
        dependencies=dependencies,
        metadata=metadata,
    )


def run(
    *,
    work: job,
    boundary: execution_boundary,
    run_policy: policy | None = None,
    convergence_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(work, job):
        raise logo_design_error(
            "work must be an urge job"
        )

    domain = work.metadata.get(
        "domain"
    )

    if domain != "logo-design":
        raise logo_design_error(
            "logo-design runner requires a "
            "logo-design job"
        )

    bridge = adapter(
        boundary
    )

    result = project(
        work,
        evaluator=bridge.evaluator,
        reviser=bridge.reviser,
        run_policy=(
            run_policy
            or policy(
                max_cycles=12,
                branch_factor=4,
                min_improvement=0.003,
                target_score=0.90,
                patience=3,
                max_candidates=48,
                max_failures=6,
                preserve_alternates=4,
            )
        ),
        convergence_policy=convergence_policy,
    )

    return {
        "schema": schema,
        "owner": owner,
        "domain": "logo-design",
        "authority_effect": "none",
        "projection_only": True,
        "result": result,
        "best_candidate": result[
            "iteration"
        ][
            "best"
        ],
        "alternates": result[
            "iteration"
        ][
            "alternates"
        ],
        "lineage": result[
            "iteration"
        ][
            "lineage"
        ],
        "stop_reason": result[
            "iteration"
        ][
            "stop_reason"
        ],
        "boundaries": {
            "declares_truth": False,
            "verifies_fact": False,
            "admits_evidence": False,
            "mutates_canon": False,
            "mutates_source": False,
            "creates_authority": False,
            "selects_provider": False,
            "executes_model": False,
        },
        "digest": result[
            "digest"
        ],
    }


__all__ = [
    "create_job",
    "logo_design_error",
    "run",
]

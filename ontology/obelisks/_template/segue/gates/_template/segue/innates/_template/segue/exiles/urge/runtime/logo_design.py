from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from .iteration import criterion, job, policy
from .iteration_composition import project
from .job_adapter import adapter, execution_boundary


schema = "savant://runtime/urge/jobs/logo-design/2.0.0"
owner = "exile:urge"


class logo_design_error(ValueError):
    pass


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
            "logo design value must be canonical-json serializable"
        ) from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(value, str):
        value = (value,)

    if (
        isinstance(value, bytes)
        or not isinstance(value, Sequence)
    ):
        raise logo_design_error(
            "expected a sequence"
        )

    result = []
    seen = set()

    for item in value:
        text = str(item).strip()

        if text and text not in seen:
            seen.add(text)
            result.append(text)

    return tuple(result)


_default_criteria = (
    criterion(
        id="conceptual_fit",
        weight=1.35,
        target=0.92,
        required=True,
    ),
    criterion(
        id="distinctiveness",
        weight=1.35,
        target=0.90,
        required=True,
    ),
    criterion(
        id="anti_cliche",
        weight=1.30,
        target=0.92,
        required=True,
    ),
    criterion(
        id="semantic_density",
        weight=1.15,
        target=0.88,
    ),
    criterion(
        id="surprising_coherence",
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
        weight=1.05,
        target=0.88,
    ),
    criterion(
        id="reproduction_resilience",
        weight=1.05,
        target=0.92,
        required=True,
    ),
    criterion(
        id="memorability",
        weight=1.15,
        target=0.90,
    ),
    criterion(
        id="system_extensibility",
        weight=1.00,
        target=0.86,
    ),
    criterion(
        id="negative_space_intelligence",
        weight=0.85,
        target=0.78,
    ),
    criterion(
        id="geometry_integrity",
        weight=0.95,
        target=0.88,
    ),
    criterion(
        id="monochrome_integrity",
        weight=1.00,
        target=0.92,
        required=True,
    ),
    criterion(
        id="micro_scale_integrity",
        weight=1.00,
        target=0.90,
        required=True,
    ),
    criterion(
        id="large_scale_presence",
        weight=0.90,
        target=0.86,
    ),
    criterion(
        id="motion_potential",
        weight=0.70,
        target=0.76,
    ),
    criterion(
        id="identity_ownership",
        weight=1.20,
        target=0.90,
        required=True,
    ),
)


def create_job(
    *,
    job_id: str,
    objective: str,
    initial_candidate: Any,
    brief: Mapping[str, Any],
    constraints: Sequence[str] = (),
    provenance: Sequence[str] = (),
    dependencies: Sequence[str] = (),
    known_tropes: Sequence[str] = (),
    protected_invariants: Sequence[str] = (),
    creative_alignment: Mapping[str, Any] | None = None,
) -> job:
    if not isinstance(brief, Mapping):
        raise logo_design_error(
            "brief must be a mapping"
        )

    if (
        creative_alignment is not None
        and not isinstance(
            creative_alignment,
            Mapping,
        )
    ):
        raise logo_design_error(
            "creative_alignment must be a mapping"
        )

    normalized_brief = dict(
        brief
    )

    metadata = {
        "schema": schema,
        "domain": "logo-design",
        "brief": normalized_brief,
        "brief_digest": _digest(
            normalized_brief
        ),
        "known_tropes": list(
            _strings(
                known_tropes
            )
        ),
        "protected_invariants": list(
            _strings(
                protected_invariants
            )
        ),
        "creative_alignment": (
            dict(
                creative_alignment
            )
            if creative_alignment
            is not None
            else None
        ),
        "design_protocol": {
            "concept_before_style": True,
            "mechanism_before_decoration": True,
            "divergent_families_before_variants": True,
            "monochrome_before_color_dependency": True,
            "silhouette_before_detail": True,
            "micro_scale_validation": True,
            "large_scale_validation": True,
            "negative_space_validation": True,
            "geometry_validation": True,
            "category_trope_rejection": True,
            "internal_similarity_rejection": True,
            "semantic_explanation_required": True,
            "reproduction_validation": True,
            "identity_system_extension": True,
            "motion_extension": True,
        },
        "iteration_owner": owner,
        "execution_owner": "external",
    }

    return job(
        id=job_id,
        objective=objective,
        payload=initial_candidate,
        criteria=_default_criteria,
        constraints=_strings(
            constraints
        ),
        provenance=_strings(
            provenance
        ),
        dependencies=_strings(
            dependencies
        ),
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

    if (
        work.metadata.get(
            "domain"
        )
        != "logo-design"
    ):
        raise logo_design_error(
            "logo-design runner requires a logo-design job"
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
                max_cycles=16,
                branch_factor=6,
                min_improvement=0.002,
                target_score=0.92,
                patience=4,
                max_candidates=96,
                max_failures=8,
                preserve_alternates=8,
            )
        ),
        convergence_policy=convergence_policy,
    )

    projection = {
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
        "design_quality": {
            "criteria": [
                item.id
                for item in work.criteria
            ],
            "required_criteria": [
                item.id
                for item in work.criteria
                if item.required
            ],
            "brief_digest": work.metadata[
                "brief_digest"
            ],
            "creative_alignment_digest": (
                None
                if work.metadata.get(
                    "creative_alignment"
                )
                is None
                else work.metadata[
                    "creative_alignment"
                ].get(
                    "digest"
                )
            ),
        },
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
    }

    projection["digest"] = _digest(
        projection
    )

    return projection


__all__ = [
    "create_job",
    "logo_design_error",
    "run",
]

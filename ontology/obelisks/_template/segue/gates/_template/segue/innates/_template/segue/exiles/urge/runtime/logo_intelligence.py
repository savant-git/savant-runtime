from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from .creative_orchestration import (
    creative_engine,
    creative_policy,
)


schema = "savant://runtime/urge/logo-intelligence/1.0.0"
owner = "exile:urge"


class logo_intelligence_error(
    ValueError
):
    pass


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        _canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def _strings(
    value: Any,
) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(
        value,
        str,
    ):
        value = (
            value,
        )

    if (
        isinstance(
            value,
            bytes,
        )
        or not isinstance(
            value,
            Sequence,
        )
    ):
        raise logo_intelligence_error(
            "expected a sequence"
        )

    output = []
    seen = set()

    for item in value:
        text = str(
            item
        ).strip()

        if (
            text
            and text not in seen
        ):
            seen.add(
                text
            )
            output.append(
                text
            )

    return tuple(
        output
    )


_default_cliches = (
    "initials merged into an arbitrary monogram",
    "letter hidden inside negative space without deeper meaning",
    "generic geometric icon beside a wordmark",
    "infinity symbol",
    "abstract swoosh",
    "generic orbit",
    "generic spark",
    "generic starburst",
    "generic shield",
    "generic cube",
    "generic hexagon",
    "generic network nodes",
    "generic circuit traces",
    "generic brain",
    "generic fingerprint",
    "generic eye",
    "generic lightbulb",
    "generic rocket",
    "generic crown",
    "generic mountain",
    "generic globe",
    "generic arrow",
    "generic checkmark",
    "generic chat bubble",
    "generic aperture",
    "generic atom",
    "generic wave",
    "generic gradient blob",
    "generic futuristic glyph",
    "randomized geometry justified after the fact",
    "thin sans serif wordmark presented as premium identity",
    "black and gold presented as luxury without conceptual basis",
    "neon gradient presented as technology without conceptual basis",
)


_logo_invariants = (
    "the concept must remain recognizable when color is removed",
    "the identity must survive reduction to practical small sizes",
    "the identity must survive enlargement without depending on micro-detail",
    "the central mechanism must be explainable without marketing fiction",
    "the concept must not depend on animation to make static use coherent",
    "the symbol and wordmark must have an intentional relationship",
    "visual novelty must arise from a defensible mechanism",
    "geometry must serve identity rather than decorate it",
    "the system must support deterministic vector realization",
    "the concept must remain extensible into a broader identity system",
)


_stress_tests = (
    "one-color reproduction",
    "reversed reproduction",
    "favicon scale",
    "social-avatar crop",
    "small print",
    "large signage",
    "embroidery",
    "laser engraving",
    "vinyl cutting",
    "low-resolution display",
    "silhouette-only recognition",
    "blurred peripheral recognition",
    "horizontal lockup",
    "vertical lockup",
    "symbol-only use",
    "wordmark-only use",
    "motion transition",
    "dark background",
    "light background",
    "accessibility contrast",
)


def project(
    *,
    name: str,
    brief: Mapping[
        str,
        Any,
    ],
    objective: str | None = None,
    constraints: Sequence[str] = (),
    protected_invariants: Sequence[str] = (),
    known_cliches: Sequence[str] = (),
    references_to_avoid: Sequence[str] = (),
    run_policy: creative_policy
    | None = None,
) -> dict[str, Any]:
    name = str(
        name
    ).strip()

    if not name:
        raise logo_intelligence_error(
            "name is required"
        )

    if not isinstance(
        brief,
        Mapping,
    ):
        raise logo_intelligence_error(
            "brief must be a mapping"
        )

    normalized_brief = dict(
        brief
    )

    normalized_constraints = (
        _strings(
            constraints
        )
    )

    invariants = tuple(
        dict.fromkeys(
            (
                *_logo_invariants,
                *_strings(
                    protected_invariants
                ),
            )
        )
    )

    cliches = tuple(
        dict.fromkeys(
            (
                *_default_cliches,
                *_strings(
                    known_cliches
                ),
            )
        )
    )

    baselines = _strings(
        references_to_avoid
    )

    resolved_objective = (
        str(
            objective
        ).strip()
        if objective is not None
        else ""
    )

    if not resolved_objective:
        resolved_objective = (
            f"create a proprietary, coherent, memorable, "
            f"highly extensible logo identity for {name} "
            "whose distinction comes from its underlying "
            "conceptual and visual mechanism rather than "
            "from fashionable styling"
        )

    engine = creative_engine(
        run_policy
    )

    creative = engine.project(
        objective=resolved_objective,
        constraints=(
            normalized_constraints
        ),
        invariants=invariants,
        cliches=cliches,
        baselines=baselines,
        context={
            "domain": "logo-design",
            "name": name,
            "brief": normalized_brief,
            "brief_digest": _digest(
                normalized_brief
            ),
            "stress_tests": list(
                _stress_tests
            ),
            "evaluation_dimensions": [
                "conceptual_fit",
                "distinctiveness",
                "anti_cliche",
                "semantic_density",
                "surprising_coherence",
                "legibility",
                "scalability",
                "silhouette_strength",
                "reproduction_resilience",
                "memorability",
                "system_extensibility",
                "negative_space_intelligence",
                "geometry_integrity",
                "monochrome_integrity",
                "micro_scale_integrity",
                "large_scale_presence",
                "motion_potential",
                "identity_ownership",
            ],
            "renderer": {
                "state": (
                    "integration-reserved"
                ),
                "contract": (
                    "savant-svg-renderer"
                ),
                "ownership": (
                    "external-to-urge"
                ),
                "canonical_vector_output": (
                    False
                ),
                "integration_rule": (
                    "attach completed renderer "
                    "through a typed projection "
                    "boundary without moving "
                    "renderer ownership into urge"
                ),
            },
        },
    )

    projection = {
        "schema": schema,
        "owner": owner,
        "authority_effect": "none",
        "projection_only": True,
        "name": name,
        "brief": normalized_brief,
        "brief_digest": _digest(
            normalized_brief
        ),
        "objective": (
            resolved_objective
        ),
        "constraints": list(
            normalized_constraints
        ),
        "invariants": list(
            invariants
        ),
        "cliche_baselines": list(
            cliches
        ),
        "references_to_avoid": list(
            baselines
        ),
        "stress_tests": list(
            _stress_tests
        ),
        "creative_projection": (
            creative
        ),
        "frontier": creative[
            "frontier"
        ],
        "renderer_integration": {
            "state": (
                "reserved"
            ),
            "renderer": (
                "savant-svg-renderer"
            ),
            "binding": None,
            "rule": (
                "renderer integration is "
                "instanced when the renderer "
                "is complete; urge does not "
                "duplicate renderer substance"
            ),
        },
        "boundaries": {
            "creates_authority": False,
            "mutates_canon": False,
            "mutates_source": False,
            "owns_provider_routing": False,
            "owns_underscore": False,
            "owns_svg_renderer": False,
            "owns_iteration": True,
        },
    }

    projection[
        "digest"
    ] = _digest(
        projection
    )

    return projection


__all__ = [
    "logo_intelligence_error",
    "project",
]

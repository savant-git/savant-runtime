from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence


schema = "savant://runtime/underscore/creative-alignment/1.0.0"
owner = "exile:underscore"


class creative_alignment_error(ValueError):
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
        raise creative_alignment_error(
            "creative alignment input must be canonical-json serializable"
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
        raise creative_alignment_error(
            "expected a sequence"
        )

    result: list[str] = []
    seen: set[str] = set()

    for item in value:
        text = str(item).strip()

        if text and text not in seen:
            seen.add(text)
            result.append(text)

    return tuple(result)


def project(
    *,
    objective: str,
    constraints: Sequence[str] = (),
    known_patterns: Sequence[str] = (),
    protected_invariants: Sequence[str] = (),
    context: Mapping[str, Any] | None = None,
    dimensions: Sequence[str] = (),
) -> dict[str, Any]:
    objective = str(objective).strip()

    if not objective:
        raise creative_alignment_error(
            "objective is required"
        )

    normalized_constraints = _strings(
        constraints
    )

    normalized_patterns = _strings(
        known_patterns
    )

    normalized_invariants = _strings(
        protected_invariants
    )

    normalized_dimensions = _strings(
        dimensions
    )

    normalized_context = dict(
        context or {}
    )

    axes = (
        "assumption_inversion",
        "constraint_recombination",
        "semantic_distance",
        "structural_transposition",
        "negative_space",
        "functional_metaphor",
        "cross_domain_transfer",
        "temporal_reframing",
        "scale_shift",
        "representation_shift",
        "interaction_reversal",
        "hierarchy_reversal",
        "material_behavior",
        "failure_as_signal",
        "asymmetry",
        "compression",
        "emergence",
        "latent_relationship",
        "counterfactual",
        "orthogonal_combination",
        "boundary_interrogation",
        "affordance_mutation",
        "context_collision",
        "primitive_recomposition",
    )

    anti_trope_rules = (
        "do not substitute visual novelty for conceptual novelty",
        "do not use a familiar trope merely because it is legible",
        "do not treat category conventions as requirements unless explicitly constrained",
        "do not use generic futurism, generic minimalism, generic luxury, generic disruption, or generic ai symbolism as a shortcut",
        "do not use literal subject depiction when a stronger structural idea exists",
        "do not converge early on the first coherent concept",
        "do not reward complexity merely for being unusual",
        "do not confuse obscurity with originality",
        "do not erase usability to increase novelty",
        "do not imitate a named creator, studio, brand, or existing artifact",
        "do not create novelty by random mutation alone",
        "do not preserve an assumption that has not earned preservation",
    )

    search_protocol = (
        {
            "stage": "decompose",
            "instruction": (
                "separate objective, invariants, constraints, assumptions, "
                "category habits, desired effects, and implementation details"
            ),
        },
        {
            "stage": "subtract",
            "instruction": (
                "remove conventional answers, default metaphors, obvious symbols, "
                "stylistic filler, and solutions that merely resemble category leaders"
            ),
        },
        {
            "stage": "diverge",
            "instruction": (
                "generate candidates from meaningfully different structural principles "
                "rather than cosmetic variations of one idea"
            ),
        },
        {
            "stage": "cross",
            "instruction": (
                "transfer useful structures from distant domains while preserving "
                "the actual objective and constraints"
            ),
        },
        {
            "stage": "invert",
            "instruction": (
                "challenge assumptions, hierarchy, interaction direction, representation, "
                "scale, sequence, and conventional ownership of visible elements"
            ),
        },
        {
            "stage": "compress",
            "instruction": (
                "seek a smaller primitive that produces multiple desired properties "
                "through emergence rather than independent decoration"
            ),
        },
        {
            "stage": "differentiate",
            "instruction": (
                "compare candidates by underlying mechanism and discard those whose "
                "difference is primarily surface treatment"
            ),
        },
        {
            "stage": "stress",
            "instruction": (
                "test each surviving idea against invariants, usability, edge conditions, "
                "reproduction, semantic drift, and likely cliché regression"
            ),
        },
        {
            "stage": "synthesize",
            "instruction": (
                "combine compatible strengths only when the combination produces a "
                "coherent new mechanism rather than a collage"
            ),
        },
        {
            "stage": "distill",
            "instruction": (
                "remove everything that does not materially strengthen identity, "
                "function, comprehension, memorability, or extensibility"
            ),
        },
    )

    projection = {
        "schema": schema,
        "owner": owner,
        "authority_effect": "none",
        "projection_only": True,
        "objective": objective,
        "constraints": list(
            normalized_constraints
        ),
        "protected_invariants": list(
            normalized_invariants
        ),
        "known_patterns": list(
            normalized_patterns
        ),
        "dimensions": list(
            normalized_dimensions
        ),
        "context": normalized_context,
        "creative_search_space": {
            "axes": list(axes),
            "anti_trope_rules": list(
                anti_trope_rules
            ),
            "protocol": list(
                search_protocol
            ),
        },
        "selection_requirements": {
            "prefer_mechanism_over_surface": True,
            "prefer_emergent_multi_property_primitives": True,
            "require_constraint_integrity": True,
            "require_invariant_integrity": True,
            "preserve_usefulness": True,
            "preserve_legibility_where_required": True,
            "penalize_category_default_similarity": True,
            "penalize_internal_candidate_similarity": True,
            "penalize_unearned_complexity": True,
            "reward_structural_distinction": True,
            "reward_semantic_density": True,
            "reward_reusability": True,
            "reward_extensibility": True,
            "reward_surprising_coherence": True,
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
            "owns_iteration": False,
            "owns_provider_routing": False,
        },
    }

    projection["digest"] = _digest(
        projection
    )

    return projection


__all__ = [
    "creative_alignment_error",
    "project",
]

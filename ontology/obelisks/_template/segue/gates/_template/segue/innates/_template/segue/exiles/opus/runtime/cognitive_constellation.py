#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence


schema = "savant://opus/cognitive-constellation/1.0.0"
owner = "opus"


class constellation_error(RuntimeError):
    pass


class facet_kind(str, Enum):
    authority = "authority"
    factual = "factual"
    analytical = "analytical"
    relational = "relational"
    semantic = "semantic"
    adversarial = "adversarial"
    creative = "creative"
    constraint = "constraint"
    uncertainty = "uncertainty"
    synthesis = "synthesis"
    verification = "verification"
    counterfactual = "counterfactual"
    causal = "causal"
    temporal = "temporal"
    compositional = "compositional"


class cognitive_role(str, Enum):
    solver = "solver"
    specialist = "specialist"
    critic = "critic"
    counterpoint = "counterpoint"
    falsifier = "falsifier"
    synthesizer = "synthesizer"
    verifier = "verifier"
    uncertainty_examiner = "uncertainty_examiner"


@dataclass(frozen=True)
class trait_evidence:
    trait_id: str
    provider_id: str
    model_id: str | None
    score: float
    confidence: float
    sample_count: int = 0
    evaluation_refs: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()
    failure_rate: float = 0.0
    latency_score: float = 0.5
    cost_score: float = 0.5

    def normalized(self) -> "trait_evidence":
        return trait_evidence(
            trait_id=str(self.trait_id).strip().lower(),
            provider_id=str(self.provider_id).strip().lower(),
            model_id=(
                str(self.model_id).strip()
                if self.model_id is not None
                else None
            ),
            score=_bounded(self.score),
            confidence=_bounded(self.confidence),
            sample_count=max(0, int(self.sample_count)),
            evaluation_refs=_normalized_tuple(self.evaluation_refs),
            provenance=_normalized_tuple(self.provenance),
            domains=_normalized_tuple(self.domains),
            failure_rate=_bounded(self.failure_rate),
            latency_score=_bounded(self.latency_score),
            cost_score=_bounded(self.cost_score),
        )


@dataclass(frozen=True)
class provider_profile:
    provider_id: str
    model_id: str | None
    capabilities: tuple[str, ...]
    traits: tuple[trait_evidence, ...]
    available: bool = True
    health: float = 1.0

    def normalized(self) -> "provider_profile":
        provider_id = str(self.provider_id).strip().lower()

        normalized_traits = tuple(
            sorted(
                (
                    item.normalized()
                    for item in self.traits
                    if item.provider_id.strip().lower() == provider_id
                ),
                key=lambda item: (
                    item.trait_id,
                    item.provider_id,
                    item.model_id or "",
                ),
            )
        )

        return provider_profile(
            provider_id=provider_id,
            model_id=(
                str(self.model_id).strip()
                if self.model_id is not None
                else None
            ),
            capabilities=_normalized_tuple(self.capabilities),
            traits=normalized_traits,
            available=bool(self.available),
            health=_bounded(self.health),
        )


@dataclass(frozen=True)
class cognitive_facet:
    facet_id: str
    kind: facet_kind
    objective: str
    required_traits: tuple[str, ...]
    required_capabilities: tuple[str, ...] = ("text_inference",)
    weight: float = 1.0
    authority_sensitive: bool = False
    uncertainty_sensitive: bool = False
    contradiction_sensitive: bool = False
    independent_evidence_desired: bool = False

    def normalized(self) -> "cognitive_facet":
        return cognitive_facet(
            facet_id=str(self.facet_id).strip().lower(),
            kind=facet_kind(self.kind),
            objective=str(self.objective).strip(),
            required_traits=_normalized_tuple(self.required_traits),
            required_capabilities=_normalized_tuple(
                self.required_capabilities
            ),
            weight=max(0.0, float(self.weight)),
            authority_sensitive=bool(self.authority_sensitive),
            uncertainty_sensitive=bool(self.uncertainty_sensitive),
            contradiction_sensitive=bool(self.contradiction_sensitive),
            independent_evidence_desired=bool(
                self.independent_evidence_desired
            ),
        )


@dataclass(frozen=True)
class cognitive_assignment:
    assignment_id: str
    facet_id: str
    provider_id: str
    model_id: str | None
    role: cognitive_role
    utility: float
    trait_fit: float
    evidence_confidence: float
    diversity_value: float
    health: float
    rationale: tuple[str, ...]


@dataclass(frozen=True)
class cognitive_lane:
    lane_id: str
    purpose: str
    assignments: tuple[cognitive_assignment, ...]
    independent: bool
    can_influence_final: bool = True


@dataclass(frozen=True)
class constellation_policy:
    max_providers: int = 3
    max_assignments: int = 8
    max_assignments_per_facet: int = 3
    minimum_trait_fit: float = 0.30
    minimum_provider_health: float = 0.25
    minimum_evidence_confidence: float = 0.20
    diversity_weight: float = 0.18
    health_weight: float = 0.12
    trait_weight: float = 0.58
    evidence_weight: float = 0.12
    latency_weight: float = 0.0
    cost_weight: float = 0.0
    authority_requires_counterpoint: bool = True
    contradiction_requires_falsifier: bool = True
    uncertainty_requires_examiner: bool = True
    independent_evidence_requires_distinct_provider: bool = True

    def normalized(self) -> "constellation_policy":
        return constellation_policy(
            max_providers=max(1, int(self.max_providers)),
            max_assignments=max(1, int(self.max_assignments)),
            max_assignments_per_facet=max(
                1,
                int(self.max_assignments_per_facet),
            ),
            minimum_trait_fit=_bounded(self.minimum_trait_fit),
            minimum_provider_health=_bounded(
                self.minimum_provider_health
            ),
            minimum_evidence_confidence=_bounded(
                self.minimum_evidence_confidence
            ),
            diversity_weight=max(0.0, float(self.diversity_weight)),
            health_weight=max(0.0, float(self.health_weight)),
            trait_weight=max(0.0, float(self.trait_weight)),
            evidence_weight=max(0.0, float(self.evidence_weight)),
            latency_weight=max(0.0, float(self.latency_weight)),
            cost_weight=max(0.0, float(self.cost_weight)),
            authority_requires_counterpoint=bool(
                self.authority_requires_counterpoint
            ),
            contradiction_requires_falsifier=bool(
                self.contradiction_requires_falsifier
            ),
            uncertainty_requires_examiner=bool(
                self.uncertainty_requires_examiner
            ),
            independent_evidence_requires_distinct_provider=bool(
                self.independent_evidence_requires_distinct_provider
            ),
        )


@dataclass(frozen=True)
class constellation:
    schema: str
    owner: str
    request_digest: str
    policy_digest: str
    provider_snapshot_digest: str
    facets: tuple[cognitive_facet, ...]
    lanes: tuple[cognitive_lane, ...]
    provider_ids: tuple[str, ...]
    assignment_count: int
    composition_digest: str
    enhancements: tuple[str, ...]
    unresolved: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


enhancements = (
    "atomic_cognitive_facets",
    "empirical_trait_routing",
    "provider_neutral_traits",
    "facet_specific_provider_selection",
    "complementary_provider_portfolios",
    "deliberate_cognitive_heterogeneity",
    "independent_counterpoint_lanes",
    "falsification_lanes",
    "uncertainty_examination_lanes",
    "authority_sensitive_counterpoint",
    "contradiction_sensitive_falsification",
    "evidence_confidence_weighting",
    "provider_health_weighting",
    "bounded_provider_participation",
    "bounded_assignment_count",
    "capability_safe_routing",
    "provider_failure_isolation",
    "trait_evidence_provenance",
    "deterministic_provider_ranking",
    "deterministic_constellation_digest",
    "replayable_orchestration_decisions",
    "anti_monoculture_diversity_bonus",
    "minimum_sufficient_provider_set",
    "role_separated_reasoning",
    "provider_independent_persona_boundary",
    "latency_optional_optimization",
    "cost_optional_optimization",
    "explicit_unresolved_state",
    "semantic_trait_composition",
    "envoy_compatible_trait_projection",
    "lineage_ready_assignments",
    "no_private_chain_of_thought_persistence",
)


def _bounded(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0

    if not math.isfinite(number):
        return 0.0

    return max(0.0, min(1.0, number))


def _normalized_tuple(values: Iterable[Any]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(value).strip().lower()
                for value in values
                if str(value).strip()
            }
        )
    )


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value

    if isinstance(value, Mapping):
        return {
            str(key): _jsonable(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }

    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]

    if hasattr(value, "__dataclass_fields__"):
        return _jsonable(asdict(value))

    return value


def _capability_fit(
    facet: cognitive_facet,
    provider: provider_profile,
) -> bool:
    required = set(facet.required_capabilities)
    available = set(provider.capabilities)
    return required.issubset(available)


def _trait_map(
    provider: provider_profile,
) -> dict[str, trait_evidence]:
    result: dict[str, trait_evidence] = {}

    for evidence in provider.traits:
        current = result.get(evidence.trait_id)

        if current is None:
            result[evidence.trait_id] = evidence
            continue

        current_key = (
            current.score * current.confidence,
            current.sample_count,
            current.score,
        )

        challenger_key = (
            evidence.score * evidence.confidence,
            evidence.sample_count,
            evidence.score,
        )

        if challenger_key > current_key:
            result[evidence.trait_id] = evidence

    return result


def _trait_fit(
    facet: cognitive_facet,
    provider: provider_profile,
) -> tuple[float, float, tuple[str, ...]]:
    required = tuple(facet.required_traits)

    if not required:
        return 1.0, 1.0, ()

    evidence = _trait_map(provider)

    weighted_scores: list[float] = []
    confidence_scores: list[float] = []
    missing: list[str] = []

    for trait_id in required:
        item = evidence.get(trait_id)

        if item is None:
            weighted_scores.append(0.0)
            confidence_scores.append(0.0)
            missing.append(trait_id)
            continue

        reliability = 1.0 - item.failure_rate

        weighted_scores.append(
            item.score
            * item.confidence
            * reliability
        )

        confidence_scores.append(
            item.confidence
            * reliability
        )

    return (
        sum(weighted_scores) / len(required),
        sum(confidence_scores) / len(required),
        tuple(sorted(missing)),
    )


def _provider_utility(
    facet: cognitive_facet,
    provider: provider_profile,
    policy: constellation_policy,
    selected_provider_ids: set[str],
) -> tuple[float, dict[str, Any]]:
    trait_fit, evidence_confidence, missing = _trait_fit(
        facet,
        provider,
    )

    diversity = (
        1.0
        if provider.provider_id not in selected_provider_ids
        else 0.0
    )

    trait_evidence_map = _trait_map(provider)

    latency_values = [
        item.latency_score
        for trait_id, item in trait_evidence_map.items()
        if trait_id in facet.required_traits
    ]

    cost_values = [
        item.cost_score
        for trait_id, item in trait_evidence_map.items()
        if trait_id in facet.required_traits
    ]

    latency = (
        sum(latency_values) / len(latency_values)
        if latency_values
        else 0.5
    )

    cost = (
        sum(cost_values) / len(cost_values)
        if cost_values
        else 0.5
    )

    numerator = (
        trait_fit * policy.trait_weight
        + evidence_confidence * policy.evidence_weight
        + provider.health * policy.health_weight
        + diversity * policy.diversity_weight
        + latency * policy.latency_weight
        + cost * policy.cost_weight
    )

    denominator = (
        policy.trait_weight
        + policy.evidence_weight
        + policy.health_weight
        + policy.diversity_weight
        + policy.latency_weight
        + policy.cost_weight
    )

    utility = (
        numerator / denominator
        if denominator > 0.0
        else trait_fit
    )

    return (
        _bounded(utility),
        {
            "trait_fit": trait_fit,
            "evidence_confidence": evidence_confidence,
            "health": provider.health,
            "diversity": diversity,
            "latency": latency,
            "cost": cost,
            "missing_traits": missing,
        },
    )


def _eligible(
    facet: cognitive_facet,
    provider: provider_profile,
    policy: constellation_policy,
) -> bool:
    if not provider.available:
        return False

    if provider.health < policy.minimum_provider_health:
        return False

    if not _capability_fit(facet, provider):
        return False

    trait_fit, confidence, _ = _trait_fit(
        facet,
        provider,
    )

    if trait_fit < policy.minimum_trait_fit:
        return False

    if confidence < policy.minimum_evidence_confidence:
        return False

    return True


def _role_for_primary(
    facet: cognitive_facet,
) -> cognitive_role:
    if facet.kind == facet_kind.verification:
        return cognitive_role.verifier

    if facet.kind == facet_kind.uncertainty:
        return cognitive_role.uncertainty_examiner

    return cognitive_role.specialist


def _assignment(
    facet: cognitive_facet,
    provider: provider_profile,
    role: cognitive_role,
    utility: float,
    metrics: Mapping[str, Any],
    ordinal: int,
) -> cognitive_assignment:
    assignment_payload = {
        "facet_id": facet.facet_id,
        "provider_id": provider.provider_id,
        "model_id": provider.model_id,
        "role": role.value,
        "ordinal": ordinal,
    }

    assignment_id = (
        "assignment:"
        + _digest(assignment_payload)[:24]
    )

    rationale = [
        f"facet:{facet.facet_id}",
        f"role:{role.value}",
        f"trait_fit:{float(metrics['trait_fit']):.6f}",
        (
            "evidence_confidence:"
            f"{float(metrics['evidence_confidence']):.6f}"
        ),
        f"health:{float(metrics['health']):.6f}",
        f"diversity:{float(metrics['diversity']):.6f}",
    ]

    missing = tuple(metrics.get("missing_traits") or ())

    if missing:
        rationale.append(
            "missing_traits:" + ",".join(missing)
        )

    return cognitive_assignment(
        assignment_id=assignment_id,
        facet_id=facet.facet_id,
        provider_id=provider.provider_id,
        model_id=provider.model_id,
        role=role,
        utility=_bounded(utility),
        trait_fit=_bounded(metrics["trait_fit"]),
        evidence_confidence=_bounded(
            metrics["evidence_confidence"]
        ),
        diversity_value=_bounded(metrics["diversity"]),
        health=_bounded(metrics["health"]),
        rationale=tuple(rationale),
    )


def _ranked_providers(
    facet: cognitive_facet,
    providers: Sequence[provider_profile],
    policy: constellation_policy,
    selected_provider_ids: set[str],
) -> list[
    tuple[
        provider_profile,
        float,
        Mapping[str, Any],
    ]
]:
    ranked: list[
        tuple[
            provider_profile,
            float,
            Mapping[str, Any],
        ]
    ] = []

    for provider in providers:
        if not _eligible(facet, provider, policy):
            continue

        utility, metrics = _provider_utility(
            facet,
            provider,
            policy,
            selected_provider_ids,
        )

        ranked.append(
            (
                provider,
                utility,
                metrics,
            )
        )

    ranked.sort(
        key=lambda item: (
            -item[1],
            -float(item[2]["trait_fit"]),
            -float(item[2]["evidence_confidence"]),
            -item[0].health,
            item[0].provider_id,
            item[0].model_id or "",
        )
    )

    return ranked


def _distinct_provider(
    ranked: Sequence[
        tuple[
            provider_profile,
            float,
            Mapping[str, Any],
        ]
    ],
    excluded: set[str],
) -> tuple[
    provider_profile,
    float,
    Mapping[str, Any],
] | None:
    for item in ranked:
        if item[0].provider_id not in excluded:
            return item

    return None


def _lane(
    purpose: str,
    assignments: Sequence[cognitive_assignment],
    independent: bool,
) -> cognitive_lane:
    payload = {
        "purpose": purpose,
        "assignments": [
            assignment.assignment_id
            for assignment in assignments
        ],
        "independent": independent,
    }

    return cognitive_lane(
        lane_id="lane:" + _digest(payload)[:24],
        purpose=purpose,
        assignments=tuple(assignments),
        independent=independent,
    )


def compile_constellation(
    request: Mapping[str, Any],
    facets: Sequence[cognitive_facet],
    providers: Sequence[provider_profile],
    policy: constellation_policy | None = None,
) -> constellation:
    policy = (
        policy or constellation_policy()
    ).normalized()

    normalized_facets = tuple(
        sorted(
            (
                facet.normalized()
                for facet in facets
            ),
            key=lambda item: item.facet_id,
        )
    )

    normalized_providers = tuple(
        sorted(
            (
                provider.normalized()
                for provider in providers
            ),
            key=lambda item: (
                item.provider_id,
                item.model_id or "",
            ),
        )
    )

    if not normalized_facets:
        raise constellation_error(
            "at least one cognitive facet is required"
        )

    if not normalized_providers:
        raise constellation_error(
            "at least one provider profile is required"
        )

    provider_snapshot = [
        {
            "provider_id": provider.provider_id,
            "model_id": provider.model_id,
            "capabilities": provider.capabilities,
            "available": provider.available,
            "health": provider.health,
            "traits": [
                asdict(item)
                for item in provider.traits
            ],
        }
        for provider in normalized_providers
    ]

    selected_provider_ids: set[str] = set()
    assignments: list[cognitive_assignment] = []
    lanes: list[cognitive_lane] = []
    unresolved: list[str] = []

    for facet in normalized_facets:
        if len(assignments) >= policy.max_assignments:
            unresolved.append(
                f"{facet.facet_id}:assignment_budget_exhausted"
            )
            continue

        ranked = _ranked_providers(
            facet,
            normalized_providers,
            policy,
            selected_provider_ids,
        )

        if not ranked:
            unresolved.append(
                f"{facet.facet_id}:no_eligible_provider"
            )
            continue

        primary_provider, primary_utility, primary_metrics = (
            ranked[0]
        )

        if (
            primary_provider.provider_id
            not in selected_provider_ids
            and len(selected_provider_ids)
            >= policy.max_providers
        ):
            within_portfolio = [
                item
                for item in ranked
                if item[0].provider_id
                in selected_provider_ids
            ]

            if not within_portfolio:
                unresolved.append(
                    f"{facet.facet_id}:provider_budget_exhausted"
                )
                continue

            (
                primary_provider,
                primary_utility,
                primary_metrics,
            ) = within_portfolio[0]

        primary = _assignment(
            facet,
            primary_provider,
            _role_for_primary(facet),
            primary_utility,
            primary_metrics,
            ordinal=len(assignments),
        )

        assignments.append(primary)
        selected_provider_ids.add(
            primary_provider.provider_id
        )

        facet_assignments = [primary]

        need_counterpoint = (
            facet.authority_sensitive
            and policy.authority_requires_counterpoint
        )

        need_falsifier = (
            facet.contradiction_sensitive
            and policy.contradiction_requires_falsifier
        )

        need_uncertainty = (
            facet.uncertainty_sensitive
            and policy.uncertainty_requires_examiner
        )

        supplemental_roles: list[cognitive_role] = []

        if need_counterpoint:
            supplemental_roles.append(
                cognitive_role.counterpoint
            )

        if need_falsifier:
            supplemental_roles.append(
                cognitive_role.falsifier
            )

        if need_uncertainty:
            supplemental_roles.append(
                cognitive_role.uncertainty_examiner
            )

        if (
            facet.independent_evidence_desired
            and not supplemental_roles
        ):
            supplemental_roles.append(
                cognitive_role.critic
            )

        used_for_facet = {
            primary_provider.provider_id
        }

        for role in supplemental_roles:
            if (
                len(assignments)
                >= policy.max_assignments
            ):
                unresolved.append(
                    f"{facet.facet_id}:supplemental_budget_exhausted"
                )
                break

            if (
                len(facet_assignments)
                >= policy.max_assignments_per_facet
            ):
                break

            candidate = _distinct_provider(
                ranked,
                used_for_facet,
            )

            if candidate is None:
                if (
                    policy
                    .independent_evidence_requires_distinct_provider
                ):
                    unresolved.append(
                        f"{facet.facet_id}:"
                        f"{role.value}_distinct_provider_unavailable"
                    )
                    continue

                candidate = ranked[0]

            provider, utility, metrics = candidate

            if (
                provider.provider_id
                not in selected_provider_ids
                and len(selected_provider_ids)
                >= policy.max_providers
            ):
                alternative = _distinct_provider(
                    [
                        item
                        for item in ranked
                        if item[0].provider_id
                        in selected_provider_ids
                    ],
                    used_for_facet,
                )

                if alternative is None:
                    unresolved.append(
                        f"{facet.facet_id}:"
                        f"{role.value}_provider_budget_exhausted"
                    )
                    continue

                provider, utility, metrics = alternative

            supplemental = _assignment(
                facet,
                provider,
                role,
                utility,
                metrics,
                ordinal=len(assignments),
            )

            assignments.append(supplemental)
            facet_assignments.append(supplemental)
            selected_provider_ids.add(
                provider.provider_id
            )
            used_for_facet.add(
                provider.provider_id
            )

        lanes.append(
            _lane(
                purpose=f"solve:{facet.facet_id}",
                assignments=facet_assignments,
                independent=False,
            )
        )

        independent_assignments = [
            item
            for item in facet_assignments
            if item.role
            in {
                cognitive_role.counterpoint,
                cognitive_role.falsifier,
                cognitive_role.uncertainty_examiner,
                cognitive_role.critic,
            }
        ]

        if independent_assignments:
            lanes.append(
                _lane(
                    purpose=f"challenge:{facet.facet_id}",
                    assignments=independent_assignments,
                    independent=True,
                )
            )

    if not assignments:
        raise constellation_error(
            "no cognitive assignments could be compiled"
        )

    synthesis_facet = cognitive_facet(
        facet_id="constellation_synthesis",
        kind=facet_kind.synthesis,
        objective=(
            "synthesize admitted cognitive evidence while "
            "preserving disagreements and unresolved claims"
        ),
        required_traits=(
            "synthesis",
            "constraint_control",
            "uncertainty_calibration",
        ),
        required_capabilities=("text_inference",),
        weight=1.0,
        authority_sensitive=any(
            facet.authority_sensitive
            for facet in normalized_facets
        ),
        uncertainty_sensitive=True,
        contradiction_sensitive=True,
    )

    synthesis_ranked = _ranked_providers(
        synthesis_facet,
        normalized_providers,
        policy,
        selected_provider_ids,
    )

    if (
        synthesis_ranked
        and len(assignments) < policy.max_assignments
    ):
        allowed_synthesis = [
            item
            for item in synthesis_ranked
            if (
                item[0].provider_id in selected_provider_ids
                or len(selected_provider_ids)
                < policy.max_providers
            )
        ]

        if allowed_synthesis:
            provider, utility, metrics = (
                allowed_synthesis[0]
            )

            synthesis_assignment = _assignment(
                synthesis_facet,
                provider,
                cognitive_role.synthesizer,
                utility,
                metrics,
                ordinal=len(assignments),
            )

            assignments.append(
                synthesis_assignment
            )
            selected_provider_ids.add(
                provider.provider_id
            )

            lanes.append(
                _lane(
                    purpose="synthesis",
                    assignments=(
                        synthesis_assignment,
                    ),
                    independent=False,
                )
            )

    request_digest = _digest(request)
    policy_digest = _digest(asdict(policy))
    provider_snapshot_digest = _digest(
        provider_snapshot
    )

    composition_payload = {
        "schema": schema,
        "request_digest": request_digest,
        "policy_digest": policy_digest,
        "provider_snapshot_digest": (
            provider_snapshot_digest
        ),
        "facets": [
            asdict(facet)
            for facet in normalized_facets
        ],
        "lanes": [
            asdict(lane)
            for lane in lanes
        ],
        "provider_ids": sorted(
            selected_provider_ids
        ),
        "unresolved": sorted(set(unresolved)),
    }

    return constellation(
        schema=schema,
        owner=owner,
        request_digest=request_digest,
        policy_digest=policy_digest,
        provider_snapshot_digest=(
            provider_snapshot_digest
        ),
        facets=normalized_facets,
        lanes=tuple(lanes),
        provider_ids=tuple(
            sorted(selected_provider_ids)
        ),
        assignment_count=len(assignments),
        composition_digest=_digest(
            composition_payload
        ),
        enhancements=enhancements,
        unresolved=tuple(
            sorted(set(unresolved))
        ),
    )


def trait_projection(
    providers: Sequence[provider_profile],
) -> dict[str, Any]:
    projected: dict[str, list[dict[str, Any]]] = {}

    for provider in sorted(
        (
            item.normalized()
            for item in providers
        ),
        key=lambda item: (
            item.provider_id,
            item.model_id or "",
        ),
    ):
        for evidence in provider.traits:
            projected.setdefault(
                evidence.trait_id,
                [],
            ).append(
                {
                    "provider_id": provider.provider_id,
                    "model_id": provider.model_id,
                    "score": evidence.score,
                    "confidence": evidence.confidence,
                    "sample_count": evidence.sample_count,
                    "failure_rate": evidence.failure_rate,
                    "evaluation_refs": list(
                        evidence.evaluation_refs
                    ),
                    "provenance": list(
                        evidence.provenance
                    ),
                    "domains": list(
                        evidence.domains
                    ),
                }
            )

    for trait_id in projected:
        projected[trait_id].sort(
            key=lambda item: (
                -(
                    float(item["score"])
                    * float(item["confidence"])
                    * (
                        1.0
                        - float(item["failure_rate"])
                    )
                ),
                -int(item["sample_count"]),
                str(item["provider_id"]),
                str(item["model_id"] or ""),
            )
        )

    payload = {
        "schema": (
            "savant://opus/"
            "provider-trait-projection/1.0.0"
        ),
        "owner": owner,
        "projection_only": True,
        "traits": projected,
    }

    payload["projection_digest"] = _digest(
        payload
    )

    return payload


def selftest() -> dict[str, Any]:
    providers = (
        provider_profile(
            provider_id="catalog_text",
            model_id="gemini-flash-latest",
            capabilities=(
                "text_inference",
                "context",
                "system_instructions",
            ),
            traits=(
                trait_evidence(
                    trait_id="semantic_analysis",
                    provider_id="catalog_text",
                    model_id="gemini-flash-latest",
                    score=0.86,
                    confidence=0.82,
                    sample_count=20,
                ),
                trait_evidence(
                    trait_id="counterfactual_reasoning",
                    provider_id="catalog_text",
                    model_id="gemini-flash-latest",
                    score=0.84,
                    confidence=0.80,
                    sample_count=20,
                ),
                trait_evidence(
                    trait_id="synthesis",
                    provider_id="catalog_text",
                    model_id="gemini-flash-latest",
                    score=0.80,
                    confidence=0.80,
                    sample_count=20,
                ),
                trait_evidence(
                    trait_id="constraint_control",
                    provider_id="catalog_text",
                    model_id="gemini-flash-latest",
                    score=0.82,
                    confidence=0.80,
                    sample_count=20,
                ),
                trait_evidence(
                    trait_id="uncertainty_calibration",
                    provider_id="catalog_text",
                    model_id="gemini-flash-latest",
                    score=0.79,
                    confidence=0.78,
                    sample_count=20,
                ),
            ),
        ),
        provider_profile(
            provider_id="openai_text",
            model_id="gpt-5",
            capabilities=(
                "text_inference",
                "context",
                "system_instructions",
                "structured_response",
            ),
            traits=(
                trait_evidence(
                    trait_id="constraint_control",
                    provider_id="openai_text",
                    model_id="gpt-5",
                    score=0.93,
                    confidence=0.90,
                    sample_count=20,
                ),
                trait_evidence(
                    trait_id="causal_reasoning",
                    provider_id="openai_text",
                    model_id="gpt-5",
                    score=0.90,
                    confidence=0.88,
                    sample_count=20,
                ),
                trait_evidence(
                    trait_id="synthesis",
                    provider_id="openai_text",
                    model_id="gpt-5",
                    score=0.91,
                    confidence=0.88,
                    sample_count=20,
                ),
                trait_evidence(
                    trait_id="uncertainty_calibration",
                    provider_id="openai_text",
                    model_id="gpt-5",
                    score=0.86,
                    confidence=0.84,
                    sample_count=20,
                ),
            ),
        ),
        provider_profile(
            provider_id="anthropic_text",
            model_id="claude-sonnet-5",
            capabilities=(
                "text_inference",
                "context",
                "system_instructions",
            ),
            traits=(
                trait_evidence(
                    trait_id="authority_reasoning",
                    provider_id="anthropic_text",
                    model_id="claude-sonnet-5",
                    score=0.95,
                    confidence=0.92,
                    sample_count=20,
                ),
                trait_evidence(
                    trait_id="relationship_reasoning",
                    provider_id="anthropic_text",
                    model_id="claude-sonnet-5",
                    score=0.94,
                    confidence=0.91,
                    sample_count=20,
                ),
                trait_evidence(
                    trait_id="uncertainty_calibration",
                    provider_id="anthropic_text",
                    model_id="claude-sonnet-5",
                    score=0.92,
                    confidence=0.90,
                    sample_count=20,
                ),
                trait_evidence(
                    trait_id="synthesis",
                    provider_id="anthropic_text",
                    model_id="claude-sonnet-5",
                    score=0.90,
                    confidence=0.89,
                    sample_count=20,
                ),
                trait_evidence(
                    trait_id="constraint_control",
                    provider_id="anthropic_text",
                    model_id="claude-sonnet-5",
                    score=0.89,
                    confidence=0.87,
                    sample_count=20,
                ),
            ),
        ),
    )

    facets = (
        cognitive_facet(
            facet_id="authority",
            kind=facet_kind.authority,
            objective=(
                "resolve authority without inventing reconciliation"
            ),
            required_traits=(
                "authority_reasoning",
                "uncertainty_calibration",
            ),
            authority_sensitive=True,
            uncertainty_sensitive=True,
            contradiction_sensitive=True,
            independent_evidence_desired=True,
        ),
        cognitive_facet(
            facet_id="causal",
            kind=facet_kind.causal,
            objective=(
                "derive causal consequences from admitted evidence"
            ),
            required_traits=(
                "causal_reasoning",
                "constraint_control",
            ),
            contradiction_sensitive=True,
        ),
    )

    first = compile_constellation(
        request={
            "text": "selftest",
            "required_capabilities": [
                "text_inference"
            ],
        },
        facets=facets,
        providers=providers,
    )

    second = compile_constellation(
        request={
            "text": "selftest",
            "required_capabilities": [
                "text_inference"
            ],
        },
        facets=facets,
        providers=providers,
    )

    if (
        first.composition_digest
        != second.composition_digest
    ):
        raise constellation_error(
            "identical inputs produced different constellations"
        )

    if len(first.provider_ids) > 3:
        raise constellation_error(
            "provider cap violated"
        )

    if first.assignment_count > 8:
        raise constellation_error(
            "assignment cap violated"
        )

    projection = trait_projection(
        providers
    )

    return {
        "ok": True,
        "schema": first.schema,
        "owner": first.owner,
        "provider_ids": list(
            first.provider_ids
        ),
        "assignment_count": (
            first.assignment_count
        ),
        "composition_digest": (
            first.composition_digest
        ),
        "deterministic": True,
        "bounded": True,
        "enhancement_count": len(
            first.enhancements
        ),
        "trait_projection_digest": (
            projection["projection_digest"]
        ),
        "unresolved": list(
            first.unresolved
        ),
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )

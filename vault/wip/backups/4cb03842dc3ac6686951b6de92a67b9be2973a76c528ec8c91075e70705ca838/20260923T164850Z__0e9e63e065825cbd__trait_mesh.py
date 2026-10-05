#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .router import (
    load_provider_module,
    policy,
    provider,
    route,
)
from .model_projection import (
    model_supports_layers,
    provider_model,
)


schema = "savant://runtime/opus/trait-mesh/1.1.0"
owner = "opus"
authority_effect = "none"

text_route_id = "text_inference_route"


class trait_mesh_error(RuntimeError):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(value).encode(
            "utf-8"
        )
    ).hexdigest()


def stable_id(
    prefix: str,
    value: Any,
) -> str:
    return (
        f"{prefix}:"
        f"{digest(value)[:24]}"
    )


def normalized_strings(
    values: Iterable[Any] | None,
) -> List[str]:
    if values is None:
        return []

    return sorted(
        {
            str(value).strip()
            for value in values
            if str(value).strip()
        }
    )


def bounded_float(
    value: Any,
    *,
    default: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        result = default

    return max(
        minimum,
        min(
            maximum,
            result,
        ),
    )


@dataclass(frozen=True)
class trait_requirement:
    trait_id: str
    purpose: str
    required_capabilities: tuple[str, ...]
    required_layers: tuple[str, ...]
    weight: float
    independence_required: bool
    adversarial: bool

    def projection(
        self,
    ) -> Dict[str, Any]:
        return {
            "trait_id": self.trait_id,
            "purpose": self.purpose,
            "required_capabilities": list(
                self.required_capabilities
            ),
            "required_layers": list(
                self.required_layers
            ),
            "weight": self.weight,
            "independence_required": (
                self.independence_required
            ),
            "adversarial": self.adversarial,
        }


@dataclass(frozen=True)
class provider_candidate:
    provider_id: str
    model_id: str | None
    route_rank: int
    capabilities: tuple[str, ...]
    required_layers_supported: bool
    evidence_score: float
    evidence: tuple[
        Mapping[str, Any],
        ...
    ]

    def projection(
        self,
    ) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "route_rank": self.route_rank,
            "capabilities": list(
                self.capabilities
            ),
            "required_layers_supported": (
                self.required_layers_supported
            ),
            "evidence_score": self.evidence_score,
            "evidence": [
                dict(item)
                for item in self.evidence
            ],
        }


@dataclass(frozen=True)
class trait_execution:
    execution_id: str
    trait_id: str
    provider_id: str
    model_id: str | None
    status: str
    response: Dict[str, Any] | None
    error: str | None

    def projection(
        self,
    ) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "trait_id": self.trait_id,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "status": self.status,
            "response": self.response,
            "error": self.error,
        }


def _route_provider_ids() -> List[str]:
    route_data = route(
        text_route_id
    )

    ordered = (
        route_data.get(
            "fallback_order"
        )
        or [
            route_data.get(
                "default_provider"
            )
        ]
    )

    result: List[str] = []

    for value in ordered:
        provider_id = str(
            value or ""
        ).strip()

        if (
            provider_id
            and provider_id not in result
        ):
            result.append(
                provider_id
            )

    return result


def _provider_capabilities(
    provider_data: Mapping[str, Any],
) -> set[str]:
    return set(
        normalized_strings(
            provider_data.get(
                "capabilities"
            )
            or ()
        )
    )


def _supports_capabilities(
    provider_data: Mapping[str, Any],
    required: Iterable[str],
) -> bool:
    required_set = set(
        normalized_strings(
            required
        )
    )

    if not required_set:
        return True

    return required_set.issubset(
        _provider_capabilities(
            provider_data
        )
    )


def _supports_layers(
    provider_data: Mapping[str, Any],
    required: Iterable[str],
) -> bool:
    required_set = set(
        normalized_strings(
            required
        )
    )

    if not required_set:
        return True

    model_id = provider_model(
        dict(provider_data)
    )

    if not model_id:
        return False

    return model_supports_layers(
        model_id,
        required_set,
    )


def _evidence_for_candidate(
    *,
    provider_id: str,
    model_id: str | None,
    trait_id: str,
    evidence: Sequence[
        Mapping[str, Any]
    ],
) -> tuple[
    float,
    tuple[Mapping[str, Any], ...],
]:
    matches: List[
        Mapping[str, Any]
    ] = []

    weighted = 0.0
    total_weight = 0.0

    for item in evidence:
        item_provider = str(
            item.get(
                "provider",
                "",
            )
        ).strip()

        item_model = str(
            item.get(
                "model",
                "",
            )
        ).strip()

        item_trait = str(
            item.get(
                "trait_id",
                "",
            )
        ).strip()

        if (
            item_provider
            and item_provider != provider_id
        ):
            continue

        if (
            item_model
            and model_id
            and item_model != model_id
        ):
            continue

        if (
            item_trait
            and item_trait != trait_id
        ):
            continue

        reliability = bounded_float(
            item.get(
                "reliability"
            ),
            default=0.5,
        )

        confidence = bounded_float(
            item.get(
                "confidence"
            ),
            default=0.5,
        )

        score = bounded_float(
            item.get(
                "score"
            ),
            default=0.5,
        )

        weight = max(
            0.000001,
            reliability * confidence,
        )

        weighted += score * weight
        total_weight += weight

        matches.append(
            item
        )

    if total_weight <= 0.0:
        return (
            0.0,
            tuple(),
        )

    return (
        weighted / total_weight,
        tuple(matches),
    )


def candidate_providers(
    requirement: trait_requirement,
    *,
    provider_model_evidence: Sequence[
        Mapping[str, Any]
    ] = (),
    unavailable_providers: Iterable[
        str
    ] = (),
) -> List[provider_candidate]:
    unavailable = set(
        normalized_strings(
            unavailable_providers
        )
    )

    candidates: List[
        provider_candidate
    ] = []

    for rank, provider_id in enumerate(
        _route_provider_ids()
    ):
        if provider_id in unavailable:
            continue

        try:
            provider_data = provider(
                provider_id
            )
        except Exception:
            continue

        if not _supports_capabilities(
            provider_data,
            requirement.required_capabilities,
        ):
            continue

        layers_supported = (
            _supports_layers(
                provider_data,
                requirement.required_layers,
            )
        )

        if not layers_supported:
            continue

        try:
            module = load_provider_module(
                provider_id
            )
        except Exception:
            continue

        available = getattr(
            module,
            "available",
            None,
        )

        if callable(available):
            try:
                if not bool(
                    available()
                ):
                    continue
            except Exception:
                continue

        model_id = provider_model(
            provider_data
        )

        (
            evidence_score,
            evidence,
        ) = _evidence_for_candidate(
            provider_id=provider_id,
            model_id=model_id,
            trait_id=(
                requirement.trait_id
            ),
            evidence=(
                provider_model_evidence
            ),
        )

        candidates.append(
            provider_candidate(
                provider_id=provider_id,
                model_id=model_id,
                route_rank=rank,
                capabilities=tuple(
                    sorted(
                        _provider_capabilities(
                            provider_data
                        )
                    )
                ),
                required_layers_supported=(
                    layers_supported
                ),
                evidence_score=(
                    evidence_score
                ),
                evidence=evidence,
            )
        )

    return sorted(
        candidates,
        key=lambda item: (
            -item.evidence_score,
            item.route_rank,
            item.provider_id,
            item.model_id or "",
        ),
    )


def _provider_timeout() -> float:
    route_data = route(
        text_route_id
    )

    policy_id = str(
        route_data.get(
            "policy_ref"
        )
        or ""
    ).strip()

    if not policy_id:
        return 60.0

    try:
        policy_data = policy(
            policy_id
        )
    except Exception:
        return 60.0

    try:
        timeout = float(
            policy_data.get(
                "timeout_seconds",
                60,
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        timeout = 60.0

    return max(
        1.0,
        timeout,
    )


def _execute_provider(
    *,
    provider_id: str,
    request: Dict[str, Any],
) -> Dict[str, Any]:
    provider_data = provider(
        provider_id
    )

    module = load_provider_module(
        provider_id
    )

    infer = getattr(
        module,
        "infer",
        None,
    )

    if not callable(infer):
        raise trait_mesh_error(
            "provider has no infer callable: "
            f"{provider_id}"
        )

    selected = dict(
        provider_data
    )

    selected["selected"] = True
    selected["route_id"] = (
        text_route_id
    )
    selected["selected_model"] = (
        provider_model(
            selected
        )
    )
    selected["timeout_seconds"] = (
        _provider_timeout()
    )

    result = infer(
        request,
        selected,
    )

    if not isinstance(
        result,
        dict,
    ):
        raise trait_mesh_error(
            "provider result must be an object"
        )

    projected = dict(
        result
    )

    projected["lineage"] = {
        "owner": owner,
        "route": text_route_id,
        "provider": provider_id,
        "model": selected.get(
            "selected_model"
        ),
        "request_owner": request.get(
            "owner",
            owner,
        ),
        "trait_id": request.get(
            "trait_id"
        ),
        "authority_effect": (
            authority_effect
        ),
    }

    return projected


def trait_prompt(
    *,
    task: str,
    context: Mapping[str, Any],
    requirement: trait_requirement,
) -> str:
    return (
        "You are one bounded cognitive "
        "component inside an Opus "
        "trait-composed orchestration.\n\n"
        "Do not attempt to imitate an entire "
        "assistant persona. Perform only the "
        "assigned cognitive trait.\n\n"
        f"Trait: {requirement.trait_id}\n"
        f"Purpose: {requirement.purpose}\n"
        f"Weight: {requirement.weight}\n"
        "Adversarial: "
        f"{requirement.adversarial}\n\n"
        "Rules:\n"
        "- Supplied authority outranks model "
        "output.\n"
        "- Model output creates no authority.\n"
        "- Distinguish source-derived facts, "
        "verified facts, inference, "
        "hypothesis, speculation, and "
        "unknown.\n"
        "- Preserve material contradictions "
        "and uncertainty.\n"
        "- Do not manufacture missing facts.\n"
        "- Optimize for this trait rather "
        "than generic helpfulness.\n"
        "- Return the strongest contribution "
        "you can make for this trait.\n\n"
        f"Task:\n{task}\n\n"
        "Context:\n"
        f"{canonical_json(dict(context))}"
    )


def execute_trait(
    *,
    task: str,
    context: Mapping[str, Any],
    requirement: trait_requirement,
    candidate: provider_candidate,
) -> trait_execution:
    request = {
        "owner": owner,
        "operation": (
            "trait_composed_inference"
        ),
        "trait_id": (
            requirement.trait_id
        ),
        "prompt": trait_prompt(
            task=task,
            context=context,
            requirement=requirement,
        ),
        "required_capabilities": list(
            requirement.required_capabilities
        ),
        "required_layers": list(
            requirement.required_layers
        ),
        "authority_effect": (
            authority_effect
        ),
    }

    identity = {
        "request": request,
        "provider": (
            candidate.provider_id
        ),
        "model": candidate.model_id,
    }

    execution_id = stable_id(
        "opus-trait-execution",
        identity,
    )

    try:
        response = _execute_provider(
            provider_id=(
                candidate.provider_id
            ),
            request=request,
        )

        return trait_execution(
            execution_id=execution_id,
            trait_id=(
                requirement.trait_id
            ),
            provider_id=(
                candidate.provider_id
            ),
            model_id=candidate.model_id,
            status="complete",
            response=response,
            error=None,
        )

    except Exception as exc:
        return trait_execution(
            execution_id=execution_id,
            trait_id=(
                requirement.trait_id
            ),
            provider_id=(
                candidate.provider_id
            ),
            model_id=candidate.model_id,
            status="failed",
            response=None,
            error=(
                f"{type(exc).__name__}: "
                f"{str(exc or '').strip()}"
            ),
        )


def default_trait_requirements() -> List[
    trait_requirement
]:
    return [
        trait_requirement(
            trait_id="analysis",
            purpose=(
                "Construct a rigorous "
                "evidence-grounded analysis."
            ),
            required_capabilities=(),
            required_layers=(),
            weight=1.0,
            independence_required=True,
            adversarial=False,
        ),
        trait_requirement(
            trait_id="skepticism",
            purpose=(
                "Detect unsupported assumptions, "
                "hidden dependencies, false "
                "certainty, and weak reasoning."
            ),
            required_capabilities=(),
            required_layers=(),
            weight=0.9,
            independence_required=True,
            adversarial=True,
        ),
        trait_requirement(
            trait_id="divergence",
            purpose=(
                "Generate materially different "
                "approaches and explanations "
                "without collapsing them early."
            ),
            required_capabilities=(),
            required_layers=(),
            weight=0.85,
            independence_required=True,
            adversarial=False,
        ),
        trait_requirement(
            trait_id="falsification",
            purpose=(
                "Search for counterexamples and "
                "conditions capable of "
                "invalidating candidate claims."
            ),
            required_capabilities=(),
            required_layers=(),
            weight=0.95,
            independence_required=True,
            adversarial=True,
        ),
        trait_requirement(
            trait_id="integration",
            purpose=(
                "Integrate compatible evidence "
                "while preserving dissent, "
                "uncertainty, and provenance."
            ),
            required_capabilities=(),
            required_layers=(),
            weight=1.0,
            independence_required=False,
            adversarial=False,
        ),
    ]


def _response_content(
    response: Mapping[str, Any] | None,
) -> Any:
    if response is None:
        return None

    for key in (
        "text",
        "content",
        "output",
        "response",
        "result",
    ):
        if key in response:
            return response[key]

    return dict(
        response
    )


def select_candidates(
    requirements: Sequence[
        trait_requirement
    ],
    *,
    provider_model_evidence: Sequence[
        Mapping[str, Any]
    ] = (),
    unavailable_providers: Iterable[
        str
    ] = (),
) -> Dict[
    str,
    List[provider_candidate],
]:
    selected: Dict[
        str,
        List[provider_candidate],
    ] = {}

    prior_primary: set[str] = set()

    for requirement in requirements:
        candidates = candidate_providers(
            requirement,
            provider_model_evidence=(
                provider_model_evidence
            ),
            unavailable_providers=(
                unavailable_providers
            ),
        )

        if (
            requirement.independence_required
            and len(candidates) > 1
        ):
            candidates = sorted(
                candidates,
                key=lambda item: (
                    item.provider_id
                    in prior_primary,
                    -item.evidence_score,
                    item.route_rank,
                    item.provider_id,
                    item.model_id or "",
                ),
            )

        selected[
            requirement.trait_id
        ] = candidates

        if candidates:
            prior_primary.add(
                candidates[0].provider_id
            )

    return selected


def execute_mesh(
    *,
    task: str,
    context: Mapping[str, Any] | None = None,
    requirements: Sequence[
        trait_requirement
    ] | None = None,
    provider_model_evidence: Sequence[
        Mapping[str, Any]
    ] = (),
    unavailable_providers: Iterable[
        str
    ] = (),
    candidates_per_trait: int = 1,
    maximum_total_calls: int = 16,
) -> Dict[str, Any]:
    task = str(
        task or ""
    ).strip()

    if not task:
        raise trait_mesh_error(
            "task must not be empty"
        )

    context = dict(
        context or {}
    )

    requirements = list(
        requirements
        or default_trait_requirements()
    )

    if not requirements:
        raise trait_mesh_error(
            "at least one trait requirement "
            "is required"
        )

    successful_candidates_per_trait = max(
        1,
        min(
            int(candidates_per_trait),
            4,
        ),
    )

    maximum_total_calls = max(
        1,
        min(
            int(maximum_total_calls),
            24,
        ),
    )

    selected = select_candidates(
        requirements,
        provider_model_evidence=(
            provider_model_evidence
        ),
        unavailable_providers=(
            unavailable_providers
        ),
    )

    executions: List[
        trait_execution
    ] = []

    calls = 0

    for requirement in requirements:
        candidates = selected.get(
            requirement.trait_id,
            [],
        )

        successful = 0

        for candidate in candidates:
            if calls >= maximum_total_calls:
                break

            execution = execute_trait(
                task=task,
                context=context,
                requirement=requirement,
                candidate=candidate,
            )

            executions.append(
                execution
            )

            calls += 1

            if (
                execution.status
                == "complete"
            ):
                successful += 1

                if (
                    successful
                    >= successful_candidates_per_trait
                ):
                    break

        if calls >= maximum_total_calls:
            break

    by_trait: Dict[
        str,
        List[Dict[str, Any]],
    ] = {}

    provider_failures: List[
        Dict[str, Any]
    ] = []

    for execution in executions:
        by_trait.setdefault(
            execution.trait_id,
            [],
        ).append(
            execution.projection()
        )

        if execution.status != "complete":
            provider_failures.append(
                execution.projection()
            )

    completed_traits = sorted(
        {
            execution.trait_id
            for execution in executions
            if execution.status
            == "complete"
        }
    )

    requested_traits = [
        item.trait_id
        for item in requirements
    ]

    missing_traits = sorted(
        set(requested_traits)
        - set(completed_traits)
    )

    successful_executions = [
        item
        for item in executions
        if item.status == "complete"
    ]

    failed_executions = [
        item
        for item in executions
        if item.status != "complete"
    ]

    contributing_providers = sorted(
        {
            item.provider_id
            for item in successful_executions
        }
    )

    contributing_models = sorted(
        {
            item.model_id
            for item in successful_executions
            if item.model_id
        }
    )

    request_identity = {
        "task": task,
        "context": context,
        "requirements": [
            item.projection()
            for item in requirements
        ],
        "provider_model_evidence": [
            dict(item)
            for item
            in provider_model_evidence
        ],
        "unavailable_providers": (
            normalized_strings(
                unavailable_providers
            )
        ),
        "successful_candidates_per_trait": (
            successful_candidates_per_trait
        ),
        "maximum_total_calls": (
            maximum_total_calls
        ),
    }

    if not missing_traits:
        status = "complete"
    elif completed_traits:
        status = "degraded"
    else:
        status = "failed"

    result = {
        "schema": schema,
        "owner": owner,
        "operation": (
            "trait_composed_orchestration"
        ),
        "mesh_id": stable_id(
            "opus-trait-mesh",
            request_identity,
        ),
        "status": status,
        "task_digest": digest(
            task
        ),
        "context_digest": digest(
            context
        ),
        "requirements": [
            item.projection()
            for item in requirements
        ],
        "candidate_projection": {
            trait_id: [
                item.projection()
                for item in candidates
            ]
            for (
                trait_id,
                candidates
            ) in selected.items()
        },
        "executions": [
            item.projection()
            for item in executions
        ],
        "by_trait": by_trait,
        "completed_traits": (
            completed_traits
        ),
        "missing_traits": (
            missing_traits
        ),
        "successful_executions": len(
            successful_executions
        ),
        "failed_executions": len(
            failed_executions
        ),
        "contributing_providers": (
            contributing_providers
        ),
        "contributing_models": (
            contributing_models
        ),
        "provider_failures": (
            provider_failures
        ),
        "inference_calls": calls,
        "call_budget": (
            maximum_total_calls
        ),
        "call_budget_exhausted": (
            calls >= maximum_total_calls
        ),
        "boundaries": {
            "creates_authority": False,
            "changes_canon": False,
            "changes_provider_registry": (
                False
            ),
            "changes_persona_authority": (
                False
            ),
            "provider_outputs_are_derived": (
                True
            ),
            "evidence_scores_are_authority": (
                False
            ),
            "consensus_is_authority": False,
            "trait_composition_is_projection": (
                True
            ),
            "failed_provider_attempts_are_"
            "preserved": True,
            "successful_trait_satisfaction_"
            "required": True,
        },
        "replay": request_identity,
        "authority_effect": (
            authority_effect
        ),
    }

    result[
        "projection_digest"
    ] = digest(
        result
    )

    return result


def synthesis_context(
    mesh: Mapping[str, Any],
) -> Dict[str, Any]:
    by_trait = mesh.get(
        "by_trait"
    )

    if not isinstance(
        by_trait,
        Mapping,
    ):
        raise trait_mesh_error(
            "mesh has no by_trait projection"
        )

    projected: Dict[
        str,
        List[Dict[str, Any]],
    ] = {}

    for (
        trait_id,
        executions,
    ) in by_trait.items():
        values: List[
            Dict[str, Any]
        ] = []

        if not isinstance(
            executions,
            Sequence,
        ):
            continue

        for execution in executions:
            if not isinstance(
                execution,
                Mapping,
            ):
                continue

            if (
                execution.get(
                    "status"
                )
                != "complete"
            ):
                continue

            response = execution.get(
                "response"
            )

            values.append(
                {
                    "execution_id": (
                        execution.get(
                            "execution_id"
                        )
                    ),
                    "provider_id": (
                        execution.get(
                            "provider_id"
                        )
                    ),
                    "model_id": (
                        execution.get(
                            "model_id"
                        )
                    ),
                    "content": (
                        _response_content(
                            response
                            if isinstance(
                                response,
                                Mapping,
                            )
                            else None
                        )
                    ),
                    "lineage": (
                        response.get(
                            "lineage"
                        )
                        if isinstance(
                            response,
                            Mapping,
                        )
                        else None
                    ),
                }
            )

        projected[
            str(trait_id)
        ] = values

    return {
        "mesh_id": mesh.get(
            "mesh_id"
        ),
        "status": mesh.get(
            "status"
        ),
        "traits": projected,
        "missing_traits": list(
            mesh.get(
                "missing_traits"
            )
            or []
        ),
        "provider_failures": list(
            mesh.get(
                "provider_failures"
            )
            or []
        ),
        "contributing_providers": list(
            mesh.get(
                "contributing_providers"
            )
            or []
        ),
        "contributing_models": list(
            mesh.get(
                "contributing_models"
            )
            or []
        ),
        "projection_digest": (
            mesh.get(
                "projection_digest"
            )
        ),
    }


def health() -> Dict[str, Any]:
    route_data = route(
        text_route_id
    )

    return {
        "status": "ok",
        "schema": schema,
        "owner": owner,
        "route": text_route_id,
        "providers": (
            _route_provider_ids()
        ),
        "default_traits": [
            item.trait_id
            for item
            in default_trait_requirements()
        ],
        "maximum_successful_candidates_"
        "per_trait": 4,
        "maximum_total_calls": 24,
        "provider_failure_fallback": True,
        "dynamic_provider_profiles": bool(
            route_data.get(
                "dynamic_provider_profiles"
            )
        ),
        "future_provider_extensible": bool(
            route_data.get(
                "future_provider_extensible"
            )
        ),
        "trait_composition_is_projection": (
            True
        ),
        "authority_effect": (
            authority_effect
        ),
    }


if __name__ == "__main__":
    print(
        json.dumps(
            health(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

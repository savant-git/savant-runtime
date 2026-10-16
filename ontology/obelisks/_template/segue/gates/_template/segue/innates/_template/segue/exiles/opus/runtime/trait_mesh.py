#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .router import (
    execute_text_request,
    route,
)


schema = "savant://runtime/opus/trait-mesh/1.2.0"
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
class trait_execution:
    execution_id: str
    trait_id: str
    status: str
    response: Dict[str, Any] | None
    error: str | None

    def projection(
        self,
    ) -> Dict[str, Any]:
        lineage = None
        provider_id = None
        model_id = None

        if isinstance(
            self.response,
            Mapping,
        ):
            candidate_lineage = (
                self.response.get(
                    "lineage"
                )
            )

            if isinstance(
                candidate_lineage,
                Mapping,
            ):
                lineage = dict(
                    candidate_lineage
                )

                provider_id = (
                    candidate_lineage.get(
                        "provider"
                    )
                )

                model_id = (
                    candidate_lineage.get(
                        "model"
                    )
                )

        return {
            "execution_id": self.execution_id,
            "trait_id": self.trait_id,
            "provider_id": provider_id,
            "model_id": model_id,
            "status": self.status,
            "response": self.response,
            "lineage": lineage,
            "error": self.error,
        }


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


def _normalized_evidence(
    evidence: Sequence[
        Mapping[str, Any]
    ],
) -> List[Dict[str, Any]]:
    normalized: List[
        Dict[str, Any]
    ] = []

    for item in evidence:
        provider_id = str(
            item.get(
                "provider",
                "",
            )
        ).strip()

        model_id = str(
            item.get(
                "model",
                "",
            )
        ).strip()

        trait_id = str(
            item.get(
                "trait_id",
                "",
            )
        ).strip()

        if not (
            provider_id
            or model_id
            or trait_id
        ):
            continue

        normalized.append(
            {
                "provider": provider_id,
                "model": model_id,
                "trait_id": trait_id,
                "score": bounded_float(
                    item.get(
                        "score"
                    ),
                    default=0.5,
                ),
                "confidence": bounded_float(
                    item.get(
                        "confidence"
                    ),
                    default=0.5,
                ),
                "reliability": bounded_float(
                    item.get(
                        "reliability"
                    ),
                    default=0.5,
                ),
                "provenance": item.get(
                    "provenance"
                ),
            }
        )

    return sorted(
        normalized,
        key=lambda item: (
            item["trait_id"],
            item["provider"],
            item["model"],
            -item["score"],
            -item["confidence"],
            -item["reliability"],
        ),
    )


def evidence_for_trait(
    trait_id: str,
    evidence: Sequence[
        Mapping[str, Any]
    ],
) -> List[Dict[str, Any]]:
    result: List[
        Dict[str, Any]
    ] = []

    for item in _normalized_evidence(
        evidence
    ):
        evidence_trait = str(
            item.get(
                "trait_id",
                "",
            )
        ).strip()

        if (
            evidence_trait
            and evidence_trait
            != trait_id
        ):
            continue

        result.append(
            item
        )

    return result


def trait_prompt(
    *,
    task: str,
    context: Mapping[str, Any],
    requirement: trait_requirement,
    provider_model_evidence: Sequence[
        Mapping[str, Any]
    ] = (),
) -> str:
    evidence = evidence_for_trait(
        requirement.trait_id,
        provider_model_evidence,
    )

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
        "Independence required: "
        f"{requirement.independence_required}\n"
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
        "- Optimize for this cognitive trait "
        "rather than generic helpfulness.\n"
        "- Do not infer provider superiority "
        "from route order.\n"
        "- Provider/model evidence is derived "
        "evidence, not authority.\n"
        "- Return the strongest bounded "
        "contribution you can make for this "
        "trait.\n\n"
        f"Task:\n{task}\n\n"
        "Context:\n"
        f"{canonical_json(dict(context))}\n\n"
        "Relevant provider/model trait "
        "evidence:\n"
        f"{canonical_json(evidence)}"
    )


def execute_trait(
    *,
    task: str,
    context: Mapping[str, Any],
    requirement: trait_requirement,
    provider_model_evidence: Sequence[
        Mapping[str, Any]
    ] = (),
) -> trait_execution:
    request = {
        "owner": owner,
        "operation": (
            "trait_composed_inference"
        ),
        "trait_id": (
            requirement.trait_id
        ),
        "message": trait_prompt(
            task=task,
            context=context,
            requirement=requirement,
            provider_model_evidence=(
                provider_model_evidence
            ),
        ),
        "required_capabilities": list(
            requirement.required_capabilities
        ),
        "required_layers": list(
            requirement.required_layers
        ),
        "trait_requirement": (
            requirement.projection()
        ),
        "provider_model_evidence": (
            evidence_for_trait(
                requirement.trait_id,
                provider_model_evidence,
            )
        ),
        "authority_effect": (
            authority_effect
        ),
    }

    execution_id = stable_id(
        "opus-trait-execution",
        request,
    )

    try:
        response = execute_text_request(
            request
        )

        if not isinstance(
            response,
            dict,
        ):
            raise trait_mesh_error(
                "resilient text router "
                "returned a non-object result"
            )

        return trait_execution(
            execution_id=execution_id,
            trait_id=(
                requirement.trait_id
            ),
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
            status="failed",
            response=None,
            error=(
                f"{type(exc).__name__}: "
                f"{str(exc or '').strip()}"
            ),
        )


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


def _execution_lineage(
    execution: trait_execution,
) -> Dict[str, Any] | None:
    response = execution.response

    if not isinstance(
        response,
        Mapping,
    ):
        return None

    lineage = response.get(
        "lineage"
    )

    if not isinstance(
        lineage,
        Mapping,
    ):
        return None

    return dict(
        lineage
    )


def _execution_provider(
    execution: trait_execution,
) -> str | None:
    lineage = _execution_lineage(
        execution
    )

    if not lineage:
        return None

    value = str(
        lineage.get(
            "provider",
            "",
        )
    ).strip()

    return value or None


def _execution_model(
    execution: trait_execution,
) -> str | None:
    lineage = _execution_lineage(
        execution
    )

    if not lineage:
        return None

    value = str(
        lineage.get(
            "model",
            "",
        )
    ).strip()

    return value or None


def _execution_attempts(
    execution: trait_execution,
) -> List[Dict[str, Any]]:
    lineage = _execution_lineage(
        execution
    )

    if not lineage:
        return []

    attempts = lineage.get(
        "attempts"
    )

    if not isinstance(
        attempts,
        list,
    ):
        return []

    return [
        dict(item)
        for item in attempts
        if isinstance(
            item,
            Mapping,
        )
    ]


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

    maximum_total_calls = max(
        1,
        min(
            int(maximum_total_calls),
            24,
        ),
    )

    requested_candidates_per_trait = max(
        1,
        min(
            int(candidates_per_trait),
            4,
        ),
    )

    normalized_unavailable = (
        normalized_strings(
            unavailable_providers
        )
    )

    normalized_evidence = (
        _normalized_evidence(
            provider_model_evidence
        )
    )

    executions: List[
        trait_execution
    ] = []

    calls = 0

    for requirement in requirements:
        if calls >= maximum_total_calls:
            break

        execution = execute_trait(
            task=task,
            context=context,
            requirement=requirement,
            provider_model_evidence=(
                normalized_evidence
            ),
        )

        executions.append(
            execution
        )

        calls += 1

    by_trait: Dict[
        str,
        List[Dict[str, Any]],
    ] = {}

    provider_failures: List[
        Dict[str, Any]
    ] = []

    routing_attempts: List[
        Dict[str, Any]
    ] = []

    successful_executions: List[
        trait_execution
    ] = []

    failed_executions: List[
        trait_execution
    ] = []

    for execution in executions:
        projection = (
            execution.projection()
        )

        by_trait.setdefault(
            execution.trait_id,
            [],
        ).append(
            projection
        )

        attempts = _execution_attempts(
            execution
        )

        for attempt in attempts:
            routing_attempts.append(
                {
                    "trait_id": (
                        execution.trait_id
                    ),
                    "execution_id": (
                        execution.execution_id
                    ),
                    **attempt,
                }
            )

        if (
            execution.status
            == "complete"
        ):
            successful_executions.append(
                execution
            )
        else:
            failed_executions.append(
                execution
            )

            provider_failures.append(
                projection
            )

    completed_traits = sorted(
        {
            execution.trait_id
            for execution
            in successful_executions
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

    contributing_providers = sorted(
        {
            provider_id
            for provider_id in (
                _execution_provider(
                    execution
                )
                for execution
                in successful_executions
            )
            if provider_id
        }
    )

    contributing_models = sorted(
        {
            model_id
            for model_id in (
                _execution_model(
                    execution
                )
                for execution
                in successful_executions
            )
            if model_id
        }
    )

    failed_routing_attempts = [
        item
        for item in routing_attempts
        if item.get(
            "state"
        )
        == "failed"
    ]

    skipped_routing_attempts = [
        item
        for item in routing_attempts
        if item.get(
            "state"
        )
        == "skipped"
    ]

    successful_routing_attempts = [
        item
        for item in routing_attempts
        if item.get(
            "state"
        )
        == "succeeded"
    ]

    fallback_traits = sorted(
        {
            execution.trait_id
            for execution
            in successful_executions
            if (
                (
                    _execution_lineage(
                        execution
                    )
                    or {}
                ).get(
                    "fallback_triggered"
                )
                is True
            )
        }
    )

    if not missing_traits:
        status = "complete"
    elif completed_traits:
        status = "degraded"
    else:
        status = "failed"

    request_identity = {
        "task": task,
        "context": context,
        "requirements": [
            item.projection()
            for item in requirements
        ],
        "provider_model_evidence": (
            normalized_evidence
        ),
        "unavailable_providers": (
            normalized_unavailable
        ),
        "requested_candidates_per_trait": (
            requested_candidates_per_trait
        ),
        "maximum_total_calls": (
            maximum_total_calls
        ),
        "provider_execution_owner": (
            "resilient_text"
        ),
    }

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
        "provider_model_evidence": (
            normalized_evidence
        ),
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
        "routing_attempts": (
            routing_attempts
        ),
        "failed_routing_attempts": (
            failed_routing_attempts
        ),
        "skipped_routing_attempts": (
            skipped_routing_attempts
        ),
        "successful_routing_attempts": (
            successful_routing_attempts
        ),
        "fallback_traits": (
            fallback_traits
        ),
        "inference_calls": calls,
        "call_budget": (
            maximum_total_calls
        ),
        "call_budget_exhausted": (
            calls >= maximum_total_calls
            and bool(missing_traits)
        ),
        "provider_execution_owner": (
            "resilient_text"
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
            "trait_mesh_selects_provider": (
                False
            ),
            "resilient_text_selects_provider": (
                True
            ),
            "resilient_text_owns_fallback": (
                True
            ),
            "routing_attempts_preserved": (
                True
            ),
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

            lineage = (
                response.get(
                    "lineage"
                )
                if isinstance(
                    response,
                    Mapping,
                )
                else None
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
                    "lineage": lineage,
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
        "routing_attempts": list(
            mesh.get(
                "routing_attempts"
            )
            or []
        ),
        "fallback_traits": list(
            mesh.get(
                "fallback_traits"
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

    fallback_order = [
        str(value).strip()
        for value in (
            route_data.get(
                "fallback_order"
            )
            or []
        )
        if str(value).strip()
    ]

    return {
        "status": "ok",
        "schema": schema,
        "owner": owner,
        "route": text_route_id,
        "providers": fallback_order,
        "default_traits": [
            item.trait_id
            for item
            in default_trait_requirements()
        ],
        "maximum_total_calls": 24,
        "provider_execution_owner": (
            "resilient_text"
        ),
        "provider_failure_fallback": True,
        "routing_attempt_lineage": True,
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
        "trait_mesh_selects_provider": (
            False
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

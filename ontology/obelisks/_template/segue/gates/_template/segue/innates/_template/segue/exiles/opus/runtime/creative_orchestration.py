from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence


schema = "savant://runtime/opus/creative-orchestration/1.0.0"
owner = "exile:opus"


class creative_orchestration_error(ValueError):
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
        raise creative_orchestration_error(
            "orchestration value must be canonical-json serializable"
        ) from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _invoke(
    function: Callable[..., Any],
    *args: Any,
) -> Any:
    value = function(*args)

    if inspect.isawaitable(value):
        raise creative_orchestration_error(
            "async provider adapters require an async opus boundary"
        )

    return value


@dataclass(frozen=True, slots=True)
class provider:
    id: str
    execute: Callable[
        [Mapping[str, Any]],
        Mapping[str, Any],
    ]
    capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not str(self.id).strip():
            raise creative_orchestration_error(
                "provider id is required"
            )

        if not callable(
            self.execute
        ):
            raise creative_orchestration_error(
                "provider execute must be callable"
            )


class orchestrator:
    def __init__(
        self,
        providers: Sequence[provider],
    ) -> None:
        normalized = tuple(
            providers
        )

        if not normalized:
            raise creative_orchestration_error(
                "at least one provider is required"
            )

        ids = [
            item.id
            for item in normalized
        ]

        if len(ids) != len(set(ids)):
            raise creative_orchestration_error(
                "provider ids must be unique"
            )

        self.providers = normalized

    def _request(
        self,
        *,
        operation: str,
        payload: Any,
        context: Mapping[str, Any],
        alignment: Mapping[str, Any] | None,
        provider_id: str,
    ) -> dict[str, Any]:
        request = {
            "schema": schema,
            "owner": owner,
            "operation": operation,
            "provider_id": provider_id,
            "payload": payload,
            "context": dict(
                context
            ),
            "creative_alignment": (
                dict(alignment)
                if alignment
                is not None
                else None
            ),
            "execution_contract": {
                "follow_objective": True,
                "preserve_constraints": True,
                "preserve_invariants": True,
                "generate_structurally_distinct_candidates": True,
                "avoid_category_default_convergence": True,
                "avoid_surface_only_variation": True,
                "expose_reasoning_summary_not_hidden_chain": True,
                "return_structured_data": True,
                "preserve_provenance": True,
            },
        }

        request["digest"] = _digest(
            request
        )

        return request

    def execute(
        self,
        *,
        operation: str,
        payload: Any,
        context: Mapping[str, Any],
        alignment: Mapping[str, Any] | None = None,
        provider_ids: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        selected_ids = (
            tuple(
                provider_ids
            )
            if provider_ids
            is not None
            else tuple(
                item.id
                for item in self.providers
            )
        )

        providers = {
            item.id: item
            for item in self.providers
        }

        unknown = (
            set(selected_ids)
            - set(providers)
        )

        if unknown:
            raise creative_orchestration_error(
                "unknown providers: "
                + ", ".join(
                    sorted(
                        unknown
                    )
                )
            )

        responses = []
        failures = []

        for provider_id in selected_ids:
            selected = providers[
                provider_id
            ]

            request = self._request(
                operation=operation,
                payload=payload,
                context=context,
                alignment=alignment,
                provider_id=provider_id,
            )

            try:
                response = _invoke(
                    selected.execute,
                    request,
                )

                if not isinstance(
                    response,
                    Mapping,
                ):
                    raise creative_orchestration_error(
                        "provider response must be a mapping"
                    )

                normalized = {
                    "provider_id": provider_id,
                    "request_digest": request[
                        "digest"
                    ],
                    "response": dict(
                        response
                    ),
                    "response_digest": _digest(
                        response
                    ),
                }

                normalized[
                    "digest"
                ] = _digest(
                    normalized
                )

                responses.append(
                    normalized
                )

            except Exception as exc:
                failures.append(
                    {
                        "provider_id": provider_id,
                        "error_type": type(
                            exc
                        ).__name__,
                        "error": str(
                            exc
                        ),
                    }
                )

        projection = {
            "schema": schema,
            "owner": owner,
            "operation": operation,
            "responses": responses,
            "failures": failures,
            "provider_count": len(
                selected_ids
            ),
            "successful_provider_count": len(
                responses
            ),
            "authority_effect": "none",
            "projection_only": True,
            "boundaries": {
                "declares_truth": False,
                "verifies_fact": False,
                "admits_evidence": False,
                "mutates_canon": False,
                "mutates_source": False,
                "creates_authority": False,
                "owns_iteration": False,
                "owns_alignment": False,
            },
        }

        projection["digest"] = _digest(
            projection
        )

        return projection


__all__ = [
    "creative_orchestration_error",
    "orchestrator",
    "provider",
]

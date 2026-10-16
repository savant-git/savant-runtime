from __future__ import annotations

from collections.abc import Mapping
from typing import Any

try:
    from .creative_orchestration import orchestrator
    from .creative_result_adapter import first_artifact
except ImportError:
    from creative_orchestration import orchestrator
    from creative_result_adapter import first_artifact


schema = "savant://runtime/opus/creative-workflow-binding/1.0.0"
owner = "exile:opus"


class creative_binding_error(ValueError):
    pass


class binding:
    def __init__(
        self,
        execution: orchestrator,
        *,
        provider_ids: tuple[str, ...] | None = None,
    ) -> None:
        if not isinstance(execution, orchestrator):
            raise creative_binding_error(
                "an opus creative orchestrator is required"
            )

        self.execution = execution
        self.provider_ids = provider_ids

    def __call__(
        self,
        request: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(request, Mapping):
            raise creative_binding_error(
                "creative request must be a mapping"
            )

        if request.get("executor_owner") != owner:
            raise creative_binding_error(
                "request does not target opus"
            )

        operation = request.get("operation")

        if operation not in {"generate", "refine"}:
            raise creative_binding_error(
                "unsupported creative operation"
            )

        if operation == "refine":
            reference = request.get(
                "baseline_artifact_reference"
            )

            if not isinstance(reference, Mapping) or not reference:
                raise creative_binding_error(
                    "refinement requires an artifact baseline"
                )

        projection = self.execution.execute(
            operation=operation,
            payload={
                "brief": request["brief"],
                "instruction": request["instruction"],
                "baseline_artifact_id": request.get(
                    "baseline_artifact_id"
                ),
                "baseline_artifact_reference": request.get(
                    "baseline_artifact_reference"
                ),
                "continuity": request.get(
                    "continuity",
                    False,
                ),
            },
            context={
                "session_id": request["session_id"],
                "request_schema": request["schema"],
                "request_owner": request["owner"],
            },
            alignment={
                "preserve_approved_baseline": (
                    operation == "refine"
                ),
                "requires_artifact_output": True,
                "requires_execution_provenance": True,
            },
            provider_ids=self.provider_ids,
        )

        return first_artifact(projection)

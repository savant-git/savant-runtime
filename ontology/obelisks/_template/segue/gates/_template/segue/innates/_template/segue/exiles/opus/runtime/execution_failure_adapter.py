from __future__ import annotations

import inspect
from typing import Any, Mapping

from . import failure_projection


schema = (
    "savant://runtime/opus/"
    "execution-failure-adapter/1.0.0"
)

owner = "exile:opus"


class execution_failure_adapter_error(
    RuntimeError
):
    pass


def _projection_callable():
    candidate = getattr(
        failure_projection,
        "project",
        None,
    )

    if not callable(
        candidate
    ):
        raise execution_failure_adapter_error(
            "failure_projection.project "
            "is not available"
        )

    return candidate


def _accepted_parameters(
    function,
) -> set[str]:
    return {
        name
        for name, parameter
        in inspect.signature(
            function
        ).parameters.items()
        if parameter.kind
        in {
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        }
    }


def _call_projection(
    *,
    category: str,
    message: str,
    retry_after_seconds: float | None,
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    function = (
        _projection_callable()
    )

    accepted = (
        _accepted_parameters(
            function
        )
    )

    available = {
        "category": category,
        "message": message,
        "retry_after_seconds":
            retry_after_seconds,
        "provenance":
            dict(
                provenance
            ),
    }

    required_unknown = []

    signature = inspect.signature(
        function
    )

    for (
        name,
        parameter,
    ) in signature.parameters.items():
        if (
            parameter.kind
            in {
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            }
            and parameter.default
            is inspect.Parameter.empty
            and name not in available
        ):
            required_unknown.append(
                name
            )

    if required_unknown:
        raise execution_failure_adapter_error(
            "failure projection has "
            "unsupported required parameters: "
            + ", ".join(
                sorted(
                    required_unknown
                )
            )
        )

    kwargs = {
        name: value
        for name, value
        in available.items()
        if name in accepted
        and (
            value is not None
            or name
            != "retry_after_seconds"
        )
    }

    result = function(
        **kwargs
    )

    if not isinstance(
        result,
        Mapping,
    ):
        raise execution_failure_adapter_error(
            "failure projection did not "
            "return an object"
        )

    return dict(
        result
    )


def project_internal_execution(
    error: BaseException,
    *,
    request_id: Any = None,
    trace_id: Any = None,
    tenant_id: Any = None,
    execution_id: Any = None,
    attempt: Any = None,
) -> dict[str, Any]:
    provenance = {
        "request_id": request_id,
        "trace_id": trace_id,
        "tenant_id": tenant_id,
        "execution_id": execution_id,
        "attempt": attempt,
    }

    provenance = {
        key: value
        for key, value
        in provenance.items()
        if value is not None
    }

    return _call_projection(
        category="internal_execution",
        message=type(
            error
        ).__name__,
        retry_after_seconds=None,
        provenance=provenance,
    )


def project_timeout(
    error: BaseException,
    *,
    request_id: Any = None,
    trace_id: Any = None,
    tenant_id: Any = None,
    execution_id: Any = None,
    attempt: Any = None,
) -> dict[str, Any]:
    provenance = {
        "request_id": request_id,
        "trace_id": trace_id,
        "tenant_id": tenant_id,
        "execution_id": execution_id,
        "attempt": attempt,
    }

    provenance = {
        key: value
        for key, value
        in provenance.items()
        if value is not None
    }

    return _call_projection(
        category="provider_timeout",
        message=type(
            error
        ).__name__,
        retry_after_seconds=None,
        provenance=provenance,
    )


def project_deadline(
    error: BaseException,
    *,
    request_id: Any = None,
    trace_id: Any = None,
    tenant_id: Any = None,
    execution_id: Any = None,
    attempt: Any = None,
) -> dict[str, Any]:
    provenance = {
        "request_id": request_id,
        "trace_id": trace_id,
        "tenant_id": tenant_id,
        "execution_id": execution_id,
        "attempt": attempt,
    }

    provenance = {
        key: value
        for key, value
        in provenance.items()
        if value is not None
    }

    return _call_projection(
        category="deadline",
        message=type(
            error
        ).__name__,
        retry_after_seconds=None,
        provenance=provenance,
    )

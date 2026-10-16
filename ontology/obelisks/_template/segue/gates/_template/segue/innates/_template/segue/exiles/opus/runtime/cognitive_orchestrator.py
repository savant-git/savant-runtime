from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from cognitive_capabilities import (
    canonical_list,
)
from cognitive_context import (
    context_from_request,
    inject_context,
)
from cognitive_execution import (
    execute_cognitive_request,
)
from cognitive_provider_health import (
    capability_healthy_providers,
)
from cognitive_synthesis import (
    synthesize,
)


def _required_capabilities(
    request: Mapping[str, Any],
) -> list[str]:
    raw = request.get(
        "required_capabilities"
    )

    if raw is None:
        raw = [
            "text_inference",
        ]

    if isinstance(
        raw,
        str,
    ):
        raw = [
            raw,
        ]

    if not isinstance(
        raw,
        Sequence,
    ):
        raise ValueError(
            "required_capabilities must be a sequence"
        )

    required = canonical_list(
        raw
    )

    if not required:
        required = [
            "text_inference",
        ]

    return required


def _synthesis_dict(
    synthesis: Any,
) -> Dict[str, Any]:
    as_dict = getattr(
        synthesis,
        "as_dict",
        None,
    )

    if callable(
        as_dict
    ):
        value = as_dict()

        if isinstance(
            value,
            Mapping,
        ):
            return dict(
                value
            )

    if isinstance(
        synthesis,
        Mapping,
    ):
        return dict(
            synthesis
        )

    return {}


def _synthesis_text(
    synthesis: Any,
    synthesis_data: Mapping[str, Any],
) -> str:
    direct = getattr(
        synthesis,
        "text",
        None,
    )

    if direct:
        return str(
            direct
        ).strip()

    for key in (
        "text",
        "selected_text",
        "synthesized_text",
        "output",
        "response",
    ):
        value = synthesis_data.get(
            key
        )

        if value:
            return str(
                value
            ).strip()

    return ""


def orchestrate(
    request: Mapping[str, Any],
    providers: Sequence[
        Mapping[str, Any]
    ],
    executor=None,
) -> Dict[str, Any]:
    request_value = dict(
        request
    )

    required = (
        _required_capabilities(
            request_value
        )
    )

    request_value[
        "required_capabilities"
    ] = required

    context = (
        context_from_request(
            request_value
        )
    )

    contextual_request = (
        inject_context(
            request_value,
            context,
        )
    )

    contextual_request[
        "required_capabilities"
    ] = required

    healthy = (
        capability_healthy_providers(
            providers,
            required,
        )
    )

    if not healthy:
        return {
            "ok": False,
            "error":
                "no capability-compatible "
                "Opus provider available",
            "text": "",
            "provider": None,
            "model": None,
            "context":
                context.as_dict(),
            "provider_count":
                len(
                    providers
                ),
            "eligible_provider_count":
                0,
            "required_capabilities":
                required,
            "cognitive_orchestration":
                True,
        }

    execution = (
        execute_cognitive_request(
            contextual_request,
            healthy,
            executor=executor,
        )
    )

    candidates = (
        execution.get(
            "candidates"
        )
        or []
    )

    synthesis = synthesize(
        candidates
    )

    synthesis_data = (
        _synthesis_dict(
            synthesis
        )
    )

    text = (
        _synthesis_text(
            synthesis,
            synthesis_data,
        )
        or str(
            execution.get(
                "text"
            )
            or ""
        ).strip()
    )

    provider_id = (
        execution.get(
            "provider"
        )
        or synthesis_data.get(
            "provider"
        )
        or synthesis_data.get(
            "provider_id"
        )
        or synthesis_data.get(
            "selected_provider"
        )
    )

    model = (
        execution.get(
            "model"
        )
        or synthesis_data.get(
            "model"
        )
        or synthesis_data.get(
            "selected_model"
        )
    )

    ok = bool(
        execution.get(
            "ok",
            bool(text),
        )
        and text
    )

    result = dict(
        execution
    )

    result.update(
        {
            "ok":
                ok,
            "text":
                text,
            "provider":
                provider_id,
            "model":
                model,
            "context":
                context.as_dict(),
            "provider_count":
                len(
                    providers
                ),
            "eligible_provider_count":
                len(
                    healthy
                ),
            "required_capabilities":
                required,
            "synthesis":
                synthesis_data,
            "cognitive_orchestration":
                True,
        }
    )

    return result


def orchestrate_text(
    request: Mapping[str, Any],
    providers: Sequence[
        Mapping[str, Any]
    ],
    executor=None,
) -> Dict[str, Any]:
    value = dict(
        request
    )

    value.setdefault(
        "required_capabilities",
        [
            "text_inference",
        ],
    )

    return orchestrate(
        value,
        providers,
        executor=executor,
    )

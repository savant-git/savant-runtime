from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from .image_renderer import (
    baseline_image,
    project_image,
)

from ...opus.runtime.creative_orchestration import (
    provider,
)


schema = "savant://runtime/urge/opus-image-provider/1.0.0"
owner = "exile:urge"


class opus_image_provider_error(ValueError):
    pass


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise opus_image_provider_error(
            f"{name} must be a nonempty string"
        )
    return value.strip()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _baseline(
    reference: Any,
) -> baseline_image:
    if not isinstance(reference, Mapping):
        raise opus_image_provider_error(
            "baseline reference must be a mapping"
        )

    source = _text(
        reference.get("source"),
        "baseline source",
    )

    media_type = _text(
        reference.get("media_type"),
        "baseline media_type",
    )

    if not media_type.startswith("image/"):
        raise opus_image_provider_error(
            "baseline must reference an image"
        )

    return baseline_image(
        name=reference.get("name") or "baseline.png",
        media_type=media_type,
        source=source,
    )


def execute(
    request: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        raise opus_image_provider_error(
            "request must be a mapping"
        )

    operation = request.get("operation")

    if operation not in {"generate", "refine"}:
        raise opus_image_provider_error(
            "unsupported operation"
        )

    payload = request.get("payload")

    if not isinstance(payload, Mapping):
        raise opus_image_provider_error(
            "payload must be a mapping"
        )

    instruction = _text(
        payload.get("instruction"),
        "instruction",
    )

    brief = _text(
        payload.get("brief"),
        "brief",
    )

    baseline = None

    if operation == "refine":
        baseline = _baseline(
            payload.get("baseline_artifact_reference")
        )

    render_request = {
        "brief": brief,
        "instruction": instruction,
        "candidate": {
            "brief": brief,
            "instruction": instruction,
        },
        "context": dict(
            request.get("context") or {}
        ),
    }

    rendered = project_image(
        render_request,
        baseline=baseline,
    )

    image = _text(
        rendered.get("image"),
        "rendered image",
    )

    model = _text(
        rendered.get("model"),
        "model",
    )

    reference = {
        "source": image,
        "media_type": _text(
            rendered.get("media_type"),
            "media_type",
        ),
        "name": "artifact.png",
    }

    result = {
        "status": "succeeded",
        "owner": "exile:opus",
        "provider": "openai",
        "model": model,
        "artifact_reference": reference,
        "renderer_schema": rendered.get("schema"),
        "renderer_operation": rendered.get("operation"),
        "request_digest": request.get("digest"),
    }

    result["execution_id"] = (
        "opus-image:"
        + _digest(result)
    )

    return result


def binding() -> provider:
    return provider(
        id="openai-image",
        execute=execute,
        capabilities=(
            "image-generation",
            "image-editing",
            "approved-baseline-refinement",
        ),
    )

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


schema = "savant://runtime/opus/creative-result-adapter/1.0.0"
owner = "exile:opus"


class creative_result_error(ValueError):
    pass


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


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise creative_result_error(
            f"{name} must be a nonempty string"
        )
    return value.strip()


def normalize(
    projection: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(projection, Mapping):
        raise creative_result_error(
            "opus projection must be a mapping"
        )

    if projection.get("owner") != owner:
        raise creative_result_error(
            "projection is not owned by opus"
        )

    if projection.get("projection_only") is not True:
        raise creative_result_error(
            "unexpected orchestration contract"
        )

    responses = projection.get("responses")

    if not isinstance(responses, list):
        raise creative_result_error(
            "opus responses must be a list"
        )

    artifacts = []

    for entry in responses:
        if not isinstance(entry, Mapping):
            continue

        response = entry.get("response")

        if not isinstance(response, Mapping):
            continue

        if response.get("status") != "succeeded":
            continue

        reference = response.get("artifact_reference")

        if not isinstance(reference, Mapping) or not reference:
            continue

        provider_id = _text(
            entry.get("provider_id"),
            "provider_id",
        )

        model = _text(
            response.get("model"),
            "model",
        )

        execution_id = _text(
            response.get("execution_id"),
            "execution_id",
        )

        artifact = {
            "status": "succeeded",
            "owner": owner,
            "provider": provider_id,
            "model": model,
            "execution_id": execution_id,
            "artifact_reference": dict(reference),
            "opus_request_digest": entry.get(
                "request_digest"
            ),
            "opus_response_digest": entry.get(
                "response_digest"
            ),
        }

        artifact["digest"] = _digest(artifact)
        artifacts.append(artifact)

    if not artifacts:
        raise creative_result_error(
            "no successful artifact-producing "
            "opus response"
        )

    return {
        "schema": schema,
        "owner": owner,
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "failures": list(
            projection.get("failures", [])
        ),
        "projection_digest": projection.get(
            "digest"
        ),
    }


def first_artifact(
    projection: Mapping[str, Any],
) -> dict[str, Any]:
    return normalize(projection)["artifacts"][0]

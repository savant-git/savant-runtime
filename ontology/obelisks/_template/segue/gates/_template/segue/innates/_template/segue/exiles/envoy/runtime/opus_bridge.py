from __future__ import annotations

import base64
import sys
from pathlib import Path
from typing import Any, Dict, Iterable


ROOT = Path("/root/savant-runtime")

ENVOY_RUNTIME = (
    ROOT
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "envoy"
    / "runtime"
)

OPUS_RUNTIME = (
    ROOT
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "opus"
    / "runtime"
)

for path in (
    OPUS_RUNTIME,
    ENVOY_RUNTIME,
):
    value = str(path)

    if value not in sys.path:
        sys.path.insert(
            0,
            value,
        )


from cognitive_projection import (
    opus_request_projection,
    project_cognitive_layers,
)
from router import execute_text_request
from voice_orchestrator import (
    synthesize as opus_synthesize,
)


OWNER = "envoy"
EXECUTION_OWNER = "opus"

TEXT_ROUTE = "text_inference_route"
VOICE_ROUTE = "voice_tts_route"

TEXT_BRIDGE_SCHEMA = (
    "savant.envoy.opus-text-bridge.v1"
)

MIME_FORMATS = {
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/ogg": "ogg",
    "audio/flac": "flac",
    "audio/aac": "aac",
}


class OpusBridgeError(
    RuntimeError
):
    pass


def _audio_format(
    mime_type: Any,
) -> str | None:
    normalized = str(
        mime_type
        or ""
    ).strip().lower()

    if not normalized:
        return None

    known = MIME_FORMATS.get(
        normalized
    )

    if known:
        return known

    if "/" not in normalized:
        return normalized

    subtype = normalized.split(
        "/",
        1,
    )[1].strip()

    if not subtype:
        return None

    if subtype.startswith(
        "x-"
    ):
        subtype = subtype[2:]

    return (
        subtype
        or None
    )


def synthesize_with_opus(
    text: str,
    voice_profile: Dict[str, Any],
) -> Dict[str, Any]:
    result = opus_synthesize(
        text,
        voice_profile,
    )

    if not isinstance(
        result,
        dict,
    ):
        raise OpusBridgeError(
            "opus voice synthesis result "
            "must be an object"
        )

    provider = str(
        result.get(
            "provider",
            "",
        )
        or ""
    ).strip()

    if not provider:
        raise OpusBridgeError(
            "opus voice synthesis result "
            "lacks provider"
        )

    mime_type = str(
        result.get(
            "mime_type",
            "",
        )
        or ""
    ).strip()

    if not mime_type:
        raise OpusBridgeError(
            "opus voice synthesis result "
            "lacks mime_type"
        )

    audio = result.get(
        "audio"
    )

    if not isinstance(
        audio,
        bytes,
    ):
        raise OpusBridgeError(
            "opus voice synthesis result "
            "lacks byte audio"
        )

    audio_format = _audio_format(
        mime_type
    )

    if not audio_format:
        raise OpusBridgeError(
            "unable to derive audio format "
            f"from mime_type={mime_type!r}"
        )

    return {
        "provider": provider,
        "mime_type": mime_type,
        "format": audio_format,
        "audio_base64": (
            base64.b64encode(
                audio
            ).decode(
                "ascii"
            )
        ),
    }


def _validate_text_result(
    result: Any,
) -> Dict[str, Any]:
    if not isinstance(
        result,
        dict,
    ):
        raise OpusBridgeError(
            "opus text inference result "
            "must be an object"
        )

    lineage = result.get(
        "lineage"
    )

    if not isinstance(
        lineage,
        dict,
    ):
        raise OpusBridgeError(
            "opus text inference result "
            "lacks lineage"
        )

    if (
        lineage.get(
            "owner"
        )
        != EXECUTION_OWNER
    ):
        raise OpusBridgeError(
            "opus text inference authority "
            "boundary violated"
        )

    if (
        lineage.get(
            "route"
        )
        != TEXT_ROUTE
    ):
        raise OpusBridgeError(
            "unexpected opus text route: "
            f"{lineage.get('route')!r}"
        )

    return result


def infer_with_opus(
    request: Dict[str, Any],
) -> Dict[str, Any]:
    if not isinstance(
        request,
        dict,
    ):
        raise OpusBridgeError(
            "text inference request must "
            "be an object"
        )

    bridged_request = dict(
        request
    )

    request_owner = str(
        bridged_request.get(
            "owner"
        )
        or OWNER
    ).strip()

    if not request_owner:
        request_owner = OWNER

    bridged_request[
        "owner"
    ] = request_owner

    result = execute_text_request(
        bridged_request
    )

    return _validate_text_result(
        result
    )


def infer_with_cognitive_projection(
    request: Dict[str, Any],
    persona_projection: Dict[str, Any],
    *,
    domains: Iterable[Any] = (),
    signals: Iterable[Any] = (),
    requested_layers: Iterable[Any] = (),
) -> Dict[str, Any]:
    if not isinstance(
        request,
        dict,
    ):
        raise OpusBridgeError(
            "text inference request must "
            "be an object"
        )

    if not isinstance(
        persona_projection,
        dict,
    ):
        raise OpusBridgeError(
            "persona projection must "
            "be an object"
        )

    cognitive = (
        project_cognitive_layers(
            persona_projection,
            domains=domains,
            signals=signals,
            requested_layers=(
                requested_layers
            ),
        )
    )

    routing_projection = (
        opus_request_projection(
            cognitive
        )
    )

    bridged_request = dict(
        request
    )

    request_owner = str(
        bridged_request.get(
            "owner"
        )
        or OWNER
    ).strip()

    if not request_owner:
        request_owner = OWNER

    bridged_request[
        "owner"
    ] = request_owner

    bridged_request.update(
        routing_projection
    )

    result = execute_text_request(
        bridged_request
    )

    validated = (
        _validate_text_result(
            result
        )
    )

    validated[
        "cognitive_projection"
    ] = cognitive

    return validated


def text_bridge_projection() -> Dict[
    str,
    Any,
]:
    return {
        "schema": TEXT_BRIDGE_SCHEMA,
        "owner": OWNER,
        "execution_owner": (
            EXECUTION_OWNER
        ),
        "route": TEXT_ROUTE,
        "provider_selection_owner": (
            EXECUTION_OWNER
        ),
        "model_selection_owner": (
            EXECUTION_OWNER
        ),
        "provider_routing_owner": (
            EXECUTION_OWNER
        ),
        "provider_credentials_owner": (
            EXECUTION_OWNER
        ),
        "provider_execution_owner": (
            EXECUTION_OWNER
        ),
        "provider_retry_policy_owner": (
            EXECUTION_OWNER
        ),
        "provider_fallback_policy_owner": (
            EXECUTION_OWNER
        ),
        "envoy_may_project_cognitive_layers": (
            True
        ),
        "envoy_may_select_provider": False,
        "envoy_may_select_model": False,
        "envoy_may_access_credentials": (
            False
        ),
        "envoy_may_execute_provider_calls": (
            False
        ),
        "envoy_may_define_provider_retry": (
            False
        ),
        "envoy_may_define_provider_fallback": (
            False
        ),
        "ready": True,
    }


def selftest() -> Dict[str, Any]:
    projection = (
        text_bridge_projection()
    )

    if (
        projection["owner"]
        != OWNER
    ):
        raise OpusBridgeError(
            "bridge owner mismatch"
        )

    if (
        projection[
            "execution_owner"
        ]
        != EXECUTION_OWNER
    ):
        raise OpusBridgeError(
            "execution owner mismatch"
        )

    if (
        projection["route"]
        != TEXT_ROUTE
    ):
        raise OpusBridgeError(
            "text route mismatch"
        )

    forbidden = (
        "envoy_may_select_provider",
        "envoy_may_select_model",
        "envoy_may_access_credentials",
        "envoy_may_execute_provider_calls",
        "envoy_may_define_provider_retry",
        "envoy_may_define_provider_fallback",
    )

    for field in forbidden:
        if (
            projection[field]
            is not False
        ):
            raise OpusBridgeError(
                "authority boundary failed: "
                f"{field}"
            )

    if (
        projection[
            "envoy_may_project_cognitive_layers"
        ]
        is not True
    ):
        raise OpusBridgeError(
            "cognitive projection boundary "
            "is unavailable"
        )

    if not callable(
        execute_text_request
    ):
        raise OpusBridgeError(
            "opus execute_text_request "
            "is unavailable"
        )

    if not callable(
        opus_synthesize
    ):
        raise OpusBridgeError(
            "opus voice synthesis "
            "is unavailable"
        )

    if not callable(
        project_cognitive_layers
    ):
        raise OpusBridgeError(
            "envoy cognitive projection "
            "is unavailable"
        )

    if not callable(
        opus_request_projection
    ):
        raise OpusBridgeError(
            "opus cognitive request "
            "projection is unavailable"
        )

    if (
        _audio_format(
            "audio/mpeg"
        )
        != "mp3"
    ):
        raise OpusBridgeError(
            "audio format projection failed"
        )

    return {
        "ok": True,
        "schema": TEXT_BRIDGE_SCHEMA,
        "owner": OWNER,
        "text_execution_owner": (
            EXECUTION_OWNER
        ),
        "text_route": TEXT_ROUTE,
        "voice_execution_owner": (
            EXECUTION_OWNER
        ),
        "voice_route": VOICE_ROUTE,
        "provider_authority_preserved": (
            True
        ),
        "model_authority_preserved": (
            True
        ),
        "cognitive_projection_ready": (
            True
        ),
        "voice_bridge_preserved": True,
        "audio_format_projection": True,
        "text_bridge_ready": True,
    }


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )

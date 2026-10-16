#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Iterable

from envoy_bridge import (
    DEFAULT_PERSONA_ID,
    load_envoy_opus_bridge,
    project_persona,
)


OWNER = "palaver"
PERSONA_OWNER = "envoy"
EXECUTION_OWNER = "opus"
SCHEMA = "savant.palaver.cognitive-bridge.v1"


class CognitiveBridgeError(RuntimeError):
    pass


def infer(
    text: str,
    *,
    persona_id: str | None = None,
    domains: Iterable[Any] = (),
    signals: Iterable[Any] = (),
    cap: int | None = None,
    required_layers: Iterable[Any] = (),
    required_capabilities: Iterable[Any] = (),
    **request_fields: Any,
) -> dict[str, Any]:
    value = str(
        text or ""
    ).strip()

    if not value:
        raise CognitiveBridgeError(
            "Palaver inference request missing text"
        )

    selected_persona = (
        str(
            persona_id
            or DEFAULT_PERSONA_ID
        ).strip()
        or DEFAULT_PERSONA_ID
    )

    persona = project_persona(
        selected_persona,
        domains=domains,
        signals=signals,
        cap=cap,
    )

    if not isinstance(persona, dict):
        raise CognitiveBridgeError(
            "Envoy returned invalid persona projection"
        )

    if persona.get("owner") != PERSONA_OWNER:
        raise CognitiveBridgeError(
            "persona authority must remain Envoy"
        )

    request = {
        **request_fields,
        "owner": OWNER,
        "message": value,
        "persona_id": selected_persona,
        "persona_projection": persona,
        "required_layers": [
            str(item).strip().lower()
            for item in required_layers
            if str(item).strip()
        ],
        "required_capabilities": [
            str(item).strip().lower()
            for item in required_capabilities
            if str(item).strip()
        ],
    }

    opus_bridge = load_envoy_opus_bridge()

    infer_with_opus = getattr(
        opus_bridge,
        "infer_with_opus",
        None,
    )

    if not callable(infer_with_opus):
        raise CognitiveBridgeError(
            "Envoy Opus bridge lacks infer_with_opus()"
        )

    result = infer_with_opus(
        request
    )

    if not isinstance(result, dict):
        raise CognitiveBridgeError(
            "Opus returned invalid inference result"
        )

    lineage = result.get("lineage")

    if not isinstance(lineage, dict):
        raise CognitiveBridgeError(
            "Opus result lacks lineage"
        )

    if lineage.get("owner") != EXECUTION_OWNER:
        raise CognitiveBridgeError(
            "provider execution authority must remain Opus"
        )

    if lineage.get("request_owner") != OWNER:
        raise CognitiveBridgeError(
            "Palaver request ownership was not preserved"
        )

    result["palaver"] = {
        "schema": SCHEMA,
        "conversation_owner": OWNER,
        "persona_owner": PERSONA_OWNER,
        "execution_owner": EXECUTION_OWNER,
        "persona_id": selected_persona,
        "persona_composition_digest": (
            persona.get("composition_digest")
        ),
        "authority_effect": "none",
    }

    return result


def selftest() -> dict[str, Any]:
    persona = project_persona(
        DEFAULT_PERSONA_ID,
        domains=("engineering",),
        signals=("implement",),
        cap=4,
    )

    if not isinstance(persona, dict):
        raise CognitiveBridgeError(
            "persona projection failed"
        )

    if persona.get("owner") != PERSONA_OWNER:
        raise CognitiveBridgeError(
            "persona ownership failed"
        )

    opus_bridge = load_envoy_opus_bridge()

    if not callable(
        getattr(
            opus_bridge,
            "infer_with_opus",
            None,
        )
    ):
        raise CognitiveBridgeError(
            "Opus inference bridge unavailable"
        )

    return {
        "ok": True,
        "schema": SCHEMA,
        "conversation_owner": OWNER,
        "persona_owner": PERSONA_OWNER,
        "execution_owner": EXECUTION_OWNER,
        "default_persona": DEFAULT_PERSONA_ID,
        "persona_projection_ready": True,
        "text_inference_bridge_ready": True,
        "authority_effect": "none",
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

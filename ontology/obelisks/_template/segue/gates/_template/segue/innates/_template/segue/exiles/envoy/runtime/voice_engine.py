from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from opus_bridge import synthesize_with_opus
from persona_engine import (
    DEFAULT_PERSONA_ID,
    list_personas as list_registered_personas,
    load_persona,
)


ENVOY_ROOT = Path(__file__).resolve().parents[1]

VOICES = (
    ENVOY_ROOT
    / "registry"
    / "voices"
)

DEFAULT_VOICE_REF = "synthetic/palaver_default"


class VoiceError(RuntimeError):
    pass


def read_json(
    path: Path,
) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )
    except FileNotFoundError as exc:
        raise VoiceError(
            f"voice profile missing: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise VoiceError(
            f"invalid voice profile JSON: {path}: {exc}"
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise VoiceError(
            f"voice profile must be a JSON object: {path}"
        )

    return value


def resolve_persona(
    persona_id: str | None = None,
) -> dict[str, Any]:
    return load_persona(
        persona_id
        or DEFAULT_PERSONA_ID
    )


def list_personas() -> list[dict[str, Any]]:
    return list_registered_personas()


def _voice_path(
    voice_ref: str,
) -> Path:
    normalized = str(
        voice_ref
        or ""
    ).strip().lstrip("/")

    if not normalized:
        normalized = DEFAULT_VOICE_REF

    candidate = (
        VOICES
        / f"{normalized}.json"
    ).resolve()

    voice_root = VOICES.resolve()

    if (
        candidate != voice_root
        and voice_root not in candidate.parents
    ):
        raise VoiceError(
            "voice reference escapes Envoy voice registry"
        )

    return candidate


def resolve_voice(
    persona_id: str | None = None,
) -> dict[str, Any]:
    persona = resolve_persona(
        persona_id
    )

    voice_ref = str(
        persona.get(
            "voice_ref"
        )
        or DEFAULT_VOICE_REF
    ).strip()

    requested_path = _voice_path(
        voice_ref
    )

    fallback_used = False

    if requested_path.is_file():
        selected_path = requested_path
    else:
        selected_path = _voice_path(
            DEFAULT_VOICE_REF
        )
        fallback_used = True

    voice = read_json(
        selected_path
    )

    result = dict(
        voice
    )

    result[
        "persona"
    ] = persona

    result[
        "resolved_voice_ref"
    ] = str(
        selected_path.relative_to(
            VOICES
        )
    ).removesuffix(
        ".json"
    )

    result[
        "requested_voice_ref"
    ] = voice_ref

    result[
        "fallback_used"
    ] = fallback_used

    result[
        "owner"
    ] = "envoy"

    return result


def synthesize(
    text: str,
    persona_id: str | None = None,
) -> dict[str, Any]:
    value = str(
        text
        or ""
    ).strip()

    if not value:
        raise VoiceError(
            "speech request missing text"
        )

    voice = resolve_voice(
        persona_id
    )

    return synthesize_with_opus(
        value,
        voice,
    )


def synthesize_base64(
    text: str,
    persona_id: str | None = None,
) -> dict[str, Any]:
    voice = resolve_voice(
        persona_id
    )

    out = synthesize(
        text,
        persona_id,
    )

    return {
        "persona_id": (
            voice[
                "persona"
            ].get(
                "persona_id"
            )
        ),
        "display_name": (
            voice[
                "persona"
            ].get(
                "display_name"
            )
        ),
        "voice": voice,
        "provider": (
            out.get(
                "provider"
            )
        ),
        "mime_type": (
            out.get(
                "mime_type",
                "audio/mpeg",
            )
        ),
        "format": (
            out.get(
                "format"
            )
        ),
        "audio_base64": (
            out.get(
                "audio_base64"
            )
        ),
    }


def integration_status() -> dict[str, Any]:
    default_persona = (
        resolve_persona()
    )

    default_voice = (
        resolve_voice()
    )

    return {
        "owner": "envoy",
        "persona_owner": "envoy",
        "voice_owner": "envoy",
        "provider_execution_owner": "opus",
        "default_persona": (
            default_persona[
                "persona_id"
            ]
        ),
        "default_voice_ref": (
            default_voice[
                "resolved_voice_ref"
            ]
        ),
        "persona_count": len(
            list_personas()
        ),
        "direct_provider_execution": False,
        "ready": True,
    }


def selftest() -> dict[str, Any]:
    default_persona = (
        resolve_persona()
    )

    if (
        default_persona[
            "persona_id"
        ]
        != DEFAULT_PERSONA_ID
    ):
        raise VoiceError(
            "voice resolver default persona is not Orobouros"
        )

    historical = (
        resolve_persona(
            "historical_research_mode"
        )
    )

    if (
        historical[
            "persona_id"
        ]
        != "historical_research_mode"
    ):
        raise VoiceError(
            "non-default persona resolution failed"
        )

    historical_voice = (
        resolve_voice(
            "historical_research_mode"
        )
    )

    if (
        historical_voice[
            "persona"
        ][
            "persona_id"
        ]
        != "historical_research_mode"
    ):
        raise VoiceError(
            "historical persona and voice became detached"
        )

    return {
        "ok": True,
        "default_persona": (
            default_persona[
                "persona_id"
            ]
        ),
        "non_default_persona": (
            historical[
                "persona_id"
            ]
        ),
        "non_default_voice": (
            historical_voice[
                "resolved_voice_ref"
            ]
        ),
        "persona_owner": "envoy",
        "voice_owner": "envoy",
        "provider_execution_owner": "opus",
        "direct_provider_execution": False,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )

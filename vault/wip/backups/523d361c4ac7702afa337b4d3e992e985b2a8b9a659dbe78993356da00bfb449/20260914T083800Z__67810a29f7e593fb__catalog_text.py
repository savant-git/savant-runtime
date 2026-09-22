#!/usr/bin/env python3

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from providers.base import ProviderError
from providers import native_text
from providers import universal_text


OPUS_ROOT = Path(
    __file__
).resolve().parents[2]

CATALOG_PATH = (
    OPUS_ROOT
    / "registry"
    / "providers"
    / "universal_text_catalog.json"
)

EXPLICIT_PROFILE_ENV = (
    "OPUS_UNIVERSAL_PROVIDER"
)

SCHEMA = (
    "savant.opus.catalog-text.v3"
)

OWNER = "opus"

UNIVERSAL_PROTOCOLS = {
    "openai_responses",
    "openai_chat",
    "anthropic_messages",
    "gemini_generate_content",
    "generic_json",
}

NATIVE_PROTOCOLS = {
    "bedrock_converse",
    "cohere_chat",
    "ollama_chat",
    "replicate_prediction",
}


def _catalog() -> Dict[str, Any]:
    try:
        value = json.loads(
            CATALOG_PATH.read_text(
                encoding="utf-8"
            )
        )
    except FileNotFoundError as exc:
        raise ProviderError(
            "opus universal provider catalog missing"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ProviderError(
            "opus universal provider catalog invalid: "
            f"{exc}"
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise ProviderError(
            "opus universal provider catalog "
            "must be an object"
        )

    profiles = value.get(
        "profiles"
    )

    if not isinstance(
        profiles,
        dict,
    ):
        raise ProviderError(
            "opus universal provider catalog "
            "profiles missing"
        )

    return value


def _env(
    name: object,
) -> str:
    key = str(
        name
        or ""
    ).strip()

    if not key:
        return ""

    return str(
        os.getenv(
            key,
            "",
        )
        or ""
    ).strip()


def _base_configured(
    profile: Dict[str, Any],
) -> bool:
    if str(
        profile.get(
            "api_base"
        )
        or ""
    ).strip():
        return True

    return bool(
        _env(
            profile.get(
                "api_base_env"
            )
        )
    )


def _credential_configured(
    profile: Dict[str, Any],
) -> bool:
    header_env = profile.get(
        "header_env"
    )

    if isinstance(
        header_env,
        dict,
    ):
        if any(
            _env(value)
            for value
            in header_env.values()
        ):
            return True

    if _env(
        profile.get(
            "api_key_env"
        )
    ):
        return True

    if _env(
        profile.get(
            "api_key_env_fallback"
        )
    ):
        return True

    return bool(
        profile.get(
            "api_key_optional",
            False,
        )
    )


def _profile_configured(
    profile_id: str,
    profile: Dict[str, Any],
    *,
    automatic: bool,
) -> bool:
    protocol = str(
        profile.get(
            "protocol"
        )
        or ""
    ).strip().lower()

    if (
        automatic
        and profile_id
        == "custom"
    ):
        return False

    if protocol == "bedrock_converse":
        return native_text.profile_available(
            {
                **profile,
                "profile_id":
                    profile_id,
            }
        )

    if protocol == "ollama_chat":
        return _base_configured(
            profile
        )

    if protocol in {
        "cohere_chat",
        "replicate_prediction",
    }:
        return (
            _base_configured(
                profile
            )
            and _credential_configured(
                profile
            )
        )

    if protocol in UNIVERSAL_PROTOCOLS:
        return (
            _base_configured(
                profile
            )
            and _credential_configured(
                profile
            )
        )

    return False


def available_profiles() -> list[str]:
    profiles = _catalog()[
        "profiles"
    ]

    result: list[str] = []

    for (
        profile_id,
        profile,
    ) in profiles.items():
        if not isinstance(
            profile,
            dict,
        ):
            continue

        if _profile_configured(
            str(
                profile_id
            ),
            profile,
            automatic=True,
        ):
            result.append(
                str(
                    profile_id
                )
            )

    return result


def available() -> bool:
    requested = str(
        os.getenv(
            EXPLICIT_PROFILE_ENV,
            "",
        )
        or ""
    ).strip()

    if requested:
        profile = _catalog()[
            "profiles"
        ].get(
            requested
        )

        return (
            isinstance(
                profile,
                dict,
            )
            and _profile_configured(
                requested,
                profile,
                automatic=False,
            )
        )

    return bool(
        available_profiles()
    )


def _selected(
    request: Dict[str, Any],
) -> tuple[
    str,
    Dict[str, Any],
]:
    requested = str(
        request.get(
            "provider_profile"
        )
        or os.getenv(
            EXPLICIT_PROFILE_ENV,
            "",
        )
        or ""
    ).strip()

    profiles = _catalog()[
        "profiles"
    ]

    if requested:
        profile = profiles.get(
            requested
        )

        if not isinstance(
            profile,
            dict,
        ):
            raise ProviderError(
                "unknown opus provider profile: "
                f"{requested}"
            )

        if not _profile_configured(
            requested,
            profile,
            automatic=False,
        ):
            raise ProviderError(
                "opus provider profile unavailable: "
                f"{requested}"
            )

        return (
            requested,
            dict(
                profile
            ),
        )

    candidates = (
        available_profiles()
    )

    if not candidates:
        raise ProviderError(
            "no configured opus catalog "
            "provider available"
        )

    profile_id = candidates[0]

    return (
        profile_id,
        dict(
            profiles[
                profile_id
            ]
        ),
    )


def infer(
    request: Dict[str, Any],
    provider: Dict[str, Any],
) -> Dict[str, Any]:
    if not isinstance(
        request,
        dict,
    ):
        raise ProviderError(
            "request must be an object"
        )

    (
        profile_id,
        profile,
    ) = _selected(
        request
    )

    protocol = str(
        profile.get(
            "protocol"
        )
        or ""
    ).strip().lower()

    profile[
        "profile_id"
    ] = profile_id

    delegated = dict(
        request
    )

    delegated[
        "provider_profile"
    ] = profile_id

    if protocol in NATIVE_PROTOCOLS:
        result = native_text.infer(
            delegated,
            provider,
            profile,
        )

    elif protocol in UNIVERSAL_PROTOCOLS:
        result = universal_text.infer(
            delegated,
            provider,
        )

    else:
        raise ProviderError(
            "unsupported catalog protocol: "
            f"{protocol}"
        )

    if not isinstance(
        result,
        dict,
    ):
        raise ProviderError(
            "catalog provider returned "
            "non-object result"
        )

    result[
        "provider"
    ] = "catalog_text"

    result[
        "provider_profile"
    ] = profile_id

    result[
        "catalog_schema"
    ] = SCHEMA

    result[
        "owner"
    ] = OWNER

    result[
        "authority_effect"
    ] = "none"

    return result

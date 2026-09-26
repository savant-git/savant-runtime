#!/usr/bin/env python3

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from .base import ProviderError
from . import native_text
from . import universal_text

try:
    from ..admission_projection import (
        load_projection,
    )
except ImportError:
    from admission_projection import (
        load_projection,
    )


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
    "savant.opus.catalog-text.v4"
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
            "opus universal provider catalog invalid"
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
    direct = str(
        profile.get(
            "api_base"
        )
        or ""
    ).strip()

    if direct:
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
            _env(
                value
            )
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

    if (
        protocol
        == "bedrock_converse"
    ):
        return (
            native_text.profile_available(
                {
                    **profile,
                    "profile_id":
                        profile_id,
                }
            )
        )

    if (
        protocol
        == "ollama_chat"
    ):
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

    return sorted(
        result
    )


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

    projection = (
        load_projection()
    )

    if not isinstance(
        projection,
        dict,
    ):
        return False

    admitted = projection.get(
        "admitted_profiles"
    )

    return bool(
        isinstance(
            admitted,
            list,
        )
        and admitted
    )


def _admitted_candidates(
    profiles: Dict[str, Any],
) -> tuple[
    list[str],
    dict[str, str],
    str | None,
]:
    projection = (
        load_projection()
    )

    if not isinstance(
        projection,
        dict,
    ):
        return (
            [],
            {},
            None,
        )

    admitted_profiles = (
        projection.get(
            "admitted_profiles"
        )
    )

    admitted_models = (
        projection.get(
            "admitted_models"
        )
    )

    if not isinstance(
        admitted_profiles,
        list,
    ):
        return (
            [],
            {},
            None,
        )

    if not isinstance(
        admitted_models,
        dict,
    ):
        admitted_models = {}

    candidates: list[str] = []

    models: dict[
        str,
        str,
    ] = {}

    for value in admitted_profiles:
        profile_id = str(
            value
            or ""
        ).strip()

        if not profile_id:
            continue

        profile = profiles.get(
            profile_id
        )

        if not isinstance(
            profile,
            dict,
        ):
            continue

        if not _profile_configured(
            profile_id,
            profile,
            automatic=True,
        ):
            continue

        candidates.append(
            profile_id
        )

        model = str(
            admitted_models.get(
                profile_id
            )
            or ""
        ).strip()

        if model:
            models[
                profile_id
            ] = model

    return (
        candidates,
        models,
        str(
            projection.get(
                "digest"
            )
            or ""
        ).strip()
        or None,
    )


def _selection_candidates(
    request: Dict[str, Any],
) -> tuple[
    list[
        tuple[
            str,
            Dict[str, Any],
            str | None,
        ]
    ],
    str | None,
    bool,
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
            [
                (
                    requested,
                    dict(
                        profile
                    ),
                    None,
                )
            ],
            None,
            True,
        )

    (
        admitted,
        admitted_models,
        admission_digest,
    ) = _admitted_candidates(
        profiles
    )

    if not admitted:
        raise ProviderError(
            "no admitted opus catalog "
            "provider projection available"
        )

    return (
        [
            (
                profile_id,
                dict(
                    profiles[
                        profile_id
                    ]
                ),
                admitted_models.get(
                    profile_id
                ),
            )
            for profile_id
            in admitted
        ],
        admission_digest,
        False,
    )


def _infer_profile(
    request: Dict[str, Any],
    provider: Dict[str, Any],
    *,
    profile_id: str,
    profile: Dict[str, Any],
    admitted_model: str | None,
) -> Dict[str, Any]:
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

    if (
        not str(
            delegated.get(
                "model"
            )
            or delegated.get(
                "requested_model"
            )
            or ""
        ).strip()
        and admitted_model
    ):
        delegated[
            "model"
        ] = admitted_model

    if protocol in NATIVE_PROTOCOLS:
        return native_text.infer(
            delegated,
            provider,
            profile,
        )

    if protocol in UNIVERSAL_PROTOCOLS:
        return universal_text.infer(
            delegated,
            provider,
        )

    raise ProviderError(
        "unsupported catalog protocol: "
        f"{protocol}"
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
        candidates,
        admission_digest,
        explicit_selection,
    ) = _selection_candidates(
        request
    )

    attempts: list[
        dict[str, Any]
    ] = []

    last_error: (
        Exception
        | None
    ) = None

    for (
        profile_id,
        profile,
        admitted_model,
    ) in candidates:
        try:
            result = _infer_profile(
                request,
                provider,
                profile_id=(
                    profile_id
                ),
                profile=profile,
                admitted_model=(
                    admitted_model
                ),
            )

        except Exception as exc:
            last_error = exc

            attempts.append(
                {
                    "profile_id":
                        profile_id,
                    "state":
                        "failed",
                    "error_type":
                        type(
                            exc
                        ).__name__,
                }
            )

            if explicit_selection:
                raise

            continue

        if not isinstance(
            result,
            dict,
        ):
            last_error = ProviderError(
                "catalog provider returned "
                "non-object result"
            )

            attempts.append(
                {
                    "profile_id":
                        profile_id,
                    "state":
                        "failed",
                    "error_type":
                        "ProviderError",
                }
            )

            if explicit_selection:
                raise last_error

            continue

        attempts.append(
            {
                "profile_id":
                    profile_id,
                "state":
                    "succeeded",
                "model":
                    (
                        result.get(
                            "model"
                        )
                        or admitted_model
                    ),
            }
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

        result[
            "catalog_attempts"
        ] = attempts

        result[
            "admission_selected"
        ] = bool(
            admission_digest
        )

        if admission_digest:
            result[
                "admission_projection_digest"
            ] = admission_digest

        return result

    if last_error is not None:
        raise ProviderError(
            "all admitted opus catalog "
            "provider profiles failed"
        ) from last_error

    raise ProviderError(
        "no admitted opus catalog "
        "provider could be executed"
    )

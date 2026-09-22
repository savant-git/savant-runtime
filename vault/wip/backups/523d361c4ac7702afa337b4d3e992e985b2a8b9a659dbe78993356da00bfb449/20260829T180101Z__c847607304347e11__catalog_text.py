#!/usr/bin/env python3

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from providers.base import ProviderError
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
    "savant.opus.catalog-text.v1"
)

OWNER = "opus"


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
    name: Any,
) -> str:
    key = str(
        name or ""
    ).strip()

    if not key:
        return ""

    return str(
        os.getenv(
            key,
            ""
        )
        or ""
    ).strip()


def _credential_available(
    profile: Dict[str, Any],
) -> bool:
    if bool(
        profile.get(
            "api_key_optional",
            False,
        )
    ):
        return True

    primary = _env(
        profile.get(
            "api_key_env"
        )
    )

    if primary:
        return True

    fallback = _env(
        profile.get(
            "api_key_env_fallback"
        )
    )

    return bool(
        fallback
    )


def _base_available(
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


def _model_available(
    profile: Dict[str, Any],
) -> bool:
    direct = str(
        profile.get(
            "model_default"
        )
        or ""
    ).strip()

    if direct:
        return True

    return bool(
        _env(
            profile.get(
                "model_env"
            )
        )
    )


def _profile_eligible(
    profile_id: str,
    profile: Dict[str, Any],
    *,
    automatic: bool,
) -> bool:
    if str(
        profile.get(
            "status",
            "active",
        )
    ).strip().lower() not in {
        "active",
        "enabled",
    }:
        return False

    if not _base_available(
        profile
    ):
        return False

    if not _credential_available(
        profile
    ):
        return False

    if not _model_available(
        profile
    ):
        return False

    if (
        automatic
        and bool(
            profile.get(
                "api_key_optional",
                False,
            )
        )
        and not bool(
            profile.get(
                "automatic_local",
                False,
            )
        )
    ):
        return False

    if (
        automatic
        and profile_id
        == "custom"
    ):
        return False

    return True


def available_profiles() -> list[str]:
    profiles = _catalog()[
        "profiles"
    ]

    result: list[str] = []

    for profile_id, profile in profiles.items():
        if not isinstance(
            profile,
            dict,
        ):
            continue

        if _profile_eligible(
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
    explicit = str(
        os.getenv(
            EXPLICIT_PROFILE_ENV,
            ""
        )
        or ""
    ).strip()

    if explicit:
        profiles = _catalog()[
            "profiles"
        ]

        profile = profiles.get(
            explicit
        )

        return (
            isinstance(
                profile,
                dict,
            )
            and _profile_eligible(
                explicit,
                profile,
                automatic=False,
            )
        )

    return bool(
        available_profiles()
    )


def _select_profile(
    request: Dict[str, Any],
) -> str:
    requested = str(
        request.get(
            "provider_profile"
        )
        or os.getenv(
            EXPLICIT_PROFILE_ENV,
            ""
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

        if not _profile_eligible(
            requested,
            profile,
            automatic=False,
        ):
            raise ProviderError(
                "opus provider profile unavailable: "
                f"{requested}"
            )

        return requested

    available_ids = (
        available_profiles()
    )

    if not available_ids:
        raise ProviderError(
            "no configured opus catalog provider available"
        )

    return available_ids[
        0
    ]


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

    selected_profile = (
        _select_profile(
            request
        )
    )

    delegated_request = dict(
        request
    )

    delegated_request[
        "provider_profile"
    ] = selected_profile

    result = universal_text.infer(
        delegated_request,
        provider,
    )

    if not isinstance(
        result,
        dict,
    ):
        raise ProviderError(
            "universal provider returned "
            "non-object result"
        )

    result[
        "provider"
    ] = "catalog_text"

    result[
        "provider_profile"
    ] = selected_profile

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

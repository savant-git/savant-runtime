#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict

from .environment import load_environment


SCHEMA = "savant.opus.model-discovery.v1"
OWNER = "opus"

OPUS_ROOT = Path(
    __file__
).resolve().parents[1]

CATALOG_PATH = (
    OPUS_ROOT
    / "registry"
    / "providers"
    / "universal_text_catalog.json"
)


class ModelDiscoveryError(
    RuntimeError
):
    pass


def _catalog() -> Dict[str, Any]:
    value = json.loads(
        CATALOG_PATH.read_text(
            encoding="utf-8"
        )
    )

    profiles = value.get(
        "profiles"
    )

    if not isinstance(
        profiles,
        dict,
    ):
        raise ModelDiscoveryError(
            "provider catalog profiles missing"
        )

    return value


def _env(
    name: Any,
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


def _base(
    profile: Dict[str, Any],
) -> str:
    env_name = str(
        profile.get(
            "api_base_env"
        )
        or ""
    ).strip()

    value = (
        _env(
            env_name
        )
        if env_name
        else ""
    )

    return str(
        value
        or profile.get(
            "api_base"
        )
        or ""
    ).strip().rstrip("/")


def _credential(
    profile: Dict[str, Any],
) -> str:
    value = _env(
        profile.get(
            "api_key_env"
        )
    )

    if value:
        return value

    return _env(
        profile.get(
            "api_key_env_fallback"
        )
    )


def _headers(
    profile: Dict[str, Any],
) -> Dict[str, str]:
    result = {
        "Accept": "application/json",
    }

    header_env = profile.get(
        "header_env"
    )

    if isinstance(
        header_env,
        dict,
    ):
        for header, env_name in (
            header_env.items()
        ):
            value = _env(
                env_name
            )

            if value:
                result[
                    str(
                        header
                    )
                ] = value

    key = _credential(
        profile
    )

    protocol = str(
        profile.get(
            "protocol"
        )
        or ""
    ).lower()

    if key:
        if protocol == "anthropic_messages":
            result[
                "x-api-key"
            ] = key

            result[
                "anthropic-version"
            ] = str(
                profile.get(
                    "anthropic_version"
                )
                or "2023-06-01"
            )

        elif protocol != "gemini_generate_content":
            result[
                "Authorization"
            ] = (
                "Bearer "
                + key
            )

    return result


def _safe_get_json(
    url: str,
    headers: Dict[str, str],
    timeout: int,
) -> Dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers=headers,
        method="GET",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
            context=ssl.create_default_context(),
        ) as response:
            raw = response.read().decode(
                "utf-8"
            )

    except urllib.error.HTTPError as exc:
        raise ModelDiscoveryError(
            "model discovery http failure: "
            f"{exc.code}"
        ) from exc

    except urllib.error.URLError as exc:
        raise ModelDiscoveryError(
            "model discovery network failure: "
            f"{type(exc.reason).__name__}"
        ) from exc

    except TimeoutError as exc:
        raise ModelDiscoveryError(
            "model discovery timeout"
        ) from exc

    except Exception as exc:
        raise ModelDiscoveryError(
            "model discovery request failure: "
            f"{type(exc).__name__}"
        ) from exc

    try:
        value = json.loads(
            raw
        )
    except json.JSONDecodeError as exc:
        raise ModelDiscoveryError(
            "model discovery returned invalid json"
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise ModelDiscoveryError(
            "model discovery response must be object"
        )

    return value


def _extract_ids(
    value: Dict[str, Any],
) -> list[str]:
    candidates = (
        value.get(
            "data"
        )
        or value.get(
            "models"
        )
        or []
    )

    if not isinstance(
        candidates,
        list,
    ):
        return []

    result: set[str] = set()

    for row in candidates:
        if isinstance(
            row,
            str,
        ):
            identifier = row

        elif isinstance(
            row,
            dict,
        ):
            identifier = str(
                row.get(
                    "id"
                )
                or row.get(
                    "name"
                )
                or row.get(
                    "model"
                )
                or ""
            )

        else:
            continue

        identifier = (
            identifier.strip()
        )

        if identifier.startswith(
            "models/"
        ):
            identifier = identifier[
                len(
                    "models/"
                ):
            ]

        if identifier:
            result.add(
                identifier
            )

    return sorted(
        result
    )


def _model_url(
    profile: Dict[str, Any],
) -> str | None:
    base = _base(
        profile
    )

    if not base:
        return None

    protocol = str(
        profile.get(
            "protocol"
        )
        or ""
    ).strip().lower()

    if protocol in {
        "openai_chat",
        "openai_responses",
    }:
        return (
            base
            + "/models"
        )

    if protocol == "gemini_generate_content":
        key = _credential(
            profile
        )

        if not key:
            return None

        return (
            base
            + "/models?key="
            + urllib.parse.quote(
                key,
                safe="",
            )
        )

    return None


def discover(
    profile_id: str,
    *,
    timeout_seconds: int = 15,
) -> Dict[str, Any]:
    load_environment()

    catalog = _catalog()

    profile = catalog[
        "profiles"
    ].get(
        profile_id
    )

    if not isinstance(
        profile,
        dict,
    ):
        raise ModelDiscoveryError(
            "unknown provider profile: "
            f"{profile_id}"
        )

    configured_model = _env(
        profile.get(
            "model_env"
        )
    )

    default_model = str(
        profile.get(
            "model_default"
        )
        or ""
    ).strip()

    if configured_model:
        return {
            "schema": SCHEMA,
            "owner": OWNER,
            "profile_id": profile_id,
            "state": "configured",
            "selected_model":
                configured_model,
            "models": [
                configured_model
            ],
            "authority_effect": "none",
        }

    if default_model:
        return {
            "schema": SCHEMA,
            "owner": OWNER,
            "profile_id": profile_id,
            "state": "default",
            "selected_model":
                default_model,
            "models": [
                default_model
            ],
            "authority_effect": "none",
        }

    url = _model_url(
        profile
    )

    if not url:
        return {
            "schema": SCHEMA,
            "owner": OWNER,
            "profile_id": profile_id,
            "state":
                "discovery_unsupported",
            "selected_model": None,
            "models": [],
            "authority_effect": "none",
        }

    try:
        value = _safe_get_json(
            url,
            _headers(
                profile
            ),
            max(
                1,
                min(
                    int(
                        timeout_seconds
                    ),
                    60,
                ),
            ),
        )

    except Exception as exc:
        return {
            "schema": SCHEMA,
            "owner": OWNER,
            "profile_id": profile_id,
            "state":
                "discovery_failed",
            "selected_model": None,
            "models": [],
            "diagnostic": (
                f"{type(exc).__name__}: "
                f"{str(exc)}"
            )[:300],
            "credential_values_exposed":
                False,
            "authority_effect": "none",
        }

    models = _extract_ids(
        value
    )

    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "profile_id": profile_id,
        "state": (
            "discovered"
            if models
            else "no_models"
        ),
        "selected_model": (
            models[0]
            if models
            else None
        ),
        "models": models,
        "model_count": len(
            models
        ),
        "credential_values_exposed":
            False,
        "authority_effect": "none",
    }

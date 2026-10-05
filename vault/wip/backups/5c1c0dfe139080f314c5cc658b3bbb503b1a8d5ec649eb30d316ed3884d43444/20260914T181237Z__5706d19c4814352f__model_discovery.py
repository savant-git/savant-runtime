#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict

from .environment import load_environment


SCHEMA = "savant.opus.model-discovery.v3"
OWNER = "opus"

OPUS_ROOT = Path(__file__).resolve().parents[1]

CATALOG_PATH = (
    OPUS_ROOT
    / "registry"
    / "providers"
    / "universal_text_catalog.json"
)


_EXCLUDED_MARKERS = (
    "audio",
    "embedding",
    "image",
    "moderation",
    "realtime",
    "speech",
    "transcribe",
    "tts",
    "whisper",
    "sora",
    "gpt-live",
)

_DEPRIORITIZED_MARKERS = (
    "search",
    "deep-research",
    "codex",
)

_PREVIEW_MARKERS = (
    "preview",
    "experimental",
    "-exp",
)

_LEGACY_MARKERS = (
    "babbage",
    "davinci",
)

_TIER_SCORE = {
    "pro": 50,
    "sol": 45,
    "astra": 44,
    "terra": 40,
    "latest": 35,
    "luna": 30,
    "max": 25,
    "mini": -20,
    "nano": -30,
}

_GPT_DOTTED_VERSION_RE = re.compile(
    r"(?:^|[-_])gpt[-_]?(\d+)(?:\.(\d+))?"
)

_OPENAI_COMPACT_VERSION_RE = re.compile(
    r"(?:^|[-_])gpt[-_]?(\d)(\d)(?:[-_]|$)"
)

_DATE_RE = re.compile(
    r"(20\d{2})[-_](\d{2})[-_](\d{2})"
)


class ModelDiscoveryError(RuntimeError):
    pass


def _catalog() -> Dict[str, Any]:
    try:
        value = json.loads(
            CATALOG_PATH.read_text(
                encoding="utf-8"
            )
        )
    except FileNotFoundError as exc:
        raise ModelDiscoveryError(
            "provider catalog missing"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ModelDiscoveryError(
            "provider catalog invalid"
        ) from exc

    if not isinstance(value, dict):
        raise ModelDiscoveryError(
            "provider catalog must be an object"
        )

    profiles = value.get("profiles")

    if not isinstance(profiles, dict):
        raise ModelDiscoveryError(
            "provider catalog profiles missing"
        )

    return value


def _env(name: Any) -> str:
    key = str(name or "").strip()

    if not key:
        return ""

    return str(
        os.getenv(key, "") or ""
    ).strip()


def _base(profile: Dict[str, Any]) -> str:
    env_name = str(
        profile.get("api_base_env") or ""
    ).strip()

    configured = (
        _env(env_name)
        if env_name
        else ""
    )

    return str(
        configured
        or profile.get("api_base")
        or ""
    ).strip().rstrip("/")


def _credential(profile: Dict[str, Any]) -> str:
    primary = _env(
        profile.get("api_key_env")
    )

    if primary:
        return primary

    return _env(
        profile.get("api_key_env_fallback")
    )


def _headers(
    profile: Dict[str, Any],
) -> Dict[str, str]:
    result: Dict[str, str] = {
        "Accept": "application/json",
    }

    header_env = profile.get("header_env")

    if isinstance(header_env, dict):
        for header, env_name in header_env.items():
            value = _env(env_name)

            if value:
                result[str(header)] = value

    key = _credential(profile)

    protocol = str(
        profile.get("protocol") or ""
    ).strip().lower()

    if key:
        if protocol == "anthropic_messages":
            result["x-api-key"] = key
            result["anthropic-version"] = str(
                profile.get("anthropic_version")
                or "2023-06-01"
            )
        elif protocol != "gemini_generate_content":
            result["Authorization"] = (
                "Bearer " + key
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
            raw = response.read().decode("utf-8")

    except urllib.error.HTTPError as exc:
        raise ModelDiscoveryError(
            f"model discovery http failure: {exc.code}"
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
        value = json.loads(raw)

    except json.JSONDecodeError as exc:
        raise ModelDiscoveryError(
            "model discovery returned invalid json"
        ) from exc

    if not isinstance(value, dict):
        raise ModelDiscoveryError(
            "model discovery response must be object"
        )

    return value


def _extract_ids(
    value: Dict[str, Any],
) -> list[str]:
    candidates = (
        value.get("data")
        or value.get("models")
        or []
    )

    if not isinstance(candidates, list):
        return []

    result: set[str] = set()

    for row in candidates:
        if isinstance(row, str):
            identifier = row

        elif isinstance(row, dict):
            identifier = str(
                row.get("id")
                or row.get("name")
                or row.get("model")
                or ""
            )

        else:
            continue

        identifier = identifier.strip()

        if identifier.startswith("models/"):
            identifier = identifier[len("models/"):]

        if identifier:
            result.add(identifier)

    return sorted(result)


def _model_url(
    profile: Dict[str, Any],
) -> str | None:
    base = _base(profile)

    if not base:
        return None

    protocol = str(
        profile.get("protocol") or ""
    ).strip().lower()

    if protocol in {
        "openai_chat",
        "openai_responses",
    }:
        return base + "/models"

    if protocol == "gemini_generate_content":
        key = _credential(profile)

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


def _gpt_version(
    model_id: str,
) -> tuple[int, int]:
    text = model

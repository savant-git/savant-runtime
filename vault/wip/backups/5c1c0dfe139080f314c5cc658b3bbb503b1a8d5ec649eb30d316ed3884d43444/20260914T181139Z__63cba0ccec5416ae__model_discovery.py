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

_GPT_VERSION_RE = re.compile(
    r"(?:^|[-_])gpt[-_]?(\d+)(?:[._-](\d+))?"
)

_OPENAI_COMPACT_VERSION_RE = re.compile(
    r"(?:^|[-_])gpt[-_]?(\d)(\d)(?:[-_]|$)"
)

_DATE_RE = re.compile(
    r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})"
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
    text = model_id.lower()

    match = _GPT_VERSION_RE.search(text)

    if match:
        return (
            int(match.group(1)),
            int(match.group(2) or 0),
        )

    compact = _OPENAI_COMPACT_VERSION_RE.search(
        text
    )

    if compact:
        return (
            int(compact.group(1)),
            int(compact.group(2)),
        )

    return (0, 0)


def _date_score(model_id: str) -> int:
    matches = _DATE_RE.findall(
        model_id.lower()
    )

    if not matches:
        return 0

    year, month, day = matches[-1]

    return (
        int(year) * 10000
        + int(month) * 100
        + int(day)
    )


def _tier_score(model_id: str) -> int:
    text = model_id.lower()

    score = 0

    for marker, value in _TIER_SCORE.items():
        if marker in text:
            score += value

    return score


def _is_text_candidate(
    model_id: str,
) -> bool:
    text = model_id.lower()

    if any(
        marker in text
        for marker in _EXCLUDED_MARKERS
    ):
        return False

    if text.startswith(
        (
            "text-embedding",
            "omni-moderation",
        )
    ):
        return False

    return True


def _family_score(
    model_id: str,
) -> int:
    text = model_id.lower()

    if "gpt" in text:
        return 100

    if "claude" in text:
        return 95

    if "gemini" in text:
        return 92

    if "deepseek" in text:
        return 90

    if "qwen" in text:
        return 88

    if "llama" in text:
        return 86

    if "mistral" in text:
        return 84

    if "command" in text:
        return 82

    if "sonar" in text:
        return 80

    return 50


def _rank_key(
    model_id: str,
) -> tuple[
    int,
    int,
    int,
    int,
    int,
    int,
    str,
]:
    text = model_id.lower()

    major, minor = _gpt_version(model_id)

    deprioritized = int(
        any(
            marker in text
            for marker in _DEPRIORITIZED_MARKERS
        )
    )

    preview = int(
        any(
            marker in text
            for marker in _PREVIEW_MARKERS
        )
    )

    return (
        major,
        minor,
        _family_score(model_id),
        _tier_score(model_id),
        _date_score(model_id),
        -deprioritized,
        -preview,
        text,
    )


def _score_model(
    model_id: str,
) -> int:
    major, minor = _gpt_version(model_id)

    return (
        major * 100000
        + minor * 1000
        + _family_score(model_id) * 10
        + _tier_score(model_id)
    )


def _rank_text_candidates(
    models: list[str],
) -> list[dict[str, Any]]:
    candidates = [
        model
        for model in models
        if _is_text_candidate(model)
    ]

    candidates.sort(
        key=_rank_key,
        reverse=True,
    )

    return [
        {
            "model": model,
            "score": _score_model(model),
        }
        for model in candidates
    ]


def _projection(
    *,
    profile_id: str,
    state: str,
    selected_model: str | None,
    selection_source: str | None,
    models: list[str],
    ranked: list[dict[str, Any]],
    diagnostic: dict[str, Any] | None = None,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "schema": SCHEMA,
        "owner": OWNER,
        "profile_id": profile_id,
        "state": state,
        "selected_model": selected_model,
        "selection_source": selection_source,
        "models": models,
        "model_count": len(models),
        "ranked_text_candidates": ranked,
        "credential_values_exposed": False,
        "authority_effect": "none",
    }

    if diagnostic:
        result["diagnostic"] = diagnostic

    return result


def discover(
    profile_id: str,
    *,
    timeout_seconds: int = 15,
) -> Dict[str, Any]:
    load_environment()

    catalog = _catalog()

    profile = catalog["profiles"].get(
        profile_id
    )

    if not isinstance(profile, dict):
        raise ModelDiscoveryError(
            "unknown provider profile: "
            f"{profile_id}"
        )

    configured_model = _env(
        profile.get("model_env")
    )

    default_model = str(
        profile.get("model_default") or ""
    ).strip()

    preferred_model = (
        configured_model
        or default_model
        or None
    )

    preferred_source = (
        "explicit_model_environment"
        if configured_model
        else (
            "catalog_default"
            if default_model
            else None
        )
    )

    discovered_models: list[str] = []

    discovery_error: (
        dict[str, Any] | None
    ) = None

    url = _model_url(profile)

    if url:
        try:
            value = _safe_get_json(
                url,
                _headers(profile),
                max(
                    1,
                    min(
                        int(timeout_seconds),
                        60,
                    ),
                ),
            )

            discovered_models = _extract_ids(
                value
            )
        except Exception as exc:
            discovery_error = {
                "error_type": type(exc).__name__,
                "failure_class": "discovery_failed",
            }

    models: list[str] = []

    if preferred_model:
        models.append(preferred_model)

    for model in discovered_models:
        if model not in models:
            models.append(model)

    discovered_ranked = (
        _rank_text_candidates(
            [
                model
                for model in models
                if (
                    not preferred_model
                    or model != preferred_model
                )
            ]
        )
    )

    ranked: list[dict[str, Any]] = []

    if preferred_model:
        ranked.append(
            {
                "model": preferred_model,
                "score": _score_model(
                    preferred_model
                ),
                "priority": preferred_source,
            }
        )

    ranked.extend(discovered_ranked)

    if preferred_model:
        selected_model = preferred_model
        state = (
            "configured"
            if configured_model
            else "default"
        )
        selection_source = preferred_source

    elif discovered_ranked:
        selected_model = str(
            discovered_ranked[0]["model"]
        )
        state = "discovered"
        selection_source = (
            "ranked_text_discovery"
        )

    elif url and discovery_error:
        selected_model = None
        state = "discovery_failed"
        selection_source = None

    elif url:
        selected_model = None
        state = "no_text_models"
        selection_source = None

    else:
        selected_model = None
        state = "discovery_unsupported"
        selection_source = None

    return _projection(
        profile_id=profile_id,
        state=state,
        selected_model=selected_model,
        selection_source=selection_source,
        models=models,
        ranked=ranked,
        diagnostic=discovery_error,
    )

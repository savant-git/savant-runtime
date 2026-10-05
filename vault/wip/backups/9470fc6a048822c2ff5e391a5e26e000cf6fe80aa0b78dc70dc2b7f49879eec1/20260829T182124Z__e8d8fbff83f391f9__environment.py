from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, Mapping


DEFAULT_ENV_PATHS = (
    Path("/root/.env"),
    Path("/root/savant-runtime/.env"),
)

OPUS_ROOT = Path(__file__).resolve().parents[1]

UNIVERSAL_CATALOG = (
    OPUS_ROOT
    / "registry"
    / "providers"
    / "universal_text_catalog.json"
)

_LOADED = False
_LOADED_PATHS: tuple[str, ...] = ()


def _parse_env_line(line: str) -> tuple[str, str] | None:
    raw = line.strip()

    if not raw or raw.startswith("#") or "=" not in raw:
        return None

    if raw.startswith("export "):
        raw = raw[7:].lstrip()

    key, value = raw.split("=", 1)
    key = key.strip()
    value = value.strip()

    if not key:
        return None

    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        value = value[1:-1]

    return key, value


def _stdlib_load(
    path: Path,
    *,
    override: bool,
) -> None:
    for line in path.read_text(
        encoding="utf-8",
        errors="ignore",
    ).splitlines():
        parsed = _parse_env_line(line)

        if parsed is None:
            continue

        key, value = parsed

        if override or key not in os.environ:
            os.environ[key] = value


def load_environment(
    paths: Iterable[Path] = DEFAULT_ENV_PATHS,
    *,
    override: bool = False,
    force: bool = False,
) -> tuple[str, ...]:
    global _LOADED
    global _LOADED_PATHS

    if _LOADED and not force:
        return _LOADED_PATHS

    candidates = tuple(Path(path) for path in paths)
    existing = tuple(path for path in candidates if path.is_file())

    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None

    for path in existing:
        if load_dotenv is not None:
            load_dotenv(
                dotenv_path=path,
                override=override,
            )
        else:
            _stdlib_load(
                path,
                override=override,
            )

    _LOADED_PATHS = tuple(str(path) for path in existing)
    _LOADED = True

    return _LOADED_PATHS


def get(
    name: str,
    default: str | None = None,
) -> str | None:
    load_environment()
    return os.getenv(name, default)


def first(
    *names: str,
) -> tuple[str | None, str | None]:
    load_environment()

    for name in names:
        value = os.getenv(name)

        if value:
            return name, value

    return None, None


def available(*names: str) -> bool:
    name, value = first(*names)
    return bool(name and value)


def availability(
    mapping: Mapping[str, Iterable[str]],
) -> dict[str, bool]:
    load_environment()

    return {
        provider: available(*tuple(keys))
        for provider, keys in mapping.items()
    }


def _env(name: object) -> str:
    key = str(name or "").strip()

    if not key:
        return ""

    return str(os.getenv(key, "") or "").strip()


def _catalog_profiles() -> dict[str, dict[str, object]]:
    if not UNIVERSAL_CATALOG.is_file():
        return {}

    try:
        value = json.loads(
            UNIVERSAL_CATALOG.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return {}

    profiles = value.get("profiles")

    if not isinstance(profiles, dict):
        return {}

    result: dict[str, dict[str, object]] = {}

    for profile_id, profile in profiles.items():
        if isinstance(profile, dict):
            result[str(profile_id)] = dict(profile)

    return result


def _model_available(
    profile: Mapping[str, object],
) -> bool:
    model_default = str(
        profile.get("model_default") or ""
    ).strip()

    if model_default:
        return True

    return bool(_env(profile.get("model_env")))


def _base_available(
    profile: Mapping[str, object],
) -> bool:
    direct = str(profile.get("api_base") or "").strip()

    if direct:
        return True

    return bool(_env(profile.get("api_base_env")))


def _credential_available(
    profile: Mapping[str, object],
) -> bool:
    if bool(profile.get("api_key_optional", False)):
        header_env = profile.get("header_env")

        if isinstance(header_env, dict):
            configured = [
                _env(value)
                for value in header_env.values()
            ]

            if any(configured):
                return True

        return True

    if _env(profile.get("api_key_env")):
        return True

    if _env(profile.get("api_key_env_fallback")):
        return True

    header_env = profile.get("header_env")

    if isinstance(header_env, dict):
        return any(
            _env(value)
            for value in header_env.values()
        )

    return False


def _bedrock_available(
    profile: Mapping[str, object],
) -> bool:
    if not _model_available(profile):
        return False

    region = (
        _env(profile.get("region_env"))
        or os.getenv("AWS_REGION", "")
        or os.getenv("AWS_DEFAULT_REGION", "")
    )

    if not str(region).strip():
        return False

    try:
        import boto3
    except ImportError:
        return False

    try:
        session = boto3.Session()
        return session.get_credentials() is not None
    except Exception:
        return False


def _profile_available(
    profile: Mapping[str, object],
) -> bool:
    protocol = str(
        profile.get("protocol") or ""
    ).strip().lower()

    if protocol == "bedrock_converse":
        return _bedrock_available(profile)

    if protocol == "ollama_chat":
        return (
            _base_available(profile)
            and _model_available(profile)
        )

    if protocol in {
        "cohere_chat",
        "replicate_prediction",
    }:
        return (
            _base_available(profile)
            and _credential_available(profile)
            and _model_available(profile)
        )

    if protocol in {
        "openai_responses",
        "openai_chat",
        "anthropic_messages",
        "gemini_generate_content",
        "generic_json",
    }:
        return (
            _base_available(profile)
            and _credential_available(profile)
            and _model_available(profile)
        )

    return False


def provider_availability() -> dict[str, bool]:
    load_environment()

    result = {
        "elevenlabs": bool(
            os.getenv("ELEVENLABS_SERVER_KEY")
            or os.getenv("ELEVENLABS_API_KEY")
        ),
    }

    for profile_id, profile in _catalog_profiles().items():
        result[profile_id] = _profile_available(profile)

    return dict(sorted(result.items()))


def status() -> dict[str, object]:
    load_environment()

    providers = provider_availability()

    available_ids = [
        provider_id
        for provider_id, state in providers.items()
        if state
    ]

    unavailable_ids = [
        provider_id
        for provider_id, state in providers.items()
        if not state
    ]

    return {
        "owner": "opus",
        "loaded_paths": list(_LOADED_PATHS),
        "providers": providers,
        "provider_count": len(providers),
        "available_provider_count": len(available_ids),
        "available_providers": available_ids,
        "unavailable_providers": unavailable_ids,
        "universal_catalog": str(UNIVERSAL_CATALOG),
        "universal_catalog_present": UNIVERSAL_CATALOG.is_file(),
        "provider_discovery": "registry_projection",
        "credential_values_exposed": False,
        "authority_effect": "none",
    }

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Mapping


DEFAULT_ENV_PATHS = (
    Path("/root/.env"),
    Path("/root/savant-runtime/.env"),
)

_LOADED = False
_LOADED_PATHS: tuple[str, ...] = ()


def _parse_env_line(
    line: str,
) -> tuple[str, str] | None:
    raw = line.strip()

    if (
        not raw
        or raw.startswith("#")
        or "=" not in raw
    ):
        return None

    if raw.startswith("export "):
        raw = raw[7:].lstrip()

    key, value = raw.split(
        "=",
        1,
    )

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
        parsed = _parse_env_line(
            line
        )

        if parsed is None:
            continue

        key, value = parsed

        if (
            override
            or key not in os.environ
        ):
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

    candidates = tuple(
        Path(path)
        for path in paths
    )

    existing = tuple(
        path
        for path in candidates
        if path.is_file()
    )

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

    _LOADED_PATHS = tuple(
        str(path)
        for path in existing
    )

    _LOADED = True

    return _LOADED_PATHS


def get(
    name: str,
    default: str | None = None,
) -> str | None:
    load_environment()

    return os.getenv(
        name,
        default,
    )


def first(
    *names: str,
) -> tuple[str | None, str | None]:
    load_environment()

    for name in names:
        value = os.getenv(
            name
        )

        if value:
            return name, value

    return None, None


def available(
    *names: str,
) -> bool:
    name, value = first(
        *names
    )

    return bool(
        name
        and value
    )


def availability(
    mapping: Mapping[
        str,
        Iterable[str],
    ],
) -> dict[str, bool]:
    load_environment()

    return {
        provider: available(
            *tuple(keys)
        )
        for provider, keys
        in mapping.items()
    }


def status() -> dict[str, object]:
    load_environment()

    return {
        "owner": "opus",
        "loaded_paths": list(
            _LOADED_PATHS
        ),
        "providers": availability(
            {
                "openai": (
                    "OPENAI_API_KEY",
                ),
                "anthropic": (
                    "ANTHROPIC_API_KEY",
                ),
                "google": (
                    "GOOGLE_API_KEY",
                    "GEMINI_API_KEY",
                ),
                "elevenlabs": (
                    "ELEVENLABS_SERVER_KEY",
                    "ELEVENLABS_API_KEY",
                ),
                "groq": (
                    "GROQ_API_KEY",
                ),
                "deepseek": (
                    "DEEPSEEK_API_KEY",
                ),
            }
        ),
        "credential_values_exposed": False,
        "authority_effect": "none",
    }

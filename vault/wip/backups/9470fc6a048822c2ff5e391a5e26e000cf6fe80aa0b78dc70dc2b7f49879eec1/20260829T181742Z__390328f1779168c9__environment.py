from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, Mapping


DEFAULT_ENV_PATHS = (
    Path("/root/.env"),
    Path("/root/savant-runtime/.env"),
)

OPUS_ROOT = Path(
    __file__
).resolve().parents[1]

UNIVERSAL_CATALOG = (
    OPUS_ROOT
    / "registry"
    / "providers"
    / "universal_text_catalog.json"
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

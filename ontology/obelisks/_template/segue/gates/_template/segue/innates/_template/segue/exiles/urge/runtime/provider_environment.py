
from __future__ import annotations

import os
import re
from pathlib import Path


schema = "savant://runtime/urge/provider-environment/1.0.0"

environment_file = Path("/root/.env")

_name = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class environment_error(RuntimeError):
    pass


def _parse(line: str) -> tuple[str, str] | None:
    value = line.strip()

    if not value or value.startswith("#"):
        return None

    if value.startswith("export "):
        value = value[7:].strip()

    if "=" not in value:
        raise environment_error(
            "invalid environment assignment"
        )

    name, raw = value.split("=", 1)
    name = name.strip()

    if not _name.fullmatch(name):
        raise environment_error(
            "invalid environment variable name"
        )

    raw = raw.strip()

    if raw.startswith(("'", '"')):
        quote = raw[0]

        if len(raw) < 2 or raw[-1] != quote:
            raise environment_error(
                "unterminated quoted value"
            )

        raw = raw[1:-1]

    return name, raw


def load(
    path: str | Path = environment_file,
    *,
    overwrite: bool = False,
) -> tuple[str, ...]:
    source = Path(path)

    if not source.is_file():
        raise environment_error(
            "credential environment file is unavailable"
        )

    if source.is_symlink():
        raise environment_error(
            "credential environment file cannot be a symlink"
        )

    permissions = source.stat().st_mode & 0o777

    if permissions & 0o077:
        raise environment_error(
            "credential environment file must be private"
        )

    try:
        content = source.read_text(
            encoding="utf-8"
        )
    except OSError as exc:
        raise environment_error(
            "unable to read credential environment file"
        ) from exc

    parsed: dict[str, str] = {}

    for number, line in enumerate(
        content.splitlines(),
        1,
    ):
        try:
            assignment = _parse(line)
        except environment_error as exc:
            raise environment_error(
                f"invalid environment entry at line {number}"
            ) from exc

        if assignment is None:
            continue

        name, value = assignment

        if name in parsed:
            raise environment_error(
                f"duplicate environment variable: {name}"
            )

        parsed[name] = value

    loaded = []

    for name, value in parsed.items():
        if overwrite or name not in os.environ:
            os.environ[name] = value
            loaded.append(name)

    return tuple(loaded)


def require(*names: str) -> tuple[str, ...]:
    missing = []

    for name in names:
        if not _name.fullmatch(name):
            raise environment_error(
                "invalid credential variable name"
            )

        if not os.environ.get(name):
            missing.append(name)

    if missing:
        raise environment_error(
            "required credentials are not configured: "
            + ", ".join(missing)
        )

    return names

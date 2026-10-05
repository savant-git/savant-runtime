from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import Profile


class ProfileError(RuntimeError):
    pass


def package_root() -> Path:
    return Path(__file__).resolve().parent.parent


def profiles_root() -> Path:
    return package_root() / "profiles"


def list_profiles() -> list[str]:
    root = profiles_root()
    if not root.is_dir():
        return []
    return sorted(path.stem for path in root.glob("*.json") if path.is_file())


def _string_set(value: Any, field: str) -> frozenset[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ProfileError(f"profile field {field!r} must be an array of strings")
    return frozenset(item.casefold() for item in value)


def _string_tuple(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ProfileError(f"profile field {field!r} must be an array of strings")
    return tuple(value)


def load_profile(name_or_path: str) -> Profile:
    candidate = Path(name_or_path).expanduser()
    if candidate.is_file():
        path = candidate.resolve()
    else:
        path = profiles_root() / f"{name_or_path}.json"

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        available = ", ".join(list_profiles()) or "none"
        raise ProfileError(
            f"profile not found: {name_or_path}; available profiles: {available}"
        ) from error
    except json.JSONDecodeError as error:
        raise ProfileError(f"invalid profile JSON in {path}: {error}") from error

    if not isinstance(payload, dict):
        raise ProfileError(f"profile must be a JSON object: {path}")

    required = {
        "id",
        "description",
        "include_extensions",
        "include_filenames",
        "canon_path_names",
        "exclude_dir_names",
        "exclude_file_names",
        "exclude_extensions",
        "exclude_patterns",
        "secret_file_patterns",
        "max_file_bytes",
        "max_total_content_bytes",
        "max_files",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ProfileError(f"profile is missing required fields: {', '.join(missing)}")

    for numeric in ("max_file_bytes", "max_total_content_bytes", "max_files"):
        if not isinstance(payload[numeric], int) or payload[numeric] < 1:
            raise ProfileError(f"profile field {numeric!r} must be a positive integer")

    return Profile(
        id=str(payload["id"]),
        description=str(payload["description"]),
        include_extensions=_string_set(payload["include_extensions"], "include_extensions"),
        include_filenames=_string_set(payload["include_filenames"], "include_filenames"),
        canon_path_names=_string_set(payload["canon_path_names"], "canon_path_names"),
        exclude_dir_names=_string_set(payload["exclude_dir_names"], "exclude_dir_names"),
        exclude_file_names=_string_set(payload["exclude_file_names"], "exclude_file_names"),
        exclude_extensions=_string_set(payload["exclude_extensions"], "exclude_extensions"),
        exclude_patterns=_string_tuple(payload["exclude_patterns"], "exclude_patterns"),
        secret_file_patterns=_string_tuple(payload["secret_file_patterns"], "secret_file_patterns"),
        max_file_bytes=payload["max_file_bytes"],
        max_total_content_bytes=payload["max_total_content_bytes"],
        max_files=payload["max_files"],
        include_tree=bool(payload.get("include_tree", False)),
        include_inventory=bool(payload.get("include_inventory", False)),
        respect_gitignore=bool(payload.get("respect_gitignore", True)),
        redact_secrets=bool(payload.get("redact_secrets", True)),
        follow_symlinks=bool(payload.get("follow_symlinks", False)),
    )

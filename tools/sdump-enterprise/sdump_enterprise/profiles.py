from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import Profile


class ProfileError(
    RuntimeError
):
    pass


def package_root() -> Path:
    return (
        Path(
            __file__
        )
        .resolve()
        .parent
        .parent
    )


def profiles_root() -> Path:
    return (
        package_root()
        / "profiles"
    )


def list_profiles() -> list[
    str
]:
    root = profiles_root()

    if not root.is_dir():
        return []

    return sorted(
        path.stem
        for path in root.glob(
            "*.json"
        )
        if path.is_file()
    )


def _string_set(
    value: Any,
    field: str,
) -> frozenset[
    str
]:
    if (
        not isinstance(
            value,
            list,
        )
        or not all(
            isinstance(
                item,
                str,
            )
            for item in value
        )
    ):
        raise ProfileError(
            "profile field "
            f"{field!r} must be "
            "an array of strings"
        )

    return frozenset(
        item.casefold()
        for item in value
    )


def _string_tuple(
    value: Any,
    field: str,
) -> tuple[
    str,
    ...,
]:
    if (
        not isinstance(
            value,
            list,
        )
        or not all(
            isinstance(
                item,
                str,
            )
            for item in value
        )
    ):
        raise ProfileError(
            "profile field "
            f"{field!r} must be "
            "an array of strings"
        )

    return tuple(
        value
    )


def _optional_string_set(
    payload: dict[
        str,
        Any,
    ],
    field: str,
) -> frozenset[
    str
]:
    return _string_set(
        payload.get(
            field,
            [],
        ),
        field,
    )


def _optional_string_tuple(
    payload: dict[
        str,
        Any,
    ],
    field: str,
) -> tuple[
    str,
    ...,
]:
    return _string_tuple(
        payload.get(
            field,
            [],
        ),
        field,
    )


def _positive_int(
    payload: dict[
        str,
        Any,
    ],
    field: str,
) -> int:
    value = payload[
        field
    ]

    if (
        not isinstance(
            value,
            int,
        )
        or value < 1
    ):
        raise ProfileError(
            "profile field "
            f"{field!r} must be "
            "a positive integer"
        )

    return value


def _non_negative_int(
    payload: dict[
        str,
        Any,
    ],
    field: str,
    default: int,
) -> int:
    value = payload.get(
        field,
        default,
    )

    if (
        not isinstance(
            value,
            int,
        )
        or value < 0
    ):
        raise ProfileError(
            "profile field "
            f"{field!r} must be "
            "a non-negative integer"
        )

    return value


def load_profile(
    name_or_path: str,
) -> Profile:
    candidate = Path(
        name_or_path
    ).expanduser()

    if candidate.is_file():
        path = (
            candidate.resolve()
        )
    else:
        path = (
            profiles_root()
            / f"{name_or_path}.json"
        )

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except FileNotFoundError as error:
        available = (
            ", ".join(
                list_profiles()
            )
            or "none"
        )

        raise ProfileError(
            "profile not found: "
            f"{name_or_path}; "
            "available profiles: "
            f"{available}"
        ) from error

    except json.JSONDecodeError as error:
        raise ProfileError(
            "invalid profile JSON "
            f"in {path}: {error}"
        ) from error

    if not isinstance(
        payload,
        dict,
    ):
        raise ProfileError(
            "profile must be a "
            f"JSON object: {path}"
        )

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

    missing = sorted(
        required
        - payload.keys()
    )

    if missing:
        raise ProfileError(
            "profile is missing "
            "required fields: "
            + ", ".join(
                missing
            )
        )

    try:
        return Profile(
            id=str(
                payload[
                    "id"
                ]
            ).casefold(),
            description=str(
                payload[
                    "description"
                ]
            ),
            include_extensions=(
                _string_set(
                    payload[
                        "include_extensions"
                    ],
                    "include_extensions",
                )
            ),
            include_filenames=(
                _string_set(
                    payload[
                        "include_filenames"
                    ],
                    "include_filenames",
                )
            ),
            canon_path_names=(
                _string_set(
                    payload[
                        "canon_path_names"
                    ],
                    "canon_path_names",
                )
            ),
            exclude_dir_names=(
                _string_set(
                    payload[
                        "exclude_dir_names"
                    ],
                    "exclude_dir_names",
                )
            ),
            exclude_file_names=(
                _string_set(
                    payload[
                        "exclude_file_names"
                    ],
                    "exclude_file_names",
                )
            ),
            exclude_extensions=(
                _string_set(
                    payload[
                        "exclude_extensions"
                    ],
                    "exclude_extensions",
                )
            ),
            exclude_patterns=(
                _string_tuple(
                    payload[
                        "exclude_patterns"
                    ],
                    "exclude_patterns",
                )
            ),
            secret_file_patterns=(
                _string_tuple(
                    payload[
                        "secret_file_patterns"
                    ],
                    "secret_file_patterns",
                )
            ),
            max_file_bytes=(
                _positive_int(
                    payload,
                    "max_file_bytes",
                )
            ),
            max_total_content_bytes=(
                _positive_int(
                    payload,
                    "max_total_content_bytes",
                )
            ),
            max_files=(
                _positive_int(
                    payload,
                    "max_files",
                )
            ),
            include_tree=bool(
                payload.get(
                    "include_tree",
                    False,
                )
            ),
            include_inventory=bool(
                payload.get(
                    "include_inventory",
                    False,
                )
            ),
            respect_gitignore=bool(
                payload.get(
                    "respect_gitignore",
                    True,
                )
            ),
            redact_secrets=bool(
                payload.get(
                    "redact_secrets",
                    True,
                )
            ),
            follow_symlinks=bool(
                payload.get(
                    "follow_symlinks",
                    False,
                )
            ),
            budget_strategy=str(
                payload.get(
                    "budget_strategy",
                    "path_order",
                )
            ).casefold(),
            critical_path_prefixes=(
                _optional_string_tuple(
                    payload,
                    "critical_path_prefixes",
                )
            ),
            priority_path_prefixes=(
                _optional_string_tuple(
                    payload,
                    "priority_path_prefixes",
                )
            ),
            deprioritized_path_fragments=(
                _optional_string_tuple(
                    payload,
                    "deprioritized_path_fragments",
                )
            ),
            priority_filenames=(
                _optional_string_set(
                    payload,
                    "priority_filenames",
                )
            ),
            recent_window_days=(
                _non_negative_int(
                    payload,
                    "recent_window_days",
                    30,
                )
            ),
            very_recent_window_days=(
                _non_negative_int(
                    payload,
                    "very_recent_window_days",
                    7,
                )
            ),
            small_file_bonus_bytes=(
                _non_negative_int(
                    payload,
                    "small_file_bonus_bytes",
                    (
                        64
                        * 1024
                    ),
                )
            ),
            metadata_only_on_budget_exhaustion=(
                bool(
                    payload.get(
                        "metadata_only_on_budget_exhaustion",
                        True,
                    )
                )
            ),
        )

    except ValueError as error:
        raise ProfileError(
            "invalid profile "
            f"{path}: {error}"
        ) from error

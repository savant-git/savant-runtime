#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping


SCHEMA = (
    "savant.opus."
    "admission-projection.v1"
)

OWNER = "opus"

SAVANT_ROOT = Path(
    os.getenv(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
)

STATE_PATH = (
    SAVANT_ROOT
    / "runtime"
    / "state"
    / "opus"
    / "provider-admission.json"
)


class AdmissionProjectionError(
    RuntimeError
):
    pass


def _canonical(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode(
        "utf-8"
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        _canonical(
            value
        )
    ).hexdigest()


def normalize_projection(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    admitted_profiles_raw = (
        value.get(
            "admitted_profiles",
            [],
        )
    )

    admitted_profiles: list[str] = []

    if isinstance(
        admitted_profiles_raw,
        list,
    ):
        for item in admitted_profiles_raw:
            profile_id = str(
                item
                or ""
            ).strip()

            if (
                profile_id
                and profile_id
                not in admitted_profiles
            ):
                admitted_profiles.append(
                    profile_id
                )

    admitted_models_raw = (
        value.get(
            "admitted_models",
            {},
        )
    )

    admitted_models: dict[
        str,
        str,
    ] = {}

    if isinstance(
        admitted_models_raw,
        Mapping,
    ):
        for (
            profile_id,
            model_id,
        ) in admitted_models_raw.items():
            profile = str(
                profile_id
                or ""
            ).strip()

            model = str(
                model_id
                or ""
            ).strip()

            if (
                profile
                and model
                and profile
                in admitted_profiles
            ):
                admitted_models[
                    profile
                ] = model

    normalized = {
        "schema":
            SCHEMA,
        "owner":
            OWNER,
        "projection_type":
            "provider_admission",
        "admitted_profiles":
            admitted_profiles,
        "admitted_models":
            admitted_models,
        "credential_values_exposed":
            False,
        "authority_effect":
            "none",
        "source_schema":
            str(
                value.get(
                    "schema"
                )
                or ""
            ),
        "source_digest":
            str(
                value.get(
                    "digest"
                )
                or ""
            ),
    }

    normalized[
        "digest"
    ] = digest(
        normalized
    )

    return normalized


def write_projection(
    value: Mapping[str, Any],
    *,
    path: Path = STATE_PATH,
) -> dict[str, Any]:
    projection = (
        normalize_projection(
            value
        )
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        fd,
        temp_name,
    ) = tempfile.mkstemp(
        prefix=".provider-admission.",
        suffix=".tmp",
        dir=str(
            path.parent
        ),
        text=True,
    )

    temp_path = Path(
        temp_name
    )

    try:
        os.fchmod(
            fd,
            0o600,
        )

        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                projection,
                handle,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )

            handle.write(
                "\n"
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.replace(
            temp_path,
            path,
        )

        os.chmod(
            path,
            0o600,
        )

    finally:
        if temp_path.exists():
            temp_path.unlink()

    return {
        **projection,
        "projection_path":
            str(
                path
            ),
    }


def load_projection(
    *,
    path: Path = STATE_PATH,
) -> dict[str, Any] | None:
    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except (
        FileNotFoundError,
        OSError,
        json.JSONDecodeError,
    ):
        return None

    if not isinstance(
        value,
        dict,
    ):
        return None

    if (
        value.get(
            "schema"
        )
        != SCHEMA
    ):
        return None

    if (
        value.get(
            "owner"
        )
        != OWNER
    ):
        return None

    if (
        value.get(
            "authority_effect"
        )
        != "none"
    ):
        return None

    if (
        value.get(
            "credential_values_exposed"
        )
        is not False
    ):
        return None

    supplied_digest = str(
        value.get(
            "digest"
        )
        or ""
    )

    unsigned = dict(
        value
    )

    unsigned.pop(
        "digest",
        None,
    )

    if supplied_digest != digest(
        unsigned
    ):
        return None

    admitted_profiles = (
        value.get(
            "admitted_profiles"
        )
    )

    admitted_models = (
        value.get(
            "admitted_models"
        )
    )

    if not isinstance(
        admitted_profiles,
        list,
    ):
        return None

    if not isinstance(
        admitted_models,
        dict,
    ):
        return None

    return {
        **value,
        "projection_path":
            str(
                path
            ),
    }

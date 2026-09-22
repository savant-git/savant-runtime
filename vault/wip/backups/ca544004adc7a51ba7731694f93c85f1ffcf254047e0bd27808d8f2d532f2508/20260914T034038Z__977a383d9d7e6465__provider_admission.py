#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict

from .environment import load_environment
from .providers import catalog_text
from .providers.base import ProviderError


SCHEMA = "savant.opus.provider-admission.v1"
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

PLACEHOLDERS = {
    "",
    "replace_me",
    "changeme",
    "your_api_key",
    "your_actual_api_key",
    "your_key_here",
}


class ProviderAdmissionError(
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
    ).encode("utf-8")


def _digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        _canonical(value)
    ).hexdigest()


def _catalog() -> Dict[str, Any]:
    try:
        value = json.loads(
            CATALOG_PATH.read_text(
                encoding="utf-8"
            )
        )
    except FileNotFoundError as exc:
        raise ProviderAdmissionError(
            "opus universal provider catalog missing"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ProviderAdmissionError(
            "opus universal provider catalog invalid"
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise ProviderAdmissionError(
            "opus universal provider catalog must be an object"
        )

    profiles = value.get(
        "profiles"
    )

    if not isinstance(
        profiles,
        dict,
    ):
        raise ProviderAdmissionError(
            "opus universal provider catalog profiles missing"
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


def _credential_names(
    profile: Dict[str, Any],
) -> list[str]:
    names: set[str] = set()

    for field in (
        "api_key_env",
        "api_key_env_fallback",
    ):
        value = str(
            profile.get(
                field
            )
            or ""
        ).strip()

        if value:
            names.add(
                value
            )

    header_env = profile.get(
        "header_env"
    )

    if isinstance(
        header_env,
        dict,
    ):
        for value in header_env.values():
            name = str(
                value
                or ""
            ).strip()

            if name:
                names.add(
                    name
                )

    return sorted(
        names
    )


def _credential_state(
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    names = _credential_names(
        profile
    )

    present = []
    placeholder = []

    for name in names:
        value = _env(
            name
        )

        if value:
            present.append(
                name
            )

            if value.lower() in PLACEHOLDERS:
                placeholder.append(
                    name
                )

    optional = bool(
        profile.get(
            "api_key_optional",
            False,
        )
    )

    configured = (
        optional
        or bool(
            present
        )
    )

    return {
        "credential_names": names,
        "credential_present": bool(
            present
        ),
        "credential_present_names": sorted(
            present
        ),
        "credential_placeholder_names": sorted(
            placeholder
        ),
        "credential_optional": optional,
        "credential_configured": configured,
        "credential_values_exposed": False,
    }


def _base_state(
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    direct = str(
        profile.get(
            "api_base"
        )
        or ""
    ).strip()

    env_name = str(
        profile.get(
            "api_base_env"
        )
        or ""
    ).strip()

    env_value = _env(
        env_name
    )

    return {
        "api_base_declared": bool(
            direct
            or env_name
        ),
        "api_base_configured": bool(
            direct
            or env_value
        ),
        "api_base_env": (
            env_name
            or None
        ),
        "api_base_value_exposed": False,
    }


def _model_state(
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    model_env = str(
        profile.get(
            "model_env"
        )
        or ""
    ).strip()

    configured = (
        _env(
            model_env
        )
        if model_env
        else ""
    )

    default = str(
        profile.get(
            "model_default"
        )
        or ""
    ).strip()

    return {
        "model_env": (
            model_env
            or None
        ),
        "model_configured": bool(
            configured
            or default
        ),
        "model_source": (
            "environment"
            if configured
            else (
                "default"
                if default
                else "none"
            )
        ),
    }


def _configured(
    profile_id: str,
    profile: Dict[str, Any],
) -> bool:
    try:
        return profile_id in (
            catalog_text.available_profiles()
        )
    except Exception:
        return False


def configuration_projection() -> Dict[str, Any]:
    load_environment()

    catalog = _catalog()

    rows = []

    for profile_id in sorted(
        catalog[
            "profiles"
        ]
    ):
        profile = catalog[
            "profiles"
        ][
            profile_id
        ]

        if not isinstance(
            profile,
            dict,
        ):
            continue

        credential = _credential_state(
            profile
        )

        base = _base_state(
            profile
        )

        model = _model_state(
            profile
        )

        rows.append(
            {
                "profile_id": profile_id,
                "protocol": str(
                    profile.get(
                        "protocol"
                    )
                    or ""
                ),
                "configured": _configured(
                    profile_id,
                    profile,
                ),
                **credential,
                **base,
                **model,
            }
        )

    projection = {
        "schema": SCHEMA,
        "owner": OWNER,
        "projection_type":
            "provider_configuration",
        "profiles": rows,
        "profile_count": len(
            rows
        ),
        "configured_count": sum(
            1
            for row in rows
            if row[
                "configured"
            ]
        ),
        "credential_values_exposed": False,
        "authority_effect": "none",
    }

    projection[
        "digest"
    ] = _digest(
        projection
    )

    return projection


def _failure_state(
    exc: Exception,
) -> str:
    text = (
        f"{type(exc).__name__}: "
        f"{str(exc or '')}"
    ).lower()

    if any(
        marker in text
        for marker in (
            "401",
            "unauthorized",
            "invalid api key",
            "incorrect api key",
            "authentication",
        )
    ):
        return "unauthorized"

    if any(
        marker in text
        for marker in (
            "403",
            "forbidden",
            "permission denied",
        )
    ):
        return "forbidden"

    if any(
        marker in text
        for marker in (
            "429",
            "rate limit",
            "too many requests",
        )
    ):
        return "rate_limited"

    if any(
        marker in text
        for marker in (
            "404",
            "model not found",
            "model unavailable",
        )
    ):
        return "incompatible"

    if any(
        marker in text
        for marker in (
            "timeout",
            "timed out",
            "connection",
            "network",
            "name or service",
        )
    ):
        return "unreachable"

    return "provider_error"


def _safe_diagnostic(
    exc: Exception,
) -> str:
    text = (
        f"{type(exc).__name__}: "
        f"{str(exc or '').strip()}"
    )

    if len(
        text
    ) > 500:
        text = text[
            :500
        ]

    return text


def probe_profile(
    profile_id: str,
    *,
    timeout_seconds: int = 20,
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
        raise ProviderAdmissionError(
            f"unknown opus provider profile: {profile_id}"
        )

    configured = _configured(
        profile_id,
        profile,
    )

    if not configured:
        return {
            "profile_id": profile_id,
            "state": "unconfigured",
            "admitted": False,
            "authority_effect": "none",
        }

    model_state = _model_state(
        profile
    )

    if not model_state[
        "model_configured"
    ]:
        return {
            "profile_id": profile_id,
            "state": "model_unconfigured",
            "admitted": False,
            "authority_effect": "none",
        }

    started = time.monotonic()

    try:
        result = catalog_text.infer(
            {
                "provider_profile":
                    profile_id,
                "message":
                    "Reply with exactly: opus-ok",
                "temperature":
                    0,
                "max_tokens":
                    16,
                "timeout_seconds":
                    max(
                        1,
                        min(
                            int(
                                timeout_seconds
                            ),
                            60,
                        ),
                    ),
            },
            {
                "id":
                    "catalog_text",
                "timeout_seconds":
                    timeout_seconds,
            },
        )

    except Exception as exc:
        return {
            "profile_id": profile_id,
            "state": _failure_state(
                exc
            ),
            "admitted": False,
            "latency_ms": round(
                (
                    time.monotonic()
                    - started
                )
                * 1000,
                3,
            ),
            "diagnostic": _safe_diagnostic(
                exc
            ),
            "credential_values_exposed": False,
            "authority_effect": "none",
        }

    text = str(
        result.get(
            "text"
        )
        or ""
    ).strip()

    admitted = bool(
        result.get(
            "ok"
        )
        and text
    )

    return {
        "profile_id": profile_id,
        "state": (
            "admitted"
            if admitted
            else "invalid_response"
        ),
        "admitted": admitted,
        "latency_ms": round(
            (
                time.monotonic()
                - started
            )
            * 1000,
            3,
        ),
        "provider": result.get(
            "provider"
        ),
        "provider_profile": result.get(
            "provider_profile"
        ),
        "protocol": result.get(
            "protocol"
        ),
        "model": result.get(
            "model"
        ),
        "response_verified": (
            text.lower()
            == "opus-ok"
        ),
        "credential_values_exposed": False,
        "authority_effect": "none",
    }


def probe_configured(
    *,
    timeout_seconds: int = 20,
) -> Dict[str, Any]:
    load_environment()

    configuration = (
        configuration_projection()
    )

    probes = []

    for row in configuration[
        "profiles"
    ]:
        if not row[
            "configured"
        ]:
            continue

        probes.append(
            probe_profile(
                row[
                    "profile_id"
                ],
                timeout_seconds=(
                    timeout_seconds
                ),
            )
        )

    admitted = sorted(
        row[
            "profile_id"
        ]
        for row in probes
        if row.get(
            "admitted"
        )
    )

    projection = {
        "schema": SCHEMA,
        "owner": OWNER,
        "projection_type":
            "provider_admission",
        "configured_count": (
            configuration[
                "configured_count"
            ]
        ),
        "probe_count": len(
            probes
        ),
        "admitted_count": len(
            admitted
        ),
        "admitted_profiles": admitted,
        "probes": probes,
        "credential_values_exposed": False,
        "authority_effect": "none",
    }

    projection[
        "digest"
    ] = _digest(
        projection
    )

    return projection


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="provider_admission"
    )

    parser.add_argument(
        "operation",
        choices=(
            "configuration",
            "probe",
        ),
    )

    parser.add_argument(
        "--profile",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
    )

    args = parser.parse_args()

    if args.operation == "configuration":
        output = configuration_projection()

    elif args.profile:
        output = probe_profile(
            args.profile,
            timeout_seconds=args.timeout,
        )

    else:
        output = probe_configured(
            timeout_seconds=args.timeout,
        )

    print(
        json.dumps(
            output,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

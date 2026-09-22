#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict

from .environment import load_environment
from .model_discovery import discover
from .providers import catalog_text


SCHEMA = "savant.opus.provider-admission.v2"
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
    ).encode(
        "utf-8"
    )


def _digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        _canonical(
            value
        )
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
        name = str(
            profile.get(
                field
            )
            or ""
        ).strip()

        if name:
            names.add(
                name
            )

    header_env = profile.get(
        "header_env"
    )

    if isinstance(
        header_env,
        dict,
    ):
        for value in (
            header_env.values()
        ):
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
    placeholders = []

    for name in names:
        value = _env(
            name
        )

        if not value:
            continue

        present.append(
            name
        )

        if (
            value.lower()
            in PLACEHOLDERS
        ):
            placeholders.append(
                name
            )

    optional = bool(
        profile.get(
            "api_key_optional",
            False,
        )
    )

    return {
        "credential_names": names,
        "credential_present_names":
            sorted(
                present
            ),
        "credential_placeholder_names":
            sorted(
                placeholders
            ),
        "credential_present": bool(
            present
        ),
        "credential_optional":
            optional,
        "credential_configured": (
            optional
            or bool(
                present
            )
        ),
        "credential_values_exposed":
            False,
    }


def _base_configured(
    profile: Dict[str, Any],
) -> bool:
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

    return bool(
        direct
        or (
            env_name
            and _env(
                env_name
            )
        )
    )


def _configured(
    profile_id: str,
    profile: Dict[str, Any],
) -> bool:
    try:
        return (
            profile_id
            in catalog_text.available_profiles()
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

        credentials = (
            _credential_state(
                profile
            )
        )

        rows.append(
            {
                "profile_id":
                    profile_id,
                "protocol": str(
                    profile.get(
                        "protocol"
                    )
                    or ""
                ),
                "configured":
                    _configured(
                        profile_id,
                        profile,
                    ),
                "api_base_configured":
                    _base_configured(
                        profile
                    ),
                **credentials,
            }
        )

    result = {
        "schema": SCHEMA,
        "owner": OWNER,
        "projection_type":
            "provider_configuration",
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
        "profiles": rows,
        "credential_values_exposed":
            False,
        "authority_effect": "none",
    }

    result[
        "digest"
    ] = _digest(
        result
    )

    return result


def _failure_state(
    exc: Exception,
) -> str:
    text = (
        f"{type(exc).__name__}: "
        f"{str(exc or '')}"
    ).lower()

    groups = (
        (
            "unauthorized",
            (
                "401",
                "unauthorized",
                "authentication",
                "invalid api key",
                "incorrect api key",
            ),
        ),
        (
            "forbidden",
            (
                "403",
                "forbidden",
                "permission denied",
            ),
        ),
        (
            "rate_limited",
            (
                "429",
                "rate limit",
                "too many requests",
            ),
        ),
        (
            "incompatible",
            (
                "404",
                "model not found",
                "model unavailable",
            ),
        ),
        (
            "unreachable",
            (
                "timeout",
                "network",
                "connection",
                "name or service",
            ),
        ),
    )

    for state, markers in groups:
        if any(
            marker in text
            for marker in markers
        ):
            return state

    return "provider_error"


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
            "unknown opus provider profile: "
            f"{profile_id}"
        )

    if not _configured(
        profile_id,
        profile,
    ):
        return {
            "profile_id":
                profile_id,
            "state":
                "unconfigured",
            "admitted":
                False,
            "authority_effect":
                "none",
        }

    discovery = discover(
        profile_id,
        timeout_seconds=(
            timeout_seconds
        ),
    )

    model = str(
        discovery.get(
            "selected_model"
        )
        or ""
    ).strip()

    if not model:
        return {
            "profile_id":
                profile_id,
            "state":
                discovery.get(
                    "state",
                    "model_unavailable",
                ),
            "admitted":
                False,
            "model_discovery":
                discovery,
            "credential_values_exposed":
                False,
            "authority_effect":
                "none",
        }

    started = time.monotonic()

    try:
        result = (
            catalog_text.infer(
                {
                    "provider_profile":
                        profile_id,
                    "model":
                        model,
                    "message":
                        (
                            "Reply with "
                            "exactly: opus-ok"
                        ),
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
        )

    except Exception as exc:
        return {
            "profile_id":
                profile_id,
            "state":
                _failure_state(
                    exc
                ),
            "admitted":
                False,
            "model":
                model,
            "latency_ms":
                round(
                    (
                        time.monotonic()
                        - started
                    )
                    * 1000,
                    3,
                ),
            "diagnostic": (
                f"{type(exc).__name__}: "
                f"{str(exc)}"
            )[:300],
            "model_discovery":
                discovery,
            "credential_values_exposed":
                False,
            "authority_effect":
                "none",
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
        "profile_id":
            profile_id,
        "state": (
            "admitted"
            if admitted
            else "invalid_response"
        ),
        "admitted":
            admitted,
        "model":
            result.get(
                "model"
            )
            or model,
        "protocol":
            result.get(
                "protocol"
            ),
        "latency_ms":
            round(
                (
                    time.monotonic()
                    - started
                )
                * 1000,
                3,
            ),
        "response_verified": (
            text.lower()
            == "opus-ok"
        ),
        "model_discovery":
            discovery,
        "credential_values_exposed":
            False,
        "authority_effect":
            "none",
    }


def probe_configured(
    *,
    timeout_seconds: int = 20,
) -> Dict[str, Any]:
    configuration = (
        configuration_projection()
    )

    probes = []

    for row in configuration[
        "profiles"
    ]:
        if not row.get(
            "configured"
        ):
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

    result = {
        "schema": SCHEMA,
        "owner": OWNER,
        "projection_type":
            "provider_admission",
        "configured_count":
            configuration[
                "configured_count"
            ],
        "probe_count":
            len(
                probes
            ),
        "admitted_count":
            len(
                admitted
            ),
        "admitted_profiles":
            admitted,
        "probes":
            probes,
        "credential_values_exposed":
            False,
        "authority_effect":
            "none",
    }

    result[
        "digest"
    ] = _digest(
        result
    )

    return result


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

    if (
        args.operation
        == "configuration"
    ):
        output = (
            configuration_projection()
        )

    elif args.profile:
        output = probe_profile(
            args.profile,
            timeout_seconds=(
                args.timeout
            ),
        )

    else:
        output = probe_configured(
            timeout_seconds=(
                args.timeout
            ),
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

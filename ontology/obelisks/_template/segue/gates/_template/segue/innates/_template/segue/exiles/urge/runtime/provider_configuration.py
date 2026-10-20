
from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit


class configuration_error(ValueError):
    pass


_variable = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*$"
)


def validate(
    providers: Sequence[Mapping[str, Any]],
    *,
    require_credentials: bool = False,
) -> list[dict[str, Any]]:
    if isinstance(providers, (str, bytes)):
        raise configuration_error(
            "providers must be a sequence"
        )

    result = []
    identities = set()

    for provider in providers:
        if not isinstance(provider, Mapping):
            raise configuration_error(
                "provider must be a mapping"
            )

        identity = provider.get("id")
        model = provider.get("model")
        endpoint = provider.get("endpoint")
        variable = provider.get("credential_variable")

        for name, value in (
            ("id", identity),
            ("model", model),
            ("endpoint", endpoint),
            ("credential_variable", variable),
        ):
            if (
                not isinstance(value, str)
                or not value.strip()
            ):
                raise configuration_error(
                    f"invalid provider {name}"
                )

        if identity in identities:
            raise configuration_error(
                "duplicate provider identity"
            )

        identities.add(identity)

        parsed = urlsplit(endpoint)

        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            raise configuration_error(
                "invalid HTTPS provider endpoint"
            )

        if not _variable.fullmatch(variable):
            raise configuration_error(
                "invalid credential variable name"
            )

        if require_credentials and not os.getenv(variable):
            raise configuration_error(
                f"credential not configured: {variable}"
            )

        temperature = provider.get(
            "temperature",
            0.4,
        )

        if (
            isinstance(temperature, bool)
            or not isinstance(
                temperature,
                (int, float),
            )
            or not 0 <= temperature <= 2
        ):
            raise configuration_error(
                "invalid temperature"
            )

        result.append({
            "id": identity,
            "model": model,
            "endpoint": endpoint,
            "credential_variable": variable,
            "temperature": float(temperature),
        })

    if not result:
        raise configuration_error(
            "at least one provider is required"
        )

    return result

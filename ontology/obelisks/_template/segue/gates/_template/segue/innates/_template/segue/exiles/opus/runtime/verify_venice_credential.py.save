#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os

import environment


def main() -> None:
    environment.load_environment(
        force=True
    )

    value = str(
        os.getenv(
            "VENICE_API_KEY",
            "",
        )
        or ""
    ).strip()

    placeholder_values = {
        "",
        "your_actual_venice_api_key",
        "your_venice_api_key",
        "replace_me",
        "changeme",
    }

    output = {
        "credential_present": bool(
            value
        ),
        "credential_length": len(
            value
        ),
        "credential_is_placeholder": (
            value.lower()
            in placeholder_values
        ),
        "credential_fingerprint": (
            hashlib.sha256(
                value.encode(
                    "utf-8"
                )
            ).hexdigest()[:12]
            if value
            else None
        ),
        "credential_values_exposed": False,
        "owner": "opus",
        "authority_effect": "none",
    }

    print(
        json.dumps(
            output,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

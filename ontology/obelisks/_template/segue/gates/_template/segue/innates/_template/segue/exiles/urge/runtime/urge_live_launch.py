
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

runtime = Path(__file__).resolve().parent
sys.path.insert(0, str(runtime))

from provider_environment import load
from provider_configuration import validate


class launch_error(RuntimeError):
    pass


def main():
    parser = argparse.ArgumentParser(
        description="Launch the real Urge execution interface"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=18765,
    )

    parser.add_argument(
        "--provider-id",
        default="primary",
    )

    parser.add_argument(
        "--model",
    )

    parser.add_argument(
        "--endpoint",
    )

    parser.add_argument(
        "--credential-variable",
    )

    args = parser.parse_args()

    load()

    model = args.model or os.getenv(
        "SAVANT_URGE_MODEL"
    )

    endpoint = args.endpoint or os.getenv(
        "SAVANT_URGE_ENDPOINT"
    )

    credential_variable = (
        args.credential_variable
        or os.getenv(
            "SAVANT_URGE_CREDENTIAL_VARIABLE"
        )
    )

    missing = [
        name
        for name, value in (
            ("model", model),
            ("endpoint", endpoint),
            ("credential variable", credential_variable),
        )
        if not value
    ]

    if missing:
        raise launch_error(
            "missing provider configuration: "
            + ", ".join(missing)
        )

    providers = validate(
        [
            {
                "id": args.provider_id,
                "model": model,
                "endpoint": endpoint,
                "credential_variable":
                    credential_variable,
            }
        ],
        require_credentials=True,
    )

    if not (runtime / "urge_live.html").is_file():
        raise launch_error(
            "urge_live.html is not installed"
        )

    if not (runtime / "urge_live_server.py").is_file():
        raise launch_error(
            "urge_live_server.py is not installed"
        )

    provider = providers[0]

    command = [
        sys.executable,
        str(runtime / "urge_live_server.py"),
        "--port",
        str(args.port),
        "--provider-id",
        provider["id"],
        "--model",
        provider["model"],
        "--endpoint",
        provider["endpoint"],
        "--credential-variable",
        provider["credential_variable"],
    ]

    print(
        json.dumps(
            {
                "service": "urge",
                "mode": "live",
                "provider": provider["id"],
                "model": provider["model"],
                "url": (
                    f"http://127.0.0.1:{args.port}/"
                ),
                "status": "starting",
            },
            indent=2,
        ),
        flush=True,
    )

    raise SystemExit(
        subprocess.call(
            command,
            cwd=str(runtime),
        )
    )


if __name__ == "__main__":
    main()

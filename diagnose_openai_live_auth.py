#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


ENV_FILE = Path(
    "/root/.env"
)

SERVICE = (
    "palaver.service"
)

KEY_NAME = (
    "OPENAI_API_KEY"
)

ME_URL = (
    "https://api.openai.com/v1/me"
)


def digest(
    value: str,
) -> str:
    if not value:
        return ""

    return hashlib.sha256(
        value.encode(
            "utf-8"
        )
    ).hexdigest()[:12]


def load_file_key() -> str:
    if not ENV_FILE.is_file():
        return ""

    for raw in ENV_FILE.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        line = raw.strip()

        if (
            not line
            or line.startswith("#")
            or "=" not in line
        ):
            continue

        name, value = line.split(
            "=",
            1,
        )

        if name.strip() != KEY_NAME:
            continue

        return (
            value
            .strip()
            .strip('"')
            .strip("'")
        )

    return ""


def service_pid() -> int:
    result = subprocess.run(
        [
            "systemctl",
            "show",
            SERVICE,
            "--property=MainPID",
            "--value",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    value = result.stdout.strip()

    if not value:
        return 0

    return int(
        value
    )


def process_key(
    pid: int,
) -> str:
    if pid <= 0:
        return ""

    path = Path(
        f"/proc/{pid}/environ"
    )

    if not path.is_file():
        return ""

    raw = path.read_bytes()

    prefix = (
        KEY_NAME.encode(
            "utf-8"
        )
        + b"="
    )

    for item in raw.split(
        b"\x00"
    ):
        if item.startswith(
            prefix
        ):
            return (
                item[
                    len(
                        prefix
                    ):
                ]
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

    return ""


def probe(
    label: str,
    key: str,
) -> dict[str, object]:
    result: dict[str, object] = {
        "label": label,
        "present": bool(
            key
        ),
        "length": len(
            key
        ),
        "sha256_12": digest(
            key
        ),
        "http_status": None,
        "authenticated": False,
        "error_type": None,
    }

    if not key:
        result[
            "error_type"
        ] = "missing_key"

        return result

    request = urllib.request.Request(
        ME_URL,
        headers={
            "Authorization": (
                f"Bearer {key}"
            ),
            "Accept": (
                "application/json"
            ),
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=20,
        ) as response:
            response.read()

            result[
                "http_status"
            ] = response.status

            result[
                "authenticated"
            ] = (
                200
                <= response.status
                < 300
            )

    except urllib.error.HTTPError as exc:
        result[
            "http_status"
        ] = exc.code

        result[
            "error_type"
        ] = (
            "http_error"
        )

        try:
            body = (
                exc.read()
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

            parsed = json.loads(
                body
            )

            error = parsed.get(
                "error"
            )

            if isinstance(
                error,
                dict,
            ):
                result[
                    "provider_error_type"
                ] = error.get(
                    "type"
                )

                result[
                    "provider_error_code"
                ] = error.get(
                    "code"
                )

            elif isinstance(
                error,
                str,
            ):
                result[
                    "provider_error"
                ] = error[:200]

        except Exception:
            pass

    except Exception as exc:
        result[
            "error_type"
        ] = type(
            exc
        ).__name__

    return result


def main() -> int:
    file_key = load_file_key()

    pid = service_pid()

    live_key = process_key(
        pid
    )

    report = {
        "service": SERVICE,
        "pid": pid,
        "file_key": {
            "present": bool(
                file_key
            ),
            "length": len(
                file_key
            ),
            "sha256_12": digest(
                file_key
            ),
        },
        "process_key": {
            "present": bool(
                live_key
            ),
            "length": len(
                live_key
            ),
            "sha256_12": digest(
                live_key
            ),
        },
        "same_key": (
            bool(
                file_key
            )
            and bool(
                live_key
            )
            and file_key
            == live_key
        ),
        "file_key_probe": probe(
            "file_key",
            file_key,
        ),
        "process_key_probe": probe(
            "process_key",
            live_key,
        ),
    }

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

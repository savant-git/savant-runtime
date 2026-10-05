#!/usr/bin/env python3

from pathlib import Path
import hashlib


ENV_PATHS = (
    Path("/root/.env"),
    Path("/root/savant-runtime/.env"),
)

VISIBLE_KEYS = {
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
}


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}

    for raw in path.read_text(
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

        key, value = line.split(
            "=",
            1,
        )

        key = key.strip()
        value = (
            value
            .strip()
            .strip('"')
            .strip("'")
        )

        if key in VISIBLE_KEYS:
            values[key] = value

    return values


def key_report(
    value: str,
) -> dict[str, object]:
    if not value:
        return {
            "present": False,
            "length": 0,
            "prefix": "",
            "sha256_12": "",
        }

    return {
        "present": True,
        "length": len(value),
        "prefix": value[:7],
        "sha256_12": hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()[:12],
    }


def main() -> int:
    for path in ENV_PATHS:
        print(
            f"\n=== {path} ==="
        )

        if not path.exists():
            print("missing")
            continue

        print("present")

        values = parse_env(
            path
        )

        print(
            "OPENAI_API_KEY:",
            key_report(
                values.get(
                    "OPENAI_API_KEY",
                    "",
                )
            ),
        )

        print(
            "OPENAI_MODEL:",
            values.get(
                "OPENAI_MODEL",
                "(unset)",
            ),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

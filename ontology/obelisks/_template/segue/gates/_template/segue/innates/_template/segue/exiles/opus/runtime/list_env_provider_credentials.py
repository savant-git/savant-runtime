#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from pathlib import Path


ENV_PATHS = (
    Path("/root/.env"),
    Path("/root/savant-runtime/.env"),
)

CREDENTIAL_SUFFIXES = (
    "_API_KEY",
    "_API_TOKEN",
    "_ACCESS_TOKEN",
    "_AUTH_TOKEN",
    "_SECRET_KEY",
)

EXCLUDED_PREFIXES = (
    "AWS_",
)

PROVIDER_ALIASES = {
    "GOOGLE": "google",
    "GEMINI": "gemini",
    "OPENAI": "openai",
    "ANTHROPIC": "anthropic",
    "CLAUDE": "anthropic",
    "GROQ": "groq",
    "FIREWORKS": "fireworks",
    "DEEPSEEK": "deepseek",
    "VENICE": "venice",
    "MISTRAL": "mistral",
    "COHERE": "cohere",
    "TOGETHER": "together",
    "PERPLEXITY": "perplexity",
    "OPENROUTER": "openrouter",
    "XAI": "xai",
    "GROK": "xai",
    "CEREBRAS": "cerebras",
    "SAMBANOVA": "sambanova",
    "REPLICATE": "replicate",
    "HUGGINGFACE": "huggingface",
    "HF": "huggingface",
    "AI21": "ai21",
    "NVIDIA": "nvidia",
    "NOVITA": "novita",
    "DEEPINFRA": "deepinfra",
    "CLOUDFLARE": "cloudflare",
    "ELEVENLABS": "elevenlabs",
    "ASSEMBLYAI": "assemblyai",
    "DEEPGRAM": "deepgram",
    "AZURE_OPENAI": "azure_openai",
    "AZURE": "azure",
    "BEDROCK": "bedrock",
}


def parse_env(
    path: Path,
) -> dict[str, bool]:
    found: dict[str, bool] = {}

    if not path.exists():
        return found

    for raw_line in path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        line = raw_line.strip()

        if (
            not line
            or line.startswith("#")
            or "=" not in line
        ):
            continue

        if line.startswith("export "):
            line = line[7:].strip()

        key, value = line.split(
            "=",
            1,
        )

        key = key.strip()

        if not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*",
            key,
        ):
            continue

        value = value.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            value = value[1:-1]

        found[key] = bool(
            value.strip()
        )

    return found


def looks_like_provider_credential(
    key: str,
) -> bool:
    upper = key.upper()

    if any(
        upper.startswith(prefix)
        for prefix in EXCLUDED_PREFIXES
    ):
        return False

    return any(
        upper.endswith(suffix)
        for suffix in CREDENTIAL_SUFFIXES
    )


def infer_provider(
    key: str,
) -> str:
    upper = key.upper()

    stem = upper

    for suffix in CREDENTIAL_SUFFIXES:
        if stem.endswith(suffix):
            stem = stem[
                :-len(suffix)
            ]
            break

    if stem in PROVIDER_ALIASES:
        return PROVIDER_ALIASES[
            stem
        ]

    for prefix, provider in sorted(
        PROVIDER_ALIASES.items(),
        key=lambda item: len(
            item[0]
        ),
        reverse=True,
    ):
        if (
            stem == prefix
            or stem.startswith(
                prefix + "_"
            )
        ):
            return provider

    return stem.lower()


def main() -> int:
    merged: dict[
        str,
        dict[str, object]
    ] = {}

    existing_paths: list[str] = []

    for path in ENV_PATHS:
        if not path.exists():
            continue

        existing_paths.append(
            str(path)
        )

        values = parse_env(
            path
        )

        for key, populated in values.items():
            if not looks_like_provider_credential(
                key
            ):
                continue

            entry = merged.setdefault(
                key,
                {
                    "variable":
                        key,
                    "provider":
                        infer_provider(
                            key
                        ),
                    "configured":
                        False,
                    "sources":
                        [],
                },
            )

            entry[
                "configured"
            ] = bool(
                entry[
                    "configured"
                ]
                or populated
            )

            sources = entry[
                "sources"
            ]

            if isinstance(
                sources,
                list,
            ):
                sources.append(
                    str(path)
                )

    credentials = sorted(
        merged.values(),
        key=lambda item: (
            str(
                item[
                    "provider"
                ]
            ),
            str(
                item[
                    "variable"
                ]
            ),
        ),
    )

    providers: dict[
        str,
        list[str]
    ] = {}

    for entry in credentials:
        provider = str(
            entry[
                "provider"
            ]
        )

        providers.setdefault(
            provider,
            []
        ).append(
            str(
                entry[
                    "variable"
                ]
            )
        )

    output = {
        "schema":
            "opus.env.provider_credentials.v1",
        "env_files":
            existing_paths,
        "credential_count":
            len(
                credentials
            ),
        "provider_count":
            len(
                providers
            ),
        "providers":
            providers,
        "credentials":
            credentials,
        "secret_values_exposed":
            False,
    }

    print(
        json.dumps(
            output,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

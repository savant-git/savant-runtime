import os
import sys
from pathlib import Path


ENV_FILE = Path("/root/.env")

OPUS_RUNTIME = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/exiles/"
    "opus/runtime"
)


def load_env_file(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError(
            f"environment file missing: {path}"
        )

    for raw_line in path.read_text(
        encoding="utf-8"
    ).splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].strip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            value = value[1:-1]

        if key:
            os.environ.setdefault(
                key,
                value,
            )


def main() -> int:
    load_env_file(
        ENV_FILE
    )

    if not os.getenv(
        "OPENAI_API_KEY"
    ):
        print(
            "provider_error="
            "OPENAI_API_KEY missing"
        )
        return 1

    runtime_path = str(
        OPUS_RUNTIME
    )

    if runtime_path not in sys.path:
        sys.path.insert(
            0,
            runtime_path,
        )

    try:
        from providers import openai_text
    except Exception as exc:
        print(
            "provider_import_error_type="
            + type(exc).__name__
        )
        print(
            "provider_import_error="
            + str(exc)
        )
        return 1

    provider = {
        "env_key": "OPENAI_API_KEY",
        "model_env": "SAVANT_MODEL",
        "model_default": "gpt-5",
        "timeout_seconds": 120,
    }

    try:
        result = openai_text.infer(
            {
                "message": (
                    "Return exactly: "
                    "SAVANT_OPENAI_OK"
                )
            },
            provider,
        )
    except Exception as exc:
        print(
            "provider_error_type="
            + type(exc).__name__
        )
        print(
            "provider_error="
            + str(exc)
        )
        return 1

    print(
        "provider_ok="
        + str(result.get("ok"))
    )
    print(
        "provider="
        + str(result.get("provider"))
    )
    print(
        "model="
        + str(result.get("model"))
    )
    print(
        "text="
        + str(result.get("text"))
    )

    expected = "SAVANT_OPENAI_OK"

    if str(result.get("text", "")).strip() != expected:
        print(
            "exact_response_match=False"
        )
        return 1

    print(
        "exact_response_match=True"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

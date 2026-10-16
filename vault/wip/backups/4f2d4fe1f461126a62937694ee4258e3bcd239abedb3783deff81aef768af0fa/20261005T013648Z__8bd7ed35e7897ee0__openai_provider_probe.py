import importlib.util
import os
from pathlib import Path


ENV_FILE = Path("/root/.env")

PROVIDER_FILE = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/exiles/"
    "opus/runtime/providers/openai_text.py"
)


def load_env_file(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError(f"environment file missing: {path}")

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
            os.environ.setdefault(key, value)


def load_provider():
    if not PROVIDER_FILE.is_file():
        raise RuntimeError(
            f"provider implementation missing: {PROVIDER_FILE}"
        )

    spec = importlib.util.spec_from_file_location(
        "openai_text_probe",
        PROVIDER_FILE,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "could not load OpenAI provider implementation"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def main() -> int:
    load_env_file(ENV_FILE)

    if not os.getenv("OPENAI_API_KEY"):
        print("provider_error=OPENAI_API_KEY missing")
        return 1

    module = load_provider()

    provider = {
        "env_key": "OPENAI_API_KEY",
        "model_env": "SAVANT_MODEL",
        "model_default": "gpt-5",
        "timeout_seconds": 120,
    }

    try:
        result = module.infer(
            {
                "message": (
                    "Return exactly: SAVANT_OPENAI_OK"
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

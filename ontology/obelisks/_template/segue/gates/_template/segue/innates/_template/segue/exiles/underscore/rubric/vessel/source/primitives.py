#!/usr/bin/env python3

from __future__ import annotations

from typing import Any
import json
import sys
from pathlib import Path
import importlib.util
from typing import Iterable


schema_version = (
    "savant.underscore.vessel.primitives.v1"
)

authority_effect = "none"


def require_object(
    value: Any,
    name: str,
) -> dict[str, Any]:
    if not isinstance(
        value,
        dict,
    ):
        raise TypeError(
            f"{name} must be an object"
        )

    return value


def self_check() -> dict[str, Any]:
    value = {
        "subject": "vessel",
    }

    result = require_object(
        value,
        "input",
    )

    if result is not value:
        raise RuntimeError(
            "require_object identity "
            "preservation failed"
        )

    try:
        require_object(
            [],
            "candidate",
        )

    except TypeError as exc:
        if str(exc) != (
            "candidate must be an object"
        ):
            raise RuntimeError(
                "require_object error "
                "contract changed"
            ) from exc

    else:
        raise RuntimeError(
            "require_object accepted "
            "non-object input"
        )

    return {
        "schema": schema_version,
        "authority_effect": (
            authority_effect
        ),
        "self_check": "passed",
        "primitives": [
            "require_object",
        ],
        "invariants": {
            "authority_effect_none": True,
            "object_identity_preserved": True,
            "non_object_rejected": True,
            "error_contract_preserved": True,
        },
    }


def main() -> int:
    import json

    print(
        json.dumps(
            self_check(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return 0



def bind_stable_id(
    digest_function: Any,
):
    if not callable(
        digest_function
    ):
        raise TypeError(
            "digest_function must be callable"
        )

    def stable_id(
        prefix: str,
        value: Any,
        width: int = 24,
    ) -> str:
        return (
            f"{prefix}_"
            f"{digest_function(value)[:width]}"
        )

    return stable_id


def load_json(
    path: str,
) -> dict[str, Any]:
    if path == "-":
        raw = sys.stdin.read()

    else:
        raw = Path(
            path
        ).read_text(
            encoding="utf-8"
        )

    return require_object(
        json.loads(
            raw
        ),
        "input",
    )


def load_module(
    name: str,
    path: Path,
) -> Any:
    if not path.is_file():
        raise RuntimeError(
            f"required module unavailable: "
            f"{path}"
        )

    spec = (
        importlib.util.spec_from_file_location(
            name,
            path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            f"unable to load module: {path}"
        )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    sys.modules[
        spec.name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module

def normalize_strings(
    values: Iterable[Any],
) -> list[str]:
    output = []

    for value in values:
        text = str(value).strip()

        if text:
            output.append(text)

    return output

def load_payload(path: str) -> dict[str, Any]:
    if path == '-':
        raw = sys.stdin.read()
    else:
        raw = Path(path).read_text(encoding='utf-8')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise TypeError('input must be a JSON object')
    return value

def load_module_production(name: str, path: Path) -> Any:
    if not path.is_file():
        raise RuntimeError('required module unavailable: ' + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError('unable to load module: ' + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

if __name__ == "__main__":
    raise SystemExit(
        main()
    )

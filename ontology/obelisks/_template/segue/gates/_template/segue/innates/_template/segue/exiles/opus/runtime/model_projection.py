from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable
from .normalization import normalized_strings as _normalized


OPUS_ROOT = Path(
    __file__
).resolve().parents[1]

MODEL_REGISTRY = (
    OPUS_ROOT
    / "registry"
    / "models"
    / "text_models.json"
)


def _registry() -> Dict[str, Any]:
    return json.loads(
        MODEL_REGISTRY.read_text(
            encoding="utf-8"
        )
    )


def models() -> Dict[str, Any]:
    data = _registry()

    raw = data.get(
        "models"
    )

    if not isinstance(
        raw,
        dict,
    ):
        raise RuntimeError(
            "opus model registry models "
            "must be an object"
        )

    return raw


def model_projection(
    model_id: str,
) -> Dict[str, Any]:
    model_id = str(
        model_id or ""
    ).strip()

    if not model_id:
        raise RuntimeError(
            "model_id is required"
        )

    raw = models().get(
        model_id
    )

    if not isinstance(
        raw,
        dict,
    ):
        return {
            "model_id": model_id,
            "registered": False,
            "providers": [],
            "layers": [],
        }

    return {
        "model_id": model_id,
        "registered": True,
        "providers": list(
            raw.get(
                "providers"
            )
            or []
        ),
        "layers": sorted(
            _normalized(
                raw.get(
                    "layers"
                )
                or []
            )
        ),
    }


def model_supports_layers(
    model_id: str,
    required_layers: Iterable[Any] | None,
) -> bool:
    required = _normalized(
        required_layers
    )

    if not required:
        return True

    projection = model_projection(
        model_id
    )

    available = _normalized(
        projection.get(
            "layers"
        )
    )

    return required.issubset(
        available
    )


def provider_model(
    provider_data: Dict[str, Any],
) -> str:
    model_env = str(
        provider_data.get(
            "model_env"
        )
        or ""
    ).strip()

    configured = (
        os.getenv(
            model_env
        )
        if model_env
        else None
    )

    return str(
        configured
        or provider_data.get(
            "model_default"
        )
        or ""
    ).strip()


def provider_model_projection(
    provider_data: Dict[str, Any],
) -> Dict[str, Any]:
    model_id = provider_model(
        provider_data
    )

    projection = model_projection(
        model_id
    )

    projection[
        "provider_id"
    ] = str(
        provider_data.get(
            "id"
        )
        or ""
    )

    return projection


def candidates_for_layers(
    provider_rows: Iterable[
        Dict[str, Any]
    ],
    required_layers: Iterable[Any] | None,
) -> list[Dict[str, Any]]:
    required = _normalized(
        required_layers
    )

    result: list[
        Dict[str, Any]
    ] = []

    for provider_data in provider_rows:
        projection = (
            provider_model_projection(
                provider_data
            )
        )

        if required.issubset(
            _normalized(
                projection.get(
                    "layers"
                )
            )
        ):
            result.append(
                projection
            )

    return result

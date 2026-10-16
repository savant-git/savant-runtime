
from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from . import image_renderer


schema = "savant://runtime/urge/prepared-image-renderer/1.0.0"
owner = "exile:urge"

max_source_bytes = 32 * 1024 * 1024


class prepared_image_renderer_error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class prepared_binding:
    renderer: Any
    original_baseline: dict[str, str]
    prepared_baseline: dict[str, str]
    preprocessing: dict[str, Any]


def _decode_source(source: str) -> bytes:
    if not isinstance(source, str):
        raise prepared_image_renderer_error(
            "baseline source must be a data URL"
        )

    try:
        header, payload = source.split(",", 1)
    except ValueError as exc:
        raise prepared_image_renderer_error(
            "malformed baseline data URL"
        ) from exc

    if not header.startswith("data:image/"):
        raise prepared_image_renderer_error(
            "baseline must contain an image"
        )

    if not header.endswith(";base64"):
        raise prepared_image_renderer_error(
            "baseline must use base64 encoding"
        )

    if len(payload) > (max_source_bytes * 4 // 3) + 8:
        raise prepared_image_renderer_error(
            "baseline exceeds size limit"
        )

    try:
        decoded = base64.b64decode(
            payload,
            validate=True,
        )
    except (ValueError, binascii.Error) as exc:
        raise prepared_image_renderer_error(
            "invalid baseline encoding"
        ) from exc

    if not decoded or len(decoded) > max_source_bytes:
        raise prepared_image_renderer_error(
            "invalid baseline size"
        )

    return decoded


def create_binding(
    baseline: Mapping[str, Any],
    *,
    media_profile: str = "generic",
    remove_background: bool = False,
    tolerance: int = 24,
) -> prepared_binding:
    if not isinstance(baseline, Mapping):
        raise prepared_image_renderer_error(
            "baseline must be a mapping"
        )

    original = {
        "name": str(baseline.get("name") or "baseline.png"),
        "media_type": str(
            baseline.get("media_type") or ""
        ),
        "source": str(baseline.get("source") or ""),
    }

    if not original["media_type"].startswith("image/"):
        raise prepared_image_renderer_error(
            "unsupported baseline media type"
        )

    source_bytes = _decode_source(original["source"])

    try:
        from .media_preprocessing import prepare

        prepared = prepare(
            source_bytes,
            media_profile=media_profile,
            remove_background=remove_background,
            tolerance=tolerance,
        )
    except ImportError as exc:
        raise prepared_image_renderer_error(
            "media preprocessing dependencies unavailable"
        ) from exc

    projection_source = (
        "data:image/png;base64,"
        + base64.b64encode(
            prepared.projection
        ).decode("ascii")
    )

    projected = {
        "name": "prepared-baseline.png",
        "media_type": "image/png",
        "source": projection_source,
    }

    renderer = image_renderer.binding(
        baseline=projected
    )

    return prepared_binding(
        renderer=renderer,
        original_baseline=original,
        prepared_baseline=projected,
        preprocessing=dict(prepared.metadata),
    )


__all__ = [
    "create_binding",
    "prepared_binding",
    "prepared_image_renderer_error",
    "schema",
]

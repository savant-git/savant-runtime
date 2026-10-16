
from __future__ import annotations

import hashlib
import io
import json
from collections import deque
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError


schema = "savant://runtime/urge/media-preprocessing/1.0.0"
owner = "exile:urge"

profiles = frozenset({
    "logo",
    "illustration",
    "photography",
    "interface",
    "generic",
})


class media_preprocessing_error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class prepared_media:
    original: bytes
    projection: bytes
    metadata: dict[str, Any]


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _background_color(
    image: Image.Image,
) -> tuple[int, int, int]:
    width, height = image.size
    pixels = image.load()

    corners = (
        pixels[0, 0][:3],
        pixels[width - 1, 0][:3],
        pixels[0, height - 1][:3],
        pixels[width - 1, height - 1][:3],
    )

    return min(
        corners,
        key=lambda color: sum(
            max(
                abs(color[channel] - other[channel])
                for channel in range(3)
            )
            for other in corners
        ),
    )


def _remove_background(
    image: Image.Image,
    tolerance: int,
) -> tuple[Image.Image, int]:
    width, height = image.size
    pixels = image.load()
    background = _background_color(image)

    visited = bytearray(width * height)
    pending: deque[tuple[int, int]] = deque()

    def enqueue(x: int, y: int) -> None:
        index = y * width + x

        if visited[index]:
            return

        visited[index] = 1
        red, green, blue, alpha = pixels[x, y]

        if alpha == 0 or max(
            abs(red - background[0]),
            abs(green - background[1]),
            abs(blue - background[2]),
        ) <= tolerance:
            pending.append((x, y))

    for x in range(width):
        enqueue(x, 0)
        enqueue(x, height - 1)

    for y in range(height):
        enqueue(0, y)
        enqueue(width - 1, y)

    removed = 0

    while pending:
        x, y = pending.popleft()
        red, green, blue, alpha = pixels[x, y]

        if alpha:
            pixels[x, y] = (red, green, blue, 0)
            removed += 1

        if x:
            enqueue(x - 1, y)

        if x + 1 < width:
            enqueue(x + 1, y)

        if y:
            enqueue(x, y - 1)

        if y + 1 < height:
            enqueue(x, y + 1)

    return image, removed


def prepare(
    source: bytes,
    *,
    media_profile: str,
    remove_background: bool = False,
    tolerance: int = 24,
    max_pixels: int = 16_000_000,
) -> prepared_media:
    if media_profile not in profiles:
        raise media_preprocessing_error(
            "unsupported media profile"
        )

    if not isinstance(source, bytes) or not source:
        raise media_preprocessing_error(
            "source must contain image bytes"
        )

    if not 0 <= tolerance <= 80:
        raise media_preprocessing_error(
            "invalid background tolerance"
        )

    if not 1 <= max_pixels <= 64_000_000:
        raise media_preprocessing_error(
            "invalid pixel limit"
        )

    if remove_background and media_profile != "logo":
        raise media_preprocessing_error(
            "background removal requires logo profile"
        )

    try:
        with Image.open(io.BytesIO(source)) as opened:
            width, height = opened.size

            if width * height > max_pixels:
                raise media_preprocessing_error(
                    "image exceeds pixel limit"
                )

            image = ImageOps.exif_transpose(
                opened
            ).convert("RGBA")

    except (
        OSError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
    ) as exc:
        raise media_preprocessing_error(
            "unsupported or malformed image"
        ) from exc

    removed = 0

    if remove_background:
        image, removed = _remove_background(
            image,
            tolerance,
        )

    output = io.BytesIO()
    image.save(
        output,
        format="PNG",
        optimize=True,
    )

    projection = output.getvalue()

    metadata = {
        "schema": schema,
        "owner": owner,
        "media_profile": media_profile,
        "source_sha256": _digest(source),
        "projection_sha256": _digest(projection),
        "source_bytes": len(source),
        "projection_bytes": len(projection),
        "width": image.width,
        "height": image.height,
        "projection_format": "png",
        "background_removal": remove_background,
        "background_pixels_removed": removed,
        "tolerance": (
            tolerance if remove_background else None
        ),
        "original_preserved": True,
        "vectorized": False,
        "provider": None,
    }

    metadata["digest"] = _digest(
        _canonical(metadata)
    )

    return prepared_media(
        original=source,
        projection=projection,
        metadata=metadata,
    )

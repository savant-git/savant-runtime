
from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from typing import Any

from PIL import Image


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


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _background_color(image: Image.Image) -> tuple[int, int, int]:
    width, height = image.size
    points = (
        (0, 0),
        (width - 1, 0),
        (0, height - 1),
        (width - 1, height - 1),
    )
    colors = [image.getpixel(point)[:3] for point in points]
    return tuple(
        sorted(color[channel] for color in colors)[2]
        for channel in range(3)
    )


def _remove_edge_background(
    image: Image.Image,
    tolerance: int,
) -> tuple[Image.Image, int]:
    width, height = image.size
    background = _background_color(image)
    pixels = image.load()

    def matches(x: int, y: int) -> bool:
        color = pixels[x, y]
        if color[3] == 0:
            return True
        return max(
            abs(color[index] - background[index])
            for index in range(3)
        ) <= tolerance

    visited = bytearray(width * height)
    queue: list[tuple[int, int]] = []

    def enqueue(x: int, y: int) -> None:
        index = y * width + x
        if not visited[index] and matches(x, y):
            visited[index] = 1
            queue.append((x, y))

    for x in range(width):
        enqueue(x, 0)
        enqueue(x, height - 1)

    for y in range(height):
        enqueue(0, y)
        enqueue(width - 1, y)

    removed = 0
    position = 0

    while position < len(queue):
        x, y = queue[position]
        position += 1

        red, green, blue, alpha = pixels[x, y]
        if alpha:
            pixels[x, y] = (red, green, blue, 0)
            removed += 1

        if x > 0:
            enqueue(x - 1, y)
        if x + 1 < width:
            enqueue(x + 1, y)
        if y > 0:
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
            "tolerance must be between 0 and 80"
        )

    if not 1 <= max_pixels <= 64_000_000:
        raise media_preprocessing_error(
            "invalid pixel limit"
        )

    if remove_background and media_profile != "logo":
        raise media_preprocessing_error(
            "automatic background removal requires logo profile"
        )

    try:
        with Image.open(io.BytesIO(source)) as opened:
            width, height = opened.size

            if width * height > max_pixels:
                raise media_preprocessing_error(
                    "image exceeds pixel limit"
                )

            image = opened.convert("RGBA")
    except (OSError, ValueError) as exc:
        if isinstance(exc, media_preprocessing_error):
            raise
        raise media_preprocessing_error(
            "unsupported or malformed image"
        ) from exc

    removed = 0

    if remove_background:
        image, removed = _remove_edge_background(
            image, tolerance
        )

    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    projection = output.getvalue()

    operation = {
        "schema": schema,
        "owner": owner,
        "media_profile": media_profile,
        "source_sha256": _digest(source),
        "projection_sha256": _digest(projection),
        "source_size": len(source),
        "projection_size": len(projection),
        "width": width,
        "height": height,
        "background_removal_requested": remove_background,
        "background_pixels_removed": removed,
        "tolerance": tolerance if remove_background else None,
        "projection_format": "png",
        "original_preserved": True,
        "vectorized": False,
        "provider": None,
    }

    operation["digest"] = hashlib.sha256(
        _canonical(operation)
    ).hexdigest()

    return prepared_media(
        original=source,
        projection=projection,
        metadata=operation,
    )

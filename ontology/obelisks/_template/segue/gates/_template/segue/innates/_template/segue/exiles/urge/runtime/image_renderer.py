from __future__ import annotations

import base64
import json
import mimetypes
import os
import secrets
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping

from .renderer_slot import renderer_binding


schema = "savant://runtime/urge/image-renderer/1.0.0"
owner = "exile:opus"
renderer_owner = "openai:gpt-image-2"

generation_url = (
    "https://api.openai.com/v1/images/generations"
)

edit_url = (
    "https://api.openai.com/v1/images/edits"
)

default_model = "gpt-image-2"
default_size = "1024x1024"
default_quality = "high"
default_timeout_seconds = 300


class image_renderer_error(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class baseline_image:
    name: str
    media_type: str
    source: str


def _text(
    value: Any,
) -> str:
    if value is None:
        return ""

    if isinstance(
        value,
        str,
    ):
        return value.strip()

    return str(
        value
    ).strip()


def _mapping(
    value: Any,
) -> dict[str, Any]:
    if isinstance(
        value,
        Mapping,
    ):
        return dict(
            value
        )

    return {}


def _first_text(
    source: Mapping[
        str,
        Any,
    ],
    *keys: str,
) -> str:
    for key in keys:
        value = _text(
            source.get(
                key
            )
        )

        if value:
            return value

    return ""


def _collect_strings(
    value: Any,
    *,
    limit: int = 24,
) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()

    def visit(
        candidate: Any,
        depth: int,
    ) -> None:
        if (
            len(output) >= limit
            or depth > 6
            or candidate is None
        ):
            return

        if isinstance(
            candidate,
            str,
        ):
            text = (
                candidate.strip()
            )

            if (
                text
                and text not in seen
                and len(text) <= 2000
            ):
                seen.add(
                    text
                )
                output.append(
                    text
                )

            return

        if isinstance(
            candidate,
            Mapping,
        ):
            for nested in (
                candidate.values()
            ):
                visit(
                    nested,
                    depth + 1,
                )

            return

        if isinstance(
            candidate,
            (
                list,
                tuple,
                set,
            ),
        ):
            for nested in candidate:
                visit(
                    nested,
                    depth + 1,
                )

    visit(
        value,
        0,
    )

    return output


def _candidate_prompt(
    request: Mapping[
        str,
        Any,
    ],
) -> str:
    candidate = _mapping(
        request.get(
            "candidate"
        )
    )

    context = _mapping(
        request.get(
            "context"
        )
    )

    name = ""

    brief = _mapping(
        candidate.get(
            "brief"
        )
    )

    if brief:
        name = _first_text(
            brief,
            "name",
            "identity",
            "title",
        )

    if not name:
        name = _first_text(
            candidate,
            "name",
            "title",
            "identity",
        )

    objective = _first_text(
        context,
        "objective",
    )

    candidate_text = (
        _collect_strings(
            candidate
        )
    )

    evidence = "\n".join(
        "- " + item
        for item in candidate_text
    )

    prompt_parts = [
        (
            "Create a finished professional "
            "logo design image."
        ),
        (
            "This is a logo identity design "
            "iteration, not a mood board, "
            "presentation slide, mockup, "
            "photograph, or explanatory diagram."
        ),
        (
            "Render the logo itself centered "
            "cleanly on a neutral presentation "
            "field with no surrounding devices, "
            "merchandise, walls, paper, hands, "
            "or environmental mockups."
        ),
        (
            "Prioritize proprietary visual logic, "
            "distinctiveness, semantic density, "
            "memorability, legibility, balance, "
            "reproduction quality, and usefulness "
            "as a real identity system."
        ),
        (
            "Avoid generic AI imagery, stock-logo "
            "geometry, gratuitous gradients, "
            "decorative complexity, and visual "
            "effects that do not strengthen the "
            "identity concept."
        ),
    ]

    if name:
        prompt_parts.append(
            "Identity name: "
            + name
        )

    if objective:
        prompt_parts.append(
            "Praxis objective: "
            + objective
        )

    if evidence:
        prompt_parts.append(
            "Authoritative design projection "
            "from Urge:\n"
            + evidence
        )

    prompt_parts.append(
        "Resolve the supplied design projection "
        "into one coherent, production-quality "
        "logo result. Do not display design notes "
        "or prose in the image unless lettering "
        "is intrinsically part of the logo."
    )

    return "\n\n".join(
        prompt_parts
    )


def _api_key() -> str:
    value = os.getenv(
        "OPENAI_API_KEY",
        "",
    ).strip()

    if not value:
        raise image_renderer_error(
            "OPENAI_API_KEY is missing"
        )

    return value


def _model() -> str:
    return (
        os.getenv(
            "SAVANT_URGE_IMAGE_MODEL",
            default_model,
        ).strip()
        or default_model
    )


def _size() -> str:
    return (
        os.getenv(
            "SAVANT_URGE_IMAGE_SIZE",
            default_size,
        ).strip()
        or default_size
    )


def _quality() -> str:
    return (
        os.getenv(
            "SAVANT_URGE_IMAGE_QUALITY",
            default_quality,
        ).strip()
        or default_quality
    )


def _timeout() -> int:
    raw = os.getenv(
        "SAVANT_URGE_IMAGE_TIMEOUT_SECONDS",
        str(
            default_timeout_seconds
        ),
    ).strip()

    try:
        value = int(
            raw
        )
    except ValueError as exc:
        raise image_renderer_error(
            "SAVANT_URGE_IMAGE_TIMEOUT_SECONDS "
            "must be an integer"
        ) from exc

    return max(
        30,
        min(
            value,
            900,
        ),
    )


def _decode_data_url(
    source: str,
) -> tuple[
    str,
    bytes,
]:
    if not source.startswith(
        "data:"
    ):
        raise image_renderer_error(
            "baseline source must be a data URL"
        )

    try:
        header, payload = (
            source.split(
                ",",
                1,
            )
        )
    except ValueError as exc:
        raise image_renderer_error(
            "baseline data URL is malformed"
        ) from exc

    metadata = header[
        len("data:"):
    ]

    pieces = (
        metadata.split(
            ";"
        )
    )

    media_type = (
        pieces[0].strip()
        or "application/octet-stream"
    )

    if (
        "base64"
        not in pieces[1:]
    ):
        raise image_renderer_error(
            "baseline data URL must use base64"
        )

    try:
        binary = (
            base64.b64decode(
                payload,
                validate=True,
            )
        )
    except Exception as exc:
        raise image_renderer_error(
            "baseline image base64 is invalid"
        ) from exc

    if not binary:
        raise image_renderer_error(
            "baseline image is empty"
        )

    return (
        media_type,
        binary,
    )


def _json_request(
    *,
    url: str,
    payload: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    body = json.dumps(
        dict(
            payload
        ),
        ensure_ascii=False,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization":
                "Bearer "
                + _api_key(),
            "Content-Type":
                "application/json",
            "Accept":
                "application/json",
        },
        method="POST",
    )

    return _perform(
        request
    )


def _multipart_body(
    *,
    fields: Mapping[
        str,
        str,
    ],
    file_field: str,
    filename: str,
    media_type: str,
    binary: bytes,
) -> tuple[
    bytes,
    str,
]:
    boundary = (
        "----savant-urge-"
        + secrets.token_hex(
            16
        )
    )

    chunks: list[bytes] = []

    for name, value in (
        fields.items()
    ):
        chunks.extend([
            (
                "--"
                + boundary
                + "\r\n"
            ).encode(
                "ascii"
            ),
            (
                'Content-Disposition: form-data; '
                f'name="{name}"\r\n\r\n'
            ).encode(
                "utf-8"
            ),
            str(
                value
            ).encode(
                "utf-8"
            ),
            b"\r\n",
        ])

    safe_filename = (
        filename.replace(
            '"',
            "",
        )
        or "baseline.png"
    )

    chunks.extend([
        (
            "--"
            + boundary
            + "\r\n"
        ).encode(
            "ascii"
        ),
        (
            'Content-Disposition: form-data; '
            f'name="{file_field}"; '
            f'filename="{safe_filename}"\r\n'
        ).encode(
            "utf-8"
        ),
        (
            "Content-Type: "
            + media_type
            + "\r\n\r\n"
        ).encode(
            "ascii",
            errors="replace",
        ),
        binary,
        b"\r\n",
        (
            "--"
            + boundary
            + "--\r\n"
        ).encode(
            "ascii"
        ),
    ])

    return (
        b"".join(
            chunks
        ),
        boundary,
    )


def _edit_request(
    *,
    prompt: str,
    baseline: baseline_image,
) -> dict[str, Any]:
    detected_type, binary = (
        _decode_data_url(
            baseline.source
        )
    )

    media_type = (
        baseline.media_type
        if baseline.media_type.startswith(
            "image/"
        )
        else detected_type
    )

    filename = (
        baseline.name
        or (
            "baseline"
            + (
                mimetypes.guess_extension(
                    media_type
                )
                or ".png"
            )
        )
    )

    body, boundary = (
        _multipart_body(
            fields={
                "model":
                    _model(),
                "prompt":
                    prompt,
                "size":
                    _size(),
                "quality":
                    _quality(),
            },
            file_field="image",
            filename=filename,
            media_type=media_type,
            binary=binary,
        )
    )

    request = urllib.request.Request(
        edit_url,
        data=body,
        headers={
            "Authorization":
                "Bearer "
                + _api_key(),
            "Content-Type":
                (
                    "multipart/form-data; "
                    "boundary="
                    + boundary
                ),
            "Accept":
                "application/json",
        },
        method="POST",
    )

    return _perform(
        request
    )


def _perform(
    request: urllib.request.Request,
) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(
            request,
            timeout=_timeout(),
        ) as response:
            raw = response.read()

    except urllib.error.HTTPError as exc:
        raw = exc.read()

        try:
            detail = json.loads(
                raw.decode(
                    "utf-8",
                    errors="replace",
                )
            )
        except Exception:
            detail = raw.decode(
                "utf-8",
                errors="replace",
            )

        raise image_renderer_error(
            "image provider returned HTTP "
            + str(
                exc.code
            )
            + ": "
            + json.dumps(
                detail,
                ensure_ascii=False,
            )
            if not isinstance(
                detail,
                str,
            )
            else (
                "image provider returned HTTP "
                + str(
                    exc.code
                )
                + ": "
                + detail
            )
        ) from exc

    except urllib.error.URLError as exc:
        raise image_renderer_error(
            "image provider connection failed: "
            + str(
                exc.reason
            )
        ) from exc

    try:
        payload = json.loads(
            raw.decode(
                "utf-8"
            )
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise image_renderer_error(
            "image provider returned invalid JSON"
        ) from exc

    if not isinstance(
        payload,
        Mapping,
    ):
        raise image_renderer_error(
            "image provider response must be a mapping"
        )

    return dict(
        payload
    )


def _extract_image(
    payload: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    data = payload.get(
        "data"
    )

    if not isinstance(
        data,
        list,
    ) or not data:
        raise image_renderer_error(
            "image provider returned no image data"
        )

    first = data[0]

    if not isinstance(
        first,
        Mapping,
    ):
        raise image_renderer_error(
            "image provider returned invalid image data"
        )

    b64 = _text(
        first.get(
            "b64_json"
        )
    )

    url = _text(
        first.get(
            "url"
        )
    )

    revised_prompt = _text(
        first.get(
            "revised_prompt"
        )
    )

    if b64:
        image = (
            "data:image/png;base64,"
            + b64
        )
    elif url:
        image = url
    else:
        raise image_renderer_error(
            "image provider returned neither "
            "b64_json nor url"
        )

    return {
        "image": image,
        "image_url": image,
        "media_type": (
            "image/png"
        ),
        "revised_prompt": (
            revised_prompt
            or None
        ),
    }


def project_image(
    request: Mapping[
        str,
        Any,
    ],
    *,
    baseline: baseline_image
    | None = None,
) -> dict[str, Any]:
    if not isinstance(
        request,
        Mapping,
    ):
        raise image_renderer_error(
            "renderer request must be a mapping"
        )

    prompt = _candidate_prompt(
        request
    )

    if baseline is None:
        provider_payload = (
            _json_request(
                url=generation_url,
                payload={
                    "model":
                        _model(),
                    "prompt":
                        prompt,
                    "size":
                        _size(),
                    "quality":
                        _quality(),
                },
            )
        )

        operation = "generate"

    else:
        provider_payload = (
            _edit_request(
                prompt=prompt,
                baseline=baseline,
            )
        )

        operation = "edit"

    image = _extract_image(
        provider_payload
    )

    return {
        "schema": schema,
        "owner": owner,
        "provider_owner":
            "exile:opus",
        "renderer_owner":
            renderer_owner,
        "provider": "openai",
        "model": _model(),
        "operation": operation,
        "size": _size(),
        "quality": _quality(),
        "prompt": prompt,
        **image,
        "authority_effect": "none",
        "projection_only": True,
    }


def binding(
    *,
    baseline: Mapping[
        str,
        Any,
    ]
    | None = None,
) -> renderer_binding:
    normalized_baseline = None

    if baseline is not None:
        name = _text(
            baseline.get(
                "name"
            )
        ) or "baseline.png"

        media_type = _text(
            baseline.get(
                "media_type"
            )
        )

        source = _text(
            baseline.get(
                "source"
            )
        )

        if not media_type.startswith(
            "image/"
        ):
            raise image_renderer_error(
                "baseline media_type must be image/*"
            )

        if not source:
            raise image_renderer_error(
                "baseline source is required"
            )

        normalized_baseline = (
            baseline_image(
                name=name,
                media_type=media_type,
                source=source,
            )
        )

    def render(
        request: Mapping[
            str,
            Any,
        ],
    ) -> Mapping[
        str,
        Any,
    ]:
        return project_image(
            request,
            baseline=(
                normalized_baseline
            ),
        )

    return renderer_binding(
        id=(
            "openai:"
            + _model()
        ),
        project=render,
        media_type="image/png",
        owner=renderer_owner,
    )


__all__ = [
    "baseline_image",
    "binding",
    "image_renderer_error",
    "owner",
    "project_image",
    "renderer_owner",
    "schema",
]

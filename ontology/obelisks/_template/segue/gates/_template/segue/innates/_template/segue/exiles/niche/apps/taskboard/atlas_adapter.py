#!/usr/bin/env python3

from __future__ import annotations

import json
import mimetypes
import sys
from http import HTTPStatus
from pathlib import Path
from urllib.parse import unquote, urlparse


schema_version = "savant.niche.atlas-adapter.v1"
authority_effect = "none"
owner = "exile:niche"
projection_only = True
mutation_authority = False

niche_root = Path(
    "/root/savant-runtime"
    "/ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/niche"
)

atlas_root = (
    niche_root
    / "apps"
    / "atlas"
)

atlas_assets_root = (
    atlas_root
    / "assets"
)

atlas_index_path = (
    atlas_assets_root
    / "index.html"
)

if str(atlas_root) not in sys.path:
    sys.path.insert(
        0,
        str(atlas_root),
    )

from atlas_projection import (  # noqa: E402
    atlas_projection,
    self_check as atlas_self_check,
    summary_projection,
)


class AtlasAdapterError(
    RuntimeError
):
    pass


def _request_path(
    handler,
) -> str:
    return urlparse(
        handler.path
    ).path


def _send_security_headers(
    handler,
) -> None:
    handler.send_header(
        "X-Content-Type-Options",
        "nosniff",
    )

    handler.send_header(
        "Referrer-Policy",
        "no-referrer",
    )

    handler.send_header(
        "Cross-Origin-Resource-Policy",
        "same-origin",
    )

    handler.send_header(
        "X-Savant-Authority-Effect",
        authority_effect,
    )

    handler.send_header(
        "X-Savant-Mutation-Authority",
        "false",
    )


def _send_json(
    handler,
    value,
    status: HTTPStatus = HTTPStatus.OK,
) -> None:
    substance = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )

    handler.send_response(
        status
    )

    handler.send_header(
        "Content-Type",
        "application/json; charset=utf-8",
    )

    handler.send_header(
        "Content-Length",
        str(
            len(
                substance
            )
        ),
    )

    handler.send_header(
        "Cache-Control",
        "no-store",
    )

    _send_security_headers(
        handler
    )

    handler.end_headers()

    handler.wfile.write(
        substance
    )


def _resolved_asset(
    relative_path: str,
) -> Path | None:
    try:
        root = atlas_assets_root.resolve(
            strict=True
        )

        candidate = (
            atlas_assets_root
            / relative_path
        ).resolve(
            strict=True
        )

    except (
        FileNotFoundError,
        OSError,
    ):
        return None

    try:
        candidate.relative_to(
            root
        )

    except ValueError:
        return None

    if not candidate.is_file():
        return None

    return candidate


def _send_file(
    handler,
    path: Path,
) -> None:
    substance = path.read_bytes()

    content_type = (
        mimetypes.guess_type(
            path.name
        )[0]
        or "application/octet-stream"
    )

    handler.send_response(
        HTTPStatus.OK
    )

    handler.send_header(
        "Content-Type",
        content_type,
    )

    handler.send_header(
        "Content-Length",
        str(
            len(
                substance
            )
        ),
    )

    handler.send_header(
        "Cache-Control",
        "no-store",
    )

    handler.send_header(
        "Content-Security-Policy",
        (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "base-uri 'none'; "
            "frame-ancestors 'self'"
        ),
    )

    _send_security_headers(
        handler
    )

    handler.end_headers()

    handler.wfile.write(
        substance
    )


def atlas_health_projection():
    return {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "status":
            "ok",
        "owner":
            owner,
        "projection_only":
            True,
        "mutation_authority":
            False,
        "surface":
            "atlas",
    }


def handles_path(
    path: str,
) -> bool:
    return (
        path == "/atlas"
        or path == "/atlas/"
        or path == "/atlas/index.html"
        or path.startswith(
            "/atlas/assets/"
        )
        or path == "/api/atlas"
        or path == "/api/atlas/summary"
        or path == "/api/atlas/self-check"
        or path == "/api/atlas/health"
    )


def try_handle_get(
    handler,
) -> bool:
    path = _request_path(
        handler
    )

    if not handles_path(
        path
    ):
        return False

    try:
        if path == "/api/atlas":
            _send_json(
                handler,
                atlas_projection(),
            )

            return True

        if path == "/api/atlas/summary":
            _send_json(
                handler,
                summary_projection(),
            )

            return True

        if path == "/api/atlas/self-check":
            _send_json(
                handler,
                atlas_self_check(),
            )

            return True

        if path == "/api/atlas/health":
            _send_json(
                handler,
                atlas_health_projection(),
            )

            return True

        if (
            path == "/atlas"
            or path == "/atlas/"
            or path == "/atlas/index.html"
        ):
            if not atlas_index_path.is_file():
                _send_json(
                    handler,
                    {
                        "schema":
                            schema_version,
                        "authority_effect":
                            authority_effect,
                        "status":
                            "frontend-not-installed",
                        "owner":
                            owner,
                        "projection_only":
                            True,
                        "mutation_authority":
                            False,
                    },
                    HTTPStatus.SERVICE_UNAVAILABLE,
                )

                return True

            _send_file(
                handler,
                atlas_index_path,
            )

            return True

        if path.startswith(
            "/atlas/assets/"
        ):
            relative_path = unquote(
                path[
                    len(
                        "/atlas/assets/"
                    ):
                ]
            )

            asset = _resolved_asset(
                relative_path
            )

            if asset is None:
                _send_json(
                    handler,
                    {
                        "schema":
                            schema_version,
                        "authority_effect":
                            authority_effect,
                        "status":
                            "not-found",
                        "owner":
                            owner,
                        "projection_only":
                            True,
                        "mutation_authority":
                            False,
                    },
                    HTTPStatus.NOT_FOUND,
                )

                return True

            _send_file(
                handler,
                asset,
            )

            return True

    except Exception as exc:
        _send_json(
            handler,
            {
                "schema":
                    schema_version,
                "authority_effect":
                    authority_effect,
                "status":
                    "failed",
                "owner":
                    owner,
                "projection_only":
                    True,
                "mutation_authority":
                    False,
                "error":
                    str(
                        exc
                    ),
            },
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

        return True

    return False


def reject_atlas_mutation(
    handler,
) -> bool:
    path = _request_path(
        handler
    )

    if not handles_path(
        path
    ):
        return False

    _send_json(
        handler,
        {
            "schema":
                schema_version,
            "authority_effect":
                authority_effect,
            "status":
                "method-not-allowed",
            "owner":
                owner,
            "projection_only":
                True,
            "mutation_authority":
                False,
        },
        HTTPStatus.METHOD_NOT_ALLOWED,
    )

    return True

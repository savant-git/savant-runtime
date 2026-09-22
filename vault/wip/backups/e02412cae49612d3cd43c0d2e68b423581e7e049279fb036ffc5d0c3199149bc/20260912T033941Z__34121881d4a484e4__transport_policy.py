from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import secrets
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from .deployment import deployment_config


schema = (
    "savant://runtime/palaver/"
    "transport-policy/1.0.0"
)

owner = "exile:palaver"

request_id_pattern = re.compile(
    r"^[a-zA-Z0-9._:-]{1,128}$"
)

safe_methods = frozenset(
    {
        "GET",
        "HEAD",
        "OPTIONS",
        "POST",
    }
)

json_media_types = frozenset(
    {
        "application/json",
        "application/problem+json",
    }
)

no_store_prefixes = (
    "/api/",
)

security_headers = {
    "x-content-type-options":
        "nosniff",
    "x-frame-options":
        "DENY",
    "referrer-policy":
        "no-referrer",
    "permissions-policy":
        (
            "camera=(), geolocation=(), "
            "microphone=(self)"
        ),
    "cross-origin-opener-policy":
        "same-origin",
    "cross-origin-resource-policy":
        "same-origin",
}


class transport_policy_error(
    ValueError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class admission:
    allowed: bool
    status: int
    code: str
    message: str
    request_id: str
    method: str
    path: str
    content_length: int
    content_type: str | None
    origin: str | None
    authority_effect: str = "none"

    def projection(
        self,
    ) -> dict[str, Any]:
        result = {
            "schema":
                schema,
            "owner":
                owner,
            "type":
                "palaver_transport_admission",
            "allowed":
                self.allowed,
            "status":
                self.status,
            "code":
                self.code,
            "message":
                self.message,
            "request_id":
                self.request_id,
            "method":
                self.method,
            "path":
                self.path,
            "content_length":
                self.content_length,
            "content_type":
                self.content_type,
            "origin":
                self.origin,
            "authority_effect":
                self.authority_effect,
            "boundaries": {
                "executes_provider":
                    False,
                "owns_persona":
                    False,
                "mutates_conversation":
                    False,
                "mutates_files":
                    False,
                "creates_authority":
                    False,
            },
        }

        result[
            "projection_digest"
        ] = digest(
            {
                key: value
                for key, value
                in result.items()
                if key
                != "request_id"
            }
        )

        return result


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        allow_nan=False,
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def request_id(
    supplied: str | None = None,
) -> str:
    candidate = str(
        supplied
        or ""
    ).strip()

    if (
        candidate
        and request_id_pattern.fullmatch(
            candidate
        )
    ):
        return candidate

    return (
        "palreq_"
        + secrets.token_hex(
            16
        )
    )


def normalized_method(
    value: Any,
) -> str:
    method = str(
        value
        or ""
    ).strip().upper()

    if not method:
        raise transport_policy_error(
            "request method is empty"
        )

    return method


def normalized_path(
    value: Any,
) -> str:
    raw = str(
        value
        or "/"
    )

    split = urlsplit(
        raw
    )

    path = split.path or "/"

    if not path.startswith(
        "/"
    ):
        raise transport_policy_error(
            "request path must be absolute"
        )

    if "\x00" in path:
        raise transport_policy_error(
            "request path contains null byte"
        )

    if len(path) > 4096:
        raise transport_policy_error(
            "request path is too long"
        )

    segments = path.split(
        "/"
    )

    if any(
        segment
        in {
            ".",
            "..",
        }
        for segment
        in segments
    ):
        raise transport_policy_error(
            "request path traversal rejected"
        )

    return path


def query_size(
    raw_target: Any,
) -> int:
    target = str(
        raw_target
        or ""
    )

    query = urlsplit(
        target
    ).query

    return len(
        query.encode(
            "utf-8"
        )
    )


def normalized_content_length(
    value: Any,
) -> int:
    if value in (
        None,
        "",
    ):
        return 0

    raw = str(
        value
    ).strip()

    if not raw:
        return 0

    if not raw.isdigit():
        raise transport_policy_error(
            "invalid content-length"
        )

    result = int(
        raw
    )

    if result < 0:
        raise transport_policy_error(
            "negative content-length"
        )

    return result


def normalized_content_type(
    value: Any,
) -> str | None:
    raw = str(
        value
        or ""
    ).strip()

    if not raw:
        return None

    media_type = raw.split(
        ";",
        1,
    )[0].strip().casefold()

    if not media_type:
        return None

    return media_type


def normalized_origin(
    value: Any,
) -> str | None:
    raw = str(
        value
        or ""
    ).strip()

    if not raw:
        return None

    parsed = urlsplit(
        raw
    )

    if parsed.scheme not in {
        "http",
        "https",
    }:
        raise transport_policy_error(
            "unsupported origin scheme"
        )

    if (
        not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in (
            "",
            "/",
        )
        or parsed.query
        or parsed.fragment
    ):
        raise transport_policy_error(
            "invalid origin"
        )

    host = parsed.hostname.casefold()

    if ":" in host:
        host = f"[{host}]"

    authority = host

    if parsed.port is not None:
        authority += (
            ":"
            + str(
                parsed.port
            )
        )

    return (
        parsed.scheme.casefold()
        + "://"
        + authority
    )


def normalized_header_count(
    headers: Mapping[
        str,
        Any,
    ],
) -> int:
    return len(
        headers
    )


def header_bytes(
    headers: Mapping[
        str,
        Any,
    ],
) -> int:
    total = 0

    for key, value in headers.items():
        total += len(
            str(
                key
            ).encode(
                "utf-8"
            )
        )

        total += len(
            str(
                value
            ).encode(
                "utf-8"
            )
        )

        total += 4

    return total


def header_value(
    headers: Mapping[
        str,
        Any,
    ],
    name: str,
) -> str | None:
    wanted = name.casefold()

    for key, value in headers.items():
        if str(
            key
        ).casefold() == wanted:
            return str(
                value
            )

    return None


def same_origin(
    origin: str,
    *,
    host: str,
    port: int,
    tls: bool,
) -> bool:
    scheme = (
        "https"
        if tls
        else "http"
    )

    expected_host = host

    if host in {
        "0.0.0.0",
        "::",
    }:
        return False

    if ":" in expected_host:
        expected_host = (
            "["
            + expected_host
            + "]"
        )

    expected = (
        scheme
        + "://"
        + expected_host
        + ":"
        + str(
            port
        )
    )

    return (
        origin.casefold()
        == expected.casefold()
    )


def origin_allowed(
    origin: str | None,
    config: deployment_config,
) -> bool:
    if origin is None:
        return True

    if same_origin(
        origin,
        host=config.host,
        port=config.port,
        tls=config.tls_enabled,
    ):
        return True

    allowed = {
        value.casefold()
        for value
        in config.allowed_origins
    }

    return (
        origin.casefold()
        in allowed
    )


def trusted_proxy(
    address: str | None,
    config: deployment_config,
) -> bool:
    if not address:
        return False

    candidate = str(
        address
    ).strip()

    if not candidate:
        return False

    for raw in config.trusted_proxies:
        value = raw.strip()

        if not value:
            continue

        try:
            network = ipaddress.ip_network(
                value,
                strict=False,
            )

            address_value = (
                ipaddress.ip_address(
                    candidate
                )
            )

            if address_value in network:
                return True

            continue

        except ValueError:
            pass

        if (
            candidate.casefold()
            == value.casefold()
        ):
            return True

    return False


def forwarded_client(
    *,
    peer: str | None,
    forwarded_for: str | None,
    config: deployment_config,
) -> str | None:
    if (
        not config.reverse_proxy
        or not config.forwarded_headers
        or not trusted_proxy(
            peer,
            config,
        )
    ):
        return peer

    raw = str(
        forwarded_for
        or ""
    ).strip()

    if not raw:
        return peer

    first = raw.split(
        ",",
        1,
    )[0].strip()

    if not first:
        return peer

    try:
        return str(
            ipaddress.ip_address(
                first
            )
        )
    except ValueError:
        return peer


def response_headers(
    *,
    path: str,
    request_identifier: str,
    origin: str | None,
    config: deployment_config,
) -> dict[str, str]:
    headers = dict(
        security_headers
    )

    headers[
        "x-palaver-request-id"
    ] = request_identifier

    headers[
        "x-palaver-owner"
    ] = owner

    if path.startswith(
        no_store_prefixes
    ):
        headers[
            "cache-control"
        ] = (
            "no-store, "
            "max-age=0"
        )

        headers[
            "pragma"
        ] = "no-cache"

    if (
        origin
        and origin_allowed(
            origin,
            config,
        )
    ):
        headers[
            "access-control-allow-origin"
        ] = origin

        headers[
            "vary"
        ] = "Origin"

    return headers


def public_error(
    *,
    status: int,
    code: str,
    message: str,
    request_identifier: str,
) -> dict[str, Any]:
    return {
        "ok": False,
        "error": message,
        "error_code": code,
        "request_id":
            request_identifier,
        "authority_effect":
            "none",
    }


def admit(
    *,
    method: Any,
    target: Any,
    headers: Mapping[
        str,
        Any,
    ],
    config: deployment_config,
    request_identifier: str | None = None,
    maximum_header_count: int = 128,
    maximum_header_bytes: int = 65536,
    maximum_query_bytes: int = 16384,
) -> admission:
    identifier = request_id(
        request_identifier
        or header_value(
            headers,
            "x-request-id",
        )
    )

    try:
        normalized_request_method = (
            normalized_method(
                method
            )
        )

        path = normalized_path(
            target
        )

        if (
            normalized_request_method
            not in safe_methods
        ):
            return admission(
                allowed=False,
                status=405,
                code="method_not_allowed",
                message=(
                    "Request method is not "
                    "supported by Palaver."
                ),
                request_id=identifier,
                method=
                    normalized_request_method,
                path=path,
                content_length=0,
                content_type=None,
                origin=None,
            )

        if (
            normalized_header_count(
                headers
            )
            > maximum_header_count
        ):
            return admission(
                allowed=False,
                status=431,
                code="too_many_headers",
                message=(
                    "Request contains too "
                    "many headers."
                ),
                request_id=identifier,
                method=
                    normalized_request_method,
                path=path,
                content_length=0,
                content_type=None,
                origin=None,
            )

        if (
            header_bytes(
                headers
            )
            > maximum_header_bytes
        ):
            return admission(
                allowed=False,
                status=431,
                code="headers_too_large",
                message=(
                    "Request headers are "
                    "too large."
                ),
                request_id=identifier,
                method=
                    normalized_request_method,
                path=path,
                content_length=0,
                content_type=None,
                origin=None,
            )

        if (
            query_size(
                target
            )
            > maximum_query_bytes
        ):
            return admission(
                allowed=False,
                status=414,
                code="query_too_large",
                message=(
                    "Request query is "
                    "too large."
                ),
                request_id=identifier,
                method=
                    normalized_request_method,
                path=path,
                content_length=0,
                content_type=None,
                origin=None,
            )

        length = (
            normalized_content_length(
                header_value(
                    headers,
                    "content-length",
                )
            )
        )

        content_type = (
            normalized_content_type(
                header_value(
                    headers,
                    "content-type",
                )
            )
        )

        origin = (
            normalized_origin(
                header_value(
                    headers,
                    "origin",
                )
            )
        )

        if (
            length
            > config.request_body_limit_bytes
        ):
            return admission(
                allowed=False,
                status=413,
                code="request_body_too_large",
                message=(
                    "Request body exceeds "
                    "Palaver's configured limit."
                ),
                request_id=identifier,
                method=
                    normalized_request_method,
                path=path,
                content_length=length,
                content_type=content_type,
                origin=origin,
            )

        if (
            normalized_request_method
            == "POST"
            and length > 0
            and content_type
            not in json_media_types
        ):
            return admission(
                allowed=False,
                status=415,
                code="unsupported_media_type",
                message=(
                    "Palaver accepts JSON "
                    "request bodies."
                ),
                request_id=identifier,
                method=
                    normalized_request_method,
                path=path,
                content_length=length,
                content_type=content_type,
                origin=origin,
            )

        if not origin_allowed(
            origin,
            config,
        ):
            return admission(
                allowed=False,
                status=403,
                code="origin_not_allowed",
                message=(
                    "Request origin is not "
                    "allowed by Palaver."
                ),
                request_id=identifier,
                method=
                    normalized_request_method,
                path=path,
                content_length=length,
                content_type=content_type,
                origin=origin,
            )

        return admission(
            allowed=True,
            status=200,
            code="admitted",
            message="Request admitted.",
            request_id=identifier,
            method=
                normalized_request_method,
            path=path,
            content_length=length,
            content_type=content_type,
            origin=origin,
        )

    except transport_policy_error:
        return admission(
            allowed=False,
            status=400,
            code="invalid_request",
            message=(
                "Request failed Palaver "
                "transport validation."
            ),
            request_id=identifier,
            method=str(
                method
                or ""
            ).upper(),
            path="/",
            content_length=0,
            content_type=None,
            origin=None,
        )

#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Type


palaver_runtime_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/palaver/runtime"
).resolve()

savant_root = Path(
    "/root/savant-runtime"
).resolve()

palaver_runtime_text = str(
    palaver_runtime_root
)

savant_root_text = str(
    savant_root
)

if palaver_runtime_text not in sys.path:
    sys.path.insert(
        0,
        palaver_runtime_text,
    )

if savant_root_text not in sys.path:
    sys.path.insert(
        1,
        savant_root_text,
    )


try:
    from .deployment import (
        deployment_config,
        load_config,
    )

    from .transport_policy import (
        admit,
        admission,
        public_error,
        response_headers,
    )

except ImportError:
    from deployment import (
        deployment_config,
        load_config,
    )

    from transport_policy import (
        admit,
        admission,
        public_error,
        response_headers,
    )


schema = (
    "savant://runtime/palaver/"
    "transport-integration/1.0.1"
)

owner = "exile:palaver"


class transport_integration_error(
    RuntimeError
):
    pass


def _header_mapping(
    handler: Any,
) -> Mapping[str, Any]:
    headers = getattr(
        handler,
        "headers",
        None,
    )

    if headers is None:
        return {}

    if hasattr(
        headers,
        "items",
    ):
        return headers

    return {}


def _request_origin(
    decision: admission,
) -> str | None:
    return decision.origin


def _write_json(
    handler: Any,
    payload: Mapping[str, Any],
    status: int,
) -> None:
    body = json.dumps(
        dict(
            payload
        ),
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        allow_nan=False,
        default=str,
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
                body
            )
        ),
    )

    handler.end_headers()

    if (
        getattr(
            handler,
            "command",
            "",
        )
        != "HEAD"
    ):
        handler.wfile.write(
            body
        )


def _reject(
    handler: Any,
    decision: admission,
) -> None:
    payload = public_error(
        status=decision.status,
        code=decision.code,
        message=decision.message,
        request_identifier=
            decision.request_id,
    )

    _write_json(
        handler,
        payload,
        decision.status,
    )


def _admit_handler(
    handler: Any,
    *,
    method: str,
    config: deployment_config,
) -> admission:
    decision = admit(
        method=method,
        target=getattr(
            handler,
            "path",
            "/",
        ),
        headers=_header_mapping(
            handler
        ),
        config=config,
    )

    handler._palaver_transport_admission = (
        decision
    )

    handler._palaver_request_id = (
        decision.request_id
    )

    return decision


def make_transport_handler(
    canonical_factory: Callable[
        [Any],
        Type[Any],
    ],
    legacy: Any,
    *,
    config: deployment_config | None = None,
) -> Type[Any]:
    if not callable(
        canonical_factory
    ):
        raise transport_integration_error(
            "canonical handler factory "
            "must be callable"
        )

    active_config = (
        config
        if config is not None
        else load_config()
    )

    canonical_handler = (
        canonical_factory(
            legacy
        )
    )

    if not isinstance(
        canonical_handler,
        type,
    ):
        raise transport_integration_error(
            "canonical handler factory "
            "did not return a handler class"
        )

    class TransportCanonicalHandler(
        canonical_handler
    ):
        palaver_transport_schema = schema
        palaver_transport_owner = owner
        palaver_transport_config = (
            active_config
        )

        def _palaver_admit(
            self,
            method: str,
        ) -> bool:
            decision = (
                _admit_handler(
                    self,
                    method=method,
                    config=active_config,
                )
            )

            if decision.allowed:
                return True

            _reject(
                self,
                decision,
            )

            return False

        def end_headers(
            self,
        ) -> None:
            decision = getattr(
                self,
                "_palaver_transport_admission",
                None,
            )

            identifier = getattr(
                self,
                "_palaver_request_id",
                None,
            )

            if identifier is None:
                fallback = admit(
                    method=getattr(
                        self,
                        "command",
                        "GET",
                    ),
                    target=getattr(
                        self,
                        "path",
                        "/",
                    ),
                    headers=_header_mapping(
                        self
                    ),
                    config=active_config,
                )

                decision = fallback
                identifier = (
                    fallback.request_id
                )

                self._palaver_request_id = (
                    identifier
                )

            path = (
                decision.path
                if isinstance(
                    decision,
                    admission,
                )
                else "/"
            )

            origin = (
                _request_origin(
                    decision
                )
                if isinstance(
                    decision,
                    admission,
                )
                else None
            )

            headers = response_headers(
                path=path,
                request_identifier=
                    identifier,
                origin=origin,
                config=active_config,
            )

            for (
                name,
                value,
            ) in headers.items():
                self.send_header(
                    name,
                    value,
                )

            super().end_headers()

        def do_GET(
            self,
        ) -> None:
            self.command = "GET"

            if not self._palaver_admit(
                "GET"
            ):
                return

            super().do_GET()

        def do_POST(
            self,
        ) -> None:
            self.command = "POST"

            if not self._palaver_admit(
                "POST"
            ):
                return

            super().do_POST()

        def do_HEAD(
            self,
        ) -> None:
            self.command = "HEAD"

            if not self._palaver_admit(
                "HEAD"
            ):
                return

            parent = getattr(
                super(),
                "do_HEAD",
                None,
            )

            if callable(
                parent
            ):
                parent()
                return

            self.send_response(
                200
            )

            self.end_headers()

        def do_OPTIONS(
            self,
        ) -> None:
            self.command = "OPTIONS"

            if not self._palaver_admit(
                "OPTIONS"
            ):
                return

            self.send_response(
                204
            )

            self.send_header(
                "Allow",
                "GET, HEAD, OPTIONS, POST",
            )

            self.send_header(
                "Access-Control-Allow-Methods",
                "GET, HEAD, OPTIONS, POST",
            )

            self.send_header(
                "Access-Control-Allow-Headers",
                (
                    "Content-Type, "
                    "X-Request-ID"
                ),
            )

            self.send_header(
                "Access-Control-Max-Age",
                "600",
            )

            self.end_headers()

        def do_PUT(
            self,
        ) -> None:
            self.command = "PUT"

            self._palaver_admit(
                "PUT"
            )

        def do_PATCH(
            self,
        ) -> None:
            self.command = "PATCH"

            self._palaver_admit(
                "PATCH"
            )

        def do_DELETE(
            self,
        ) -> None:
            self.command = "DELETE"

            self._palaver_admit(
                "DELETE"
            )

        def do_TRACE(
            self,
        ) -> None:
            self.command = "TRACE"

            self._palaver_admit(
                "TRACE"
            )

        def log_message(
            self,
            format: str,
            *args: Any,
        ) -> None:
            return None

    TransportCanonicalHandler.__name__ = (
        "PalaverTransportCanonicalHandler"
    )

    TransportCanonicalHandler.__qualname__ = (
        "PalaverTransportCanonicalHandler"
    )

    return TransportCanonicalHandler


def install(
    server_module: Any,
    *,
    config: deployment_config | None = None,
) -> None:
    original = getattr(
        server_module,
        "make_canonical_handler",
        None,
    )

    if not callable(
        original
    ):
        raise transport_integration_error(
            "Palaver canonical handler "
            "factory is unavailable"
        )

    if getattr(
        server_module,
        "_palaver_transport_installed",
        False,
    ):
        return

    active_config = (
        config
        if config is not None
        else load_config()
    )

    def hardened_factory(
        legacy: Any,
    ) -> Type[Any]:
        return make_transport_handler(
            original,
            legacy,
            config=active_config,
        )

    hardened_factory.__name__ = (
        "make_transport_canonical_handler"
    )

    server_module.make_canonical_handler = (
        hardened_factory
    )

    server_module._palaver_transport_original_factory = (
        original
    )

    server_module._palaver_transport_config = (
        active_config
    )

    server_module._palaver_transport_installed = (
        True
    )


def integration_status(
    server_module: Any,
) -> dict[str, Any]:
    installed = bool(
        getattr(
            server_module,
            "_palaver_transport_installed",
            False,
        )
    )

    config = getattr(
        server_module,
        "_palaver_transport_config",
        None,
    )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "installed":
            installed,
        "canonical_server":
            (
                "palaver.runtime.server"
            ),
        "execution_mode":
            (
                "direct-module-file"
            ),
        "root_runtime_namespace_reserved":
            True,
        "transport_factory":
            getattr(
                getattr(
                    server_module,
                    "make_canonical_handler",
                    None,
                ),
                "__name__",
                None,
            ),
        "configuration":
            (
                config.semantic_projection()
                if isinstance(
                    config,
                    deployment_config,
                )
                else None
            ),
        "enhancements": [
            "pre-body request admission",
            "request body bounds",
            "header count bounds",
            "header byte bounds",
            "query bounds",
            "method restriction",
            "media type validation",
            "path traversal rejection",
            "origin normalization",
            "origin allowlisting",
            "request identity propagation",
            "no-store api policy",
            "browser security headers",
            "trusted proxy policy",
            "sanitized transport errors",
            "options preflight handling",
            "head compatibility",
            "request log suppression",
            "root runtime namespace preservation",
        ],
        "ownership": {
            "conversation":
                "palaver",
            "provider":
                "opus",
            "persona":
                "envoy",
            "voice":
                "envoy",
            "task":
                "niche",
            "mutation":
                "coda",
        },
        "boundaries": {
            "replaces_canonical_server":
                False,
            "replaces_root_runtime":
                False,
            "executes_provider":
                False,
            "owns_persona":
                False,
            "owns_task":
                False,
            "owns_mutation":
                False,
            "creates_authority":
                False,
        },
        "authority_effect":
            "none",
    }


def _server_module() -> Any:
    if __package__:
        from . import server

        return server

    import server

    return server


def main() -> int:
    server = _server_module()

    config = load_config()

    install(
        server,
        config=config,
    )

    if (
        "--inspect"
        in sys.argv[1:]
    ):
        legacy = (
            server.bootstrap()
        )

        print(
            json.dumps(
                {
                    "transport":
                        integration_status(
                            server
                        ),
                    "palaver":
                        server.compatibility_status(
                            legacy
                        ),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            )
        )

        return 0

    return int(
        server.main()
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

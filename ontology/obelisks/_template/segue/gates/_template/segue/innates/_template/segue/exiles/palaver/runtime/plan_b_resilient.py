#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys

from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4


PALAVER_RUNTIME = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/palaver/runtime"
)

OPUS_RUNTIME = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/opus/runtime"
)

SCHEMA = "savant.palaver.plan-b-resilient.v2"

DEFAULT_PERSONA_ID = "orobouros"

DEFAULT_HOST = "127.0.0.1"

DEFAULT_PORT = 8788


for path in (
    PALAVER_RUNTIME,
    OPUS_RUNTIME,
):
    value = str(path)

    if value not in sys.path:
        sys.path.insert(
            0,
            value,
        )


import plan_b

from resilient_text import (
    execute_text_request_resilient,
    projection as opus_projection,
)
from .json_encoding import json_bytes as _json_bytes


class PalaverPlanBError(
    RuntimeError
):
    pass


def _text(
    value: Any,
) -> str:
    return str(
        value
        or ""
    ).strip()


def infer(
    *,
    message: str,
    persona_id: str = DEFAULT_PERSONA_ID,
    context: str = "",
) -> dict[str, Any]:
    message = _text(
        message
    )

    if not message:
        raise PalaverPlanBError(
            "message is required"
        )

    persona_id = (
        _text(
            persona_id
        )
        or DEFAULT_PERSONA_ID
    )

    persona_projection = (
        plan_b.project_persona(
            persona_id,
            message,
        )
    )

    system_prompt = (
        plan_b.persona_system_prompt(
            persona_projection
        )
    )

    request = {
        "owner": "palaver",
        "message": message,
        "system": system_prompt,
        "context": _text(
            context
        ),
    }

    result = (
        execute_text_request_resilient(
            request
        )
    )

    if not isinstance(
        result,
        dict,
    ):
        raise PalaverPlanBError(
            "opus result must be an object"
        )

    response_text = _text(
        result.get(
            "text"
        )
    )

    tool_calls = (
        result.get(
            "tool_calls"
        )
        or []
    )

    if (
        not response_text
        and not tool_calls
    ):
        raise PalaverPlanBError(
            "opus returned neither "
            "text nor tool calls"
        )

    lineage = (
        result.get(
            "lineage"
        )
        or {}
    )

    if not isinstance(
        lineage,
        dict,
    ):
        lineage = {}

    return {
        "schema": SCHEMA,
        "ok": True,
        "request_id": uuid4().hex,
        "owner": "palaver",
        "persona_owner": "envoy",
        "execution_owner": "opus",
        "persona": {
            "persona_id": (
                persona_projection.get(
                    "persona_id"
                )
            ),
            "display_name": (
                persona_projection.get(
                    "display_name"
                )
            ),
            "baseline_version": (
                persona_projection.get(
                    "baseline_version"
                )
            ),
            "composition_digest": (
                persona_projection.get(
                    "composition_digest"
                )
            ),
            "living_trait_crown": (
                persona_projection.get(
                    "living_trait_crown"
                )
                or []
            ),
            "degraded": bool(
                persona_projection.get(
                    "degraded"
                )
            ),
            "degradation": (
                persona_projection.get(
                    "degradation"
                )
            ),
        },
        "response": {
            "text": response_text,
            "tool_calls": tool_calls,
        },
        "lineage": lineage,
        "authority": {
            "conversation": "palaver",
            "persona": "envoy",
            "provider_execution": "opus",
            "provider_fallback": "opus",
            "authority_effect": "none",
        },
        "compatibility": {
            "legacy_server_required": False,
            "legacy_webui_required": False,
            "graph_required": False,
            "voice_required": False,
        },
    }


def health() -> dict[str, Any]:
    base = plan_b.health()

    try:
        resilient = (
            opus_projection()
        )

        resilient_state = "ready"

    except Exception as exc:
        resilient = {
            "owner": "opus",
            "state": "unavailable",
            "diagnostic": (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
            "authority_effect": "none",
        }

        resilient_state = (
            "unavailable"
        )

    return {
        "schema": SCHEMA,
        "mode": "plan_b_resilient",
        "owner": "palaver",
        "ready": (
            bool(
                base.get(
                    "ready"
                )
            )
            and resilient_state
            == "ready"
        ),
        "palaver": base,
        "opus_resilient": resilient,
        "legacy_server_required": False,
        "legacy_webui_required": False,
        "graph_required": False,
        "voice_required": False,
        "authority_effect": "none",
    }


def _error_projection(
    exc: Exception,
) -> dict[str, Any]:
    diagnostic = _text(
        exc
    )

    lowered = (
        diagnostic.lower()
    )

    if (
        "429" in lowered
        or "too many requests"
        in lowered
        or "rate limit"
        in lowered
    ):
        code = (
            "inference_rate_limited"
        )

        status = 429

    elif (
        "401" in lowered
        or "unauthorized"
        in lowered
        or "authentication"
        in lowered
    ):
        code = (
            "inference_authentication_failed"
        )

        status = 503

    elif (
        "timeout" in lowered
        or "timed out"
        in lowered
    ):
        code = "inference_timeout"

        status = 504

    elif (
        "all eligible text providers failed"
        in lowered
    ):
        code = (
            "all_inference_providers_failed"
        )

        status = 503

    elif (
        "message is required"
        in lowered
    ):
        code = "invalid_request"

        status = 400

    else:
        code = "inference_failed"

        status = 503

    return {
        "schema": SCHEMA,
        "ok": False,
        "error": code,
        "message": diagnostic,
        "http_status": status,
        "authority_effect": "none",
    }


class Handler(
    BaseHTTPRequestHandler
):
    server_version = (
        "palaver-plan-b/2"
    )

    def log_message(
        self,
        format: str,
        *args: Any,
    ) -> None:
        return

    def _send(
        self,
        status: int,
        value: dict[str, Any],
    ) -> None:
        encoded = _json_bytes(
            value
        )

        self.send_response(
            status
        )

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(
                len(
                    encoded
                )
            ),
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.end_headers()

        self.wfile.write(
            encoded
        )

    def _body(
        self,
    ) -> dict[str, Any]:
        length = int(
            self.headers.get(
                "Content-Length",
                "0",
            )
            or 0
        )

        if length <= 0:
            return {}

        raw = self.rfile.read(
            length
        )

        value = json.loads(
            raw.decode(
                "utf-8"
            )
        )

        if not isinstance(
            value,
            dict,
        ):
            raise PalaverPlanBError(
                "request body must "
                "be an object"
            )

        return value

    def do_GET(
        self,
    ) -> None:
        path = urlparse(
            self.path
        ).path.rstrip(
            "/"
        )

        if path in (
            "",
            "/health",
        ):
            self._send(
                200,
                health(),
            )

            return

        self._send(
            404,
            {
                "schema": SCHEMA,
                "ok": False,
                "error": "not_found",
                "authority_effect": "none",
            },
        )

    def do_POST(
        self,
    ) -> None:
        path = urlparse(
            self.path
        ).path.rstrip(
            "/"
        )

        if path not in (
            "/infer",
            "/chat",
            "/message",
        ):
            self._send(
                404,
                {
                    "schema": SCHEMA,
                    "ok": False,
                    "error": "not_found",
                    "authority_effect": "none",
                },
            )

            return

        try:
            body = self._body()

            result = infer(
                message=(
                    body.get(
                        "message"
                    )
                    or body.get(
                        "text"
                    )
                    or body.get(
                        "prompt"
                    )
                    or ""
                ),
                persona_id=(
                    body.get(
                        "persona_id"
                    )
                    or body.get(
                        "persona"
                    )
                    or DEFAULT_PERSONA_ID
                ),
                context=(
                    body.get(
                        "context"
                    )
                    or ""
                ),
            )

            self._send(
                200,
                result,
            )

        except Exception as exc:
            error = (
                _error_projection(
                    exc
                )
            )

            self._send(
                int(
                    error[
                        "http_status"
                    ]
                ),
                error,
            )


def serve(
    *,
    host: str,
    port: int,
) -> None:
    server = ThreadingHTTPServer(
        (
            host,
            port,
        ),
        Handler,
    )

    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "ok": True,
                "mode": (
                    "plan_b_resilient"
                ),
                "host": host,
                "port": port,
                "health": (
                    f"http://{host}:{port}/health"
                ),
                "infer": (
                    f"http://{host}:{port}/infer"
                ),
                "chat": (
                    f"http://{host}:{port}/chat"
                ),
                "legacy_server_required": False,
                "legacy_webui_required": False,
                "authority_effect": "none",
            },
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )

    server.serve_forever()


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        prog="palaver"
    )

    value.add_argument(
        "--message",
    )

    value.add_argument(
        "--persona",
        default=DEFAULT_PERSONA_ID,
    )

    value.add_argument(
        "--context",
        default="",
    )

    value.add_argument(
        "--health",
        action="store_true",
    )

    value.add_argument(
        "--serve",
        action="store_true",
    )

    value.add_argument(
        "--host",
        default=DEFAULT_HOST,
    )

    value.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
    )

    return value


def main() -> int:
    args = parser().parse_args()

    try:
        if args.health:
            payload = health()

            print(
                json.dumps(
                    payload,
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )

            return 0

        if args.serve:
            serve(
                host=args.host,
                port=args.port,
            )

            return 0

        if args.message:
            payload = infer(
                message=args.message,
                persona_id=args.persona,
                context=args.context,
            )

            print(
                json.dumps(
                    payload,
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )

            return 0

        raise PalaverPlanBError(
            "use --health, --serve, "
            "or --message"
        )

    except KeyboardInterrupt:
        return 130

    except Exception as exc:
        error = _error_projection(
            exc
        )

        print(
            json.dumps(
                error,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

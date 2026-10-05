#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
import traceback

from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from uuid import uuid4


root = Path(
    "/root/savant-runtime"
)

exiles_root = (
    root
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
)

palaver_root = (
    exiles_root
    / "palaver"
)

envoy_root = (
    exiles_root
    / "envoy"
)

envoy_runtime = (
    envoy_root
    / "runtime"
)

envoy_personas = (
    envoy_root
    / "registry"
    / "personas"
)

opus_root = (
    exiles_root
    / "opus"
)

opus_runtime = (
    opus_root
    / "runtime"
)

default_persona_id = "orobouros"

schema = (
    "savant.palaver.plan-b.v1"
)

runtime_owner = "palaver"

persona_owner = "envoy"

execution_owner = "opus"


class plan_b_error(
    RuntimeError
):
    pass


def utc_now() -> str:
    return (
        datetime.now(
            timezone.utc
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


def normalize_terms(
    value: str,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            set(
                re.findall(
                    r"[a-z0-9_]+",
                    str(
                        value
                        or ""
                    ).lower(),
                )
            )
        )
    )


def install_import_paths() -> None:
    required = (
        envoy_runtime,
        opus_runtime,
    )

    missing = [
        str(path)
        for path in required
        if not path.is_dir()
    ]

    if missing:
        raise plan_b_error(
            "required runtime paths missing: "
            + ", ".join(
                missing
            )
        )

    for path in reversed(
        required
    ):
        value = str(
            path
        )

        if value not in sys.path:
            sys.path.insert(
                0,
                value,
            )


def read_json(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        value,
        dict,
    ):
        raise plan_b_error(
            f"expected JSON object: {path}"
        )

    return value


def persona_registry_fallback(
    persona_id: str,
) -> dict[str, Any]:
    path = (
        envoy_personas
        / f"{persona_id}.json"
    )

    raw = read_json(
        path
    )

    declared = str(
        raw.get(
            "persona_id"
        )
        or ""
    ).strip()

    if declared != persona_id:
        raise plan_b_error(
            "persona registry identity mismatch: "
            f"requested={persona_id!r} "
            f"declared={declared!r}"
        )

    if str(
        raw.get(
            "exile"
        )
        or ""
    ).strip() != "envoy":
        raise plan_b_error(
            "persona registry owner is not envoy"
        )

    baseline_raw = raw.get(
        "baseline"
    )

    baseline = (
        [
            str(value)
            for value
            in baseline_raw
        ]
        if isinstance(
            baseline_raw,
            list,
        )
        else []
    )

    return {
        "schema": (
            "savant.envoy."
            "persona-registry-fallback.v1"
        ),
        "owner": "envoy",
        "persona_id": persona_id,
        "display_name": str(
            raw.get(
                "display_name"
            )
            or persona_id
        ),
        "baseline_version": (
            (
                raw.get(
                    "identity"
                )
                or {}
            ).get(
                "baseline_version"
            )
            if isinstance(
                raw.get(
                    "identity"
                ),
                dict,
            )
            else None
        ),
        "baseline": baseline,
        "traits": [],
        "living_trait_crown": [],
        "composition_digest": None,
        "degraded": True,
        "degradation": {
            "component": (
                "envoy_dynamic_composition"
            ),
            "state": "unavailable",
            "authority_effect": "none",
            "fallback": (
                "envoy_persona_registry_baseline"
            ),
        },
    }


def project_persona(
    persona_id: str,
    message: str,
) -> dict[str, Any]:
    install_import_paths()

    try:
        from persona_engine import (
            compose_persona,
        )

        projection = compose_persona(
            persona_id=persona_id,
            signals=normalize_terms(
                message
            ),
        )

        if not isinstance(
            projection,
            dict,
        ):
            raise plan_b_error(
                "envoy projection must be object"
            )

        if projection.get(
            "owner"
        ) != persona_owner:
            raise plan_b_error(
                "envoy projection owner mismatch"
            )

        if str(
            projection.get(
                "persona_id"
            )
            or ""
        ).strip() != persona_id:
            raise plan_b_error(
                "envoy persona identity mismatch"
            )

        projection = dict(
            projection
        )

        projection[
            "degraded"
        ] = False

        projection[
            "degradation"
        ] = None

        return projection

    except Exception as exc:
        projection = (
            persona_registry_fallback(
                persona_id
            )
        )

        projection[
            "degradation"
        ][
            "diagnostic"
        ] = (
            f"{type(exc).__name__}: {exc}"
        )

        return projection


def persona_system_prompt(
    projection: dict[str, Any],
) -> str:
    lines = [
        "ENVOY PERSONA PROJECTION",
        (
            "persona_id: "
            + str(
                projection.get(
                    "persona_id"
                )
                or default_persona_id
            )
        ),
        (
            "display_name: "
            + str(
                projection.get(
                    "display_name"
                )
                or ""
            )
        ),
        (
            "baseline_version: "
            + str(
                projection.get(
                    "baseline_version"
                )
                or ""
            )
        ),
        "",
        "Permanent baseline:",
    ]

    baseline = (
        projection.get(
            "baseline"
        )
        or []
    )

    if not baseline:
        lines.append(
            "- none declared"
        )

    for value in baseline:
        lines.append(
            "- "
            + str(
                value
            )
        )

    lines.extend(
        [
            "",
            "Living Trait Crown:",
        ]
    )

    traits = (
        projection.get(
            "traits"
        )
        or []
    )

    if not traits:
        lines.append(
            "- none selected"
        )

    for trait in traits:
        if not isinstance(
            trait,
            dict,
        ):
            continue

        trait_id = str(
            trait.get(
                "id"
            )
            or ""
        ).strip()

        description = str(
            trait.get(
                "description"
            )
            or ""
        ).strip()

        if (
            trait_id
            and description
        ):
            lines.append(
                f"- {trait_id}: {description}"
            )

        elif trait_id:
            lines.append(
                f"- {trait_id}"
            )

    lines.extend(
        [
            "",
            (
                "Persona identity and provider "
                "identity are separate."
            ),
            (
                "Envoy owns persona composition. "
                "Opus owns provider execution."
            ),
        ]
    )

    return "\n".join(
        lines
    )


def execute_opus(
    *,
    message: str,
    system: str,
    context: str = "",
) -> dict[str, Any]:
    install_import_paths()

    from router import (
        execute_text_request,
    )

    request = {
        "owner": runtime_owner,
        "message": message,
        "system": system,
        "context": context,
    }

    result = execute_text_request(
        request
    )

    if not isinstance(
        result,
        dict,
    ):
        raise plan_b_error(
            "opus result must be object"
        )

    lineage = result.get(
        "lineage"
    )

    if not isinstance(
        lineage,
        dict,
    ):
        raise plan_b_error(
            "opus result lacks lineage"
        )

    if lineage.get(
        "owner"
    ) != execution_owner:
        raise plan_b_error(
            "opus execution owner mismatch"
        )

    if lineage.get(
        "route"
    ) != "text_inference_route":
        raise plan_b_error(
            "unexpected opus route"
        )

    return result


def infer(
    *,
    message: str,
    persona_id: str = default_persona_id,
    context: str = "",
) -> dict[str, Any]:
    normalized_message = str(
        message
        or ""
    ).strip()

    if not normalized_message:
        raise plan_b_error(
            "message is required"
        )

    selected_persona = str(
        persona_id
        or default_persona_id
    ).strip()

    if not selected_persona:
        selected_persona = (
            default_persona_id
        )

    request_id = (
        "palaver_"
        + uuid4().hex
    )

    started_at = utc_now()

    persona_projection = (
        project_persona(
            selected_persona,
            normalized_message,
        )
    )

    system = persona_system_prompt(
        persona_projection
    )

    opus_result = execute_opus(
        message=normalized_message,
        system=system,
        context=str(
            context
            or ""
        ),
    )

    response_text = str(
        opus_result.get(
            "text"
        )
        or ""
    ).strip()

    tool_calls = (
        opus_result.get(
            "tool_calls"
        )
        or []
    )

    if (
        not response_text
        and not tool_calls
    ):
        raise plan_b_error(
            "opus returned neither text "
            "nor tool calls"
        )

    lineage = dict(
        opus_result.get(
            "lineage"
        )
        or {}
    )

    return {
        "schema": schema,
        "ok": True,
        "request_id": request_id,
        "created_at": started_at,
        "completed_at": utc_now(),
        "owner": runtime_owner,
        "persona_owner": persona_owner,
        "execution_owner": execution_owner,
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
        "inference": {
            "provider": (
                opus_result.get(
                    "provider"
                )
            ),
            "model": (
                opus_result.get(
                    "model"
                )
            ),
            "usage": (
                opus_result.get(
                    "usage"
                )
                or {}
            ),
            "provider_response_id": (
                opus_result.get(
                    "provider_response_id"
                )
            ),
        },
        "lineage": lineage,
        "authority": {
            "palaver": (
                "conversation ingress/egress"
            ),
            "envoy": (
                "persona composition"
            ),
            "opus": (
                "provider/model execution"
            ),
            "authority_effect": "none",
        },
    }


def health() -> dict[str, Any]:
    components = {}

    components[
        "palaver"
    ] = {
        "state": "ready",
        "owner": "palaver",
    }

    try:
        install_import_paths()

        from router import (
            select_provider,
        )

        provider = select_provider(
            "text_inference_route"
        )

        components[
            "opus"
        ] = {
            "state": "ready",
            "owner": "opus",
            "provider": provider.get(
                "id"
            ),
            "model": provider.get(
                "selected_model"
            ),
        }

    except Exception as exc:
        components[
            "opus"
        ] = {
            "state": "unavailable",
            "owner": "opus",
            "diagnostic": (
                f"{type(exc).__name__}: {exc}"
            ),
        }

    try:
        projection = project_persona(
            default_persona_id,
            "health",
        )

        components[
            "envoy"
        ] = {
            "state": (
                "degraded"
                if projection.get(
                    "degraded"
                )
                else "ready"
            ),
            "owner": "envoy",
            "persona_id": (
                projection.get(
                    "persona_id"
                )
            ),
            "degradation": (
                projection.get(
                    "degradation"
                )
            ),
        }

    except Exception as exc:
        components[
            "envoy"
        ] = {
            "state": "unavailable",
            "owner": "envoy",
            "diagnostic": (
                f"{type(exc).__name__}: {exc}"
            ),
        }

    inference_ready = (
        components.get(
            "opus",
            {},
        ).get(
            "state"
        )
        == "ready"
    )

    return {
        "schema": schema,
        "owner": runtime_owner,
        "mode": "plan_b",
        "ready": inference_ready,
        "components": components,
        "legacy_webui_required": False,
        "legacy_server_required": False,
        "graph_required": False,
        "voice_required": False,
        "authority_effect": "none",
        "updated_at": utc_now(),
    }


class handler(
    BaseHTTPRequestHandler
):
    server_version = (
        "palaver-plan-b/1"
    )

    def log_message(
        self,
        format: str,
        *args: Any,
    ) -> None:
        return

    def send_json(
        self,
        status: int,
        payload: dict[str, Any],
    ) -> None:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
        ).encode(
            "utf-8"
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

    def do_GET(
        self,
    ) -> None:
        if self.path.rstrip(
            "/"
        ) in {
            "",
            "/health",
        }:
            self.send_json(
                200,
                health(),
            )

            return

        self.send_json(
            404,
            {
                "ok": False,
                "error": "not_found",
            },
        )

    def do_POST(
        self,
    ) -> None:
        if self.path.rstrip(
            "/"
        ) != "/infer":
            self.send_json(
                404,
                {
                    "ok": False,
                    "error": "not_found",
                },
            )

            return

        try:
            length = int(
                self.headers.get(
                    "Content-Length",
                    "0",
                )
            )

            raw = self.rfile.read(
                length
            )

            payload = json.loads(
                raw.decode(
                    "utf-8"
                )
                if raw
                else "{}"
            )

            if not isinstance(
                payload,
                dict,
            ):
                raise plan_b_error(
                    "request body must be object"
                )

            result = infer(
                message=str(
                    payload.get(
                        "message"
                    )
                    or payload.get(
                        "text"
                    )
                    or ""
                ),
                persona_id=str(
                    payload.get(
                        "persona_id"
                    )
                    or default_persona_id
                ),
                context=str(
                    payload.get(
                        "context"
                    )
                    or ""
                ),
            )

            self.send_json(
                200,
                result,
            )

        except Exception as exc:
            self.send_json(
                503,
                {
                    "schema": schema,
                    "ok": False,
                    "error": (
                        type(
                            exc
                        ).__name__
                    ),
                    "message": str(
                        exc
                    ),
                    "authority_effect": "none",
                },
            )


def serve(
    host: str,
    port: int,
) -> None:
    server = (
        ThreadingHTTPServer(
            (
                host,
                port,
            ),
            handler,
        )
    )

    print(
        json.dumps(
            {
                "ok": True,
                "schema": schema,
                "mode": "plan_b",
                "host": host,
                "port": port,
                "health": (
                    f"http://{host}:{port}/health"
                ),
                "infer": (
                    f"http://{host}:{port}/infer"
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )

    server.serve_forever()


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        prog="palaver-plan-b"
    )

    value.add_argument(
        "--message",
    )

    value.add_argument(
        "--persona",
        default=default_persona_id,
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
        default="127.0.0.1",
    )

    value.add_argument(
        "--port",
        type=int,
        default=8788,
    )

    return value


def main() -> int:
    args = parser().parse_args()

    try:
        if args.health:
            print(
                json.dumps(
                    health(),
                    indent=2,
                    sort_keys=True,
                )
            )

            return 0

        if args.serve:
            serve(
                args.host,
                args.port,
            )

            return 0

        if args.message:
            print(
                json.dumps(
                    infer(
                        message=args.message,
                        persona_id=(
                            args.persona
                        ),
                        context=(
                            args.context
                        ),
                    ),
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )

            return 0

        raise plan_b_error(
            "use --health, --serve, "
            "or --message"
        )

    except KeyboardInterrupt:
        return 130

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema": schema,
                    "ok": False,
                    "error": (
                        type(
                            exc
                        ).__name__
                    ),
                    "message": str(
                        exc
                    ),
                    "traceback": (
                        traceback.format_exc()
                    ),
                    "authority_effect": "none",
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

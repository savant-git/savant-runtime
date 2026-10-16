#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import ModuleType
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse


PALAVER_ROOT = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/palaver"
)

PALAVER_RUNTIME = PALAVER_ROOT / "runtime"

LEGACY_WEBUI_ROOT = (
    PALAVER_ROOT
    / "apps"
    / "webui_ultra"
)

LEGACY_SERVER = (
    LEGACY_WEBUI_ROOT
    / "server.py"
)

CANONICAL_IDENTITY = "exile:palaver"

CANONICAL_ENTRYPOINT = (
    PALAVER_RUNTIME
    / "server.py"
)

LEGACY_MODULE_NAME = (
    "palaver_webui_ultra_compat"
)

DEFAULT_BIND_HOST = "127.0.0.1"
DEFAULT_PERSONA_ID = "orobouros"
WORKSPACE_PERSONA_FIELD = "persona_id"

REQUEST_PERSONA_ID: ContextVar[
    str | None
] = ContextVar(
    "palaver_request_persona_id",
    default=None,
)


INFERENCE_STATE: dict[str, Any] = {
    "status": "unknown",
    "available": None,
    "error_code": None,
    "message": (
        "Inference has not yet been exercised "
        "during this Palaver process."
    ),
    "diagnostic": None,
    "updated_at": None,
}


class PalaverInferenceError(RuntimeError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        diagnostic: str,
        http_status: int,
    ) -> None:
        super().__init__(
            message
        )

        self.code = code
        self.message = message
        self.diagnostic = diagnostic
        self.http_status = http_status


def _utc_now() -> str:
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


def _set_inference_state(
    *,
    status: str,
    available: bool | None,
    error_code: str | None,
    message: str,
    diagnostic: str | None,
) -> None:
    INFERENCE_STATE.update(
        {
            "status": status,
            "available": available,
            "error_code": error_code,
            "message": message,
            "diagnostic": diagnostic,
            "updated_at": _utc_now(),
        }
    )


def _classify_inference_exception(
    exc: Exception,
) -> PalaverInferenceError:
    diagnostic = str(
        exc
        or ""
    ).strip()

    lowered = (
        diagnostic.lower()
    )

    if (
        "429" in lowered
        or "too many requests" in lowered
        or "rate limit" in lowered
        or "rate_limit" in lowered
    ):
        return PalaverInferenceError(
            code="inference_rate_limited",
            message=(
                "Inference is temporarily rate limited. "
                "Try again shortly."
            ),
            diagnostic=diagnostic,
            http_status=429,
        )

    if (
        "401" in lowered
        or "unauthorized" in lowered
        or "invalid api key" in lowered
        or "incorrect api key" in lowered
        or "authentication" in lowered
    ):
        return PalaverInferenceError(
            code="inference_authentication_failed",
            message=(
                "The inference provider could not "
                "authenticate this request."
            ),
            diagnostic=diagnostic,
            http_status=503,
        )

    if (
        "403" in lowered
        or "forbidden" in lowered
        or "permission" in lowered
    ):
        return PalaverInferenceError(
            code="inference_permission_denied",
            message=(
                "The configured inference provider "
                "does not permit this request."
            ),
            diagnostic=diagnostic,
            http_status=503,
        )

    if (
        "404" in lowered
        and (
            "model" in lowered
            or "openai" in lowered
        )
    ):
        return PalaverInferenceError(
            code="inference_model_unavailable",
            message=(
                "The configured inference model "
                "is currently unavailable."
            ),
            diagnostic=diagnostic,
            http_status=503,
        )

    if (
        "timeout" in lowered
        or "timed out" in lowered
    ):
        return PalaverInferenceError(
            code="inference_timeout",
            message=(
                "Inference timed out before a response "
                "was received. Try again."
            ),
            diagnostic=diagnostic,
            http_status=504,
        )

    if (
        "connection refused" in lowered
        or "connection reset" in lowered
        or "network is unreachable" in lowered
        or "temporary failure in name resolution" in lowered
        or "name or service not known" in lowered
    ):
        return PalaverInferenceError(
            code="inference_provider_unreachable",
            message=(
                "The inference provider could not "
                "be reached. Try again shortly."
            ),
            diagnostic=diagnostic,
            http_status=503,
        )

    if (
        "500" in lowered
        or "502" in lowered
        or "503" in lowered
        or "504" in lowered
        or "internal server error" in lowered
        or "bad gateway" in lowered
        or "service unavailable" in lowered
    ):
        return PalaverInferenceError(
            code="inference_provider_degraded",
            message=(
                "The inference provider is temporarily "
                "unavailable. Try again shortly."
            ),
            diagnostic=diagnostic,
            http_status=503,
        )

    return PalaverInferenceError(
        code="inference_failed",
        message=(
            "Palaver could not complete inference. "
            "The request can be retried."
        ),
        diagnostic=diagnostic,
        http_status=503,
    )


def _inference_health() -> dict[str, Any]:
    return dict(
        INFERENCE_STATE
    )


def validate_layout() -> None:
    required = [
        PALAVER_ROOT,
        PALAVER_RUNTIME,
        LEGACY_WEBUI_ROOT,
        LEGACY_SERVER,
    ]

    missing = [
        str(path)
        for path in required
        if not path.exists()
    ]

    if missing:
        raise RuntimeError(
            "Palaver runtime layout incomplete: "
            + ", ".join(missing)
        )


def prepare_import_paths() -> None:
    for path in (
        PALAVER_RUNTIME,
        LEGACY_WEBUI_ROOT,
    ):
        value = str(
            path
        )

        if value not in sys.path:
            sys.path.insert(
                0,
                value,
            )


def load_legacy_server() -> ModuleType:
    spec = (
        importlib.util
        .spec_from_file_location(
            LEGACY_MODULE_NAME,
            LEGACY_SERVER,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            "Unable to construct Palaver "
            "legacy server import"
        )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    sys.modules[
        LEGACY_MODULE_NAME
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def _message_signals(
    message: str,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            set(
                re.findall(
                    r"[a-z0-9_]+",
                    str(
                        message
                        or ""
                    ).lower(),
                )
            )
        )
    )


def _workspace_state(
    legacy: ModuleType,
) -> dict[str, Any]:
    loader = getattr(
        legacy,
        "workspace_state_load",
        None,
    )

    if not callable(
        loader
    ):
        return {}

    value = loader()

    if not isinstance(
        value,
        dict,
    ):
        return {}

    return value


def _validate_persona_id(
    legacy: ModuleType,
    persona_id: str,
) -> str:
    selected = str(
        persona_id
        or ""
    ).strip()

    if not selected:
        raise RuntimeError(
            "persona_id is empty"
        )

    projection = (
        legacy
        .palaver_envoy_project_persona(
            selected
        )
    )

    resolved = str(
        projection.get(
            "persona_id",
            "",
        )
    ).strip()

    if resolved != selected:
        raise RuntimeError(
            "Envoy persona identity mismatch: "
            f"requested={selected!r} "
            f"resolved={resolved!r}"
        )

    return resolved


def _workspace_persona_id(
    legacy: ModuleType,
) -> str | None:
    state = _workspace_state(
        legacy
    )

    raw = state.get(
        WORKSPACE_PERSONA_FIELD
    )

    selected = str(
        raw
        or ""
    ).strip()

    if not selected:
        return None

    try:
        return _validate_persona_id(
            legacy,
            selected,
        )
    except Exception:
        return None


def _effective_persona_id(
    legacy: ModuleType,
    requested: str | None = None,
) -> str:
    explicit = str(
        requested
        or ""
    ).strip()

    if explicit:
        return _validate_persona_id(
            legacy,
            explicit,
        )

    workspace = (
        _workspace_persona_id(
            legacy
        )
    )

    if workspace:
        return workspace

    return DEFAULT_PERSONA_ID


def _selected_persona_id() -> str:
    selected = str(
        REQUEST_PERSONA_ID.get()
        or DEFAULT_PERSONA_ID
    ).strip()

    return (
        selected
        or DEFAULT_PERSONA_ID
    )


def _persona_prompt_block(
    message: str,
) -> str:
    from envoy_bridge import (
        project_persona,
    )

    projection = project_persona(
        _selected_persona_id(),
        signals=_message_signals(
            message
        ),
    )

    baseline = [
        str(value)
        for value in (
            projection.get(
                "baseline"
            )
            or []
        )
    ]

    traits = (
        projection.get(
            "traits"
        )
        or []
    )

    lines = [
        "ENVOY PERSONA PROJECTION",
        (
            "persona_id: "
            + str(
                projection.get(
                    "persona_id",
                    DEFAULT_PERSONA_ID,
                )
            )
        ),
        (
            "display_name: "
            + str(
                projection.get(
                    "display_name",
                    "",
                )
            )
        ),
        (
            "baseline_version: "
            + str(
                projection.get(
                    "baseline_version",
                    "",
                )
            )
        ),
        (
            "composition_digest: "
            + str(
                projection.get(
                    "composition_digest",
                    "",
                )
            )
        ),
        "",
        "Permanent baseline:",
    ]

    if not baseline:
        lines.append(
            "- none declared"
        )

    for value in baseline:
        lines.append(
            f"- {value}"
        )

    lines.extend(
        [
            "",
            "Living Trait Crown:",
        ]
    )

    if not traits:
        lines.append(
            "- none selected"
        )

    for trait in traits:
        trait_id = str(
            trait.get(
                "id",
                "",
            )
        ).strip()

        description = str(
            trait.get(
                "description",
                "",
            )
        ).strip()

        if description:
            lines.append(
                f"- {trait_id}: {description}"
            )
        else:
            lines.append(
                f"- {trait_id}"
            )

    lines.extend(
        [
            "",
            (
                "Persona identity and provider identity "
                "are separate. Envoy owns persona "
                "composition. Opus owns provider execution."
            ),
        ]
    )

    return "\n".join(
        lines
    )


def _orobouros_prompt_block(
    message: str,
) -> str:
    return _persona_prompt_block(
        message
    )


def install_scrybe_context(
    legacy: ModuleType,
) -> None:
    from scrybe_bridge import (
        clear_context_receipt,
        context_receipt,
        prompt_block,
    )

    def memory_block_through_scrybe(
        message: str,
        limit: int = 8,
    ) -> str:
        return prompt_block(
            message,
            limit=limit,
        )

    legacy.memory_block_for_prompt = (
        memory_block_through_scrybe
    )

    legacy.palaver_scrybe_context_receipt = (
        context_receipt
    )

    legacy.palaver_scrybe_clear_context_receipt = (
        clear_context_receipt
    )


def install_direct_command_bridge(
    legacy: ModuleType,
) -> None:
    from direct_command_bridge import (
        install,
    )

    install(
        legacy
    )


def install_opus_inference(
    legacy: ModuleType,
) -> None:
    from conversation_bridge import (
        prompt_block as conversation_prompt_block,
    )

    from niche_bridge import (
        prompt_block,
    )

    from opus_bridge import (
        infer,
    )

    system_prompt = str(
        getattr(
            legacy,
            "SYSTEM_PROMPT",
            "",
        )
    )

    def call_opus(
        message: str,
        context: str = "",
    ) -> str:
        niche_context = prompt_block(
            limit=9
        )

        conversation_context = (
            conversation_prompt_block(
                limit=12
            )
        )

        persona_context = (
            _persona_prompt_block(
                message
            )
        )

        composed_system = "\n\n".join(
            part
            for part in (
                system_prompt.strip(),
                persona_context,
            )
            if part
        )

        combined_context = "\n\n".join(
            part
            for part in (
                niche_context,
                conversation_context,
                str(
                    context
                    or ""
                ).strip(),
            )
            if part
        )

        try:
            result = infer(
                message,
                combined_context,
                system=composed_system,
            )

        except PalaverInferenceError:
            raise

        except Exception as exc:
            classified = (
                _classify_inference_exception(
                    exc
                )
            )

            _set_inference_state(
                status=(
                    "rate_limited"
                    if classified.code
                    == "inference_rate_limited"
                    else "degraded"
                ),
                available=False,
                error_code=classified.code,
                message=classified.message,
                diagnostic=classified.diagnostic,
            )

            raise classified from exc

        _set_inference_state(
            status="healthy",
            available=True,
            error_code=None,
            message=(
                "Inference completed successfully."
            ),
            diagnostic=None,
        )

        return result

    legacy.call_openai = (
        call_opus
    )


def install_coda_mutation(
    legacy: ModuleType,
) -> None:
    from coda_bridge import (
        save_file,
    )

    def save_through_coda(
        path: str,
        content: str,
    ) -> Dict[str, Any]:
        return save_file(
            path,
            content,
            intent="Palaver /api/file/save",
        )

    legacy.save_file_payload = (
        save_through_coda
    )


def install_patch_review_bridge(
    legacy: ModuleType,
) -> None:
    from patch_review_bridge import (
        apply_review,
        create_review,
        list_pending,
        reject_review,
    )

    def patch_review_pending_through_palaver():
        return list_pending()

    def patch_review_create_through_palaver(
        path: str,
        after: str,
    ):
        return create_review(
            path,
            after,
        )

    def patch_review_apply_through_coda(
        patch_id: str,
    ):
        return apply_review(
            patch_id
        )

    def patch_review_reject_through_palaver(
        patch_id: str,
    ):
        return reject_review(
            patch_id
        )

    legacy.patch_review_pending_payload = (
        patch_review_pending_through_palaver
    )

    legacy.patch_review_create_payload = (
        patch_review_create_through_palaver
    )

    legacy.patch_review_apply_payload = (
        patch_review_apply_through_coda
    )

    legacy.patch_review_reject_payload = (
        patch_review_reject_through_palaver
    )


def install_envoy(
    legacy: ModuleType,
) -> None:
    from envoy_bridge import (
        default_persona_projection,
        list_personas,
        project_persona,
        resolve_persona,
        resolve_voice,
        synthesize,
        synthesize_base64,
    )

    legacy.palaver_envoy_list_personas = (
        list_personas
    )

    legacy.palaver_envoy_resolve_persona = (
        resolve_persona
    )

    legacy.palaver_envoy_project_persona = (
        project_persona
    )

    legacy.palaver_envoy_resolve_voice = (
        resolve_voice
    )

    legacy.palaver_envoy_synthesize = (
        synthesize
    )

    legacy.palaver_envoy_synthesize_base64 = (
        synthesize_base64
    )

    legacy.palaver_envoy_default_persona_projection = (
        default_persona_projection
    )


def bind_host() -> str:
    configured = str(
        os.getenv(
            "PALAVER_BIND_HOST",
            DEFAULT_BIND_HOST,
        )
    ).strip()

    return (
        configured
        or DEFAULT_BIND_HOST
    )


def canonical_routes() -> dict[
    str,
    list[str],
]:
    return {
        "get": [
            "/",
            "/api/health",
            "/api/routes",
            "/api/diagnostics/crash",
            "/api/tree",
            "/api/file",
            "/api/graph",
            "/api/timeline",
            "/api/runtime",
            "/api/repository/files",
            "/api/memory/files",
            "/api/memory/search",
            "/api/agents/jobs",
            "/api/personas",
            "/api/persona",
            "/api/persona/preference",
            "/api/voice/personas",
            "/api/voice/persona",
            "/api/voice/resolve",
        ],
        "post": [
            "/api/chat",
            "/api/persona/preference",
            "/api/file/save",
            "/api/file/diff",
            "/api/workspace/save",
            "/api/patch/write",
            "/api/patch/append",
            "/api/patch-review/create",
            "/api/patch-review/apply",
            "/api/patch-review/reject",
            "/api/voice/synthesize",
        ],
    }


def _legacy_health_payload(
    legacy: ModuleType,
) -> dict[str, Any]:
    health_target = getattr(
        legacy,
        "health",
        None,
    )

    if not callable(
        health_target
    ):
        return {}

    try:
        result = health_target()

    except Exception as exc:
        return {
            "legacy_health_error": str(
                exc
            )
        }

    if not isinstance(
        result,
        dict,
    ):
        return {}

    return result


def make_canonical_handler(
    legacy: ModuleType,
):
    legacy_handler = getattr(
        legacy,
        "Handler",
        None,
    )

    if legacy_handler is None:
        raise RuntimeError(
            "Palaver legacy Handler missing"
        )

    send_json = getattr(
        legacy,
        "send_json",
        None,
    )

    body_json = getattr(
        legacy,
        "body_json",
        None,
    )

    workspace_save = getattr(
        legacy,
        "workspace_state_save",
        None,
    )

    if not callable(
        send_json
    ):
        raise RuntimeError(
            "Palaver legacy send_json missing"
        )

    if not callable(
        body_json
    ):
        raise RuntimeError(
            "Palaver legacy body_json missing"
        )

    if not callable(
        workspace_save
    ):
        raise RuntimeError(
            "Palaver legacy workspace_state_save missing"
        )

    class CanonicalHandler(
        legacy_handler
    ):
        def do_GET(
            self
        ):
            parsed = urlparse(
                self.path
            )

            path = (
                parsed.path
            )

            query = parse_qs(
                parsed.query
            )

            try:
                if path == "/api/health":
                    base_health = (
                        _legacy_health_payload(
                            legacy
                        )
                    )

                    inference = (
                        _inference_health()
                    )

                    degraded = (
                        inference.get(
                            "available"
                        )
                        is False
                    )

                    send_json(
                        self,
                        {
                            "ok": (
                                not degraded
                            ),
                            "health": {
                                **base_health,
                                "inference": (
                                    inference
                                ),
                            },
                            "owners": {
                                "conversation": "palaver",
                                "provider": "opus",
                                "persona": "envoy",
                                "memory": "scrybe",
                                "mutation": "coda",
                                "task": "niche",
                            },
                            "authority_effect": "none",
                        },
                        (
                            503
                            if degraded
                            else 200
                        ),
                    )
                    return

                if path == "/api/routes":
                    send_json(
                        self,
                        {
                            "ok": True,
                            "routes": (
                                canonical_routes()
                            ),
                        },
                    )
                    return

                if path == "/api/personas":
                    result = (
                        legacy
                        .palaver_envoy_list_personas()
                    )

                    workspace_persona = (
                        _workspace_persona_id(
                            legacy
                        )
                    )

                    send_json(
                        self,
                        {
                            "ok": True,
                            "owner": "envoy",
                            "default_persona": (
                                DEFAULT_PERSONA_ID
                            ),
                            "workspace_persona": (
                                workspace_persona
                            ),
                            "effective_persona": (
                                workspace_persona
                                or DEFAULT_PERSONA_ID
                            ),
                            "personas": result,
                        },
                    )
                    return

                if path == "/api/persona":
                    persona_id = (
                        query.get(
                            "id",
                            [None],
                        )[0]
                    )

                    selected = (
                        _effective_persona_id(
                            legacy,
                            persona_id,
                        )
                    )

                    result = (
                        legacy
                        .palaver_envoy_project_persona(
                            selected
                        )
                    )

                    send_json(
                        self,
                        {
                            "ok": True,
                            "owner": "envoy",
                            "persona_id": selected,
                            "persona": result,
                        },
                    )
                    return

                if path == "/api/persona/preference":
                    workspace_persona = (
                        _workspace_persona_id(
                            legacy
                        )
                    )

                    send_json(
                        self,
                        {
                            "ok": True,
                            "owner": "palaver",
                            "persona_authority": "envoy",
                            "workspace_persona": (
                                workspace_persona
                            ),
                            "effective_persona": (
                                workspace_persona
                                or DEFAULT_PERSONA_ID
                            ),
                            "default_persona": (
                                DEFAULT_PERSONA_ID
                            ),
                        },
                    )
                    return

                if path == "/api/voice/personas":
                    result = (
                        legacy
                        .palaver_envoy_list_personas()
                    )

                    workspace_persona = (
                        _workspace_persona_id(
                            legacy
                        )
                    )

                    send_json(
                        self,
                        {
                            "ok": True,
                            "owner": "envoy",
                            "workspace_persona": (
                                workspace_persona
                            ),
                            "effective_persona": (
                                workspace_persona
                                or DEFAULT_PERSONA_ID
                            ),
                            "default_persona": (
                                DEFAULT_PERSONA_ID
                            ),
                            "personas": result,
                        },
                    )
                    return

                if path == "/api/voice/persona":
                    requested_persona = (
                        query.get(
                            "id",
                            [None],
                        )[0]
                    )

                    selected_persona = (
                        _effective_persona_id(
                            legacy,
                            requested_persona,
                        )
                    )

                    result = (
                        legacy
                        .palaver_envoy_resolve_persona(
                            selected_persona
                        )
                    )

                    send_json(
                        self,
                        {
                            "ok": True,
                            "owner": "envoy",
                            "persona_id": (
                                selected_persona
                            ),
                            "persona_source": (
                                "request"
                                if requested_persona
                                else (
                                    "workspace"
                                    if _workspace_persona_id(
                                        legacy
                                    )
                                    else "default"
                                )
                            ),
                            "persona": result,
                        },
                    )
                    return

                if path == "/api/voice/resolve":
                    requested_persona = (
                        query.get(
                            "id",
                            [None],
                        )[0]
                    )

                    selected_persona = (
                        _effective_persona_id(
                            legacy,
                            requested_persona,
                        )
                    )

                    result = (
                        legacy
                        .palaver_envoy_resolve_voice(
                            selected_persona
                        )
                    )

                    send_json(
                        self,
                        {
                            "ok": True,
                            "owner": "envoy",
                            "persona_id": (
                                selected_persona
                            ),
                            "persona_source": (
                                "request"
                                if requested_persona
                                else (
                                    "workspace"
                                    if _workspace_persona_id(
                                        legacy
                                    )
                                    else "default"
                                )
                            ),
                            "voice": result,
                        },
                    )
                    return

                super().do_GET()

            except Exception as exc:
                send_json(
                    self,
                    {
                        "ok": False,
                        "error": (
                            "Palaver could not complete "
                            "this request."
                        ),
                        "error_code": (
                            "palaver_request_failed"
                        ),
                        "diagnostic": str(
                            exc
                        ),
                    },
                    500,
                )

        def do_POST(
            self
        ):
            path = urlparse(
                self.path
            ).path

            if path == "/api/persona/preference":
                try:
                    data = body_json(
                        self
                    )

                    if not isinstance(
                        data,
                        dict,
                    ):
                        raise RuntimeError(
                            "persona preference payload "
                            "must be an object"
                        )

                    state = dict(
                        _workspace_state(
                            legacy
                        )
                    )

                    requested = str(
                        data.get(
                            WORKSPACE_PERSONA_FIELD
                        )
                        or ""
                    ).strip()

                    if requested:
                        state[
                            WORKSPACE_PERSONA_FIELD
                        ] = _validate_persona_id(
                            legacy,
                            requested,
                        )
                    else:
                        state.pop(
                            WORKSPACE_PERSONA_FIELD,
                            None,
                        )

                    result = workspace_save(
                        state
                    )

                    workspace_persona = (
                        _workspace_persona_id(
                            legacy
                        )
                    )

                    send_json(
                        self,
                        {
                            "ok": True,
                            "result": result,
                            "workspace_persona": (
                                workspace_persona
                            ),
                            "effective_persona": (
                                workspace_persona
                                or DEFAULT_PERSONA_ID
                            ),
                            "default_persona": (
                                DEFAULT_PERSONA_ID
                            ),
                            "persona_owner": "envoy",
                            "workspace_owner": "palaver",
                        },
                    )
                    return

                except Exception as exc:
                    send_json(
                        self,
                        {
                            "ok": False,
                            "error": (
                                "Palaver could not save "
                                "the persona preference."
                            ),
                            "error_code": (
                                "persona_preference_failed"
                            ),
                            "diagnostic": str(
                                exc
                            ),
                        },
                        500,
                    )
                    return

            if path == "/api/workspace/save":
                try:
                    data = body_json(
                        self
                    )

                    if not isinstance(
                        data,
                        dict,
                    ):
                        raise RuntimeError(
                            "workspace payload must be an object"
                        )

                    previous = (
                        _workspace_state(
                            legacy
                        )
                    )

                    outgoing = dict(
                        data
                    )

                    if (
                        WORKSPACE_PERSONA_FIELD
                        in data
                    ):
                        requested = str(
                            data.get(
                                WORKSPACE_PERSONA_FIELD
                            )
                            or ""
                        ).strip()

                        if requested:
                            outgoing[
                                WORKSPACE_PERSONA_FIELD
                            ] = _validate_persona_id(
                                legacy,
                                requested,
                            )
                        else:
                            outgoing.pop(
                                WORKSPACE_PERSONA_FIELD,
                                None,
                            )

                    else:
                        existing = str(
                            previous.get(
                                WORKSPACE_PERSONA_FIELD
                            )
                            or ""
                        ).strip()

                        if existing:
                            try:
                                outgoing[
                                    WORKSPACE_PERSONA_FIELD
                                ] = _validate_persona_id(
                                    legacy,
                                    existing,
                                )
                            except Exception:
                                pass

                    result = workspace_save(
                        outgoing
                    )

                    workspace_persona = (
                        _workspace_persona_id(
                            legacy
                        )
                    )

                    send_json(
                        self,
                        {
                            "ok": True,
                            "result": result,
                            "workspace_persona": (
                                workspace_persona
                            ),
                            "effective_persona": (
                                workspace_persona
                                or DEFAULT_PERSONA_ID
                            ),
                            "default_persona": (
                                DEFAULT_PERSONA_ID
                            ),
                            "persona_owner": "envoy",
                            "workspace_owner": "palaver",
                        },
                    )
                    return

                except Exception as exc:
                    send_json(
                        self,
                        {
                            "ok": False,
                            "error": (
                                "Palaver could not save "
                                "the workspace."
                            ),
                            "error_code": (
                                "workspace_save_failed"
                            ),
                            "diagnostic": str(
                                exc
                            ),
                        },
                        500,
                    )
                    return

            if path == "/api/chat":
                try:
                    data = body_json(
                        self
                    )

                    if not isinstance(
                        data,
                        dict,
                    ):
                        send_json(
                            self,
                            {
                                "ok": False,
                                "error": (
                                    "The chat request was invalid."
                                ),
                                "error_code": (
                                    "invalid_chat_payload"
                                ),
                            },
                            400,
                        )
                        return

                    from contracts.validator import (
                        ContractValidationError,
                        validate_input,
                        validate_output,
                    )

                    try:
                        validate_input(
                            "palaver.conversation.v1",
                            data,
                        )

                    except ContractValidationError as exc:
                        send_json(
                            self,
                            {
                                "ok": False,
                                "error": (
                                    "The chat request did not "
                                    "match the Palaver conversation "
                                    "contract."
                                ),
                                "error_code": (
                                    "chat_contract_input_invalid"
                                ),
                                "diagnostic": str(
                                    exc
                                ),
                            },
                            400,
                        )
                        return

                    message = str(
                        data.get(
                            "message",
                            "",
                        )
                        or ""
                    ).strip()

                    if not message:
                        send_json(
                            self,
                            {
                                "ok": False,
                                "error": (
                                    "Enter a message before sending."
                                ),
                                "error_code": (
                                    "message_required"
                                ),
                            },
                            400,
                        )
                        return

                    requested_persona = str(
                        data.get(
                            "persona_id",
                            "",
                        )
                        or ""
                    ).strip()

                    selected_persona = (
                        _effective_persona_id(
                            legacy,
                            requested_persona,
                        )
                    )

                    token = (
                        REQUEST_PERSONA_ID.set(
                            selected_persona
                        )
                    )

                    legacy.palaver_scrybe_clear_context_receipt()

                    try:
                        result = legacy.chat(
                            message
                        )

                    finally:
                        REQUEST_PERSONA_ID.reset(
                            token
                        )

                    context_receipt = (
                        legacy
                        .palaver_scrybe_context_receipt()
                    )

                    if (
                        isinstance(
                            result,
                            dict,
                        )
                        and isinstance(
                            context_receipt,
                            dict,
                        )
                    ):
                        trace = str(
                            result.get(
                                "trace",
                                "",
                            )
                            or ""
                        ).strip()

                        receipt_trace = (
                            "scrybe context "
                            f"digest={context_receipt.get('digest')} "
                            f"memory_count={context_receipt.get('memory_count')} "
                            f"limit={context_receipt.get('limit')} "
                            "authoritative=false "
                            "rebuildable=true"
                        )

                        result[
                            "trace"
                        ] = "\n".join(
                            part
                            for part in (
                                trace,
                                receipt_trace,
                            )
                            if part
                        )

                        result[
                            "context_receipt"
                        ] = context_receipt

                    if not isinstance(
                        result,
                        dict,
                    ):
                        raise RuntimeError(
                            "Palaver chat returned "
                            "invalid result"
                        )

                    if (
                        "response" not in result
                        and "answer" in result
                    ):
                        result[
                            "response"
                        ] = result[
                            "answer"
                        ]

                    try:
                        validate_output(
                            "palaver.conversation.v1",
                            result,
                        )

                    except ContractValidationError as exc:
                        send_json(
                            self,
                            {
                                "ok": False,
                                "error": (
                                    "Palaver received an invalid "
                                    "conversation result."
                                ),
                                "error_code": (
                                    "chat_contract_output_invalid"
                                ),
                                "diagnostic": str(
                                    exc
                                ),
                            },
                            500,
                        )
                        return

                    workspace_persona = (
                        _workspace_persona_id(
                            legacy
                        )
                    )

                    source = (
                        "request"
                        if requested_persona
                        else (
                            "workspace"
                            if workspace_persona
                            else "default"
                        )
                    )

                    send_json(
                        self,
                        {
                            "ok": True,
                            **result,
                            "persona_id": (
                                selected_persona
                            ),
                            "persona_source": source,
                            "workspace_persona": (
                                workspace_persona
                            ),
                            "persona_owner": "envoy",
                            "provider_owner": "opus",
                            "conversation_owner": "palaver",
                        },
                    )
                    return

                except PalaverInferenceError as exc:
                    send_json(
                        self,
                        {
                            "ok": False,
                            "error": exc.message,
                            "error_code": exc.code,
                            "diagnostic": (
                                exc.diagnostic
                            ),
                            "retryable": (
                                exc.code
                                in {
                                    "inference_rate_limited",
                                    "inference_timeout",
                                    "inference_provider_unreachable",
                                    "inference_provider_degraded",
                                    "inference_failed",
                                }
                            ),
                            "provider_owner": "opus",
                            "conversation_owner": "palaver",
                            "authority_effect": "none",
                        },
                        exc.http_status,
                    )
                    return

                except Exception as exc:
                    send_json(
                        self,
                        {
                            "ok": False,
                            "error": (
                                "Palaver could not complete "
                                "the conversation request."
                            ),
                            "error_code": (
                                "conversation_failed"
                            ),
                            "diagnostic": str(
                                exc
                            ),
                            "retryable": True,
                            "provider_owner": "opus",
                            "conversation_owner": "palaver",
                            "authority_effect": "none",
                        },
                        500,
                    )
                    return

            if path != "/api/voice/synthesize":
                super().do_POST()
                return

            try:
                data = body_json(
                    self
                )

                if not isinstance(
                    data,
                    dict,
                ):
                    raise RuntimeError(
                        "voice synthesis payload "
                        "must be an object"
                    )

                text = str(
                    data.get(
                        "text",
                        "",
                    )
                    or ""
                ).strip()

                requested_persona = str(
                    data.get(
                        "persona_id",
                        "",
                    )
                    or ""
                ).strip()

                if not text:
                    send_json(
                        self,
                        {
                            "ok": False,
                            "error": (
                                "Text is required for "
                                "voice synthesis."
                            ),
                            "error_code": (
                                "voice_text_required"
                            ),
                        },
                        400,
                    )
                    return

                selected_persona = (
                    _effective_persona_id(
                        legacy,
                        requested_persona,
                    )
                )

                workspace_persona = (
                    _workspace_persona_id(
                        legacy
                    )
                )

                source = (
                    "request"
                    if requested_persona
                    else (
                        "workspace"
                        if workspace_persona
                        else "default"
                    )
                )

                result = (
                    legacy
                    .palaver_envoy_synthesize_base64(
                        text,
                        selected_persona,
                    )
                )

                send_json(
                    self,
                    {
                        "ok": True,
                        "conversation_owner": "palaver",
                        "voice_owner": "envoy",
                        "persona_owner": "envoy",
                        "provider_owner": "opus",
                        "persona_id": (
                            selected_persona
                        ),
                        "persona_source": source,
                        "workspace_persona": (
                            workspace_persona
                        ),
                        "speech": result,
                    },
                )

            except Exception as exc:
                send_json(
                    self,
                    {
                        "ok": False,
                        "error": (
                            "Palaver could not complete "
                            "voice synthesis."
                        ),
                        "error_code": (
                            "voice_synthesis_failed"
                        ),
                        "diagnostic": str(
                            exc
                        ),
                    },
                    500,
                )

    CanonicalHandler.__name__ = (
        "PalaverCanonicalHandler"
    )

    return CanonicalHandler


def install_canonical_server_main(
    legacy: ModuleType,
) -> None:
    original_main = getattr(
        legacy,
        "main",
        None,
    )

    legacy._palaver_legacy_main = (
        original_main
    )

    canonical_handler = (
        make_canonical_handler(
            legacy
        )
    )

    legacy.CanonicalHandler = (
        canonical_handler
    )

    def canonical_main() -> None:
        host = bind_host()

        port = int(
            getattr(
                legacy,
                "PORT",
                8787,
            )
        )

        print(
            "Palaver running: "
            f"http://{host}:{port}"
        )

        ThreadingHTTPServer(
            (
                host,
                port,
            ),
            canonical_handler,
        ).serve_forever()

    legacy.main = (
        canonical_main
    )


def compatibility_status(
    legacy: ModuleType,
) -> Dict[str, Any]:
    from envoy_bridge import (
        integration_status as envoy_status,
    )

    from niche_bridge import (
        integration_status as niche_status,
    )

    call_target = getattr(
        legacy,
        "call_openai",
        None,
    )

    save_target = getattr(
        legacy,
        "save_file_payload",
        None,
    )

    patch_apply_target = getattr(
        legacy,
        "patch_review_apply_payload",
        None,
    )

    patch_create_target = getattr(
        legacy,
        "patch_review_create_payload",
        None,
    )

    main_target = getattr(
        legacy,
        "main",
        None,
    )

    niche = (
        niche_status()
    )

    envoy = (
        envoy_status()
    )

    workspace_persona = (
        _workspace_persona_id(
            legacy
        )
    )

    return {
        "identity": CANONICAL_IDENTITY,
        "canonical_entrypoint": str(
            CANONICAL_ENTRYPOINT
        ),
        "implementation": str(
            LEGACY_SERVER
        ),
        "mode": (
            "legacy-webui-ultra-with-"
            "niche-opus-coda-envoy-bridges"
        ),
        "bind_host": bind_host(),
        "localhost_default": (
            bind_host()
            == DEFAULT_BIND_HOST
        ),
        "canonical_main_installed": (
            callable(
                main_target
            )
            and getattr(
                main_target,
                "__name__",
                "",
            )
            == "canonical_main"
        ),
        "canonical_handler_installed": (
            hasattr(
                legacy,
                "CanonicalHandler",
            )
        ),
        "persona_http_surface_installed": (
            "/api/personas"
            in canonical_routes()["get"]
            and "/api/persona"
            in canonical_routes()["get"]
        ),
        "workspace_persona_preference_installed": (
            "/api/persona/preference"
            in canonical_routes()["get"]
            and "/api/persona/preference"
            in canonical_routes()["post"]
            and "/api/workspace/save"
            in canonical_routes()["post"]
        ),
        "chat_persona_selection_installed": (
            "/api/chat"
            in canonical_routes()["post"]
        ),
        "voice_http_surface_installed": (
            "/api/voice/personas"
            in canonical_routes()["get"]
            and "/api/voice/persona"
            in canonical_routes()["get"]
            and "/api/voice/resolve"
            in canonical_routes()["get"]
            and "/api/voice/synthesize"
            in canonical_routes()["post"]
        ),
        "voice_persona_inheritance_installed": True,
        "voice_persona_precedence": [
            "request",
            "workspace",
            "default",
        ],
        "legacy_handler_present": hasattr(
            legacy,
            "Handler",
        ),
        "legacy_main_present": callable(
            getattr(
                legacy,
                "_palaver_legacy_main",
                None,
            )
        ),
        "legacy_chat_present": callable(
            getattr(
                legacy,
                "chat",
                None,
            )
        ),
        "legacy_health_present": callable(
            getattr(
                legacy,
                "health",
                None,
            )
        ),
        "workspace_state_present": (
            callable(
                getattr(
                    legacy,
                    "workspace_state_load",
                    None,
                )
            )
            and callable(
                getattr(
                    legacy,
                    "workspace_state_save",
                    None,
                )
            )
        ),
        "opus_inference_installed": (
            callable(
                call_target
            )
            and getattr(
                call_target,
                "__name__",
                "",
            )
            == "call_opus"
        ),
        "inference_health_installed": True,
        "inference_health": (
            _inference_health()
        ),
        "scrybe_context_installed": (
            callable(
                getattr(
                    legacy,
                    "memory_block_for_prompt",
                    None,
                )
            )
            and getattr(
                legacy.memory_block_for_prompt,
                "__name__",
                "",
            )
            == "memory_block_through_scrybe"
        ),
        "memory_context_owner": "scrybe",
        "scrybe_context_receipt_installed": (
            callable(
                getattr(
                    legacy,
                    "palaver_scrybe_context_receipt",
                    None,
                )
            )
            and callable(
                getattr(
                    legacy,
                    "palaver_scrybe_clear_context_receipt",
                    None,
                )
            )
        ),
        "canonical_memory_store": "fluid-canon",
        "niche_task_context_installed": (
            niche.get(
                "delegates_task_governance_to"
            )
            == "niche"
        ),
        "niche_masterplan_available": (
            niche.get(
                "available"
            )
        ),
        "envoy_voice_installed": (
            envoy.get(
                "ready"
            )
            is True
        ),
        "orobouros_default_persona": (
            envoy.get(
                "default_persona"
            )
            == DEFAULT_PERSONA_ID
        ),
        "orobouros_projection_ready": (
            envoy.get(
                "default_persona_ready"
            )
            is True
        ),
        "direct_file_save_disabled": (
            callable(
                save_target
            )
            and getattr(
                save_target,
                "__name__",
                "",
            )
            == "save_through_coda"
        ),
        "patch_review_create_fixed": (
            callable(
                patch_create_target
            )
            and getattr(
                patch_create_target,
                "__name__",
                "",
            )
            == (
                "patch_review_create_"
                "through_palaver"
            )
        ),
        "patch_review_apply_through_coda": (
            callable(
                patch_apply_target
            )
            and getattr(
                patch_apply_target,
                "__name__",
                "",
            )
            == (
                "patch_review_apply_"
                "through_coda"
            )
        ),
        "workspace_persona": (
            workspace_persona
        ),
        "effective_persona": (
            workspace_persona
            or DEFAULT_PERSONA_ID
        ),
        "task_owner": "niche",
        "provider_owner": "opus",
        "voice_owner": "envoy",
        "persona_owner": "envoy",
        "workspace_owner": "palaver",
        "default_persona": (
            DEFAULT_PERSONA_ID
        ),
        "mutation_owner": "coda",
        "patch_review_owner": "palaver",
        "conversation_owner": "palaver",
        "persona_precedence": [
            "request",
            "workspace",
            "default",
        ],
        "authority_effect": "none",
    }


def bootstrap() -> ModuleType:
    validate_layout()

    prepare_import_paths()

    legacy = (
        load_legacy_server()
    )

    install_envoy(
        legacy
    )

    install_scrybe_context(
        legacy
    )

    install_direct_command_bridge(
        legacy
    )

    install_opus_inference(
        legacy
    )

    install_coda_mutation(
        legacy
    )

    install_patch_review_bridge(
        legacy
    )

    install_canonical_server_main(
        legacy
    )

    return legacy


def main() -> int:
    legacy = bootstrap()

    if (
        os.environ.get(
            "PALAVER_BOOTSTRAP_INSPECT"
        )
        == "1"
    ):
        print(
            json.dumps(
                compatibility_status(
                    legacy
                ),
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    legacy_main = getattr(
        legacy,
        "main",
        None,
    )

    if not callable(
        legacy_main
    ):
        raise RuntimeError(
            "Palaver server has no callable main()"
        )

    legacy_main()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

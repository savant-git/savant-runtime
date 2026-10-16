from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable


ENVOY_ROOT = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/envoy"
)

ENVOY_RUNTIME = ENVOY_ROOT / "runtime"

VOICE_ENGINE = ENVOY_RUNTIME / "voice_engine.py"

PERSONA_ENGINE = ENVOY_RUNTIME / "persona_engine.py"

PSYCHOLOGIST = ENVOY_RUNTIME / "psychologist.py"

ENVOY_OPUS_BRIDGE = ENVOY_RUNTIME / "opus_bridge.py"

OPUS_RUNTIME = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/opus/runtime"
)

VOICE_ENGINE_MODULE = "savant_envoy_voice_engine"

PERSONA_ENGINE_MODULE = "savant_envoy_persona_engine"

PSYCHOLOGIST_MODULE = "savant_envoy_psychologist"

ENVOY_OPUS_BRIDGE_MODULE = "savant_envoy_opus_bridge"

DEFAULT_PERSONA_ID = "orobouros"


def prepare_import_paths() -> None:
    for path in (
        OPUS_RUNTIME,
        ENVOY_RUNTIME,
    ):
        value = str(path)

        if value in sys.path:
            sys.path.remove(value)

        sys.path.insert(
            0,
            value,
        )


def load_module(
    name: str,
    path: Path,
) -> ModuleType:
    existing = sys.modules.get(name)

    if existing is not None:
        return existing

    if not path.is_file():
        raise RuntimeError(
            f"required runtime module missing: {path}"
        )

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"unable to load runtime module: {path}"
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(
            name,
            None,
        )
        raise

    return module


def load_envoy_opus_bridge() -> ModuleType:
    prepare_import_paths()

    return load_module(
        ENVOY_OPUS_BRIDGE_MODULE,
        ENVOY_OPUS_BRIDGE,
    )


def load_envoy() -> ModuleType:
    existing = sys.modules.get(
        VOICE_ENGINE_MODULE
    )

    if existing is not None:
        return existing

    prepare_import_paths()

    envoy_opus_bridge = load_envoy_opus_bridge()

    if not callable(
        getattr(
            envoy_opus_bridge,
            "synthesize_with_opus",
            None,
        )
    ):
        raise RuntimeError(
            "Envoy Opus bridge lacks "
            "synthesize_with_opus()"
        )

    previous_bare_opus_bridge = sys.modules.get(
        "opus_bridge"
    )

    sys.modules["opus_bridge"] = envoy_opus_bridge

    try:
        return load_module(
            VOICE_ENGINE_MODULE,
            VOICE_ENGINE,
        )
    finally:
        if previous_bare_opus_bridge is None:
            sys.modules.pop(
                "opus_bridge",
                None,
            )
        else:
            sys.modules["opus_bridge"] = (
                previous_bare_opus_bridge
            )


def load_persona_engine() -> ModuleType:
    prepare_import_paths()

    persona_engine = load_module(
        PERSONA_ENGINE_MODULE,
        PERSONA_ENGINE,
    )

    required = (
        "load_persona",
        "select_living_traits",
        "compose_persona",
    )

    for name in required:
        if not callable(
            getattr(
                persona_engine,
                name,
                None,
            )
        ):
            raise RuntimeError(
                "Envoy persona engine missing "
                f"callable: {name}"
            )

    return persona_engine


def load_psychologist() -> ModuleType:
    prepare_import_paths()

    envoy_opus_bridge = load_envoy_opus_bridge()

    previous_bare_opus_bridge = sys.modules.get(
        "opus_bridge"
    )

    sys.modules["opus_bridge"] = envoy_opus_bridge

    try:
        psychologist = load_module(
            PSYCHOLOGIST_MODULE,
            PSYCHOLOGIST,
        )
    finally:
        if previous_bare_opus_bridge is None:
            sys.modules.pop(
                "opus_bridge",
                None,
            )
        else:
            sys.modules["opus_bridge"] = (
                previous_bare_opus_bridge
            )

    required = (
        "build_orobouros_psychologist",
        "selftest",
    )

    for name in required:
        if not callable(
            getattr(
                psychologist,
                name,
                None,
            )
        ):
            raise RuntimeError(
                "Envoy psychologist missing "
                f"callable: {name}"
            )

    return psychologist


def _call(
    name: str,
    *args: Any,
    **kwargs: Any,
) -> Any:
    envoy = load_envoy()

    function = getattr(
        envoy,
        name,
        None,
    )

    if not callable(function):
        raise RuntimeError(
            "Envoy voice engine missing "
            f"callable: {name}"
        )

    return function(
        *args,
        **kwargs,
    )


def list_personas() -> Any:
    return _call(
        "list_personas"
    )


def resolve_persona(
    persona_id: str | None = None,
) -> Any:
    return _call(
        "resolve_persona",
        persona_id,
    )


def resolve_voice(
    persona_id: str | None = None,
) -> Any:
    return _call(
        "resolve_voice",
        persona_id,
    )


def synthesize(
    text: str,
    persona_id: str | None = None,
) -> Any:
    value = str(
        text or ""
    ).strip()

    if not value:
        raise RuntimeError(
            "Envoy speech request missing text"
        )

    return _call(
        "synthesize",
        value,
        persona_id,
    )


def synthesize_base64(
    text: str,
    persona_id: str | None = None,
) -> dict[str, Any]:
    value = str(
        text or ""
    ).strip()

    if not value:
        raise RuntimeError(
            "Envoy speech request missing text"
        )

    result = _call(
        "synthesize_base64",
        value,
        persona_id,
    )

    if not isinstance(
        result,
        dict,
    ):
        raise RuntimeError(
            "Envoy returned invalid speech result"
        )

    return result


def project_persona(
    persona_id: str | None = None,
    *,
    domains: Iterable[Any] = (),
    signals: Iterable[Any] = (),
    cap: int | None = None,
) -> dict[str, Any]:
    persona_engine = load_persona_engine()

    selected_persona = (
        str(
            persona_id
            or DEFAULT_PERSONA_ID
        ).strip()
        or DEFAULT_PERSONA_ID
    )

    result = persona_engine.compose_persona(
        persona_id=selected_persona,
        domains=domains,
        signals=signals,
        cap=cap,
    )

    if not isinstance(
        result,
        dict,
    ):
        raise RuntimeError(
            "Envoy returned invalid persona projection"
        )

    return result


def default_persona_projection(
    *,
    domains: Iterable[Any] = (),
    signals: Iterable[Any] = (),
    cap: int | None = None,
) -> dict[str, Any]:
    return project_persona(
        DEFAULT_PERSONA_ID,
        domains=domains,
        signals=signals,
        cap=cap,
    )


def psychologist_projection() -> dict[str, Any]:
    psychologist_module = load_psychologist()

    psychologist = (
        psychologist_module
        .build_orobouros_psychologist()
    )

    result = dict(
        psychologist.integration_projection()
    )

    if (
        result.get("identity")
        != DEFAULT_PERSONA_ID
    ):
        raise RuntimeError(
            "Envoy psychologist identity mismatch"
        )

    if (
        result.get("authority_effect")
        != "none"
    ):
        raise RuntimeError(
            "Envoy psychologist acquired authority"
        )

    if (
        result.get("moral_self_mutated")
        is not False
    ):
        raise RuntimeError(
            "Envoy psychologist may mutate moral self"
        )

    if (
        result.get("persona_mutated")
        is not False
    ):
        raise RuntimeError(
            "Envoy psychologist may mutate persona"
        )

    return result


def integration_status() -> dict[str, Any]:
    envoy = load_envoy()
    persona_engine = load_persona_engine()
    psychologist_module = load_psychologist()

    required_voice = (
        "list_personas",
        "resolve_persona",
        "resolve_voice",
        "synthesize",
        "synthesize_base64",
    )

    voice_capabilities = {
        name: callable(
            getattr(
                envoy,
                name,
                None,
            )
        )
        for name in required_voice
    }

    required_persona = (
        "load_persona",
        "select_living_traits",
        "compose_persona",
    )

    persona_capabilities = {
        name: callable(
            getattr(
                persona_engine,
                name,
                None,
            )
        )
        for name in required_persona
    }

    required_psychologist = (
        "build_orobouros_psychologist",
        "selftest",
    )

    psychologist_capabilities = {
        name: callable(
            getattr(
                psychologist_module,
                name,
                None,
            )
        )
        for name in required_psychologist
    }

    envoy_opus_bridge = load_envoy_opus_bridge()

    default_projection = (
        default_persona_projection()
    )

    default_persona_ready = (
        default_projection.get(
            "persona_id"
        )
        == DEFAULT_PERSONA_ID
    )

    psychologist_state = (
        psychologist_projection()
    )

    psychologist_ready = (
        psychologist_state.get(
            "identity"
        )
        == DEFAULT_PERSONA_ID
        and psychologist_state.get(
            "authority_effect"
        )
        == "none"
        and psychologist_state.get(
            "moral_self_mutated"
        )
        is False
        and psychologist_state.get(
            "persona_mutated"
        )
        is False
        and psychologist_state.get(
            "provider_authority_preserved"
        )
        is True
    )

    return {
        "owner": "palaver",
        "delegates_voice_to": "envoy",
        "delegates_persona_to": "envoy",
        "delegates_psychologist_to": "envoy",
        "provider_orchestration_owner": "opus",
        "default_persona": DEFAULT_PERSONA_ID,
        "default_persona_ready": (
            default_persona_ready
        ),
        "voice_runtime": str(
            VOICE_ENGINE
        ),
        "persona_runtime": str(
            PERSONA_ENGINE
        ),
        "psychologist_runtime": str(
            PSYCHOLOGIST
        ),
        "envoy_opus_bridge": str(
            ENVOY_OPUS_BRIDGE
        ),
        "envoy_opus_bridge_ready": callable(
            getattr(
                envoy_opus_bridge,
                "synthesize_with_opus",
                None,
            )
        ),
        "voice_capabilities": (
            voice_capabilities
        ),
        "persona_capabilities": (
            persona_capabilities
        ),
        "psychologist_capabilities": (
            psychologist_capabilities
        ),
        "psychologist_ready": (
            psychologist_ready
        ),
        "psychologist_authority_effect": (
            psychologist_state.get(
                "authority_effect"
            )
        ),
        "psychologist_visibility": (
            psychologist_state.get(
                "private_session_visibility"
            )
        ),
        "capabilities": {
            **voice_capabilities,
            "project_persona": True,
            "default_persona_projection": True,
            "psychologist_projection": True,
        },
        "ready": (
            all(
                voice_capabilities.values()
            )
            and all(
                persona_capabilities.values()
            )
            and all(
                psychologist_capabilities.values()
            )
            and default_persona_ready
            and psychologist_ready
        ),
        "authority_effect": "none",
    }


from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


class envoy_bridge_error(RuntimeError):
    pass


def _envoy_runtime() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "envoy"
        / "runtime"
    )


def _engine():
    runtime = _envoy_runtime()
    source = runtime / "persona_engine.py"

    if not source.is_file():
        raise envoy_bridge_error(
            "envoy persona engine is unavailable"
        )

    location = str(runtime)

    if location not in sys.path:
        sys.path.insert(0, location)

    module_name = "savant_urge_envoy_persona_engine"

    cached = sys.modules.get(module_name)

    if cached is not None:
        return cached

    specification = importlib.util.spec_from_file_location(
        module_name,
        source,
    )

    if specification is None or specification.loader is None:
        raise envoy_bridge_error(
            "unable to load envoy persona engine"
        )

    module = importlib.util.module_from_spec(
        specification
    )
    sys.modules[module_name] = module

    try:
        specification.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise

    return module


def _identifier(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise envoy_bridge_error(
            "persona identifier must be nonempty"
        )

    return value.strip()


def _identity(persona: Mapping[str, Any]) -> str:
    for field in ("id", "persona_id"):
        value = persona.get(field)

        if isinstance(value, str) and value.strip():
            return value.strip()

    identity = persona.get("identity")

    if isinstance(identity, Mapping):
        for field in ("id", "persona_id"):
            value = identity.get(field)

            if isinstance(value, str) and value.strip():
                return value.strip()

    raise envoy_bridge_error(
        "persona has no recognizable identifier"
    )


def load(persona_id: str) -> dict[str, Any]:
    identity = _identifier(persona_id)
    engine = _engine()

    loader = getattr(engine, "load_persona", None)

    if not callable(loader):
        raise envoy_bridge_error(
            "envoy load_persona is unavailable"
        )

    persona = loader(identity)

    if not isinstance(persona, Mapping):
        raise envoy_bridge_error(
            "envoy returned an invalid persona"
        )

    return dict(persona)


def select(
    primary: str,
    supplemental: Sequence[str] = (),
) -> dict[str, Any]:
    primary = _identifier(primary)

    if isinstance(supplemental, (str, bytes)):
        raise envoy_bridge_error(
            "supplemental personas must be a sequence"
        )

    ordered = [primary]
    seen = {primary}

    for value in supplemental:
        identity = _identifier(value)

        if identity in seen:
            raise envoy_bridge_error(
                "duplicate persona selection"
            )

        seen.add(identity)
        ordered.append(identity)

    personas = []

    for identity in ordered:
        persona = load(identity)

        if _identity(persona) != identity:
            raise envoy_bridge_error(
                "registry persona identity mismatch"
            )

        personas.append(persona)

    return {
        "primary": primary,
        "supplemental": ordered[1:],
        "personas": personas,
    }


def prompt_projection(
    selection: Mapping[str, Any],
    *,
    goal: str,
    previous_result: Any = None,
) -> dict[str, Any]:
    if not isinstance(goal, str) or not goal.strip():
        raise envoy_bridge_error("goal is required")

    if not isinstance(selection, Mapping):
        raise envoy_bridge_error(
            "persona selection must be a mapping"
        )

    primary = selection.get("primary")
    supplemental = selection.get("supplemental", [])

    resolved = select(
        primary,
        supplemental,
    )

    return {
        "goal": goal.strip(),
        "primary_persona": resolved["personas"][0],
        "supplemental_personas": resolved["personas"][1:],
        "previous_result": previous_result,
        "instructions": (
            "Use the selected personas as reasoning "
            "perspectives, not as claims of identity. "
            "Historical perspectives are interpretive "
            "reconstructions, not authenticated speech. "
            "Preserve source attribution, uncertainty, "
            "and disagreements. Do not invent evidence."
        ),
    }

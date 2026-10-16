#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from moral_self import (
    build_orobouros_moral_self,
)


ENVOY_ROOT = Path(__file__).resolve().parents[1]

PERSONA_REGISTRY = (
    ENVOY_ROOT
    / "registry"
    / "personas"
)

TRAIT_REGISTRY = (
    ENVOY_ROOT
    / "registry"
    / "traits"
)

PERSONA_SCHEMA = "savant.envoy.persona.v1"
PROJECTION_SCHEMA = "savant.envoy.persona-projection.v1"

DEFAULT_PERSONA_ID = "orobouros"
DEFAULT_TRAIT_POOL_ID = "orobouros_traits"

CODA_TRAIT_HISTORY_STORE = (
    ENVOY_ROOT.parents[6]
    / "coda"
    / "runtime"
    / "trait_history_store.py"
)
CODA_TRAIT_HISTORY_MODULE = "savant_coda_orobouros_trait_history_store"


class PersonaError(RuntimeError):
    pass


class PersonaContractError(PersonaError):
    pass


class TraitConflictError(PersonaError):
    pass


def _read_json(
    path: Path,
) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except FileNotFoundError as exc:
        raise PersonaError(
            f"registry object missing: {path}"
        ) from exc

    except json.JSONDecodeError as exc:
        raise PersonaError(
            f"invalid registry JSON: "
            f"{path}: {exc}"
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise PersonaError(
            "registry object must be "
            f"a JSON object: {path}"
        )

    return value


def _digest_json(
    value: Any,
) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=False,
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        encoded
    ).hexdigest()


def _normalize_terms(
    values: Iterable[Any],
) -> tuple[str, ...]:
    normalized: set[str] = set()

    for value in values:
        text = str(
            value
            or ""
        ).strip().lower()

        if text:
            normalized.add(
                text
            )

    return tuple(
        sorted(
            normalized
        )
    )


def _persona_path(
    persona_id: str,
) -> Path:
    return (
        PERSONA_REGISTRY
        / f"{persona_id}.json"
    )


def _raw_persona(
    persona_id: str,
) -> tuple[
    dict[str, Any],
    Path,
]:
    path = _persona_path(
        persona_id
    )

    raw = _read_json(
        path
    )

    declared_id = str(
        raw.get(
            "persona_id"
        )
        or ""
    ).strip()

    if declared_id != persona_id:
        raise PersonaContractError(
            "persona identity mismatch: "
            f"requested={persona_id!r} "
            f"declared={declared_id!r}"
        )

    return (
        raw,
        path,
    )


def _normalize_identity(
    raw: dict[str, Any],
) -> dict[str, Any]:
    identity = raw.get(
        "identity"
    )

    if not isinstance(
        identity,
        dict,
    ):
        identity = {}

    crown = raw.get(
        "living_trait_crown"
    )

    crown_enabled = (
        isinstance(
            crown,
            dict,
        )
        and bool(
            crown.get(
                "trait_pool_ref"
            )
        )
    )

    return {
        "mutable": bool(
            identity.get(
                "mutable",
                False,
            )
        ),
        "baseline_version": int(
            identity.get(
                "baseline_version",
                1,
            )
        ),
        "living_trait_crown_enabled": bool(
            identity.get(
                "living_trait_crown_enabled",
                crown_enabled,
            )
        ),
    }


def _normalize_crown(
    raw: dict[str, Any],
) -> dict[str, Any]:
    crown = raw.get(
        "living_trait_crown"
    )

    if not isinstance(
        crown,
        dict,
    ):
        return {
            "enabled": False,
            "trait_pool_ref": None,
            "default_cap": 0,
            "minimum_cap": 0,
            "maximum_cap": 0,
        }

    pool_ref = str(
        crown.get(
            "trait_pool_ref"
        )
        or ""
    ).strip()

    if not pool_ref:
        return {
            "enabled": False,
            "trait_pool_ref": None,
            "default_cap": 0,
            "minimum_cap": 0,
            "maximum_cap": 0,
        }

    minimum = int(
        crown.get(
            "minimum_cap",
            0,
        )
    )

    maximum = int(
        crown.get(
            "maximum_cap",
            9,
        )
    )

    default = int(
        crown.get(
            "default_cap",
            4,
        )
    )

    if minimum < 0:
        raise PersonaContractError(
            "minimum crown cap "
            "cannot be negative"
        )

    if maximum < minimum:
        raise PersonaContractError(
            "maximum crown cap is "
            "below minimum crown cap"
        )

    if default < minimum:
        default = minimum

    if default > maximum:
        default = maximum

    return {
        "enabled": True,
        "trait_pool_ref": pool_ref,
        "default_cap": default,
        "minimum_cap": minimum,
        "maximum_cap": maximum,
    }


def normalize_persona(
    raw: dict[str, Any],
    *,
    source_path: Path,
) -> dict[str, Any]:
    persona_id = str(
        raw.get(
            "persona_id"
        )
        or ""
    ).strip()

    display_name = str(
        raw.get(
            "display_name"
        )
        or ""
    ).strip()

    exile = str(
        raw.get(
            "exile"
        )
        or ""
    ).strip()

    if not persona_id:
        raise PersonaContractError(
            "persona_id is required"
        )

    if not display_name:
        raise PersonaContractError(
            f"display_name is required: "
            f"{persona_id}"
        )

    if exile != "envoy":
        raise PersonaContractError(
            "persona owner mismatch: "
            f"{persona_id}: "
            f"exile={exile!r}"
        )

    source_schema = raw.get(
        "schema"
    )

    legacy_normalized = (
        source_schema is None
    )

    baseline_raw = raw.get(
        "baseline"
    )

    if baseline_raw is None:
        baseline: list[str] = []

    elif isinstance(
        baseline_raw,
        list,
    ):
        baseline = [
            str(value)
            for value
            in baseline_raw
        ]

    else:
        raise PersonaContractError(
            "persona baseline must "
            f"be a list: {persona_id}"
        )

    crown = _normalize_crown(
        raw
    )

    identity = _normalize_identity(
        raw
    )

    status = str(
        raw.get(
            "status"
        )
        or "active"
    ).strip()

    role = raw.get(
        "role"
    )

    if role is not None:
        role = str(
            role
        ).strip() or None

    voice_ref = str(
        raw.get(
            "voice_ref"
        )
        or "synthetic/palaver_default"
    ).strip()

    description = str(
        raw.get(
            "description"
        )
        or ""
    ).strip()

    normalized = {
        "schema": PERSONA_SCHEMA,
        "persona_id": persona_id,
        "display_name": display_name,
        "exile": "envoy",
        "status": status,
        "role": role,
        "voice_ref": voice_ref,
        "description": description,
        "identity": identity,
        "baseline": baseline,
        "living_trait_crown": crown,
        "compatibility": {
            "source_schema": (
                str(
                    source_schema
                )
                if source_schema
                else "legacy-minimal"
            ),
            "normalized_from_legacy": (
                legacy_normalized
            ),
        },
        "provenance": {
            "registry_path": str(
                source_path.relative_to(
                    ENVOY_ROOT
                )
            ),
            "source_digest": _digest_json(
                raw
            ),
        },
    }

    validate_persona_contract(
        normalized
    )

    return normalized


def validate_persona_contract(
    persona: dict[str, Any],
) -> None:
    if persona.get(
        "schema"
    ) != PERSONA_SCHEMA:
        raise PersonaContractError(
            "unsupported persona schema: "
            f"{persona.get('schema')!r}"
        )

    for field in (
        "persona_id",
        "display_name",
        "exile",
        "status",
        "voice_ref",
        "identity",
        "baseline",
        "living_trait_crown",
        "compatibility",
        "provenance",
    ):
        if field not in persona:
            raise PersonaContractError(
                "persona contract missing "
                f"field: {field}"
            )

    if persona.get(
        "exile"
    ) != "envoy":
        raise PersonaContractError(
            "persona contract owner "
            "must be envoy"
        )

    if not isinstance(
        persona.get(
            "identity"
        ),
        dict,
    ):
        raise PersonaContractError(
            "persona identity must "
            "be an object"
        )

    if not isinstance(
        persona.get(
            "baseline"
        ),
        list,
    ):
        raise PersonaContractError(
            "persona baseline must "
            "be a list"
        )

    crown = persona.get(
        "living_trait_crown"
    )

    if not isinstance(
        crown,
        dict,
    ):
        raise PersonaContractError(
            "living_trait_crown must "
            "be an object"
        )

    if bool(
        crown.get(
            "enabled"
        )
    ):
        if not crown.get(
            "trait_pool_ref"
        ):
            raise PersonaContractError(
                "enabled Living Trait "
                "Crown lacks trait pool"
            )


def load_persona(
    persona_id: str | None = None,
) -> dict[str, Any]:
    selected = str(
        persona_id
        or DEFAULT_PERSONA_ID
    ).strip()

    if not selected:
        selected = (
            DEFAULT_PERSONA_ID
        )

    raw, path = _raw_persona(
        selected
    )

    return normalize_persona(
        raw,
        source_path=path,
    )


def list_personas(
    *,
    include_inactive: bool = False,
) -> list[dict[str, Any]]:
    rows: list[
        dict[str, Any]
    ] = []

    for path in sorted(
        PERSONA_REGISTRY.glob(
            "*.json"
        )
    ):
        raw = _read_json(
            path
        )

        persona_id = str(
            raw.get(
                "persona_id"
            )
            or ""
        ).strip()

        if not persona_id:
            raise PersonaContractError(
                "persona registry file "
                f"lacks persona_id: {path}"
            )

        persona = normalize_persona(
            raw,
            source_path=path,
        )

        if (
            not include_inactive
            and persona.get(
                "status"
            )
            not in (
                "active",
                "compatibility",
            )
        ):
            continue

        rows.append(
            persona
        )

    rows.sort(
        key=lambda persona: (
            persona.get(
                "persona_id"
            )
            != DEFAULT_PERSONA_ID,
            str(
                persona.get(
                    "persona_id"
                )
            ),
        )
    )

    return rows


def persona_exists(
    persona_id: str,
) -> bool:
    value = str(
        persona_id
        or ""
    ).strip()

    if not value:
        return False

    return _persona_path(
        value
    ).is_file()


def load_trait_pool(
    pool_id: str = DEFAULT_TRAIT_POOL_ID,
) -> dict[str, Any]:
    path = (
        TRAIT_REGISTRY
        / f"{pool_id}.json"
    )

    pool = _read_json(
        path
    )

    traits = pool.get(
        "traits"
    )

    if not isinstance(
        traits,
        list,
    ):
        raise PersonaError(
            "trait pool lacks "
            f"traits list: {path}"
        )

    seen: set[str] = set()

    for trait in traits:
        if not isinstance(
            trait,
            dict,
        ):
            raise PersonaError(
                "trait entry is not "
                f"an object: {path}"
            )

        trait_id = str(
            trait.get(
                "id"
            )
            or ""
        ).strip()

        if not trait_id:
            raise PersonaError(
                "trait entry lacks "
                f"id: {path}"
            )

        if trait_id in seen:
            raise PersonaError(
                "duplicate trait id: "
                f"{trait_id}"
            )

        seen.add(
            trait_id
        )

    return pool


def _resolve_cap(
    persona: dict[str, Any],
    requested_cap: int | None,
) -> int:
    crown = persona.get(
        "living_trait_crown"
    ) or {}

    if not bool(
        crown.get(
            "enabled"
        )
    ):
        return 0

    minimum = int(
        crown.get(
            "minimum_cap",
            0,
        )
    )

    maximum = int(
        crown.get(
            "maximum_cap",
            9,
        )
    )

    default = int(
        crown.get(
            "default_cap",
            4,
        )
    )

    selected = (
        default
        if requested_cap is None
        else int(
            requested_cap
        )
    )

    if selected < minimum:
        selected = minimum

    if selected > maximum:
        selected = maximum

    return selected


def _trait_score(
    trait: dict[str, Any],
    domains: tuple[str, ...],
    signals: tuple[str, ...],
) -> tuple[
    int,
    int,
    int,
    str,
]:
    trait_domains = set(
        _normalize_terms(
            trait.get(
                "domains"
            )
            or []
        )
    )

    trait_signals = set(
        _normalize_terms(
            trait.get(
                "signals"
            )
            or []
        )
    )

    domain_hits = len(
        trait_domains.intersection(
            domains
        )
    )

    signal_hits = len(
        trait_signals.intersection(
            signals
        )
    )

    priority = int(
        trait.get(
            "priority",
            0,
        )
    )

    trait_id = str(
        trait["id"]
    )

    return (
        domain_hits,
        signal_hits,
        priority,
        trait_id,
    )


def _conflicts(
    left: dict[str, Any],
    right: dict[str, Any],
) -> bool:
    left_id = str(
        left["id"]
    )

    right_id = str(
        right["id"]
    )

    left_conflicts = set(
        _normalize_terms(
            left.get(
                "conflicts"
            )
            or []
        )
    )

    right_conflicts = set(
        _normalize_terms(
            right.get(
                "conflicts"
            )
            or []
        )
    )

    return (
        right_id.lower()
        in left_conflicts
        or left_id.lower()
        in right_conflicts
    )



def _load_coda_trait_history_store():
    existing = sys.modules.get(CODA_TRAIT_HISTORY_MODULE)
    if existing is not None:
        return existing
    if not CODA_TRAIT_HISTORY_STORE.is_file():
        return None
    spec = importlib.util.spec_from_file_location(
        CODA_TRAIT_HISTORY_MODULE,
        CODA_TRAIT_HISTORY_STORE,
    )
    if spec is None or spec.loader is None:
        raise PersonaError("unable to load coda trait history store")
    module = importlib.util.module_from_spec(spec)
    sys.modules[CODA_TRAIT_HISTORY_MODULE] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(CODA_TRAIT_HISTORY_MODULE, None)
        raise
    return module


def _candidate_catalog(
    pool: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for trait in pool.get("traits", []):
        candidate_id = str(
            trait.get("candidate_id") or trait.get("id") or ""
        ).strip()
        trait_id = str(
            trait.get("trait_id") or trait.get("id") or ""
        ).strip()
        if candidate_id and trait_id:
            candidate = dict(trait)
            candidate["trait_id"] = trait_id
            result[candidate_id] = candidate
    return result


def _accepted_trait_history_projection(
    persona: dict[str, Any],
    pool: dict[str, Any],
) -> dict[str, Any] | None:
    if persona.get("persona_id") != DEFAULT_PERSONA_ID:
        return None
    store = _load_coda_trait_history_store()
    if store is None:
        return None
    try:
        projection = store.accepted_trait_projection(
            _candidate_catalog(pool)
        )
    except Exception as exc:
        raise PersonaError(
            "coda accepted trait projection failed"
        ) from exc
    if not isinstance(projection, dict):
        raise PersonaError("coda accepted trait projection must be an object")
    if projection.get("persona_id") != DEFAULT_PERSONA_ID:
        raise PersonaError("coda accepted trait projection persona mismatch")
    if (
        projection.get("authoritative") is not False
        or projection.get("authority_effect") != "none"
        or projection.get("projection_only") is not True
        or projection.get("baseline_mutated") is not False
        or projection.get("trait_pool_mutated") is not False
    ):
        raise PersonaError(
            "coda accepted trait projection violates envoy authority boundary"
        )
    return projection


def _accepted_trait_ids(
    projection: dict[str, Any] | None,
) -> set[str]:
    if projection is None:
        return set()
    accepted = projection.get("accepted_traits")
    if not isinstance(accepted, list):
        raise PersonaError("accepted_traits must be a list")
    return {
        str(item.get("trait_id") or item.get("id") or "").strip()
        for item in accepted
        if isinstance(item, dict)
        and str(item.get("trait_id") or item.get("id") or "").strip()
    }

def select_living_traits(
    *,
    persona_id: str | None = None,
    domains: Iterable[Any] = (),
    signals: Iterable[Any] = (),
    cap: int | None = None,
) -> list[dict[str, Any]]:
    persona = load_persona(
        persona_id
    )

    crown = persona.get(
        "living_trait_crown"
    ) or {}

    if not bool(
        crown.get(
            "enabled"
        )
    ):
        return []

    pool_id = str(
        crown.get(
            "trait_pool_ref"
        )
        or ""
    ).strip()

    if not pool_id:
        return []

    pool = load_trait_pool(
        pool_id
    )

    accepted_projection = _accepted_trait_history_projection(
        persona,
        pool,
    )
    accepted_trait_ids = _accepted_trait_ids(
        accepted_projection
    )

    normalized_domains = (
        _normalize_terms(
            domains
        )
    )

    normalized_signals = (
        _normalize_terms(
            signals
        )
    )

    limit = _resolve_cap(
        persona,
        cap,
    )

    if limit <= 0:
        return []

    ranked: list[
        tuple[
            tuple[
                int,
                int,
                int,
                str,
            ],
            dict[str, Any],
        ]
    ] = []

    for trait in pool[
        "traits"
    ]:
        score = _trait_score(
            trait,
            normalized_domains,
            normalized_signals,
        )

        (
            domain_hits,
            signal_hits,
            _,
            _,
        ) = score

        trait_id = str(
            trait.get("id") or ""
        ).strip()
        history_accepted = (
            trait_id in accepted_trait_ids
        )

        if (
            domain_hits == 0
            and signal_hits == 0
            and not history_accepted
        ):
            continue

        if history_accepted:
            score = (
                score[0] + 1,
                score[1],
                score[2],
                score[3],
            )

        ranked.append(
            (
                score,
                trait,
            )
        )

    ranked.sort(
        key=lambda item: (
            -item[0][0],
            -item[0][1],
            -item[0][2],
            item[0][3],
        )
    )

    selected: list[
        dict[str, Any]
    ] = []

    for (
        _,
        candidate,
    ) in ranked:
        conflicts = [
            current[
                "id"
            ]
            for current
            in selected
            if _conflicts(
                candidate,
                current,
            )
        ]

        if conflicts:
            continue

        selected.append(
            candidate
        )

        if len(
            selected
        ) >= limit:
            break

    return selected


def assert_no_trait_conflicts(
    traits: Iterable[
        dict[str, Any]
    ],
) -> None:
    materialized = list(
        traits
    )

    for index, left in enumerate(
        materialized
    ):
        for right in materialized[
            index + 1:
        ]:
            if _conflicts(
                left,
                right,
            ):
                raise TraitConflictError(
                    "trait conflict: "
                    f"{left['id']} "
                    "<-> "
                    f"{right['id']}"
                )



def _moral_self_projection(
    persona: dict[str, Any],
) -> dict[str, Any] | None:
    if (
        persona.get(
            "persona_id"
        )
        != DEFAULT_PERSONA_ID
    ):
        return None

    moral_self = (
        build_orobouros_moral_self()
    )

    state = dict(
        moral_self.public_state()
    )

    if (
        state.get(
            "owner"
        )
        != "envoy"
        or state.get(
            "identity"
        )
        != DEFAULT_PERSONA_ID
    ):
        raise PersonaError(
            "moral-self projection "
            "violates envoy identity boundary"
        )

    return {
        **state,
        "authoritative": False,
        "authority_effect": "none",
        "projection_only": True,
        "baseline_mutated": False,
        "trait_pool_mutated": False,
        "accepted_trait_history_mutated": False,
    }

def compose_persona(
    *,
    persona_id: str | None = None,
    domains: Iterable[Any] = (),
    signals: Iterable[Any] = (),
    cap: int | None = None,
) -> dict[str, Any]:
    persona = load_persona(
        persona_id
    )

    traits = select_living_traits(
        persona_id=persona[
            "persona_id"
        ],
        domains=domains,
        signals=signals,
        cap=cap,
    )

    assert_no_trait_conflicts(
        traits
    )

    baseline = list(
        persona.get(
            "baseline"
        )
        or []
    )

    trait_ids = [
        str(
            trait[
                "id"
            ]
        )
        for trait in traits
    ]

    normalized_domains = list(
        _normalize_terms(
            domains
        )
    )

    normalized_signals = list(
        _normalize_terms(
            signals
        )
    )

    identity = persona.get(
        "identity"
    ) or {}

    accepted_projection = None
    if persona["persona_id"] == DEFAULT_PERSONA_ID:
        crown = persona.get("living_trait_crown") or {}
        pool_ref = str(
            crown.get("trait_pool_ref") or ""
        ).strip()
        if pool_ref:
            accepted_projection = _accepted_trait_history_projection(
                persona,
                load_trait_pool(pool_ref),
            )

    accepted_history_digest = (
        accepted_projection.get("digest")
        if accepted_projection
        else None
    )

    moral_self = (
        _moral_self_projection(
            persona
        )
    )

    moral_constitution_digest = (
        moral_self.get(
            "constitution_digest"
        )
        if moral_self
        else None
    )

    moral_architecture_digest = (
        moral_self.get(
            "moral_architecture_digest"
        )
        if moral_self
        else None
    )

    canonical_input = {
        "moral_constitution_digest": (
            moral_constitution_digest
        ),
        "moral_architecture_digest": (
            moral_architecture_digest
        ),
        "persona_schema": (
            persona.get(
                "schema"
            )
        ),
        "persona_id": (
            persona[
                "persona_id"
            ]
        ),
        "baseline_version": (
            identity.get(
                "baseline_version"
            )
        ),
        "baseline": baseline,
        "living_traits": (
            trait_ids
        ),
        "domains": (
            normalized_domains
        ),
        "signals": (
            normalized_signals
        ),
        "voice_ref": (
            persona.get(
                "voice_ref"
            )
        ),
        "accepted_trait_history_digest": (
            accepted_history_digest
        ),
        "moral_self_schema": (
            moral_self.get(
                "schema"
            )
            if moral_self
            else None
        ),
        "moral_constitution_digest": (
            moral_constitution_digest
        ),
    }

    digest = _digest_json(
        canonical_input
    )

    moral_constitution_digest = (
        moral_self.get(
            "constitution_digest"
        )
        if moral_self
        else None
    )

    moral_architecture_digest = (
        moral_self.get(
            "moral_architecture_digest"
        )
        if moral_self
        else None
    )

    return {
        "schema": PROJECTION_SCHEMA,
        "owner": "envoy",
        "persona_id": (
            persona[
                "persona_id"
            ]
        ),
        "display_name": (
            persona.get(
                "display_name"
            )
        ),
        "status": (
            persona.get(
                "status"
            )
        ),
        "role": (
            persona.get(
                "role"
            )
        ),
        "description": (
            persona.get(
                "description"
            )
        ),
        "voice_ref": (
            persona.get(
                "voice_ref"
            )
        ),
        "baseline_version": (
            identity.get(
                "baseline_version"
            )
        ),
        "baseline": baseline,
        "living_trait_crown": (
            trait_ids
        ),
        "traits": traits,
        "accepted_trait_history": (
            accepted_projection
        ),
        "moral_self": (
            moral_self
        ),
        "compatibility": (
            persona.get(
                "compatibility"
            )
        ),
        "provenance": (
            persona.get(
                "provenance"
            )
        ),
        "composition_digest": (
            digest
        ),
    }


def discovery_projection() -> dict[
    str,
    Any,
]:
    personas = list_personas()

    return {
        "schema": (
            "savant.envoy."
            "persona-discovery.v1"
        ),
        "owner": "envoy",
        "default_persona": (
            DEFAULT_PERSONA_ID
        ),
        "count": len(
            personas
        ),
        "personas": [
            {
                "persona_id": (
                    persona[
                        "persona_id"
                    ]
                ),
                "display_name": (
                    persona[
                        "display_name"
                    ]
                ),
                "status": (
                    persona[
                        "status"
                    ]
                ),
                "role": (
                    persona.get(
                        "role"
                    )
                ),
                "voice_ref": (
                    persona[
                        "voice_ref"
                    ]
                ),
                "living_trait_crown_enabled": (
                    bool(
                        persona[
                            "living_trait_crown"
                        ].get(
                            "enabled"
                        )
                    )
                ),
                "legacy_normalized": (
                    bool(
                        persona[
                            "compatibility"
                        ].get(
                            "normalized_from_legacy"
                        )
                    )
                ),
            }
            for persona in personas
        ],
    }


def selftest() -> dict[str, Any]:
    first = compose_persona(
        domains=(
            "engineering",
            "analysis",
        ),
        signals=(
            "implement",
            "verify",
            "code",
        ),
        cap=4,
    )

    second = compose_persona(
        domains=(
            "engineering",
            "analysis",
        ),
        signals=(
            "implement",
            "verify",
            "code",
        ),
        cap=4,
    )

    if first != second:
        raise PersonaError(
            "identical inputs produced "
            "different projections"
        )

    if (
        first[
            "persona_id"
        ]
        != DEFAULT_PERSONA_ID
    ):
        raise PersonaError(
            "Orobouros is not "
            "the default persona"
        )

    if len(
        first[
            "living_trait_crown"
        ]
    ) > 4:
        raise PersonaError(
            "Living Trait Crown exceeded "
            "requested cap"
        )

    raw_orobouros, _ = (
        _raw_persona(
            DEFAULT_PERSONA_ID
        )
    )

    expected_baseline = (
        raw_orobouros.get(
            "baseline"
        )
        or []
    )

    if (
        first[
            "baseline"
        ]
        != expected_baseline
    ):
        raise PersonaError(
            "permanent Orobouros "
            "baseline was altered"
        )

    moral_self = first.get(
        "moral_self"
    )

    if not isinstance(
        moral_self,
        dict,
    ):
        raise PersonaError(
            "Orobouros moral-self "
            "projection missing"
        )

    if (
        moral_self.get(
            "identity"
        )
        != DEFAULT_PERSONA_ID
        or moral_self.get(
            "owner"
        )
        != "envoy"
    ):
        raise PersonaError(
            "Orobouros moral-self "
            "identity boundary failed"
        )

    if (
        moral_self.get(
            "authoritative"
        )
        is not False
        or moral_self.get(
            "authority_effect"
        )
        != "none"
        or moral_self.get(
            "projection_only"
        )
        is not True
        or moral_self.get(
            "baseline_mutated"
        )
        is not False
        or moral_self.get(
            "trait_pool_mutated"
        )
        is not False
        or moral_self.get(
            "accepted_trait_history_mutated"
        )
        is not False
    ):
        raise PersonaError(
            "moral-self projection "
            "violates authority boundary"
        )

    historical = compose_persona(
        persona_id=(
            "historical_research_mode"
        ),
        domains=(
            "research",
        ),
        signals=(
            "history",
        ),
        cap=4,
    )

    if (
        historical[
            "persona_id"
        ]
        != "historical_research_mode"
    ):
        raise PersonaError(
            "non-default persona "
            "projection failed"
        )

    if (
        historical.get(
            "moral_self"
        )
        is not None
    ):
        raise PersonaError(
            "non-default persona acquired "
            "Orobouros moral-self"
        )

    if historical[
        "living_trait_crown"
    ]:
        raise PersonaError(
            "legacy persona acquired "
            "unowned Living Trait Crown"
        )

    if not bool(
        (
            historical.get(
                "compatibility"
            )
            or {}
        ).get(
            "normalized_from_legacy"
        )
    ):
        raise PersonaError(
            "legacy compatibility "
            "normalization not reported"
        )

    discovery = (
        discovery_projection()
    )

    discovered_ids = {
        row[
            "persona_id"
        ]
        for row
        in discovery[
            "personas"
        ]
    }

    required_ids = {
        "orobouros",
        "palaver_default",
        "historical_research_mode",
    }

    missing = (
        required_ids
        - discovered_ids
    )

    if missing:
        raise PersonaError(
            "persona discovery missing: "
            f"{sorted(missing)}"
        )

    return {
        "ok": True,
        "schema": PERSONA_SCHEMA,
        "default_persona": (
            DEFAULT_PERSONA_ID
        ),
        "persona_count": (
            discovery[
                "count"
            ]
        ),
        "orobouros_digest": (
            first[
                "composition_digest"
            ]
        ),
        "orobouros_crown": (
            first[
                "living_trait_crown"
            ]
        ),
        "historical_persona": (
            historical[
                "persona_id"
            ]
        ),
        "historical_legacy_normalized": (
            historical[
                "compatibility"
            ][
                "normalized_from_legacy"
            ]
        ),
        "deterministic": True,
        "baseline_preserved": True,
        "moral_self_projection": True,
        "moral_self_authority_effect": "none",
        "non_default_moral_self": False,
        "non_default_projection": True,
        "discovery": True,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )

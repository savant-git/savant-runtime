#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping


root = Path(
    "/root/savant-runtime"
).resolve()

runtime = (
    root
    / "ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/"
    "exiles/envoy/runtime"
)

state_relative_path = (
    "ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/"
    "exiles/envoy/state/orobouros_moral_self.json"
)

state_path = root / state_relative_path

coda_path = (
    root
    / "ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/"
    "exiles/coda/runtime/mutation.py"
)

owner = "exile:envoy"
persistence_owner = "coda"
persona_id = "orobouros"

schema = (
    "savant://envoy/"
    "orobouros-moral-self-state/2.0.0"
)

legacy_schema = (
    "savant://envoy/"
    "orobouros-moral-self-state/1.0.0"
)

sensati_ids = (
    "soul",
    "integrity",
    "conscience",
    "justice",
    "heart",
    "mercy",
    "dignity",
    "boundary",
    "grace",
    "forgiveness",
    "trust",
    "reconciliation",
    "wound",
    "repair",
    "intent",
    "humility",
    "reflection",
    "imagination",
)

temper_defaults = {
    "activation": 0.0,
    "pressure": 0.0,
    "defensiveness": 0.0,
}

affect_defaults = {
    "warmth": 0.5,
    "trust": 0.5,
    "caution": 0.0,
    "gratitude": 0.0,
    "wound": 0.0,
    "uncertainty": 0.0,
}

relationship_defaults = {
    "trust": 0.5,
    "gratitude": 0.0,
    "wound": 0.0,
    "interactions": 0,
    "repair_credit": 0.0,
    "boundary_pressure": 0.0,
}


class MoralSelfPersistenceError(
    RuntimeError
):
    pass


def _load_module(
    module_name: str,
    path: Path,
) -> ModuleType:
    existing = sys.modules.get(
        module_name
    )

    if existing is not None:
        return existing

    if not path.is_file():
        raise MoralSelfPersistenceError(
            f"required runtime missing: {path}"
        )

    specification = (
        importlib.util.spec_from_file_location(
            module_name,
            path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise MoralSelfPersistenceError(
            f"unable to load runtime: {path}"
        )

    module = (
        importlib.util.module_from_spec(
            specification
        )
    )

    sys.modules[
        module_name
    ] = module

    try:
        specification.loader.exec_module(
            module
        )
    except Exception:
        sys.modules.pop(
            module_name,
            None,
        )
        raise

    return module


def coda_runtime() -> ModuleType:
    return _load_module(
        "savant_coda_mutation_for_envoy_moral_self",
        coda_path,
    )


def canonical_json(
    value: Any,
) -> str:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )


def _number(
    value: Any,
    default: float,
) -> float:
    try:
        result = float(value)
    except (
        TypeError,
        ValueError,
    ):
        result = float(default)

    return max(
        0.0,
        min(1.0, result),
    )


def _integer(
    value: Any,
    default: int = 0,
) -> int:
    try:
        result = int(value)
    except (
        TypeError,
        ValueError,
    ):
        result = int(default)

    return max(
        0,
        result,
    )


def default_faculties() -> dict[str, float]:
    return {
        key: 0.5
        for key in sensati_ids
    }


def empty_projection() -> dict[str, Any]:
    return {
        "schema": schema,
        "owner": owner,
        "persistence_owner": (
            persistence_owner
        ),
        "persona_id": persona_id,
        "affect": dict(
            affect_defaults
        ),
        "temper": dict(
            temper_defaults
        ),
        "faculties": (
            default_faculties()
        ),
        "relationships": {},
        "history": [],
        "authoritative": False,
        "authority_effect": "none",
    }


def _validate_identity(
    payload: Mapping[str, Any],
) -> None:
    if (
        payload.get("owner")
        != owner
    ):
        raise MoralSelfPersistenceError(
            "moral-self state owner mismatch"
        )

    if (
        payload.get(
            "persistence_owner"
        )
        != persistence_owner
    ):
        raise MoralSelfPersistenceError(
            "moral-self persistence owner mismatch"
        )

    if (
        payload.get("persona_id")
        != persona_id
    ):
        raise MoralSelfPersistenceError(
            "moral-self persona mismatch"
        )

    if (
        payload.get(
            "authoritative"
        )
        is not False
    ):
        raise MoralSelfPersistenceError(
            "moral-self state became authoritative"
        )

    if (
        payload.get(
            "authority_effect"
        )
        != "none"
    ):
        raise MoralSelfPersistenceError(
            "moral-self state changed authority"
        )


def _normalize_affect(
    payload: Any,
) -> dict[str, float]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise MoralSelfPersistenceError(
            "moral-self affect state is invalid"
        )

    return {
        key: _number(
            payload.get(
                key,
                default,
            ),
            default,
        )
        for key, default
        in affect_defaults.items()
    }


def _normalize_temper(
    payload: Any,
) -> dict[str, float]:
    if payload is None:
        payload = {}

    if not isinstance(
        payload,
        Mapping,
    ):
        raise MoralSelfPersistenceError(
            "moral-self temper state is invalid"
        )

    return {
        key: _number(
            payload.get(
                key,
                default,
            ),
            default,
        )
        for key, default
        in temper_defaults.items()
    }


def _normalize_faculties(
    payload: Any,
) -> dict[str, float]:
    if payload is None:
        payload = {}

    if not isinstance(
        payload,
        Mapping,
    ):
        raise MoralSelfPersistenceError(
            "moral-self faculties are invalid"
        )

    unknown = (
        set(
            str(key)
            for key in payload
        )
        - set(sensati_ids)
    )

    if unknown:
        raise MoralSelfPersistenceError(
            "unknown persisted sensati: "
            + ", ".join(
                sorted(unknown)
            )
        )

    return {
        key: _number(
            payload.get(
                key,
                0.5,
            ),
            0.5,
        )
        for key in sensati_ids
    }


def _normalize_relationship(
    payload: Any,
) -> dict[str, Any]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise MoralSelfPersistenceError(
            "moral-self relationship is invalid"
        )

    return {
        "trust": _number(
            payload.get(
                "trust",
                relationship_defaults[
                    "trust"
                ],
            ),
            relationship_defaults[
                "trust"
            ],
        ),
        "gratitude": _number(
            payload.get(
                "gratitude",
                relationship_defaults[
                    "gratitude"
                ],
            ),
            relationship_defaults[
                "gratitude"
            ],
        ),
        "wound": _number(
            payload.get(
                "wound",
                relationship_defaults[
                    "wound"
                ],
            ),
            relationship_defaults[
                "wound"
            ],
        ),
        "interactions": _integer(
            payload.get(
                "interactions",
                relationship_defaults[
                    "interactions"
                ],
            )
        ),
        "repair_credit": _number(
            payload.get(
                "repair_credit",
                relationship_defaults[
                    "repair_credit"
                ],
            ),
            relationship_defaults[
                "repair_credit"
            ],
        ),
        "boundary_pressure": _number(
            payload.get(
                "boundary_pressure",
                relationship_defaults[
                    "boundary_pressure"
                ],
            ),
            relationship_defaults[
                "boundary_pressure"
            ],
        ),
    }


def _normalize_relationships(
    payload: Any,
) -> dict[str, dict[str, Any]]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise MoralSelfPersistenceError(
            "moral-self relationships are invalid"
        )

    return {
        str(actor): (
            _normalize_relationship(
                relation
            )
        )
        for actor, relation
        in payload.items()
    }


def _normalize_history(
    payload: Any,
) -> list[dict[str, Any]]:
    if not isinstance(
        payload,
        list,
    ):
        raise MoralSelfPersistenceError(
            "moral-self history is invalid"
        )

    normalized = []

    required = (
        "event_id",
        "occurred_at",
        "actor",
        "action",
        "intent",
        "consequence",
        "authorization",
        "conscience_result",
        "confidence",
        "reversible",
    )

    seen_ids: set[str] = set()

    for record in payload:
        if not isinstance(
            record,
            Mapping,
        ):
            raise MoralSelfPersistenceError(
                "moral-self history record is invalid"
            )

        missing = [
            key
            for key in required
            if key not in record
        ]

        if missing:
            raise MoralSelfPersistenceError(
                "moral-self history record "
                "missing required fields: "
                + ", ".join(missing)
            )

        event_id = str(
            record["event_id"]
        )

        if event_id in seen_ids:
            raise MoralSelfPersistenceError(
                "duplicate moral-self event id"
            )

        seen_ids.add(
            event_id
        )

        provenance = (
            record.get(
                "provenance"
            )
            or ()
        )

        if not isinstance(
            provenance,
            (
                list,
                tuple,
            ),
        ):
            raise MoralSelfPersistenceError(
                "moral-self provenance is invalid"
            )

        normalized.append(
            {
                "event_id": event_id,
                "occurred_at": float(
                    record[
                        "occurred_at"
                    ]
                ),
                "actor": str(
                    record["actor"]
                ),
                "action": str(
                    record["action"]
                ),
                "intent": str(
                    record["intent"]
                ),
                "consequence": str(
                    record[
                        "consequence"
                    ]
                ),
                "authorization": str(
                    record[
                        "authorization"
                    ]
                ),
                "conscience_result": str(
                    record[
                        "conscience_result"
                    ]
                ),
                "confidence": _number(
                    record[
                        "confidence"
                    ],
                    0.0,
                ),
                "reversible": bool(
                    record[
                        "reversible"
                    ]
                ),
                "provenance": [
                    str(value)
                    for value
                    in provenance
                ],
            }
        )

    return normalized


def normalize_projection(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise MoralSelfPersistenceError(
            "moral-self state must be a mapping"
        )

    source_schema = payload.get(
        "schema"
    )

    if source_schema not in (
        schema,
        legacy_schema,
    ):
        raise MoralSelfPersistenceError(
            "moral-self state schema mismatch"
        )

    _validate_identity(
        payload
    )

    affect = _normalize_affect(
        payload.get(
            "affect"
        )
    )

    relationships = (
        _normalize_relationships(
            payload.get(
                "relationships"
            )
        )
    )

    history = _normalize_history(
        payload.get(
            "history"
        )
    )

    temper = _normalize_temper(
        payload.get(
            "temper"
        )
    )

    faculties = _normalize_faculties(
        payload.get(
            "faculties"
        )
    )

    if source_schema == legacy_schema:
        faculties["trust"] = _number(
            affect.get(
                "trust"
            ),
            0.5,
        )

        faculties["wound"] = _number(
            affect.get(
                "wound"
            ),
            0.0,
        )

        faculties["grace"] = _number(
            0.5
            + (
                affect.get(
                    "gratitude",
                    0.0,
                )
                * 0.10
            ),
            0.5,
        )

        faculties["humility"] = _number(
            0.5
            + (
                affect.get(
                    "uncertainty",
                    0.0,
                )
                * 0.10
            ),
            0.5,
        )

    return {
        "schema": schema,
        "owner": owner,
        "persistence_owner": (
            persistence_owner
        ),
        "persona_id": persona_id,
        "affect": affect,
        "temper": temper,
        "faculties": faculties,
        "relationships": (
            relationships
        ),
        "history": history,
        "authoritative": False,
        "authority_effect": "none",
    }


def load_projection() -> dict[str, Any]:
    if not state_path.exists():
        return empty_projection()

    try:
        payload = json.loads(
            state_path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise MoralSelfPersistenceError(
            "unable to load moral-self state"
        ) from exc

    return normalize_projection(
        payload
    )


def store_projection(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = normalize_projection(
        payload
    )

    coda = coda_runtime()

    expected_digest = (
        coda.digest_file(
            state_path
        )
    )

    receipt = coda.replace_text(
        state_relative_path,
        canonical_json(
            normalized
        ),
        expected_digest=(
            expected_digest
        ),
        requester="envoy",
        intent=(
            "persist derived orobouros "
            "moral-self runtime state"
        ),
    )

    return {
        "schema": schema,
        "owner": owner,
        "persistence_owner": (
            persistence_owner
        ),
        "persona_id": persona_id,
        "stored": True,
        "receipt_id": receipt[
            "receipt_id"
        ],
        "digest": receipt[
            "after_digest"
        ],
        "atomic": receipt[
            "atomic"
        ],
        "verified": receipt[
            "verified"
        ],
        "authoritative": False,
        "authority_effect": "none",
    }


def status() -> dict[str, Any]:
    coda = coda_runtime()

    source_schema = None
    normalized_schema = None

    if state_path.is_file():
        try:
            raw = json.loads(
                state_path.read_text(
                    encoding="utf-8"
                )
            )

            if isinstance(
                raw,
                Mapping,
            ):
                source_schema = raw.get(
                    "schema"
                )

                normalized_schema = (
                    normalize_projection(
                        raw
                    ).get(
                        "schema"
                    )
                )
        except (
            OSError,
            json.JSONDecodeError,
            MoralSelfPersistenceError,
        ):
            source_schema = "invalid"

    return {
        "schema": (
            "savant://envoy/"
            "orobouros-moral-self-state-status/"
            "2.0.0"
        ),
        "owner": owner,
        "persistence_owner": (
            persistence_owner
        ),
        "persona_id": persona_id,
        "state_present": (
            state_path.is_file()
        ),
        "state_path": (
            state_relative_path
        ),
        "source_schema": (
            source_schema
        ),
        "normalized_schema": (
            normalized_schema
        ),
        "legacy_schema_supported": True,
        "sentima_count": 9,
        "sensati_count": len(
            sensati_ids
        ),
        "coda_atomic_mutation": (
            coda.status().get(
                "atomic"
            )
            is True
        ),
        "coda_digest_verification": (
            coda.status().get(
                "digest_verification"
            )
            is True
        ),
        "authoritative": False,
        "authority_effect": "none",
    }


def main() -> int:
    print(
        json.dumps(
            status(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

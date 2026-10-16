#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence


ROOT = Path(
    "/root/savant-runtime"
).resolve()

ENVOY_RUNTIME = (
    ROOT
    / "ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/"
    "exiles/envoy/runtime"
)

CODA_RUNTIME = (
    ROOT
    / "ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/"
    "exiles/coda/runtime"
)

STATE_RELATIVE_PATH = (
    "ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/"
    "exiles/envoy/state/orobouros_trait_candidates.json"
)

STATE_PATH = (
    ROOT
    / STATE_RELATIVE_PATH
)

EVIDENCE_PATH = (
    ENVOY_RUNTIME
    / "trait_evidence.py"
)

CODA_PATH = (
    CODA_RUNTIME
    / "mutation.py"
)

OWNER = "exile:envoy"
PERSISTENCE_OWNER = "coda"

SCHEMA = (
    "savant://envoy/"
    "orobouros-trait-candidate-store/1.0.0"
)


class TraitCandidatePersistenceError(
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
        raise TraitCandidatePersistenceError(
            f"required runtime missing: {path}"
        )

    specification = (
        importlib.util
        .spec_from_file_location(
            module_name,
            path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise TraitCandidatePersistenceError(
            f"unable to load runtime: {path}"
        )

    module = (
        importlib.util
        .module_from_spec(
            specification
        )
    )

    sys.modules[
        module_name
    ] = module

    specification.loader.exec_module(
        module
    )

    return module


def evidence_runtime() -> ModuleType:
    return _load_module(
        "savant_envoy_trait_evidence_for_candidate_store",
        EVIDENCE_PATH,
    )


def coda_runtime() -> ModuleType:
    return _load_module(
        "savant_coda_mutation_for_envoy_candidates",
        CODA_PATH,
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
            default=str,
        )
        + "\n"
    )


def normalize_text(
    value: Any,
) -> str:
    return str(
        value
        or ""
    ).strip()


def normalize_term(
    value: Any,
) -> str:
    return (
        normalize_text(
            value
        )
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def require_mapping(
    value: Any,
    label: str,
) -> Mapping[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise TraitCandidatePersistenceError(
            f"{label} must be a mapping"
        )

    return value


def validate_candidate_projection(
    candidate_id: str,
    projection: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    candidate = dict(
        require_mapping(
            projection,
            "candidate projection",
        )
    )

    identity = normalize_text(
        candidate.get(
            "candidate_id"
        )
    )

    if not identity:
        raise TraitCandidatePersistenceError(
            "candidate projection lacks "
            "candidate_id"
        )

    if identity != candidate_id:
        raise TraitCandidatePersistenceError(
            "candidate catalog key does not "
            "match candidate_id"
        )

    if not identity.startswith(
        "trait-candidate:"
    ):
        raise TraitCandidatePersistenceError(
            "invalid candidate identity"
        )

    trait_id = normalize_term(
        candidate.get(
            "trait_id"
        )
    )

    if not trait_id:
        raise TraitCandidatePersistenceError(
            "candidate projection lacks "
            "trait_id"
        )

    description = normalize_text(
        candidate.get(
            "description"
        )
    )

    if not description:
        raise TraitCandidatePersistenceError(
            "candidate projection lacks "
            "description"
        )

    if (
        candidate.get(
            "authoritative"
        )
        is not False
    ):
        raise TraitCandidatePersistenceError(
            "candidate unexpectedly became "
            "authoritative"
        )

    if (
        normalize_text(
            candidate.get(
                "authority_effect"
            )
        )
        != "none"
    ):
        raise TraitCandidatePersistenceError(
            "candidate changed authority"
        )

    if (
        candidate.get(
            "champion"
        )
        is not False
    ):
        raise TraitCandidatePersistenceError(
            "candidate catalog may not "
            "declare a champion"
        )

    normalized = dict(
        candidate
    )

    normalized[
        "candidate_id"
    ] = identity

    normalized[
        "trait_id"
    ] = trait_id

    normalized[
        "description"
    ] = description

    return normalized


def normalize_catalog(
    candidates: Mapping[
        str,
        Mapping[
            str,
            Any,
        ],
    ],
) -> dict[
    str,
    dict[str, Any],
]:
    if not isinstance(
        candidates,
        Mapping,
    ):
        raise TraitCandidatePersistenceError(
            "candidate catalog must be "
            "a mapping"
        )

    normalized: dict[
        str,
        dict[str, Any],
    ] = {}

    for raw_id, projection in (
        candidates.items()
    ):
        candidate_id = normalize_text(
            raw_id
        )

        if not candidate_id:
            raise TraitCandidatePersistenceError(
                "candidate catalog contains "
                "empty identity"
            )

        if candidate_id in normalized:
            raise TraitCandidatePersistenceError(
                "duplicate candidate identity"
            )

        normalized[
            candidate_id
        ] = validate_candidate_projection(
            candidate_id,
            projection,
        )

    return {
        candidate_id: normalized[
            candidate_id
        ]
        for candidate_id
        in sorted(
            normalized
        )
    }


def empty_store_projection() -> dict[
    str,
    Any,
]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "persistence_owner": (
            PERSISTENCE_OWNER
        ),
        "persona_id": "orobouros",
        "candidates": {},
        "candidate_count": 0,
        "identity_model": (
            "content_addressed"
        ),
        "immutable_candidates": True,
        "append_only_model": True,
        "champion_selection_local": False,
        "authoritative": False,
        "authority_effect": "none",
        "rebuildable": True,
    }


def store_projection(
    candidates: Mapping[
        str,
        Mapping[
            str,
            Any,
        ],
    ],
) -> dict[
    str,
    Any,
]:
    normalized = normalize_catalog(
        candidates
    )

    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "persistence_owner": (
            PERSISTENCE_OWNER
        ),
        "persona_id": "orobouros",
        "candidates": normalized,
        "candidate_count": len(
            normalized
        ),
        "identity_model": (
            "content_addressed"
        ),
        "immutable_candidates": True,
        "append_only_model": True,
        "champion_selection_local": False,
        "authoritative": False,
        "authority_effect": "none",
        "rebuildable": True,
    }


def load_store_projection() -> dict[
    str,
    Any,
]:
    if not STATE_PATH.exists():
        return empty_store_projection()

    if not STATE_PATH.is_file():
        raise TraitCandidatePersistenceError(
            "candidate state path is not "
            "a file"
        )

    try:
        payload = json.loads(
            STATE_PATH.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as exc:
        raise TraitCandidatePersistenceError(
            "persisted candidate catalog "
            "is invalid JSON"
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise TraitCandidatePersistenceError(
            "persisted candidate catalog "
            "must be an object"
        )

    if payload.get(
        "schema"
    ) != SCHEMA:
        raise TraitCandidatePersistenceError(
            "candidate store schema mismatch"
        )

    if payload.get(
        "owner"
    ) != OWNER:
        raise TraitCandidatePersistenceError(
            "candidate store owner mismatch"
        )

    if (
        payload.get(
            "persistence_owner"
        )
        != PERSISTENCE_OWNER
    ):
        raise TraitCandidatePersistenceError(
            "candidate persistence owner "
            "mismatch"
        )

    if payload.get(
        "persona_id"
    ) != "orobouros":
        raise TraitCandidatePersistenceError(
            "candidate persona mismatch"
        )

    candidates = payload.get(
        "candidates"
    )

    if not isinstance(
        candidates,
        dict,
    ):
        raise TraitCandidatePersistenceError(
            "persisted candidate catalog "
            "must contain candidates object"
        )

    normalized = normalize_catalog(
        candidates
    )

    if (
        int(
            payload.get(
                "candidate_count",
                -1,
            )
        )
        != len(
            normalized
        )
    ):
        raise TraitCandidatePersistenceError(
            "candidate count mismatch"
        )

    expected = store_projection(
        normalized
    )

    if payload != expected:
        raise TraitCandidatePersistenceError(
            "persisted candidate catalog "
            "is not canonical"
        )

    return payload


def load_candidates() -> dict[
    str,
    dict[str, Any],
]:
    store = load_store_projection()

    return normalize_catalog(
        store[
            "candidates"
        ]
    )


def current_digest() -> str | None:
    coda = coda_runtime()

    target, _ = coda.resolve_target(
        STATE_RELATIVE_PATH
    )

    return coda.digest_file(
        target
    )


def persist_candidates(
    candidates: Mapping[
        str,
        Mapping[
            str,
            Any,
        ],
    ],
    *,
    expected_digest: (
        str
        | None
    ) = None,
    requester: str = "envoy",
    intent: str = (
        "persist immutable Orobouros "
        "trait candidate catalog"
    ),
) -> dict[
    str,
    Any,
]:
    projection = store_projection(
        candidates
    )

    coda = coda_runtime()

    result = coda.replace_text(
        STATE_RELATIVE_PATH,
        canonical_json(
            projection
        ),
        expected_digest=(
            expected_digest
        ),
        requester=requester,
        intent=intent,
    )

    confirmed = load_candidates()

    if (
        store_projection(
            confirmed
        )
        != projection
    ):
        raise TraitCandidatePersistenceError(
            "post-persistence candidate "
            "replay verification failed"
        )

    return {
        "owner": OWNER,
        "persistence_owner": (
            PERSISTENCE_OWNER
        ),
        "persona_id": "orobouros",
        "candidate_count": len(
            confirmed
        ),
        "mutation": result,
        "authoritative": False,
        "authority_effect": "none",
        "verified": True,
    }


def append_candidate(
    candidate_projection: Mapping[
        str,
        Any,
    ],
    *,
    expected_digest: (
        str
        | None
    ) = None,
    requester: str = "envoy",
) -> dict[
    str,
    Any,
]:
    candidate = require_mapping(
        candidate_projection,
        "candidate_projection",
    )

    candidate_id = normalize_text(
        candidate.get(
            "candidate_id"
        )
    )

    if not candidate_id:
        raise TraitCandidatePersistenceError(
            "candidate projection lacks "
            "candidate_id"
        )

    normalized_candidate = (
        validate_candidate_projection(
            candidate_id,
            candidate,
        )
    )

    existing = load_candidates()

    if candidate_id in existing:
        if (
            existing[
                candidate_id
            ]
            != normalized_candidate
        ):
            raise TraitCandidatePersistenceError(
                "immutable candidate identity "
                "collision"
            )

        return {
            "owner": OWNER,
            "persistence_owner": (
                PERSISTENCE_OWNER
            ),
            "persona_id": "orobouros",
            "candidate_id": candidate_id,
            "candidate_count": len(
                existing
            ),
            "already_present": True,
            "mutation_performed": False,
            "authoritative": False,
            "authority_effect": "none",
            "verified": True,
        }

    if expected_digest is None:
        expected_digest = current_digest()

    updated = dict(
        existing
    )

    updated[
        candidate_id
    ] = normalized_candidate

    persisted = persist_candidates(
        updated,
        expected_digest=(
            expected_digest
        ),
        requester=requester,
        intent=(
            "append immutable Orobouros "
            "trait candidate"
        ),
    )

    persisted[
        "candidate_id"
    ] = candidate_id

    persisted[
        "already_present"
    ] = False

    persisted[
        "mutation_performed"
    ] = True

    return persisted


def candidate_catalog() -> dict[
    str,
    dict[str, Any],
]:
    return load_candidates()


def status() -> dict[
    str,
    Any,
]:
    existing = STATE_PATH.is_file()

    count = (
        len(
            load_candidates()
        )
        if existing
        else 0
    )

    return {
        "schema": (
            "savant://envoy/"
            "orobouros-trait-candidate-"
            "persistence-status/1.0.0"
        ),
        "owner": OWNER,
        "persistence_owner": (
            PERSISTENCE_OWNER
        ),
        "state_path": (
            STATE_RELATIVE_PATH
        ),
        "state_present": existing,
        "candidate_count": count,
        "identity_model": (
            "content_addressed"
        ),
        "append_only_model": True,
        "immutable_candidates": True,
        "deterministic_replay": True,
        "restart_replay": True,
        "optimistic_concurrency": True,
        "atomic_mutation": True,
        "mutation_receipts": True,
        "coda_executes_mutation": True,
        "envoy_executes_mutation": False,
        "champion_selection_local": False,
        "baseline_mutation": False,
        "trait_pool_mutation": False,
        "authoritative": False,
        "authority_effect": "none",
        "rebuildable": True,
    }


def selftest() -> dict[
    str,
    Any,
]:
    coda = coda_runtime()

    first = store_projection(
        {}
    )

    second = store_projection(
        {}
    )

    if first != second:
        raise TraitCandidatePersistenceError(
            "empty candidate projection "
            "is not deterministic"
        )

    if first[
        "candidates"
    ]:
        raise TraitCandidatePersistenceError(
            "empty candidate projection "
            "contains candidates"
        )

    target, relative = (
        coda.resolve_target(
            STATE_RELATIVE_PATH
        )
    )

    if relative != STATE_RELATIVE_PATH:
        raise TraitCandidatePersistenceError(
            "Coda target normalization "
            "changed candidate state identity"
        )

    if ROOT not in target.parents:
        raise TraitCandidatePersistenceError(
            "candidate state target escaped "
            "Savant root"
        )

    return {
        "ok": True,
        "owner": OWNER,
        "persistence_owner": (
            PERSISTENCE_OWNER
        ),
        "deterministic_projection": True,
        "restart_replay": True,
        "coda_target_valid": True,
        "mutation_performed": False,
        "authoritative": False,
        "authority_effect": "none",
    }


def main() -> int:
    print(
        json.dumps(
            {
                "selftest": selftest(),
                "status": status(),
            },
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

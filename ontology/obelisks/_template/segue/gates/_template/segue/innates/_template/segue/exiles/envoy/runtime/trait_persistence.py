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
    "exiles/envoy/state/orobouros_trait_history.json"
)

STATE_PATH = (
    ROOT
    / STATE_RELATIVE_PATH
)

HISTORY_PATH = (
    ENVOY_RUNTIME
    / "trait_history.py"
)

CODA_PATH = (
    CODA_RUNTIME
    / "mutation.py"
)

OWNER = "exile:envoy"
PERSISTENCE_OWNER = "coda"

SCHEMA = (
    "savant://envoy/"
    "orobouros-trait-history-store/1.0.0"
)


class TraitPersistenceError(
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
        raise TraitPersistenceError(
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
        raise TraitPersistenceError(
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


def history_runtime() -> ModuleType:
    return _load_module(
        "savant_envoy_trait_history",
        HISTORY_PATH,
    )


def coda_runtime() -> ModuleType:
    return _load_module(
        "savant_coda_mutation_for_envoy_traits",
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


def _record_from_projection(
    projection: Mapping[
        str,
        Any,
    ],
):
    history = history_runtime()

    if not isinstance(
        projection,
        Mapping,
    ):
        raise TraitPersistenceError(
            "history record must be "
            "a mapping"
        )

    try:
        return history.HistoryRecord(
            sequence=projection[
                "sequence"
            ],
            decision_id=projection[
                "decision_id"
            ],
            trait_id=projection[
                "trait_id"
            ],
            policy_id=projection[
                "policy_id"
            ],
            previous_champion_id=(
                projection.get(
                    "previous_champion_id"
                )
            ),
            winner_candidate_id=(
                projection.get(
                    "winner_candidate_id"
                )
            ),
            decision=projection[
                "decision"
            ],
            decision_digest=projection[
                "decision_digest"
            ],
            evidence_ids=tuple(
                projection.get(
                    "evidence_ids"
                )
                or ()
            ),
            lineage=tuple(
                projection.get(
                    "lineage"
                )
                or ()
            ),
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise TraitPersistenceError(
            "invalid persisted history record"
        ) from exc


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
        "records": [],
        "record_count": 0,
        "append_only_model": True,
        "immutable_records": True,
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
        raise TraitPersistenceError(
            "Orobouros trait history state "
            "path is not a file"
        )

    try:
        payload = json.loads(
            STATE_PATH.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as exc:
        raise TraitPersistenceError(
            "persisted Orobouros trait "
            "history is invalid JSON"
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise TraitPersistenceError(
            "persisted Orobouros trait "
            "history must be an object"
        )

    if (
        payload.get(
            "schema"
        )
        != SCHEMA
    ):
        raise TraitPersistenceError(
            "persisted Orobouros trait "
            "history schema mismatch"
        )

    if (
        payload.get(
            "owner"
        )
        != OWNER
    ):
        raise TraitPersistenceError(
            "persisted Orobouros trait "
            "history owner mismatch"
        )

    if (
        payload.get(
            "persistence_owner"
        )
        != PERSISTENCE_OWNER
    ):
        raise TraitPersistenceError(
            "persisted Orobouros trait "
            "history persistence owner "
            "mismatch"
        )

    if (
        payload.get(
            "persona_id"
        )
        != "orobouros"
    ):
        raise TraitPersistenceError(
            "persisted trait history "
            "persona mismatch"
        )

    records = payload.get(
        "records"
    )

    if not isinstance(
        records,
        list,
    ):
        raise TraitPersistenceError(
            "persisted trait history "
            "records must be a list"
        )

    if (
        int(
            payload.get(
                "record_count",
                -1,
            )
        )
        != len(
            records
        )
    ):
        raise TraitPersistenceError(
            "persisted trait history "
            "record count mismatch"
        )

    return payload


def load_records() -> tuple[
    Any,
    ...,
]:
    history = history_runtime()

    store = load_store_projection()

    records = tuple(
        _record_from_projection(
            projection
        )
        for projection
        in store[
            "records"
        ]
    )

    return history.validate_history(
        records
    )


def store_projection(
    records: Sequence[
        Any
    ],
) -> dict[
    str,
    Any,
]:
    history = history_runtime()

    validated = history.validate_history(
        records
    )

    projections = [
        record.projection()
        for record
        in validated
    ]

    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "persistence_owner": (
            PERSISTENCE_OWNER
        ),
        "persona_id": "orobouros",
        "records": projections,
        "record_count": len(
            projections
        ),
        "append_only_model": True,
        "immutable_records": True,
        "authoritative": False,
        "authority_effect": "none",
        "rebuildable": True,
    }


def current_digest() -> str | None:
    coda = coda_runtime()

    target, _ = coda.resolve_target(
        STATE_RELATIVE_PATH
    )

    return coda.digest_file(
        target
    )


def persist_records(
    records: Sequence[
        Any
    ],
    *,
    expected_digest: (
        str
        | None
    ) = None,
    requester: str = "envoy",
    intent: str = (
        "persist Orobouros immutable "
        "trait adjudication history"
    ),
) -> dict[
    str,
    Any,
]:
    projection = store_projection(
        records
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

    confirmed = load_records()

    if (
        store_projection(
            confirmed
        )
        != projection
    ):
        raise TraitPersistenceError(
            "post-persistence replay "
            "verification failed"
        )

    return {
        "owner": OWNER,
        "persistence_owner": (
            PERSISTENCE_OWNER
        ),
        "persona_id": "orobouros",
        "record_count": len(
            confirmed
        ),
        "mutation": result,
        "authoritative": False,
        "authority_effect": "none",
        "verified": True,
    }


def append_decision(
    decision_projection: Mapping[
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
    history = history_runtime()

    records = load_records()

    if expected_digest is None:
        expected_digest = current_digest()

    updated = history.append_record(
        records,
        decision_projection,
    )

    if len(
        updated
    ) != (
        len(
            records
        )
        + 1
    ):
        raise TraitPersistenceError(
            "append did not produce exactly "
            "one new history record"
        )

    return persist_records(
        updated,
        expected_digest=(
            expected_digest
        ),
        requester=requester,
        intent=(
            "append verified Orobouros "
            "trait adjudication decision"
        ),
    )


def accepted_projection(
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
    history = history_runtime()

    return (
        history
        .accepted_trait_projection(
            load_records(),
            candidates,
        )
    )


def status() -> dict[
    str,
    Any,
]:
    existing = STATE_PATH.is_file()

    record_count = (
        len(
            load_records()
        )
        if existing
        else 0
    )

    return {
        "schema": (
            "savant://envoy/"
            "orobouros-trait-persistence-"
            "status/1.0.0"
        ),
        "owner": OWNER,
        "persistence_owner": (
            PERSISTENCE_OWNER
        ),
        "state_path": (
            STATE_RELATIVE_PATH
        ),
        "state_present": existing,
        "record_count": (
            record_count
        ),
        "append_only_model": True,
        "immutable_history": True,
        "deterministic_replay": True,
        "optimistic_concurrency": True,
        "atomic_mutation": True,
        "mutation_receipts": True,
        "coda_executes_mutation": True,
        "envoy_executes_mutation": False,
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
    history = history_runtime()
    coda = coda_runtime()

    empty = history.validate_history(
        ()
    )

    first = store_projection(
        empty
    )

    second = store_projection(
        empty
    )

    if first != second:
        raise TraitPersistenceError(
            "empty store projection "
            "is not deterministic"
        )

    if first[
        "records"
    ]:
        raise TraitPersistenceError(
            "empty projection contains "
            "history"
        )

    target, relative = (
        coda.resolve_target(
            STATE_RELATIVE_PATH
        )
    )

    if relative != STATE_RELATIVE_PATH:
        raise TraitPersistenceError(
            "Coda target normalization "
            "changed state identity"
        )

    if ROOT not in target.parents:
        raise TraitPersistenceError(
            "state target escaped "
            "Savant root"
        )

    return {
        "ok": True,
        "owner": OWNER,
        "persistence_owner": (
            PERSISTENCE_OWNER
        ),
        "deterministic_projection": (
            True
        ),
        "coda_target_valid": True,
        "mutation_performed": False,
        "authoritative": False,
        "authority_effect": "none",
    }


def main() -> int:
    result = {
        "selftest": selftest(),
        "status": status(),
    }

    print(
        json.dumps(
            result,
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

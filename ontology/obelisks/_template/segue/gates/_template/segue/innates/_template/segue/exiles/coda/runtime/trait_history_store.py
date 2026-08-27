#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path("/root/savant-runtime").resolve()

ENVOY_TRAIT_HISTORY_PATH = (
    ROOT
    / "ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/envoy/runtime/trait_history.py"
).resolve()

STORE_ROOT = (
    ROOT
    / "vault"
    / "coda"
    / "orobouros_trait_history"
).resolve()

HISTORY_PATH = STORE_ROOT / "history.json"

OWNER = "coda"
SEMANTIC_OWNER = "exile:envoy"
PERSONA_ID = "orobouros"

SCHEMA = (
    "savant://coda/"
    "orobouros-trait-history-store/1.0.0"
)


class TraitHistoryStoreError(RuntimeError):
    pass


class TraitHistoryStoreConflict(
    TraitHistoryStoreError
):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode("utf-8")
    ).hexdigest()


def load_envoy_trait_history():
    module_name = "envoy_runtime_trait_history"

    existing = sys.modules.get(
        module_name
    )

    if existing is not None:
        return existing

    if not ENVOY_TRAIT_HISTORY_PATH.is_file():
        raise TraitHistoryStoreError(
            "envoy trait history runtime does not exist"
        )

    spec = importlib.util.spec_from_file_location(
        module_name,
        ENVOY_TRAIT_HISTORY_PATH,
    )

    if spec is None or spec.loader is None:
        raise TraitHistoryStoreError(
            "unable to load envoy trait history runtime"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(
            module
        )
    except Exception:
        sys.modules.pop(
            module_name,
            None,
        )
        raise

    return module


def store_payload(
    records: Sequence[
        Mapping[str, Any]
    ],
) -> dict[str, Any]:
    payload = {
        "schema": SCHEMA,
        "owner": OWNER,
        "semantic_owner": SEMANTIC_OWNER,
        "persona_id": PERSONA_ID,
        "records": [
            dict(record)
            for record in records
        ],
        "record_count": len(records),
        "append_only": True,
        "immutable_records": True,
        "authoritative": False,
        "authority_effect": "none",
    }

    payload["digest"] = digest(
        payload
    )

    return payload


def empty_store() -> dict[str, Any]:
    return store_payload(
        ()
    )


def normalize_store(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise TraitHistoryStoreError(
            "history store must be a mapping"
        )

    if payload.get("schema") != SCHEMA:
        raise TraitHistoryStoreError(
            "history store schema mismatch"
        )

    if payload.get("owner") != OWNER:
        raise TraitHistoryStoreError(
            "history store owner mismatch"
        )

    if (
        payload.get("semantic_owner")
        != SEMANTIC_OWNER
    ):
        raise TraitHistoryStoreError(
            "history semantic owner mismatch"
        )

    if (
        payload.get("persona_id")
        != PERSONA_ID
    ):
        raise TraitHistoryStoreError(
            "history persona mismatch"
        )

    if payload.get("authoritative") is not False:
        raise TraitHistoryStoreError(
            "history store became authoritative"
        )

    if (
        payload.get("authority_effect")
        != "none"
    ):
        raise TraitHistoryStoreError(
            "history store changed authority"
        )

    if payload.get("append_only") is not True:
        raise TraitHistoryStoreError(
            "history store is not append-only"
        )

    if (
        payload.get("immutable_records")
        is not True
    ):
        raise TraitHistoryStoreError(
            "history records are not immutable"
        )

    records = payload.get(
        "records"
    )

    if not isinstance(
        records,
        list,
    ):
        raise TraitHistoryStoreError(
            "history records must be a list"
        )

    if (
        payload.get("record_count")
        != len(records)
    ):
        raise TraitHistoryStoreError(
            "history record count mismatch"
        )

    supplied_digest = str(
        payload.get(
            "digest",
            "",
        )
    ).strip()

    calculated_digest = digest(
        {
            key: value
            for key, value
            in payload.items()
            if key != "digest"
        }
    )

    if (
        not supplied_digest
        or supplied_digest
        != calculated_digest
    ):
        raise TraitHistoryStoreError(
            "history store digest mismatch"
        )

    return dict(payload)


def load_store() -> dict[str, Any]:
    if not HISTORY_PATH.exists():
        return empty_store()

    if not HISTORY_PATH.is_file():
        raise TraitHistoryStoreError(
            "history path is not a file"
        )

    try:
        payload = json.loads(
            HISTORY_PATH.read_text(
                encoding="utf-8"
            )
        )
    except (
        json.JSONDecodeError,
        OSError,
    ) as exc:
        raise TraitHistoryStoreError(
            "unable to read history store"
        ) from exc

    return normalize_store(
        payload
    )


def record_from_projection(
    projection: Mapping[str, Any],
):
    envoy = load_envoy_trait_history()

    if not isinstance(
        projection,
        Mapping,
    ):
        raise TraitHistoryStoreError(
            "history record must be a mapping"
        )

    try:
        record = envoy.HistoryRecord(
            sequence=projection.get(
                "sequence"
            ),
            decision_id=projection.get(
                "decision_id"
            ),
            trait_id=projection.get(
                "trait_id"
            ),
            policy_id=projection.get(
                "policy_id"
            ),
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
            decision=projection.get(
                "decision"
            ),
            decision_digest=(
                projection.get(
                    "decision_digest"
                )
            ),
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
    except Exception as exc:
        raise TraitHistoryStoreError(
            "invalid envoy history record"
        ) from exc

    canonical = record.projection()

    if dict(projection) != canonical:
        raise TraitHistoryStoreError(
            "stored history record differs from "
            "envoy canonical projection"
        )

    return record


def validate_records(
    projections: Sequence[
        Mapping[str, Any]
    ],
):
    envoy = load_envoy_trait_history()

    records = tuple(
        record_from_projection(
            projection
        )
        for projection
        in projections
    )

    try:
        return envoy.validate_history(
            records
        )
    except Exception as exc:
        raise TraitHistoryStoreError(
            "envoy history validation failed"
        ) from exc


def validate_store_semantics(
    payload: Mapping[str, Any],
):
    normalized = normalize_store(
        payload
    )

    return validate_records(
        normalized["records"]
    )


def atomic_write(
    payload: Mapping[str, Any],
) -> None:
    STORE_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=".history-",
            suffix=".json",
            dir=str(STORE_ROOT),
        )
    )

    temporary = Path(
        temporary_name
    )

    encoded = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")

    try:
        with os.fdopen(
            descriptor,
            "wb",
        ) as handle:
            handle.write(
                encoded
            )
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary,
            HISTORY_PATH,
        )

    except Exception:
        temporary.unlink(
            missing_ok=True
        )
        raise


def append_decision(
    decision_projection: Mapping[
        str,
        Any,
    ],
    *,
    expected_store_digest: str | None = None,
) -> dict[str, Any]:
    envoy = load_envoy_trait_history()

    current = load_store()

    existing = validate_store_semantics(
        current
    )

    current_digest = current[
        "digest"
    ]

    if (
        expected_store_digest is not None
        and expected_store_digest
        != current_digest
    ):
        raise TraitHistoryStoreConflict(
            "history store changed since inspection"
        )

    try:
        updated = envoy.append_record(
            existing,
            decision_projection,
        )
    except Exception as exc:
        raise TraitHistoryStoreError(
            "envoy rejected history append"
        ) from exc

    records = [
        record.projection()
        for record in updated
    ]

    payload = store_payload(
        records
    )

    validate_store_semantics(
        payload
    )

    atomic_write(
        payload
    )

    return {
        "owner": OWNER,
        "semantic_owner": SEMANTIC_OWNER,
        "persona_id": PERSONA_ID,
        "appended": True,
        "record_count": payload[
            "record_count"
        ],
        "previous_store_digest": (
            current_digest
        ),
        "store_digest": payload[
            "digest"
        ],
        "record": records[-1],
        "authoritative": False,
        "authority_effect": "none",
    }


def accepted_trait_projection(
    candidates: Mapping[
        str,
        Mapping[str, Any],
    ],
) -> dict[str, Any]:
    envoy = load_envoy_trait_history()

    current = load_store()

    records = validate_store_semantics(
        current
    )

    try:
        return envoy.accepted_trait_projection(
            records,
            candidates,
        )
    except Exception as exc:
        raise TraitHistoryStoreError(
            "accepted trait projection failed"
        ) from exc


def status() -> dict[str, Any]:
    current = load_store()

    records = validate_store_semantics(
        current
    )

    payload = {
        "schema": (
            "savant://coda/"
            "orobouros-trait-history-store-status/"
            "1.0.0"
        ),
        "owner": OWNER,
        "semantic_owner": SEMANTIC_OWNER,
        "persona_id": PERSONA_ID,
        "path": str(HISTORY_PATH),
        "exists": HISTORY_PATH.exists(),
        "record_count": len(records),
        "store_digest": current[
            "digest"
        ],
        "append_only": True,
        "immutable_records": True,
        "envoy_validation": True,
        "atomic_write": True,
        "optimistic_concurrency": True,
        "persistent_state": True,
        "persistence_owner": OWNER,
        "authoritative": False,
        "authority_effect": "none",
    }

    payload["digest"] = digest(
        payload
    )

    return payload


def load_json_argument(
    value: str,
) -> dict[str, Any]:
    candidate = Path(value)

    if candidate.exists():
        payload = json.loads(
            candidate.read_text(
                encoding="utf-8"
            )
        )
    else:
        payload = json.loads(
            value
        )

    if not isinstance(
        payload,
        dict,
    ):
        raise TraitHistoryStoreError(
            "json argument must be an object"
        )

    return payload


def main() -> int:
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "status"
    )

    subparsers.add_parser(
        "history"
    )

    append_parser = subparsers.add_parser(
        "append"
    )

    append_parser.add_argument(
        "decision"
    )

    append_parser.add_argument(
        "--expected-store-digest"
    )

    project_parser = subparsers.add_parser(
        "project"
    )

    project_parser.add_argument(
        "candidates"
    )

    args = parser.parse_args()

    if args.command == "status":
        result = status()

    elif args.command == "history":
        result = load_store()

        validate_store_semantics(
            result
        )

    elif args.command == "append":
        result = append_decision(
            load_json_argument(
                args.decision
            ),
            expected_store_digest=(
                args.expected_store_digest
            ),
        )

    elif args.command == "project":
        result = accepted_trait_projection(
            load_json_argument(
                args.candidates
            )
        )

    else:
        raise TraitHistoryStoreError(
            f"unsupported command: {args.command}"
        )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

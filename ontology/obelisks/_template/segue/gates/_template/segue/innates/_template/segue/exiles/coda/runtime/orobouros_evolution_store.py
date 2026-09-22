#!/usr/bin/env python3

from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping, Sequence


schema = (
    "savant://coda/"
    "orobouros-evolution-store/1.0.0"
)

owner = "coda"
semantic_owner = "envoy"
verification_owner = "notary"
persona_id = "orobouros"

authority_effect = "none"

root = Path(
    "/root/savant-runtime"
)

store_root = (
    root
    / "vault"
    / "coda"
    / "orobouros-evolution"
)

store_path = (
    store_root
    / "history.json"
)

trait_history_path = (
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
    / "coda"
    / "runtime"
    / "trait_history_store.py"
)

store_schema = (
    "savant://coda/"
    "orobouros-evolution-history/1.0.0"
)

record_schema = (
    "savant://coda/"
    "orobouros-evolution-record/1.0.0"
)


class orobouros_evolution_store_error(
    RuntimeError
):
    pass


class orobouros_evolution_store_conflict(
    orobouros_evolution_store_error
):
    pass


def _canonical_json(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        default=str,
    ).encode(
        "utf-8"
    )


def _digest(
    value: Any,
) -> str:
    return sha256(
        _canonical_json(
            value
        )
    ).hexdigest()


def _mapping(
    value: Any,
    *,
    label: str,
) -> dict[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise (
            orobouros_evolution_store_error(
                f"{label} must be a mapping"
            )
        )

    return {
        str(key):
            item
        for key, item
        in value.items()
    }


def _required_text(
    value: Any,
    *,
    label: str,
) -> str:
    normalized = str(
        value
        or ""
    ).strip()

    if not normalized:
        raise (
            orobouros_evolution_store_error(
                f"{label} is required"
            )
        )

    return normalized


def _tokens(
    values: Any,
) -> tuple[str, ...]:
    if values is None:
        return ()

    if not isinstance(
        values,
        (
            list,
            tuple,
            set,
        ),
    ):
        raise (
            orobouros_evolution_store_error(
                "token collection must be iterable"
            )
        )

    return tuple(
        sorted(
            {
                str(item)
                .strip()
                .lower()
                for item in values
                if str(
                    item
                    or ""
                ).strip()
            }
        )
    )


def _empty_store() -> dict[str, Any]:
    payload = {
        "schema":
            store_schema,
        "owner":
            owner,
        "semantic_owner":
            semantic_owner,
        "verification_owner":
            verification_owner,
        "persona_id":
            persona_id,
        "records":
            [],
        "record_count":
            0,
        "append_only":
            True,
        "immutable_records":
            True,
        "authoritative":
            False,
        "authority_effect":
            authority_effect,
    }

    payload[
        "digest"
    ] = _digest(
        {
            key: value
            for key, value
            in payload.items()
            if key != "digest"
        }
    )

    return payload


def _normalize_record(
    value: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    record = _mapping(
        value,
        label="evolution record",
    )

    if (
        record.get(
            "schema"
        )
        != record_schema
    ):
        raise (
            orobouros_evolution_store_error(
                "invalid evolution record schema"
            )
        )

    if (
        record.get(
            "owner"
        )
        != owner
    ):
        raise (
            orobouros_evolution_store_error(
                "evolution record owner must be Coda"
            )
        )

    if (
        record.get(
            "semantic_owner"
        )
        != semantic_owner
    ):
        raise (
            orobouros_evolution_store_error(
                "semantic owner must remain Envoy"
            )
        )

    if (
        record.get(
            "verification_owner"
        )
        != verification_owner
    ):
        raise (
            orobouros_evolution_store_error(
                "verification owner must remain Notary"
            )
        )

    if (
        record.get(
            "persona_id"
        )
        != persona_id
    ):
        raise (
            orobouros_evolution_store_error(
                "invalid persona identity"
            )
        )

    if (
        record.get(
            "authoritative"
        )
        is not False
    ):
        raise (
            orobouros_evolution_store_error(
                "evolution history cannot become authority"
            )
        )

    if (
        record.get(
            "authority_effect"
        )
        != "none"
    ):
        raise (
            orobouros_evolution_store_error(
                "evolution record changed authority"
            )
        )

    if (
        record.get(
            "mutation_executed"
        )
        is not False
    ):
        raise (
            orobouros_evolution_store_error(
                "history record cannot claim mutation execution"
            )
        )

    normalized = {
        "schema":
            record_schema,
        "record_id":
            _required_text(
                record.get(
                    "record_id"
                ),
                label="record_id",
            ),
        "sequence":
            int(
                record.get(
                    "sequence"
                )
            ),
        "owner":
            owner,
        "semantic_owner":
            semantic_owner,
        "verification_owner":
            verification_owner,
        "persona_id":
            persona_id,
        "registry_digest":
            _required_text(
                record.get(
                    "registry_digest"
                ),
                label="registry_digest",
            ),
        "shadow_digest":
            _required_text(
                record.get(
                    "shadow_digest"
                ),
                label="shadow_digest",
            ),
        "gate_digest":
            _required_text(
                record.get(
                    "gate_digest"
                ),
                label="gate_digest",
            ),
        "mutation_request_digest":
            _required_text(
                record.get(
                    "mutation_request_digest"
                ),
                label="mutation_request_digest",
            ),
        "notary_admission_ref":
            _required_text(
                record.get(
                    "notary_admission_ref"
                ),
                label="notary_admission_ref",
            ),
        "notary_subject_digest":
            _required_text(
                record.get(
                    "notary_subject_digest"
                ),
                label="notary_subject_digest",
            ),
        "from_composition_digest":
            _required_text(
                record.get(
                    "from_composition_digest"
                ),
                label="from_composition_digest",
            ),
        "to_composition_digest":
            _required_text(
                record.get(
                    "to_composition_digest"
                ),
                label="to_composition_digest",
            ),
        "to_active_traits":
            list(
                _tokens(
                    record.get(
                        "to_active_traits"
                    )
                )
            ),
        "evidence_refs":
            list(
                _tokens(
                    record.get(
                        "evidence_refs"
                    )
                )
            ),
        "trait_history_store_digest":
            (
                str(
                    record.get(
                        "trait_history_store_digest"
                    )
                    or ""
                ).strip()
                or None
            ),
        "reversible":
            bool(
                record.get(
                    "reversible",
                    False,
                )
            ),
        "preserve_previous":
            bool(
                record.get(
                    "preserve_previous",
                    False,
                )
            ),
        "mutation_executed":
            False,
        "authoritative":
            False,
        "authority_effect":
            authority_effect,
    }

    if (
        normalized[
            "sequence"
        ]
        < 1
    ):
        raise (
            orobouros_evolution_store_error(
                "record sequence must be positive"
            )
        )

    material = {
        key: value
        for key, value
        in normalized.items()
        if key
        not in {
            "record_id",
            "digest",
        }
    }

    expected_record_id = (
        "oroevo-history:"
        + _digest(
            material
        )[:32]
    )

    if (
        normalized[
            "record_id"
        ]
        != expected_record_id
    ):
        raise (
            orobouros_evolution_store_error(
                "evolution record identity mismatch"
            )
        )

    normalized[
        "digest"
    ] = _digest(
        normalized
    )

    return normalized


def _validate_records(
    records: Sequence[
        Mapping[
            str,
            Any,
        ]
    ],
) -> tuple[
    dict[str, Any],
    ...,
]:
    normalized = tuple(
        _normalize_record(
            record
        )
        for record in records
    )

    seen_ids: set[str] = set()
    seen_requests: set[str] = set()

    for expected_sequence, record in enumerate(
        normalized,
        start=1,
    ):
        if (
            record[
                "sequence"
            ]
            != expected_sequence
        ):
            raise (
                orobouros_evolution_store_error(
                    "evolution history sequence discontinuity"
                )
            )

        record_id = record[
            "record_id"
        ]

        request_digest = record[
            "mutation_request_digest"
        ]

        if record_id in seen_ids:
            raise (
                orobouros_evolution_store_error(
                    "duplicate evolution record"
                )
            )

        if request_digest in seen_requests:
            raise (
                orobouros_evolution_store_error(
                    "mutation request replay detected"
                )
            )

        seen_ids.add(
            record_id
        )

        seen_requests.add(
            request_digest
        )

        if expected_sequence > 1:
            previous = normalized[
                expected_sequence - 2
            ]

            if (
                record[
                    "from_composition_digest"
                ]
                != previous[
                    "to_composition_digest"
                ]
            ):
                raise (
                    orobouros_evolution_store_error(
                        "composition lineage discontinuity"
                    )
                )

    return normalized


def _store_payload(
    records: Sequence[
        Mapping[
            str,
            Any,
        ]
    ],
) -> dict[str, Any]:
    validated = _validate_records(
        records
    )

    payload = {
        "schema":
            store_schema,
        "owner":
            owner,
        "semantic_owner":
            semantic_owner,
        "verification_owner":
            verification_owner,
        "persona_id":
            persona_id,
        "records":
            list(
                validated
            ),
        "record_count":
            len(
                validated
            ),
        "append_only":
            True,
        "immutable_records":
            True,
        "authoritative":
            False,
        "authority_effect":
            authority_effect,
    }

    payload[
        "digest"
    ] = _digest(
        {
            key: value
            for key, value
            in payload.items()
            if key != "digest"
        }
    )

    return payload


def load_store() -> dict[str, Any]:
    if not store_path.exists():
        return _empty_store()

    try:
        payload = json.loads(
            store_path.read_text(
                encoding="utf-8"
            )
        )
    except Exception as exc:
        raise (
            orobouros_evolution_store_error(
                "unable to read evolution store"
            )
        ) from exc

    value = _mapping(
        payload,
        label="evolution store",
    )

    if (
        value.get(
            "schema"
        )
        != store_schema
    ):
        raise (
            orobouros_evolution_store_error(
                "invalid evolution store schema"
            )
        )

    records = value.get(
        "records"
    )

    if not isinstance(
        records,
        list,
    ):
        raise (
            orobouros_evolution_store_error(
                "evolution store records must be a list"
            )
        )

    canonical = _store_payload(
        records
    )

    if (
        str(
            value.get(
                "digest",
                ""
            )
        )
        != canonical[
            "digest"
        ]
    ):
        raise (
            orobouros_evolution_store_error(
                "evolution store digest mismatch"
            )
        )

    return canonical


def _atomic_write(
    payload: Mapping[
        str,
        Any,
    ],
) -> None:
    store_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=".history-",
            suffix=".json",
            dir=str(
                store_root
            ),
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
    ).encode(
        "utf-8"
    )

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
            store_path,
        )

        directory_descriptor = os.open(
            store_root,
            os.O_RDONLY,
        )

        try:
            os.fsync(
                directory_descriptor
            )
        finally:
            os.close(
                directory_descriptor
            )

    except Exception:
        temporary.unlink(
            missing_ok=True
        )

        raise


def _load_trait_history_store():
    if not trait_history_path.is_file():
        raise (
            orobouros_evolution_store_error(
                "Coda trait history store is missing"
            )
        )

    specification = (
        importlib.util.spec_from_file_location(
            "savant_coda_trait_history_store",
            trait_history_path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise (
            orobouros_evolution_store_error(
                "unable to load Coda trait history store"
            )
        )

    module = (
        importlib.util.module_from_spec(
            specification
        )
    )

    specification.loader.exec_module(
        module
    )

    return module


def trait_history_store_digest() -> str | None:
    module = (
        _load_trait_history_store()
    )

    status = module.status()

    if not isinstance(
        status,
        Mapping,
    ):
        raise (
            orobouros_evolution_store_error(
                "invalid trait history status"
            )
        )

    value = str(
        status.get(
            "store_digest"
        )
        or ""
    ).strip()

    return value or None


def build_record(
    *,
    sequence: int,
    registry_projection: Mapping[
        str,
        Any,
    ],
    shadow_evaluation: Mapping[
        str,
        Any,
    ],
    promotion_gate: Mapping[
        str,
        Any,
    ],
    mutation_request: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    registry = _mapping(
        registry_projection,
        label="registry_projection",
    )

    shadow = _mapping(
        shadow_evaluation,
        label="shadow_evaluation",
    )

    gate = _mapping(
        promotion_gate,
        label="promotion_gate",
    )

    request = _mapping(
        mutation_request,
        label="mutation_request",
    )

    if (
        registry.get(
            "owner"
        )
        != "exile:envoy"
    ):
        raise (
            orobouros_evolution_store_error(
                "registry must remain Envoy-owned"
            )
        )

    if (
        shadow.get(
            "owner"
        )
        != "exile:envoy"
    ):
        raise (
            orobouros_evolution_store_error(
                "shadow evaluation must remain Envoy-owned"
            )
        )

    if (
        gate.get(
            "owner"
        )
        != "exile:envoy"
    ):
        raise (
            orobouros_evolution_store_error(
                "promotion gate must remain Envoy-owned"
            )
        )

    if (
        request.get(
            "owner"
        )
        != "exile:envoy"
    ):
        raise (
            orobouros_evolution_store_error(
                "mutation request must remain Envoy-owned"
            )
        )

    if (
        request.get(
            "target_owner"
        )
        != owner
    ):
        raise (
            orobouros_evolution_store_error(
                "mutation request must target Coda"
            )
        )

    if not gate.get(
        "eligible_for_coda_mutation",
        False,
    ):
        raise (
            orobouros_evolution_store_error(
                "promotion gate is not eligible"
            )
        )

    if not request.get(
        "requires_coda_execution",
        False,
    ):
        raise (
            orobouros_evolution_store_error(
                "request does not require Coda execution"
            )
        )

    if request.get(
        "executed"
    ):
        raise (
            orobouros_evolution_store_error(
                "request already claims execution"
            )
        )

    registry_digest = (
        _required_text(
            registry.get(
                "registry_digest"
            ),
            label="registry_digest",
        )
    )

    shadow_digest = (
        _required_text(
            shadow.get(
                "shadow_digest"
            ),
            label="shadow_digest",
        )
    )

    gate_digest = (
        _required_text(
            gate.get(
                "gate_digest"
            ),
            label="gate_digest",
        )
    )

    request_digest = (
        _required_text(
            request.get(
                "request_digest"
            ),
            label="mutation_request_digest",
        )
    )

    if (
        registry.get(
            "shadow_digest"
        )
        != shadow_digest
    ):
        raise (
            orobouros_evolution_store_error(
                "registry to shadow lineage mismatch"
            )
        )

    gate_semantic = _mapping(
        gate.get(
            "semantic"
        ),
        label="gate semantic",
    )

    if (
        gate_semantic.get(
            "registry_digest"
        )
        != registry_digest
    ):
        raise (
            orobouros_evolution_store_error(
                "gate to registry lineage mismatch"
            )
        )

    if (
        gate_semantic.get(
            "shadow_digest"
        )
        != shadow_digest
    ):
        raise (
            orobouros_evolution_store_error(
                "gate to shadow lineage mismatch"
            )
        )

    admission = _mapping(
        gate_semantic.get(
            "notary_admission"
        ),
        label="notary admission",
    )

    if not admission.get(
        "admitted",
        False,
    ):
        raise (
            orobouros_evolution_store_error(
                "Notary admission is required"
            )
        )

    if (
        admission.get(
            "owner"
        )
        != verification_owner
    ):
        raise (
            orobouros_evolution_store_error(
                "Notary ownership mismatch"
            )
        )

    request_semantic = _mapping(
        request.get(
            "semantic"
        ),
        label="mutation request semantic",
    )

    if (
        request_semantic.get(
            "gate_digest"
        )
        != gate_digest
    ):
        raise (
            orobouros_evolution_store_error(
                "request to gate lineage mismatch"
            )
        )

    material = {
        "schema":
            record_schema,
        "sequence":
            int(
                sequence
            ),
        "owner":
            owner,
        "semantic_owner":
            semantic_owner,
        "verification_owner":
            verification_owner,
        "persona_id":
            persona_id,
        "registry_digest":
            registry_digest,
        "shadow_digest":
            shadow_digest,
        "gate_digest":
            gate_digest,
        "mutation_request_digest":
            request_digest,
        "notary_admission_ref":
            _required_text(
                admission.get(
                    "admission_ref"
                ),
                label="notary_admission_ref",
            ),
        "notary_subject_digest":
            _required_text(
                admission.get(
                    "evidence_digest"
                ),
                label="notary_subject_digest",
            ),
        "from_composition_digest":
            _required_text(
                request_semantic.get(
                    "from_composition_digest"
                ),
                label="from_composition_digest",
            ),
        "to_composition_digest":
            _required_text(
                request_semantic.get(
                    "to_composition_digest"
                ),
                label="to_composition_digest",
            ),
        "to_active_traits":
            list(
                _tokens(
                    request_semantic.get(
                        "to_active_traits"
                    )
                )
            ),
        "evidence_refs":
            list(
                _tokens(
                    registry.get(
                        "evidence_refs"
                    )
                )
            ),
        "trait_history_store_digest":
            trait_history_store_digest(),
        "reversible":
            bool(
                request_semantic.get(
                    "reversible",
                    False,
                )
            ),
        "preserve_previous":
            bool(
                request_semantic.get(
                    "preserve_previous",
                    False,
                )
            ),
        "mutation_executed":
            False,
        "authoritative":
            False,
        "authority_effect":
            authority_effect,
    }

    identity_material = {
        key: value
        for key, value
        in material.items()
        if key
        not in {
            "record_id",
            "digest",
        }
    }

    material[
        "record_id"
    ] = (
        "oroevo-history:"
        + _digest(
            identity_material
        )[:32]
    )

    material[
        "digest"
    ] = _digest(
        material
    )

    return _normalize_record(
        material
    )


def append(
    *,
    registry_projection: Mapping[
        str,
        Any,
    ],
    shadow_evaluation: Mapping[
        str,
        Any,
    ],
    promotion_gate: Mapping[
        str,
        Any,
    ],
    mutation_request: Mapping[
        str,
        Any,
    ],
    expected_store_digest: str | None = None,
) -> dict[str, Any]:
    current = load_store()

    if (
        expected_store_digest is not None
        and expected_store_digest
        != current[
            "digest"
        ]
    ):
        raise (
            orobouros_evolution_store_conflict(
                "evolution store changed since inspection"
            )
        )

    record = build_record(
        sequence=(
            current[
                "record_count"
            ]
            + 1
        ),
        registry_projection=
            registry_projection,
        shadow_evaluation=
            shadow_evaluation,
        promotion_gate=
            promotion_gate,
        mutation_request=
            mutation_request,
    )

    records = [
        *current[
            "records"
        ],
        record,
    ]

    updated = _store_payload(
        records
    )

    _atomic_write(
        updated
    )

    confirmed = load_store()

    if (
        confirmed[
            "digest"
        ]
        != updated[
            "digest"
        ]
    ):
        raise (
            orobouros_evolution_store_error(
                "post-write evolution store verification failed"
            )
        )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "semantic_owner":
            semantic_owner,
        "verification_owner":
            verification_owner,
        "persona_id":
            persona_id,
        "appended":
            True,
        "record":
            record,
        "record_count":
            confirmed[
                "record_count"
            ],
        "previous_store_digest":
            current[
                "digest"
            ],
        "store_digest":
            confirmed[
                "digest"
            ],
        "crown_mutated":
            False,
        "trait_history_mutated":
            False,
        "mutation_executed":
            False,
        "authoritative":
            False,
        "authority_effect":
            authority_effect,
    }


def status() -> dict[str, Any]:
    current = load_store()

    trait_digest = None

    try:
        trait_digest = (
            trait_history_store_digest()
        )
    except Exception:
        trait_digest = None

    payload = {
        "schema":
            schema,
        "owner":
            owner,
        "semantic_owner":
            semantic_owner,
        "verification_owner":
            verification_owner,
        "persona_id":
            persona_id,
        "path":
            str(
                store_path
            ),
        "exists":
            store_path.exists(),
        "record_count":
            current[
                "record_count"
            ],
        "store_digest":
            current[
                "digest"
            ],
        "trait_history_store_digest":
            trait_digest,
        "append_only":
            True,
        "immutable_records":
            True,
        "optimistic_concurrency":
            True,
        "atomic_write":
            True,
        "lineage_validation":
            True,
        "notary_admission_required":
            True,
        "crown_mutation":
            False,
        "trait_history_mutation":
            False,
        "persistent_state":
            True,
        "authoritative":
            False,
        "authority_effect":
            authority_effect,
    }

    payload[
        "digest"
    ] = _digest(
        payload
    )

    return payload


def selftest() -> dict[str, Any]:
    current = _empty_store()

    if (
        current[
            "owner"
        ]
        != owner
    ):
        raise (
            orobouros_evolution_store_error(
                "invalid store owner"
            )
        )

    if (
        current[
            "authoritative"
        ]
        is not False
    ):
        raise (
            orobouros_evolution_store_error(
                "store became authoritative"
            )
        )

    return {
        "schema":
            schema,
        "ok":
            True,
        "owner":
            owner,
        "semantic_owner":
            semantic_owner,
        "verification_owner":
            verification_owner,
        "append_only":
            True,
        "mutation_executed":
            False,
        "authority_effect":
            authority_effect,
    }


def _load_json(
    value: str,
) -> dict[str, Any]:
    candidate = Path(
        value
    )

    if candidate.exists():
        parsed = json.loads(
            candidate.read_text(
                encoding="utf-8"
            )
        )
    else:
        parsed = json.loads(
            value
        )

    return _mapping(
        parsed,
        label="json argument",
    )


def main() -> int:
    parser = (
        argparse.ArgumentParser()
    )

    subparsers = (
        parser.add_subparsers(
            dest="command",
            required=True,
        )
    )

    subparsers.add_parser(
        "status"
    )

    subparsers.add_parser(
        "history"
    )

    append_parser = (
        subparsers.add_parser(
            "append"
        )
    )

    append_parser.add_argument(
        "registry"
    )

    append_parser.add_argument(
        "shadow"
    )

    append_parser.add_argument(
        "gate"
    )

    append_parser.add_argument(
        "request"
    )

    append_parser.add_argument(
        "--expected-store-digest"
    )

    args = parser.parse_args()

    if args.command == "status":
        result = status()

    elif args.command == "history":
        result = load_store()

    elif args.command == "append":
        result = append(
            registry_projection=
                _load_json(
                    args.registry
                ),
            shadow_evaluation=
                _load_json(
                    args.shadow
                ),
            promotion_gate=
                _load_json(
                    args.gate
                ),
            mutation_request=
                _load_json(
                    args.request
                ),
            expected_store_digest=
                args.expected_store_digest,
        )

    else:
        raise (
            orobouros_evolution_store_error(
                "unsupported command"
            )
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

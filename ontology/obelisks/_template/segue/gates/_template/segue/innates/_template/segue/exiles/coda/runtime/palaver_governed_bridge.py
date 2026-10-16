#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import sys

from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Mapping


runtime_root = Path(
    "/root/savant-runtime/"
    "ontology/obelisks/_template/"
    "segue/gates/_template/segue/"
    "innates/_template/segue/"
    "exiles/coda/runtime"
)

if str(runtime_root) not in sys.path:
    sys.path.insert(
        0,
        str(runtime_root),
    )

bridge_path = (
    runtime_root
    / "palaver_bridge.py"
)

owner = "coda"
caller = "palaver"
governance_owner = "living-governance"
authority_effect = "none"
schema = "savant.coda.palaver-governed-bridge.v1"


class coda_palaver_governed_bridge_error(
    RuntimeError
):
    pass


def clone(
    value: Any,
) -> Any:
    return copy.deepcopy(
        value
    )


def load_live_bridge() -> ModuleType:
    if not bridge_path.is_file():
        raise coda_palaver_governed_bridge_error(
            "live Coda Palaver bridge is missing"
        )

    spec = (
        importlib.util.spec_from_file_location(
            "savant_live_coda_palaver_bridge",
            bridge_path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise coda_palaver_governed_bridge_error(
            (
                "cannot load live "
                "Coda Palaver bridge"
            )
        )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    spec.loader.exec_module(
        module
    )

    return module


def load_governance_receipts() -> ModuleType:
    path = (
        runtime_root
        / "governance_receipts.py"
    )

    if not path.is_file():
        raise coda_palaver_governed_bridge_error(
            (
                "Coda governance receipt "
                "runtime is missing"
            )
        )

    spec = (
        importlib.util.spec_from_file_location(
            "savant_coda_governance_receipts",
            path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise coda_palaver_governed_bridge_error(
            (
                "cannot load Coda governance "
                "receipt runtime"
            )
        )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    spec.loader.exec_module(
        module
    )

    return module


def _mapping(
    value: Any,
) -> Mapping[str, Any] | None:
    if isinstance(
        value,
        Mapping,
    ):
        return value

    return None


def _walk_mappings(
    value: Any,
) -> Iterable[
    Mapping[str, Any]
]:
    if isinstance(
        value,
        Mapping,
    ):
        yield value

        for child in value.values():
            yield from _walk_mappings(
                child
            )

        return

    if isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):
        for child in value:
            yield from _walk_mappings(
                child
            )


def _decision_value(
    value: Mapping[str, Any],
) -> str | None:
    for field in (
        "decision",
        "result",
        "outcome",
        "state",
    ):
        raw = value.get(
            field
        )

        if raw is None:
            continue

        normalized = (
            str(raw)
            .strip()
            .lower()
            .replace(
                "_",
                "-",
            )
        )

        if normalized in {
            "allow",
            "deny",
            "advisory",
            "unknown",
            "authority-required",
        }:
            return normalized

    return None


def _candidate_governance_evaluation(
    value: Any,
) -> Mapping[str, Any] | None:
    mapping = _mapping(
        value
    )

    if mapping is None:
        return None

    if (
        _decision_value(
            mapping
        )
        is None
    ):
        return None

    declared_owner = str(
        mapping.get(
            "owner"
        )
        or mapping.get(
            "governance_owner"
        )
        or ""
    ).strip().lower()

    schema_value = str(
        mapping.get(
            "schema"
        )
        or ""
    ).strip().lower()

    kind = str(
        mapping.get(
            "kind"
        )
        or mapping.get(
            "type"
        )
        or ""
    ).strip().lower()

    governance_marked = bool(
        declared_owner
        == governance_owner
        or "living-governance"
        in schema_value
        or "governance"
        in kind
        or "governance"
        in schema_value
        or any(
            key in mapping
            for key
            in (
                "governing_rules",
                "reason_codes",
                "evidence_requirements",
                "unresolved_unknowns",
                "override_requirements",
            )
        )
    )

    if governance_marked:
        return mapping

    return None


def extract_governance_evaluation(
    request: Mapping[str, Any],
    bridge_result: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    preferred_keys = (
        "governance_evaluation",
        "governance_preflight",
        "governance",
        "preflight",
    )

    for container in (
        bridge_result,
        request,
    ):
        for key in preferred_keys:
            candidate = (
                _candidate_governance_evaluation(
                    container.get(
                        key
                    )
                )
            )

            if candidate is not None:
                return candidate

    for container in (
        bridge_result,
        request,
    ):
        for candidate in _walk_mappings(
            container
        ):
            resolved = (
                _candidate_governance_evaluation(
                    candidate
                )
            )

            if resolved is not None:
                return resolved

    return None


def _is_coda_mutation_receipt(
    value: Mapping[str, Any],
) -> bool:
    owner_value = str(
        value.get(
            "owner"
        )
        or ""
    ).strip().lower()

    schema_value = str(
        value.get(
            "schema"
        )
        or ""
    ).strip().lower()

    identifier = str(
        value.get(
            "id"
        )
        or value.get(
            "receipt_id"
        )
        or ""
    ).strip()

    operation = str(
        value.get(
            "operation"
        )
        or ""
    ).strip()

    return bool(
        owner_value
        == owner
        and identifier
        and operation
        and (
            "coda/mutation-receipt"
            in schema_value
            or identifier.startswith(
                "coda_"
            )
            or bool(
                value.get(
                    "receipt"
                )
            )
        )
    )


def extract_coda_mutation_receipt(
    bridge_result: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    for candidate in _walk_mappings(
        bridge_result
    ):
        if _is_coda_mutation_receipt(
            candidate
        ):
            return candidate

    return None


def extract_mutation_plan(
    request: Mapping[str, Any],
    bridge_result: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    for container in (
        bridge_result,
        request,
    ):
        for key in (
            "mutation_plan",
            "plan",
        ):
            candidate = _mapping(
                container.get(
                    key
                )
            )

            if candidate is not None:
                return candidate

    return None


def replace_file(
    request: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        request,
        Mapping,
    ):
        raise coda_palaver_governed_bridge_error(
            (
                "mutation request "
                "must be an object"
            )
        )

    bridge = load_live_bridge()

    replace = getattr(
        bridge,
        "replace_file",
        None,
    )

    if not callable(
        replace
    ):
        raise coda_palaver_governed_bridge_error(
            (
                "live Coda Palaver bridge "
                "does not expose replace_file()"
            )
        )

    bridge_result = replace(
        request
    )

    if not isinstance(
        bridge_result,
        Mapping,
    ):
        raise coda_palaver_governed_bridge_error(
            (
                "live bridge returned "
                "a non-object result"
            )
        )

    response = clone(
        dict(
            bridge_result
        )
    )

    evaluation = (
        extract_governance_evaluation(
            request,
            bridge_result,
        )
    )

    mutation_receipt = (
        extract_coda_mutation_receipt(
            bridge_result
        )
    )

    if evaluation is None:
        response[
            "governance_receipt_link"
        ] = {
            "emitted":
                False,

            "reason":
                (
                    "governance evaluation "
                    "not exposed by bridge "
                    "result or request"
                ),

            "authority_effect":
                "none",

            "authority_transfer":
                False,
        }

        return response

    if mutation_receipt is None:
        raise coda_palaver_governed_bridge_error(
            (
                "mutation completed but "
                "no Coda mutation receipt "
                "was exposed"
            )
        )

    receipts = (
        load_governance_receipts()
    )

    persist = getattr(
        receipts,
        "persist_linkage",
        None,
    )

    if not callable(
        persist
    ):
        raise coda_palaver_governed_bridge_error(
            (
                "Coda governance receipt "
                "runtime does not expose "
                "persist_linkage()"
            )
        )

    mutation_plan = (
        extract_mutation_plan(
            request,
            bridge_result,
        )
    )

    linkage = persist(
        coda_receipt=
            mutation_receipt,

        governance_evaluation=
            evaluation,

        mutation_plan=
            mutation_plan,

        mutation_plan_ref=(
            str(
                request.get(
                    "mutation_plan_ref"
                )
                or ""
            ).strip()
            or None
        ),
    )

    if not isinstance(
        linkage,
        Mapping,
    ):
        raise coda_palaver_governed_bridge_error(
            (
                "Coda governance linkage "
                "returned a non-object result"
            )
        )

    response[
        "governance_receipt_link"
    ] = {
        "emitted":
            True,

        "receipt":
            linkage.get(
                "receipt"
            ),

        "id":
            linkage.get(
                "id"
            ),

        "digest":
            linkage.get(
                "digest"
            ),

        (
            "governance_evaluation_"
            "receipt_id"
        ):
            linkage.get(
                (
                    "governance_evaluation_"
                    "receipt_id"
                )
            ),

        "governance_decision":
            linkage.get(
                "governance_decision"
            ),

        "mutation_owner":
            "coda",

        "governance_owner":
            "living-governance",

        "authority_effect":
            "none",

        "authority_transfer":
            False,
    }

    return response


def bridge_status() -> dict[str, Any]:
    bridge = load_live_bridge()

    receipts = (
        load_governance_receipts()
    )

    status_callable = getattr(
        bridge,
        "bridge_status",
        None,
    )

    live_status = (
        status_callable()
        if callable(
            status_callable
        )
        else {}
    )

    if not isinstance(
        live_status,
        Mapping,
    ):
        live_status = {}

    live_schema = (
        live_status.get(
            "schema"
        )
        or getattr(
            bridge,
            "SCHEMA",
            None,
        )
    )

    receipt_status_callable = getattr(
        receipts,
        "status",
        None,
    )

    receipt_status = (
        receipt_status_callable()
        if callable(
            receipt_status_callable
        )
        else {}
    )

    if not isinstance(
        receipt_status,
        Mapping,
    ):
        receipt_status = {}

    return {
        "schema":
            schema,

        "owner":
            owner,

        "caller":
            caller,

        "governance_owner":
            governance_owner,

        "authority_effect":
            authority_effect,

        "live_bridge_schema":
            live_schema,

        "live_bridge_ready":
            live_status.get(
                "ready",
                True,
            ),

        "replace_file_available":
            callable(
                getattr(
                    bridge,
                    "replace_file",
                    None,
                )
            ),

        (
            "durable_governance_"
            "linkage_available"
        ):
            callable(
                getattr(
                    receipts,
                    "persist_linkage",
                    None,
                )
            ),

        "bridge_replaced":
            False,

        "mutation_owner":
            owner,

        "authority_transfer":
            False,

        "ready":
            bool(
                callable(
                    getattr(
                        bridge,
                        "replace_file",
                        None,
                    )
                )
                and callable(
                    getattr(
                        receipts,
                        "persist_linkage",
                        None,
                    )
                )
                and live_status.get(
                    "ready",
                    True,
                )
            ),
    }


def selftest() -> dict[str, Any]:
    request = {
        "path":
            "runtime/test.py",

        "content":
            "test\n",

        "governance_evaluation": {
            "owner":
                "living-governance",

            "decision":
                "allow",

            "reason_codes":
                [
                    "test"
                ],

            "governing_rules":
                [
                    "rule:test"
                ],
        },

        "mutation_plan": {
            "id":
                "mutation-plan:test",

            "owner":
                "coda",

            "operation":
                "replace_text",

            "path":
                "runtime/test.py",
        },
    }

    bridge_result = {
        "schema":
            (
                "savant.coda."
                "palaver-mutation-bridge.v2"
            ),

        "ok":
            True,

        "owner":
            "coda",

        "result": {
            "id":
                "coda_test_receipt",

            "schema":
                (
                    "savant://coda/"
                    "mutation-receipt/2"
                ),

            "owner":
                "coda",

            "operation":
                "replace_text",

            "path":
                "runtime/test.py",

            "receipt":
                (
                    "vault/coda/"
                    "mutation_receipts/"
                    "coda_test_receipt.json"
                ),
        },
    }

    evaluation = (
        extract_governance_evaluation(
            request,
            bridge_result,
        )
    )

    receipt = (
        extract_coda_mutation_receipt(
            bridge_result
        )
    )

    plan = extract_mutation_plan(
        request,
        bridge_result,
    )

    if evaluation is None:
        raise coda_palaver_governed_bridge_error(
            (
                "governance evaluation "
                "extraction failed"
            )
        )

    if receipt is None:
        raise coda_palaver_governed_bridge_error(
            (
                "Coda mutation receipt "
                "extraction failed"
            )
        )

    if plan is None:
        raise coda_palaver_governed_bridge_error(
            (
                "mutation plan "
                "extraction failed"
            )
        )

    if (
        _decision_value(
            evaluation
        )
        != "allow"
    ):
        raise coda_palaver_governed_bridge_error(
            (
                "governance decision "
                "changed"
            )
        )

    receipts = (
        load_governance_receipts()
    )

    receipt_selftest = getattr(
        receipts,
        "selftest",
        None,
    )

    if not callable(
        receipt_selftest
    ):
        raise coda_palaver_governed_bridge_error(
            (
                "governance receipt "
                "selftest unavailable"
            )
        )

    receipt_result = (
        receipt_selftest()
    )

    if (
        not isinstance(
            receipt_result,
            Mapping,
        )
        or receipt_result.get(
            "ok"
        )
        is not True
    ):
        raise coda_palaver_governed_bridge_error(
            (
                "governance receipt "
                "selftest failed"
            )
        )

    status = bridge_status()

    if (
        status.get(
            "mutation_owner"
        )
        != "coda"
    ):
        raise coda_palaver_governed_bridge_error(
            "mutation ownership changed"
        )

    if (
        status.get(
            "authority_transfer"
        )
        is not False
    ):
        raise coda_palaver_governed_bridge_error(
            "authority transfer detected"
        )

    return {
        "schema":
            schema,

        "kind":
            "selftest",

        "owner":
            owner,

        "caller":
            caller,

        "governance_owner":
            governance_owner,

        "authority_effect":
            authority_effect,

        "ok":
            True,

        "live_bridge_loaded":
            True,

        "live_bridge_not_replaced":
            True,

        "governance_evaluation_extractable":
            True,

        "coda_mutation_receipt_extractable":
            True,

        "mutation_plan_extractable":
            True,

        (
            "durable_governance_"
            "linkage_available"
        ):
            status.get(
                (
                    "durable_governance_"
                    "linkage_available"
                )
            ),

        "mutation_owner":
            "coda",

        "authority_transfer":
            False,
    }


__all__ = [
    "bridge_status",
    "extract_coda_mutation_receipt",
    "extract_governance_evaluation",
    "extract_mutation_plan",
    "replace_file",
    "selftest",
]

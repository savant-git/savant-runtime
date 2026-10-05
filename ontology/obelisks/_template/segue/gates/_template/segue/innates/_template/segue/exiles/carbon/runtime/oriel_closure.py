#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json

from pathlib import Path
from types import ModuleType
from typing import Any, Mapping


owner = "carbon"
component = "oriel-closure"
authority_effect = "none"
schema = "savant.carbon.oriel-closure.v1"

carbon_root = (
    Path(__file__).resolve().parent.parent
)

closure_policy_path = (
    carbon_root
    / "validation/oriel_closure.json"
)

integration_test_path = (
    carbon_root
    / "tests/oriel_integration.py"
)


class oriel_closure_error(
    RuntimeError
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
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def load_json(
    path: Path,
) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except OSError as exc:
        raise oriel_closure_error(
            (
                "cannot read "
                + str(path)
                + ": "
                + str(exc)
            )
        ) from exc

    except json.JSONDecodeError as exc:
        raise oriel_closure_error(
            (
                "invalid json in "
                + str(path)
                + ": "
                + str(exc)
            )
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise oriel_closure_error(
            (
                "expected json object: "
                + str(path)
            )
        )

    return value


def closure_policy() -> dict[str, Any]:
    value = load_json(
        closure_policy_path
    )

    if (
        value.get("id")
        != "carbon.validation.oriel_closure"
    ):
        raise oriel_closure_error(
            "unexpected closure policy"
        )

    return value


def load_integration_module() -> ModuleType:
    if not integration_test_path.is_file():
        raise oriel_closure_error(
            (
                "integration validator missing: "
                + str(
                    integration_test_path
                )
            )
        )

    spec = (
        importlib.util.spec_from_file_location(
            "carbon_oriel_integration_test",
            integration_test_path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise oriel_closure_error(
            (
                "cannot load integration "
                "validator"
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


def run_validator() -> dict[str, Any]:
    module = load_integration_module()

    runner = getattr(
        module,
        "run",
        None,
    )

    if not callable(
        runner
    ):
        raise oriel_closure_error(
            (
                "integration validator "
                "does not expose run()"
            )
        )

    value = runner()

    if not isinstance(
        value,
        Mapping,
    ):
        raise oriel_closure_error(
            (
                "integration validator "
                "did not return an object"
            )
        )

    return dict(
        value
    )


def evaluate() -> dict[str, Any]:
    policy = closure_policy()

    validator = run_validator()

    failed_true = [
        field
        for field
        in policy.get(
            "required_true",
            [],
        )
        if validator.get(
            str(field)
        )
        is not True
    ]

    failed_zero = [
        field
        for field
        in policy.get(
            "required_zero",
            [],
        )
        if validator.get(
            str(field)
        )
        != 0
    ]

    failed_false = [
        field
        for field
        in policy.get(
            "required_false",
            [],
        )
        if validator.get(
            str(field)
        )
        is not False
    ]

    observed_state = str(
        validator.get(
            "observed_state",
            "",
        )
    ).strip().lower()

    allowed_states = {
        str(value).strip().lower()
        for value
        in policy.get(
            "allowed_observed_states",
            [],
        )
    }

    state_allowed = (
        observed_state
        in allowed_states
    )

    reasons = []

    if failed_true:
        reasons.append(
            (
                "required true fields failed: "
                + ", ".join(
                    sorted(
                        str(value)
                        for value
                        in failed_true
                    )
                )
            )
        )

    if failed_zero:
        reasons.append(
            (
                "required zero fields failed: "
                + ", ".join(
                    sorted(
                        str(value)
                        for value
                        in failed_zero
                    )
                )
            )
        )

    if failed_false:
        reasons.append(
            (
                "required false fields failed: "
                + ", ".join(
                    sorted(
                        str(value)
                        for value
                        in failed_false
                    )
                )
            )
        )

    if not state_allowed:
        reasons.append(
            (
                "observed state not allowed: "
                + observed_state
            )
        )

    closed = not reasons

    result = {
        "schema":
            schema,

        "kind":
            "oriel-closure-evaluation",

        "owner":
            owner,

        "component":
            component,

        "specialization":
            "carbon.oriel",

        "authority_effect":
            authority_effect,

        "closed":
            closed,

        "observed_state":
            observed_state,

        "failed_required_true":
            sorted(
                str(value)
                for value
                in failed_true
            ),

        "failed_required_zero":
            sorted(
                str(value)
                for value
                in failed_zero
            ),

        "failed_required_false":
            sorted(
                str(value)
                for value
                in failed_false
            ),

        "observed_state_allowed":
            state_allowed,

        "reasons":
            reasons,

        "validator_digest":
            validator.get(
                "digest"
            ),

        "closure_is_derived":
            True,

        "persistent_authority_created":
            False,

        "source_state_mutated":
            False,

        "canon_effect":
            "none",

        "evidence_admission":
            False,

        "authority_transfer":
            False,
    }

    result["digest"] = digest(
        {
            key: value
            for key, value
            in result.items()
            if key != "digest"
        }
    )

    return result


def status() -> dict[str, Any]:
    value = evaluate()

    return {
        "schema":
            schema,

        "kind":
            "status",

        "owner":
            owner,

        "component":
            component,

        "specialization":
            "carbon.oriel",

        "authority_effect":
            authority_effect,

        "closed":
            value[
                "closed"
            ],

        "observed_state":
            value[
                "observed_state"
            ],

        "reason_count":
            len(
                value[
                    "reasons"
                ]
            ),

        "closure_is_derived":
            True,

        "authority_transfer":
            False,

        "ready":
            value[
                "closed"
            ],
    }


def close() -> dict[str, Any]:
    value = evaluate()

    if not value[
        "closed"
    ]:
        raise oriel_closure_error(
            (
                "carbon.oriel cannot close: "
                + "; ".join(
                    value[
                        "reasons"
                    ]
                )
            )
        )

    return {
        "schema":
            schema,

        "kind":
            "closure-receipt",

        "owner":
            owner,

        "component":
            component,

        "specialization":
            "carbon.oriel",

        "authority_effect":
            authority_effect,

        "ok":
            True,

        "closed":
            True,

        "observed_state":
            value[
                "observed_state"
            ],

        "validation_digest":
            value[
                "validator_digest"
            ],

        "closure_digest":
            value[
                "digest"
            ],

        "closure_is_derived":
            True,

        "persistent_authority_created":
            False,

        "source_state_mutated":
            False,

        "canon_effect":
            "none",

        "evidence_admission":
            False,

        "authority_transfer":
            False,
    }


def selftest() -> dict[str, Any]:
    receipt = close()

    if receipt.get(
        "closed"
    ) is not True:
        raise oriel_closure_error(
            "closure receipt is not closed"
        )

    if receipt.get(
        "authority_transfer"
    ) is not False:
        raise oriel_closure_error(
            "closure transferred authority"
        )

    return {
        "schema":
            schema,

        "kind":
            "selftest",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "ok":
            True,

        "closure_gate_enforced":
            True,

        "current_validation_required":
            True,

        "closure_is_derived":
            True,

        "persistent_authority_created":
            False,

        "authority_transfer":
            False,

        "source_state_mutated":
            False,

        "canon_effect":
            "none",
    }


__all__ = [
    "close",
    "closure_policy",
    "evaluate",
    "run_validator",
    "selftest",
    "status",
]

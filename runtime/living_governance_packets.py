#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
import inspect
import json

from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Mapping, Sequence


owner = "living-governance"
authority_effect = "none"
schema = "savant.living-governance.consumer-packet.v1"

runtime_root = Path(
    "/root/savant-runtime/runtime"
)

typed_runtime_path = (
    runtime_root
    / "living_typed_governance.py"
)

consumers = {
    "palaver": {
        "role":
            "conversation_workspace_patch_review_orchestration",

        "directive_field":
            "orchestration_directive",

        "authority_owner":
            "palaver",
    },

    "opus": {
        "role":
            "provider_model_execution",

        "directive_field":
            "execution_directive",

        "authority_owner":
            "opus",
    },

    "scrybe": {
        "role":
            "memory_context",

        "directive_field":
            "context_directive",

        "authority_owner":
            "scrybe",
    },

    "niche": {
        "role":
            "task_context",

        "directive_field":
            "task_directive",

        "authority_owner":
            "niche",
    },

    "kindred": {
        "role":
            "typed_relationship_methodology",

        "directive_field":
            "relationship_directive",

        "authority_owner":
            None,
    },
}

decision_aliases = {
    "allow": "pass",
    "deny": "fail",
    "authority_required": "authority-required",
}

decision_semantics = {
    "pass": {
        "exit_code": 0,
        "exit_name": "governance_pass",
        "directive": "proceed",
        "blocking": False,
    },

    "advisory": {
        "exit_code": 10,
        "exit_name": "governance_advisory",
        "directive": "proceed_with_advisory",
        "blocking": False,
    },

    "unknown": {
        "exit_code": 20,
        "exit_name": "governance_unknown",
        "directive": "hold_for_resolution",
        "blocking": True,
    },

    "authority-required": {
        "exit_code": 30,
        "exit_name": "governance_authority_required",
        "directive": "require_authority",
        "blocking": True,
    },

    "fail": {
        "exit_code": 40,
        "exit_name": "governance_fail",
        "directive": "deny",
        "blocking": True,
    },
}

technical_exit_codes = {
    "invalid_input": 64,
    "evaluator_unavailable": 69,
    "evaluation_error": 70,
}

system_reason_codes = {
    "lg.evaluation.pass":
        "evaluation passed",

    "lg.evaluation.advisory":
        "evaluation produced advisory outcome",

    "lg.evaluation.unknown":
        "evaluation remains unresolved",

    "lg.evaluation.authority-required":
        "higher authority is required",

    "lg.evaluation.fail":
        "evaluation failed",

    "lg.provenance.incomplete":
        "evaluation packet lacks one or more provenance dimensions",

    "lg.evaluator.unavailable":
        "no compatible live typed governance evaluator was discovered",

    "lg.input.invalid":
        "input failed packet validation",
}


class living_governance_packet_error(
    RuntimeError
):
    pass


class living_governance_evaluator_unavailable(
    living_governance_packet_error
):
    pass


def clone(
    value: Any,
) -> Any:
    return copy.deepcopy(value)


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


def require_mapping(
    value: Any,
    label: str,
) -> Mapping[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise living_governance_packet_error(
            label
            + " must be a JSON object"
        )

    return value


def normalize_strings(
    value: Any,
) -> list[str]:
    if value is None:
        return []

    if isinstance(
        value,
        str,
    ):
        value = [value]

    if not isinstance(
        value,
        Sequence,
    ):
        return [
            str(value).strip()
        ] if str(value).strip() else []

    return sorted(
        {
            str(item).strip()
            for item in value
            if str(item).strip()
        }
    )


def first_collection(
    value: Mapping[str, Any],
    names: Sequence[str],
) -> list[str]:
    for name in names:
        if name in value:
            return normalize_strings(
                value.get(name)
            )

    return []


def normalize_decision(
    raw: Any,
) -> str:
    value = (
        str(raw)
        .strip()
        .lower()
        .replace("_", "-")
    )

    value = decision_aliases.get(
        value,
        value,
    )

    if value not in decision_semantics:
        raise living_governance_packet_error(
            (
                "unsupported governance "
                "decision: "
                + value
            )
        )

    return value


def decision_from_evaluation(
    evaluation: Mapping[str, Any],
) -> str:
    for field in (
        "decision",
        "result",
        "outcome",
        "state",
    ):
        raw = evaluation.get(field)

        if raw is not None:
            return normalize_decision(
                raw
            )

    raise living_governance_packet_error(
        (
            "evaluation does not expose "
            "decision/result/outcome/state"
        )
    )


def extract_trace(
    evaluation: Mapping[str, Any],
) -> Any:
    for field in (
        "evaluation_trace",
        "trace",
        "explanation_trace",
        "causal_trace",
    ):
        if field in evaluation:
            return clone(
                evaluation.get(field)
            )

    trace_ref = evaluation.get(
        "evaluation_trace_ref"
    )

    if trace_ref:
        return {
            "ref":
                str(trace_ref)
        }

    return None


def extract_evidence_refs(
    evaluation: Mapping[str, Any],
) -> list[str]:
    direct = first_collection(
        evaluation,
        (
            "evidence_refs",
            "evidence_references",
            "evidence",
        ),
    )

    provenance = evaluation.get(
        "provenance"
    )

    if isinstance(
        provenance,
        Mapping,
    ):
        direct.extend(
            first_collection(
                provenance,
                (
                    "evidence_refs",
                    "evidence_references",
                    "evidence",
                ),
            )
        )

    return sorted(
        set(direct)
    )


def extract_source_refs(
    evaluation: Mapping[str, Any],
) -> list[str]:
    direct = first_collection(
        evaluation,
        (
            "source_refs",
            "source_references",
            "sources",
        ),
    )

    provenance = evaluation.get(
        "provenance"
    )

    if isinstance(
        provenance,
        Mapping,
    ):
        direct.extend(
            first_collection(
                provenance,
                (
                    "source_refs",
                    "source_references",
                    "sources",
                ),
            )
        )

    return sorted(
        set(direct)
    )


def provenance_projection(
    evaluation: Mapping[str, Any],
    *,
    request: Mapping[str, Any]
    | None = None,
) -> dict[str, Any]:
    trace = extract_trace(
        evaluation
    )

    governing_rules = (
        first_collection(
            evaluation,
            (
                "governing_rules",
                "rules",
                "policy_refs",
            ),
        )
    )

    evidence_requirements = (
        first_collection(
            evaluation,
            (
                "evidence_requirements",
                "required_evidence",
            ),
        )
    )

    evidence_refs = extract_evidence_refs(
        evaluation
    )

    source_refs = extract_source_refs(
        evaluation
    )

    evaluation_digest = digest(
        evaluation
    )

    request_digest = (
        digest(request)
        if request is not None
        else None
    )

    trace_digest = (
        digest(trace)
        if trace is not None
        else None
    )

    evaluation_trace_complete = bool(
        evaluation_digest
        and request_digest
        and trace_digest
    )

    evidence_complete = bool(
        not evidence_requirements
        or evidence_refs
    )

    result = {
        "evaluation_digest":
            evaluation_digest,

        "request_digest":
            request_digest,

        "trace_digest":
            trace_digest,

        "governing_rule_refs":
            governing_rules,

        "evidence_requirements":
            evidence_requirements,

        "evidence_refs":
            evidence_refs,

        "source_refs":
            source_refs,

        "trace":
            trace,

        "dimensions": {
            "evaluation_digest":
                True,

            "request_digest":
                request_digest
                is not None,

            "trace":
                trace_digest
                is not None,

            "governing_rules":
                bool(
                    governing_rules
                ),

            "evidence_refs":
                bool(
                    evidence_refs
                ),

            "source_refs":
                bool(
                    source_refs
                ),
        },

        "evaluation_trace_complete":
            evaluation_trace_complete,

        "evidence_requirements_satisfied":
            evidence_complete,

        "provenance_complete":
            bool(
                evaluation_trace_complete
                and evidence_complete
            ),
    }

    return result


def taxonomy() -> dict[str, Any]:
    return {
        "schema":
            (
                "savant.living-governance."
                "machine-semantics.v1"
            ),

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "decisions":
            clone(
                decision_semantics
            ),

        "technical_exit_codes":
            clone(
                technical_exit_codes
            ),

        "system_reason_codes":
            clone(
                system_reason_codes
            ),

        "rules": {
            "unknown_collapses_to_pass":
                False,

            "unknown_collapses_to_fail":
                False,

            "authority_required_is_fail":
                False,

            "advisory_is_blocking":
                False,

            "decision_exit_codes_are_stable":
                True,

            "consumer_packet_creates_authority":
                False,

            "authority_transfer":
                False,
        },
    }


def consumer_packet(
    *,
    consumer: str,
    evaluation: Mapping[str, Any],
    request: Mapping[str, Any]
    | None = None,
) -> dict[str, Any]:
    target = (
        str(consumer)
        .strip()
        .lower()
    )

    if target not in consumers:
        raise living_governance_packet_error(
            (
                "unsupported consumer: "
                + target
            )
        )

    evaluation = require_mapping(
        evaluation,
        "evaluation",
    )

    if request is not None:
        request = require_mapping(
            request,
            "request",
        )

    decision = decision_from_evaluation(
        evaluation
    )

    semantics = decision_semantics[
        decision
    ]

    provenance = provenance_projection(
        evaluation,
        request=request,
    )

    original_reason_codes = (
        first_collection(
            evaluation,
            (
                "reason_codes",
                "reasons",
            ),
        )
    )

    system_codes = [
        "lg.evaluation."
        + decision
    ]

    if not provenance[
        "provenance_complete"
    ]:
        system_codes.append(
            "lg.provenance.incomplete"
        )

    governing_rules = (
        provenance[
            "governing_rule_refs"
        ]
    )

    constraints = {
        "affected_objects":
            first_collection(
                evaluation,
                (
                    "affected_objects",
                    "affected",
                    "targets",
                ),
            ),

        "compatibility_obligations":
            first_collection(
                evaluation,
                (
                    "compatibility_obligations",
                    "compatibility",
                ),
            ),

        "evidence_requirements":
            provenance[
                "evidence_requirements"
            ],

        "unresolved_unknowns":
            first_collection(
                evaluation,
                (
                    "unresolved_unknowns",
                    "unknowns",
                ),
            ),

        "override_requirements":
            first_collection(
                evaluation,
                (
                    "override_requirements",
                    "required_overrides",
                ),
            ),

        "remediation":
            first_collection(
                evaluation,
                (
                    "remediation",
                    "remediations",
                ),
            ),
    }

    descriptor = consumers[
        target
    ]

    directive = {
        "decision":
            decision,

        "action":
            semantics[
                "directive"
            ],

        "blocking":
            semantics[
                "blocking"
            ],

        "reason_codes":
            clone(
                original_reason_codes
            ),

        "system_reason_codes":
            clone(
                system_codes
            ),

        "governing_rules":
            clone(
                governing_rules
            ),

        "constraints":
            clone(
                constraints
            ),
    }

    identity_material = {
        "consumer":
            target,

        "evaluation_digest":
            provenance[
                "evaluation_digest"
            ],

        "request_digest":
            provenance[
                "request_digest"
            ],

        "decision":
            decision,
    }

    result = {
        "schema":
            schema,

        "id":
            (
                "living-governance:"
                "consumer-packet:"
                + digest(
                    identity_material
                )[:32]
            ),

        "kind":
            "governance-consumer-packet",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "consumer":
            target,

        "consumer_role":
            descriptor[
                "role"
            ],

        "consumer_authority_owner":
            descriptor[
                "authority_owner"
            ],

        "decision":
            decision,

        "blocking":
            semantics[
                "blocking"
            ],

        "exit": {
            "code":
                semantics[
                    "exit_code"
                ],

            "name":
                semantics[
                    "exit_name"
                ],
        },

        "reason_codes":
            clone(
                original_reason_codes
            ),

        "system_reason_codes":
            clone(
                system_codes
            ),

        "governing_rules":
            clone(
                governing_rules
            ),

        "constraints":
            clone(
                constraints
            ),

        "provenance":
            provenance,

        "source_evaluation":
            clone(
                dict(
                    evaluation
                )
            ),

        "source_request":
            (
                clone(
                    dict(
                        request
                    )
                )
                if request is not None
                else None
            ),

        "projection_only":
            True,

        "consumer_owns_packet_authority":
            False,

        "source_state_mutated":
            False,

        "authority_transfer":
            False,
    }

    result[
        descriptor[
            "directive_field"
        ]
    ] = directive

    result[
        "digest"
    ] = digest(
        {
            key:
                value
            for key, value
            in result.items()
            if key
            != "digest"
        }
    )

    return result


def packets(
    *,
    evaluation: Mapping[str, Any],
    request: Mapping[str, Any]
    | None = None,
) -> dict[str, Any]:
    result = {
        target:
            consumer_packet(
                consumer=target,
                evaluation=evaluation,
                request=request,
            )
        for target
        in consumers
    }

    return {
        "schema":
            (
                "savant.living-governance."
                "consumer-packet-set.v1"
            ),

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "consumers":
            sorted(
                consumers
            ),

        "packets":
            result,

        "packet_count":
            len(result),

        "source_state_mutated":
            False,

        "authority_transfer":
            False,
    }


def load_typed_runtime() -> ModuleType:
    if not typed_runtime_path.is_file():
        raise living_governance_evaluator_unavailable(
            (
                "live typed governance "
                "runtime is missing"
            )
        )

    spec = (
        importlib.util.spec_from_file_location(
            "savant_live_living_typed_governance",
            typed_runtime_path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise living_governance_evaluator_unavailable(
            (
                "cannot load live typed "
                "governance runtime"
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


def accepts_single_request(
    function: Callable[..., Any],
) -> bool:
    try:
        signature = inspect.signature(
            function
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    positional = []
    required_keyword_only = []

    for parameter in (
        signature.parameters.values()
    ):
        if parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            positional.append(
                parameter
            )

        elif (
            parameter.kind
            == inspect.Parameter.KEYWORD_ONLY
            and parameter.default
            is inspect.Parameter.empty
        ):
            required_keyword_only.append(
                parameter
            )

    required_positional = [
        parameter
        for parameter
        in positional
        if parameter.default
        is inspect.Parameter.empty
    ]

    return bool(
        len(
            required_positional
        )
        <= 1
        and len(
            positional
        )
        >= 1
        and not required_keyword_only
    )


def evaluator_candidates(
    module: ModuleType,
) -> list[
    tuple[
        str,
        Callable[..., Any],
    ]
]:
    names = (
        "evaluate",
        "evaluate_request",
        "evaluate_context",
        "evaluate_policy",
        "evaluate_record",
    )

    found = []

    for name in names:
        value = getattr(
            module,
            name,
            None,
        )

        if (
            callable(value)
            and accepts_single_request(
                value
            )
        ):
            found.append(
                (
                    name,
                    value,
                )
            )

    engine = getattr(
        module,
        "engine",
        None,
    )

    if (
        engine is not None
        and not callable(engine)
    ):
        for name in names:
            value = getattr(
                engine,
                name,
                None,
            )

            if (
                callable(value)
                and accepts_single_request(
                    value
                )
            ):
                found.append(
                    (
                        "engine."
                        + name,
                        value,
                    )
                )

    return found


def live_evaluator_status() -> dict[str, Any]:
    if not typed_runtime_path.is_file():
        return {
            "typed_runtime_present":
                False,

            "compatible_evaluator":
                False,

            "candidates":
                [],

            "ready":
                False,
        }

    try:
        module = load_typed_runtime()
        candidates = evaluator_candidates(
            module
        )

    except Exception as exc:
        return {
            "typed_runtime_present":
                True,

            "compatible_evaluator":
                False,

            "candidates":
                [],

            "load_error":
                str(exc),

            "ready":
                False,
        }

    return {
        "typed_runtime_present":
            True,

        "compatible_evaluator":
            bool(candidates),

        "candidates":
            [
                name
                for name, _
                in candidates
            ],

        "ready":
            bool(candidates),
    }


def evaluate_live(
    request: Mapping[str, Any],
) -> tuple[
    dict[str, Any],
    str,
]:
    request = require_mapping(
        request,
        "request",
    )

    module = load_typed_runtime()

    candidates = evaluator_candidates(
        module
    )

    if not candidates:
        raise living_governance_evaluator_unavailable(
            (
                "live typed governance "
                "runtime exposes no "
                "compatible one-request "
                "evaluator"
            )
        )

    name, evaluator = candidates[0]

    try:
        result = evaluator(
            request
        )

    except Exception as exc:
        raise living_governance_packet_error(
            (
                "live governance evaluator "
                + name
                + " failed: "
                + str(exc)
            )
        ) from exc

    if not isinstance(
        result,
        Mapping,
    ):
        raise living_governance_packet_error(
            (
                "live governance evaluator "
                + name
                + " returned a non-object"
            )
        )

    return (
        dict(result),
        name,
    )


def evaluate_and_packet(
    *,
    consumer: str,
    request: Mapping[str, Any],
) -> dict[str, Any]:
    evaluation, evaluator = evaluate_live(
        request
    )

    result = consumer_packet(
        consumer=consumer,
        evaluation=evaluation,
        request=request,
    )

    result[
        "live_evaluator"
    ] = evaluator

    result[
        "digest"
    ] = digest(
        {
            key:
                value
            for key, value
            in result.items()
            if key
            != "digest"
        }
    )

    return result


def status() -> dict[str, Any]:
    live = live_evaluator_status()

    return {
        "schema":
            schema,

        "kind":
            "status",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "consumer_count":
            len(consumers),

        "consumers":
            sorted(
                consumers
            ),

        "structured_exit_codes":
            True,

        "stable_system_reason_codes":
            True,

        "provenance_projection":
            True,

        "typed_runtime_present":
            live[
                "typed_runtime_present"
            ],

        "compatible_live_evaluator":
            live[
                "compatible_evaluator"
            ],

        "live_evaluator_candidates":
            clone(
                live[
                    "candidates"
                ]
            ),

        "projection_only":
            True,

        "authority_transfer":
            False,

        "ready":
            True,
    }


def selftest() -> dict[str, Any]:
    request = {
        "type":
            "mutation-plan",

        "subject":
            "palaver",

        "target":
            "runtime:test",

        "action":
            "replace",
    }

    evaluation = {
        "decision":
            "unknown",

        "reason_codes":
            [
                "missing-evidence"
            ],

        "governing_rules":
            [
                "rule:test"
            ],

        "evidence_requirements":
            [
                "evidence:test"
            ],

        "evidence_refs":
            [
                "evidence:test:1"
            ],

        "source_refs":
            [
                "source:test:1"
            ],

        "affected_objects":
            [
                "runtime:test"
            ],

        "compatibility_obligations":
            [
                "preserve:test"
            ],

        "unresolved_unknowns":
            [
                "unknown:test"
            ],

        "override_requirements":
            [],

        "evaluation_trace": [
            {
                "step":
                    1,

                "predicate":
                    "exists",

                "result":
                    "unknown",
            }
        ],
    }

    packet_set = packets(
        evaluation=evaluation,
        request=request,
    )

    if (
        packet_set[
            "packet_count"
        ]
        != 5
    ):
        raise living_governance_packet_error(
            "consumer packet count failed"
        )

    for target in consumers:
        packet = packet_set[
            "packets"
        ][
            target
        ]

        if (
            packet[
                "decision"
            ]
            != "unknown"
        ):
            raise living_governance_packet_error(
                (
                    target
                    + " collapsed unknown"
                )
            )

        if (
            packet[
                "exit"
            ][
                "code"
            ]
            != 20
        ):
            raise living_governance_packet_error(
                (
                    target
                    + " has wrong unknown "
                    "exit code"
                )
            )

        if (
            packet[
                "provenance"
            ][
                "provenance_complete"
            ]
            is not True
        ):
            raise living_governance_packet_error(
                (
                    target
                    + " provenance "
                    "projection incomplete"
                )
            )

        if (
            packet[
                "authority_transfer"
            ]
            is not False
        ):
            raise living_governance_packet_error(
                (
                    target
                    + " transferred authority"
                )
            )

    fail_packet = consumer_packet(
        consumer="palaver",
        evaluation={
            "decision":
                "fail",

            "evaluation_trace": [
                {
                    "result":
                        "fail"
                }
            ],
        },
        request=request,
    )

    if (
        fail_packet[
            "exit"
        ][
            "code"
        ]
        != 40
        or fail_packet[
            "blocking"
        ]
        is not True
    ):
        raise living_governance_packet_error(
            "fail machine semantics failed"
        )

    authority_packet = consumer_packet(
        consumer="niche",
        evaluation={
            "decision":
                "authority-required",

            "evaluation_trace": [
                {
                    "result":
                        "authority-required"
                }
            ],
        },
        request=request,
    )

    if (
        authority_packet[
            "exit"
        ][
            "code"
        ]
        != 30
        or authority_packet[
            "blocking"
        ]
        is not True
    ):
        raise living_governance_packet_error(
            (
                "authority-required "
                "machine semantics failed"
            )
        )

    return {
        "schema":
            schema,

        "kind":
            "selftest",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "ok":
            True,

        "palaver_packet":
            True,

        "opus_packet":
            True,

        "scrybe_packet":
            True,

        "niche_packet":
            True,

        "kindred_packet":
            True,

        "unknown_preserved":
            True,

        "structured_exit_codes":
            True,

        "stable_system_reason_codes":
            True,

        "provenance_complete_trace":
            True,

        "consumer_authority_created":
            False,

        "source_state_mutated":
            False,

        "authority_transfer":
            False,
    }


__all__ = [
    "consumer_packet",
    "decision_from_evaluation",
    "evaluate_and_packet",
    "evaluate_live",
    "live_evaluator_status",
    "packets",
    "selftest",
    "status",
    "taxonomy",
]

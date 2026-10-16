#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json

from typing import Any, Mapping, Sequence

from living_policy_arbitration import arbitrate
from living_policy_lifecycle import project as lifecycle_project


owner = "living-governance"
authority_effect = "none"
schema = "savant.living-governance.policy-pipeline.v1"


eligible_states = {
    "active",
}

excluded_states = {
    "proposed",
    "accepted_for_implementation",
    "materialized",
    "verified",
    "superseded",
    "retired",
    "indeterminate",
}


class living_policy_pipeline_error(
    RuntimeError
):
    pass


def clone(
    value: Any,
) -> Any:
    return copy.deepcopy(
        value
    )


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


def policy_id(
    record: Mapping[str, Any],
) -> str:
    identifier = str(
        record.get(
            "id",
            "",
        )
    ).strip()

    if not identifier:
        raise living_policy_pipeline_error(
            "policy id is required"
        )

    return identifier


def explicit_lifecycle(
    record: Mapping[str, Any],
) -> bool:
    if (
        "lifecycle_state"
        in record
    ):
        return True

    if (
        "lifecycle"
        in record
        and isinstance(
            record.get(
                "lifecycle"
            ),
            Mapping,
        )
    ):
        return True

    if (
        "lifecycle_events"
        in record
    ):
        return True

    if (
        "status"
        in record
        and str(
            record.get(
                "status",
                "",
            )
        ).strip().lower()
        in {
            "proposed",
            "accepted",
            "accepted_for_implementation",
            "accepted-for-implementation",
            "materialized",
            "implemented",
            "verified",
            "active",
            "superseded",
            "retired",
            "inactive",
        }
    ):
        return True

    return False


def lifecycle_eligibility(
    records: Sequence[
        Mapping[str, Any]
    ],
    lifecycle: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    policy_states = lifecycle.get(
        "policies",
        {},
    )

    if not isinstance(
        policy_states,
        Mapping,
    ):
        raise living_policy_pipeline_error(
            (
                "lifecycle projection "
                "does not expose policies"
            )
        )

    eligible = []
    excluded = []
    legacy = []

    for record in records:
        if not isinstance(
            record,
            Mapping,
        ):
            raise living_policy_pipeline_error(
                (
                    "every policy record "
                    "must be an object"
                )
            )

        identifier = policy_id(
            record
        )

        state_projection = (
            policy_states.get(
                identifier
            )
        )

        if not isinstance(
            state_projection,
            Mapping,
        ):
            raise living_policy_pipeline_error(
                (
                    "missing lifecycle "
                    "projection for "
                    + identifier
                )
            )

        state = str(
            state_projection.get(
                "effective_state",
                "",
            )
        ).strip().lower()

        declared = explicit_lifecycle(
            record
        )

        partially_superseded = bool(
            state_projection.get(
                "partially_superseded_by"
            )
        )

        if not declared:
            eligible.append(
                clone(
                    dict(
                        record
                    )
                )
            )

            legacy.append(
                {
                    "policy":
                        identifier,

                    "effective_state":
                        state,

                    "reason":
                        (
                            "legacy-policy-without-"
                            "explicit-lifecycle"
                        ),

                    "eligible":
                        True,
                }
            )

            continue

        if state in eligible_states:
            eligible.append(
                clone(
                    dict(
                        record
                    )
                )
            )

            continue

        excluded.append(
            {
                "policy":
                    identifier,

                "effective_state":
                    state,

                "partially_superseded":
                    partially_superseded,

                "eligible":
                    False,
            }
        )

    return {
        "eligible_records":
            eligible,

        "eligible_policy_ids": [
            policy_id(
                record
            )
            for record
            in eligible
        ],

        "excluded":
            excluded,

        "legacy_compatibility":
            legacy,
    }


def lifecycle_gate_decision(
    lifecycle: Mapping[
        str,
        Any,
    ],
) -> tuple[
    str | None,
    list[str],
]:
    state = str(
        lifecycle.get(
            "state",
            "",
        )
    ).strip().lower()

    reasons = []

    if state == "authority-required":
        reasons.append(
            (
                "lg.pipeline."
                "lifecycle-authority-required"
            )
        )

        return (
            "authority-required",
            reasons,
        )

    if state == "unknown":
        reasons.append(
            (
                "lg.pipeline."
                "lifecycle-unknown"
            )
        )

        return (
            "unknown",
            reasons,
        )

    cycle_ids = lifecycle.get(
        "supersession_cycle_policy_ids",
        [],
    )

    if cycle_ids:
        reasons.append(
            (
                "lg.pipeline."
                "supersession-cycle"
            )
        )

        return (
            "authority-required",
            reasons,
        )

    unresolved = lifecycle.get(
        "unresolved_supersession_edges",
        [],
    )

    if unresolved:
        reasons.append(
            (
                "lg.pipeline."
                "pryme-resolution-required"
            )
        )

        return (
            "authority-required",
            reasons,
        )

    missing = lifecycle.get(
        "missing_supersession_targets",
        [],
    )

    if missing:
        reasons.append(
            (
                "lg.pipeline."
                "supersession-target-unknown"
            )
        )

        return (
            "unknown",
            reasons,
        )

    return (
        None,
        reasons,
    )


def run(
    records: Sequence[
        Mapping[str, Any]
    ],
    *,
    supersession: Sequence[
        Mapping[str, Any]
    ]
    | None = None,
    as_of: Any = None,
    sequence: Any = None,
    default_timezone:
        str | None = None,
) -> dict[str, Any]:
    source_digest = digest(
        records
    )

    supersession_digest = digest(
        supersession
        or []
    )

    lifecycle = lifecycle_project(
        records,
        supersession=
            supersession,
    )

    eligibility = (
        lifecycle_eligibility(
            records,
            lifecycle,
        )
    )

    eligible_records = (
        eligibility[
            "eligible_records"
        ]
    )

    arbitration = arbitrate(
        eligible_records,
        as_of=
            as_of,
        sequence=
            sequence,
        default_timezone=
            default_timezone,
    )

    (
        lifecycle_decision,
        lifecycle_reasons,
    ) = lifecycle_gate_decision(
        lifecycle
    )

    arbitration_decision = str(
        arbitration.get(
            "decision",
            "unknown",
        )
    ).strip().lower()

    decision = (
        lifecycle_decision
        if lifecycle_decision
        is not None
        else arbitration_decision
    )

    blocking = bool(
        decision
        in {
            "fail",
            "unknown",
            "authority-required",
        }
    )

    reason_codes = sorted(
        set(
            lifecycle_reasons
            + [
                str(value)
                for value
                in arbitration.get(
                    "reason_codes",
                    [],
                )
            ]
        )
    )

    result = {
        "schema":
            schema,

        "kind":
            (
                "lifecycle-aware-"
                "policy-arbitration"
            ),

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "decision":
            decision,

        "blocking":
            blocking,

        "lifecycle_gate_decision":
            lifecycle_decision,

        "arbitration_decision":
            arbitration_decision,

        "reason_codes":
            reason_codes,

        "eligible_policy_ids":
            clone(
                eligibility[
                    "eligible_policy_ids"
                ]
            ),

        "excluded_policies":
            clone(
                eligibility[
                    "excluded"
                ]
            ),

        "legacy_compatibility":
            clone(
                eligibility[
                    "legacy_compatibility"
                ]
            ),

        "lifecycle":
            lifecycle,

        "arbitration":
            arbitration,

        "rules": {
            "explicit_superseded_policy_eligible":
                False,

            "explicit_retired_policy_eligible":
                False,

            (
                "explicit_pre_active_"
                "policy_eligible"
            ):
                False,

            (
                "partial_supersession_"
                "automatically_deactivates"
            ):
                False,

            (
                "legacy_policy_without_"
                "lifecycle_metadata_eligible"
            ):
                True,

            (
                "unresolved_supersession_"
                "may_finalize"
            ):
                False,

            (
                "pryme_resolves_"
                "supersession"
            ):
                True,

            (
                "living_governance_"
                "applies_supersession"
            ):
                False,
        },

        "projection_only":
            True,

        "source_state_mutated":
            (
                source_digest
                != digest(
                    records
                )
            ),

        (
            "supersession_source_"
            "mutated"
        ):
            (
                supersession_digest
                != digest(
                    supersession
                    or []
                )
            ),

        "authority_transfer":
            False,
    }

    if result[
        "source_state_mutated"
    ]:
        raise living_policy_pipeline_error(
            "policy source was mutated"
        )

    if result[
        "supersession_source_mutated"
    ]:
        raise living_policy_pipeline_error(
            (
                "supersession source "
                "was mutated"
            )
        )

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
    return {
        "schema":
            schema,

        "kind":
            "status",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "lifecycle_before_arbitration":
            True,

        "superseded_filtered":
            True,

        "retired_filtered":
            True,

        "pre_active_filtered":
            True,

        "partial_supersession_preserved":
            True,

        (
            "legacy_lifecycle_"
            "compatibility"
        ):
            True,

        (
            "unresolved_pryme_"
            "supersession_blocks_finality"
        ):
            True,

        "projection_only":
            True,

        "authority_transfer":
            False,

        "ready":
            True,
    }


def selftest() -> dict[str, Any]:
    legacy = run(
        [
            {
                "id":
                    "policy:legacy",

                "authority_class":
                    "constitutional_canon",

                "effect":
                    "allow",
            }
        ]
    )

    if (
        legacy[
            "decision"
        ]
        != "pass"
    ):
        raise living_policy_pipeline_error(
            (
                "legacy policy without "
                "lifecycle metadata "
                "was excluded"
            )
        )

    full_supersession = run(
        [
            {
                "id":
                    "policy:old",

                "lifecycle_state":
                    "active",

                "authority_class":
                    "constitutional_canon",

                "effect":
                    "deny",
            },
            {
                "id":
                    "policy:new",

                "lifecycle_state":
                    "active",

                "authority_class":
                    "constitutional_canon",

                "specificity":
                    10,

                "effect":
                    "allow",
            },
        ],
        supersession=[
            {
                "id":
                    "supersession:1",

                "kind":
                    "supersession",

                "source":
                    "policy:old",

                "target":
                    "policy:new",

                "coverage":
                    "full",

                "resolution_owner":
                    "pryme",

                "accepted":
                    True,
            }
        ],
    )

    if (
        full_supersession[
            "decision"
        ]
        != "pass"
    ):
        raise living_policy_pipeline_error(
            (
                "superseded policy "
                "participated in arbitration"
            )
        )

    if (
        "policy:old"
        in full_supersession[
            "eligible_policy_ids"
        ]
    ):
        raise living_policy_pipeline_error(
            (
                "fully superseded policy "
                "was not filtered"
            )
        )

    retired = run(
        [
            {
                "id":
                    "policy:retired",

                "lifecycle_state":
                    "retired",

                "authority_class":
                    "accepted_decision",

                "effect":
                    "deny",
            },
            {
                "id":
                    "policy:active",

                "lifecycle_state":
                    "active",

                "authority_class":
                    "constitutional_canon",

                "effect":
                    "allow",
            },
        ]
    )

    if (
        retired[
            "decision"
        ]
        != "pass"
    ):
        raise living_policy_pipeline_error(
            (
                "retired policy "
                "participated in arbitration"
            )
        )

    partial = run(
        [
            {
                "id":
                    "policy:partial-source",

                "lifecycle_state":
                    "active",

                "authority_class":
                    "accepted_decision",

                "effect":
                    "deny",
            },
            {
                "id":
                    "policy:partial-target",

                "lifecycle_state":
                    "active",

                "authority_class":
                    "constitutional_canon",

                "effect":
                    "allow",
            },
        ],
        supersession=[
            {
                "id":
                    "supersession:partial",

                "kind":
                    "supersession",

                "source":
                    "policy:partial-source",

                "target":
                    "policy:partial-target",

                "coverage":
                    "partial",

                "scope":
                    {
                        "target":
                            "special-case"
                    },

                "resolution_owner":
                    "pryme",

                "accepted":
                    True,
            }
        ],
    )

    if (
        "policy:partial-source"
        not in partial[
            "eligible_policy_ids"
        ]
    ):
        raise living_policy_pipeline_error(
            (
                "partial supersession "
                "incorrectly removed "
                "source policy"
            )
        )

    unresolved = run(
        [
            {
                "id":
                    "policy:a",

                "lifecycle_state":
                    "active",

                "authority_class":
                    "constitutional_canon",

                "effect":
                    "allow",
            },
            {
                "id":
                    "policy:b",

                "lifecycle_state":
                    "active",

                "authority_class":
                    "constitutional_canon",

                "effect":
                    "allow",
            },
        ],
        supersession=[
            {
                "kind":
                    "supersession",

                "source":
                    "policy:a",

                "target":
                    "policy:b",

                "resolution_owner":
                    "living-governance",

                "accepted":
                    True,
            }
        ],
    )

    if (
        unresolved[
            "decision"
        ]
        != "authority-required"
    ):
        raise living_policy_pipeline_error(
            (
                "unresolved Pryme "
                "supersession did not "
                "block finality"
            )
        )

    pre_active = run(
        [
            {
                "id":
                    "policy:proposed",

                "lifecycle_state":
                    "proposed",

                "authority_class":
                    "accepted_decision",

                "effect":
                    "deny",
            },
            {
                "id":
                    "policy:active",

                "lifecycle_state":
                    "active",

                "authority_class":
                    "constitutional_canon",

                "effect":
                    "allow",
            },
        ]
    )

    if (
        pre_active[
            "decision"
        ]
        != "pass"
    ):
        raise living_policy_pipeline_error(
            (
                "pre-active policy "
                "participated in arbitration"
            )
        )

    source = [
        {
            "id":
                "policy:deterministic",

            "lifecycle_state":
                "active",

            "authority_class":
                "constitutional_canon",

            "effect":
                "allow",
        }
    ]

    before = digest(
        source
    )

    first = run(
        source
    )

    second = run(
        source
    )

    if first != second:
        raise living_policy_pipeline_error(
            "pipeline is not deterministic"
        )

    if (
        before
        != digest(
            source
        )
    ):
        raise living_policy_pipeline_error(
            "pipeline mutated source"
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

        (
            "legacy_policy_"
            "compatibility"
        ):
            True,

        "superseded_filtered":
            True,

        "retired_filtered":
            True,

        "pre_active_filtered":
            True,

        (
            "partial_supersession_"
            "preserved"
        ):
            True,

        (
            "unresolved_pryme_"
            "supersession_blocks_finality"
        ):
            True,

        "lifecycle_before_arbitration":
            True,

        "deterministic":
            True,

        "source_state_mutated":
            False,

        "authority_transfer":
            False,
    }


__all__ = [
    "lifecycle_eligibility",
    "living_policy_pipeline_error",
    "run",
    "selftest",
    "status",
]

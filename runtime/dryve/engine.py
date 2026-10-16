#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


ROOT = Path("/root/savant-runtime")

DEFAULT_INSTANCE = (
    ROOT
    / "runtime/dryve/instances/niche.json"
)


DRYVE_PIPELINE = (
    "admission",
    "identity_resolution",
    "authority_resolution",

    "intent_resolution",
    "eligibility_resolution",
    "dependency_resolution",

    "workflow_resolution",
    "activity_resolution",
    "retry_resolution",

    "execution_planning",
    "checkpoint_resolution",
    "commit_gate_resolution",

    "activity_execution",
    "outcome_resolution",
    "compensation_resolution",

    "replay_projection",
    "observability",
    "receipt_generation",
)


DRYVE_ABILITIES = (
    "execution_identity",
    "intent_projection",
    "eligibility_projection",

    "workflow_definition",
    "activity_composition",
    "dependency_ordering",

    "retry_policy",
    "backoff_calculation",
    "failure_classification",

    "checkpoint_projection",
    "resume_projection",
    "commit_gate",

    "activity_invocation",
    "outcome_capture",
    "compensation_planning",

    "execution_replay",
    "execution_receipt",
    "divergence_detection",
)


DRYVE_HEALTH_DIMENSIONS = (
    "instance_integrity",
    "identity_integrity",
    "workflow_integrity",

    "retry_integrity",
    "checkpoint_integrity",
    "compensation_integrity",

    "replay_integrity",
    "authority_boundary",
    "niche_opus_boundary",
)


DRYVE_VALIDATION_DIMENSIONS = (
    "identity",
    "authority",
    "intent",

    "eligibility",
    "dependencies",
    "workflow",

    "resilience",
    "replay",
    "integration",
)


DRYVE_PROJECTIONS = (
    "execution_plan",
    "eligibility_report",
    "checkpoint",

    "resume_state",
    "retry_report",
    "compensation_plan",

    "execution_outcome",
    "execution_receipt",
    "execution_health",
)


class DryveError(RuntimeError):
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
        canonical_json(value).encode(
            "utf-8"
        )
    ).hexdigest()


@dataclass(
    frozen=True,
    slots=True,
)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    multiplier: float = 2.0
    max_delay_seconds: float = 9.0

    def __post_init__(
        self,
    ) -> None:
        if self.max_attempts < 1:
            raise DryveError(
                "max_attempts must be positive"
            )

        if self.base_delay_seconds < 0:
            raise DryveError(
                "base delay must be non-negative"
            )

        if self.multiplier < 1:
            raise DryveError(
                "retry multiplier must be >= 1"
            )

        if self.max_delay_seconds < 0:
            raise DryveError(
                "max delay must be non-negative"
            )

    def delay_for_attempt(
        self,
        attempt: int,
    ) -> float:
        if attempt < 1:
            raise DryveError(
                "attempt must be positive"
            )

        delay = (
            self.base_delay_seconds
            * (
                self.multiplier
                ** max(
                    0,
                    attempt - 1,
                )
            )
        )

        return min(
            self.max_delay_seconds,
            delay,
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "max_attempts":
                self.max_attempts,
            "base_delay_seconds":
                self.base_delay_seconds,
            "multiplier":
                self.multiplier,
            "max_delay_seconds":
                self.max_delay_seconds,
        }


ActivityFunction = Callable[
    [Any],
    Any,
]


CompensationFunction = Callable[
    [Any],
    Any,
]


@dataclass(
    frozen=True,
    slots=True,
)
class Activity:
    activity_id: str
    executor: ActivityFunction
    compensation: (
        CompensationFunction
        | None
    ) = None
    retry: RetryPolicy = RetryPolicy()
    idempotency_key: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not self.activity_id.strip():
            raise DryveError(
                "activity_id is required"
            )

        if not callable(
            self.executor
        ):
            raise DryveError(
                "activity executor must be callable"
            )

        if (
            self.compensation
            is not None
            and not callable(
                self.compensation
            )
        ):
            raise DryveError(
                "compensation must be callable"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ExecutionPlan:
    plan_id: str
    intent: Mapping[str, Any]
    activities: tuple[str, ...]
    dependencies: tuple[str, ...]
    commit_allowed: bool
    authoritative: bool = False

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "plan_id":
                self.plan_id,
            "intent":
                dict(
                    self.intent
                ),
            "activities":
                list(
                    self.activities
                ),
            "dependencies":
                list(
                    self.dependencies
                ),
            "commit_allowed":
                self.commit_allowed,
            "authoritative":
                False,
            "task_authority":
                False,
            "ai_execution_authority":
                False,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


class Dryve:
    schema = (
        "savant://runtime/"
        "dryve/1.0.0"
    )

    substrate_id = (
        "living:dryve"
    )

    def __init__(
        self,
        instance_path:
            Path = DEFAULT_INSTANCE,
    ) -> None:
        if not instance_path.is_absolute():
            raise DryveError(
                "instance path must be absolute"
            )

        self.instance_path = (
            instance_path.resolve()
        )

        self.instance = (
            self._load_json(
                self.instance_path
            )
        )

        self._validate_instance()

        self._activities: dict[
            str,
            Activity,
        ] = {}

        self._receipts: dict[
            str,
            dict[str, Any],
        ] = {}

    @staticmethod
    def _load_json(
        path: Path,
    ) -> dict[str, Any]:
        if not path.is_file():
            raise DryveError(
                f"missing file: {path}"
            )

        try:
            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as exc:
            raise DryveError(
                f"invalid JSON: {path}: {exc}"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise DryveError(
                f"invalid object: {path}"
            )

        return payload

    def _validate_instance(
        self,
    ) -> None:
        if (
            self.instance.get(
                "substrate"
            )
            != "dryve"
        ):
            raise DryveError(
                "invalid Dryve substrate"
            )

        for key in (
            "authoritative",
            "task_authority_owned",
            "ai_execution_owned",
            "durable_commit_authorized",
        ):
            if (
                self.instance.get(
                    key
                )
                is not False
            ):
                raise DryveError(
                    f"{key} must remain false"
                )

        policy = (
            self.instance.get(
                "policy",
                {},
            )
        )

        if len(policy) != 9:
            raise DryveError(
                "Dryve policy must contain "
                "9 controls"
            )

        if not all(
            isinstance(
                value,
                bool,
            )
            for value
            in policy.values()
        ):
            raise DryveError(
                "Dryve policy controls "
                "must be boolean"
            )

        groups = (
            self.instance.get(
                "enhancement_groups",
                {},
            )
        )

        if len(groups) != 9:
            raise DryveError(
                "Dryve requires "
                "9 enhancement groups"
            )

        for name, values in (
            groups.items()
        ):
            if (
                not isinstance(
                    values,
                    list,
                )
                or len(values) != 3
                or not all(
                    isinstance(
                        value,
                        str,
                    )
                    and value.strip()
                    for value in values
                )
            ):
                raise DryveError(
                    f"{name} must contain "
                    "exactly 3 enhancements"
                )

    @property
    def enhancement_count(
        self,
    ) -> int:
        return sum(
            len(values)
            for values
            in self.instance[
                "enhancement_groups"
            ].values()
        )

    def register(
        self,
        activity: Activity,
    ) -> None:
        if (
            activity.activity_id
            in self._activities
        ):
            raise DryveError(
                "duplicate activity: "
                + activity.activity_id
            )

        self._activities[
            activity.activity_id
        ] = activity

    def activities(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return tuple(
            sorted(
                self._activities
            )
        )

    def eligible(
        self,
        *,
        intent:
            Mapping[str, Any],
        required_authorization:
            bool,
        authorization_present:
            bool,
        dependencies_ready:
            bool,
    ) -> dict[str, Any]:
        reasons: list[str] = []

        if not intent:
            reasons.append(
                "intent is empty"
            )

        if (
            required_authorization
            and not authorization_present
        ):
            reasons.append(
                "required authorization "
                "is absent"
            )

        if not dependencies_ready:
            reasons.append(
                "dependencies are not ready"
            )

        eligible = not reasons

        payload = {
            "schema": (
                "savant://runtime/"
                "dryve/eligibility/1.0.0"
            ),
            "eligible":
                eligible,
            "reasons":
                reasons,
            "authority_interpreted":
                False,
            "authorization_supplied_by_owner":
                authorization_present,
            "authoritative":
                False,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def plan(
        self,
        *,
        intent:
            Mapping[str, Any],
        activity_ids:
            Sequence[str],
        dependencies:
            Sequence[str] = (),
        commit_allowed:
            bool = False,
    ) -> ExecutionPlan:
        if not intent:
            raise DryveError(
                "intent is required"
            )

        if not activity_ids:
            raise DryveError(
                "at least one activity is required"
            )

        missing = [
            activity_id
            for activity_id
            in activity_ids
            if activity_id
            not in self._activities
        ]

        if missing:
            raise DryveError(
                "unknown activities: "
                + ", ".join(
                    missing
                )
            )

        activities = tuple(
            activity_ids
        )

        dependency_values = tuple(
            sorted(
                {
                    str(value).strip()
                    for value
                    in dependencies
                    if str(value).strip()
                }
            )
        )

        material = {
            "intent":
                dict(intent),
            "activities":
                activities,
            "dependencies":
                dependency_values,
            "commit_allowed":
                bool(
                    commit_allowed
                ),
            "instance":
                self.instance[
                    "instance_id"
                ],
        }

        plan_id = (
            "dryve-plan:"
            + digest(
                material
            )[:24]
        )

        return ExecutionPlan(
            plan_id=plan_id,
            intent=dict(
                intent
            ),
            activities=activities,
            dependencies=(
                dependency_values
            ),
            commit_allowed=bool(
                commit_allowed
            ),
        )

    @staticmethod
    def _classify_failure(
        exc: Exception,
    ) -> str:
        if isinstance(
            exc,
            (
                ValueError,
                TypeError,
                KeyError,
            ),
        ):
            return "deterministic"

        if isinstance(
            exc,
            (
                TimeoutError,
                ConnectionError,
            ),
        ):
            return "transient"

        return "unknown"

    def _invoke_activity(
        self,
        activity: Activity,
        value: Any,
    ) -> dict[str, Any]:
        attempts: list[
            dict[str, Any]
        ] = []

        for attempt in range(
            1,
            activity.retry.max_attempts
            + 1,
        ):
            try:
                result = (
                    activity.executor(
                        value
                    )
                )

                attempts.append(
                    {
                        "attempt":
                            attempt,
                        "status":
                            "passed",
                    }
                )

                return {
                    "status":
                        "passed",
                    "result":
                        result,
                    "attempts":
                        attempts,
                }

            except Exception as exc:
                failure_class = (
                    self
                    ._classify_failure(
                        exc
                    )
                )

                attempts.append(
                    {
                        "attempt":
                            attempt,
                        "status":
                            "failed",
                        "failure_class":
                            failure_class,
                        "exception":
                            type(
                                exc
                            ).__name__,
                        "message":
                            str(exc),
                        "next_delay_seconds": (
                            activity
                            .retry
                            .delay_for_attempt(
                                attempt
                            )
                            if attempt
                            < activity
                            .retry
                            .max_attempts
                            else None
                        ),
                    }
                )

                if (
                    failure_class
                    == "deterministic"
                ):
                    break

        return {
            "status":
                "failed",
            "result":
                None,
            "attempts":
                attempts,
        }

    def checkpoint(
        self,
        *,
        plan:
            ExecutionPlan,
        ordinal: int,
        value: Any,
        completed:
            Sequence[str],
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://runtime/"
                "dryve/checkpoint/1.0.0"
            ),
            "plan_id":
                plan.plan_id,
            "ordinal":
                ordinal,
            "value":
                value,
            "completed":
                list(
                    completed
                ),
            "persistent":
                False,
            "authoritative":
                False,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def compensate(
        self,
        *,
        completed:
            Sequence[
                tuple[
                    Activity,
                    Any,
                ]
            ],
    ) -> dict[str, Any]:
        outcomes: list[
            dict[str, Any]
        ] = []

        for activity, value in (
            reversed(
                completed
            )
        ):
            if (
                activity.compensation
                is None
            ):
                outcomes.append(
                    {
                        "activity_id":
                            activity
                            .activity_id,
                        "status":
                            "skipped",
                    }
                )

                continue

            try:
                result = (
                    activity
                    .compensation(
                        value
                    )
                )

                outcomes.append(
                    {
                        "activity_id":
                            activity
                            .activity_id,
                        "status":
                            "passed",
                        "result":
                            result,
                    }
                )

            except Exception as exc:
                outcomes.append(
                    {
                        "activity_id":
                            activity
                            .activity_id,
                        "status":
                            "failed",
                        "exception":
                            type(
                                exc
                            ).__name__,
                        "message":
                            str(exc),
                    }
                )

        payload = {
            "schema": (
                "savant://runtime/"
                "dryve/compensation/1.0.0"
            ),
            "outcomes":
                outcomes,
            "complete": all(
                outcome[
                    "status"
                ]
                in (
                    "passed",
                    "skipped",
                )
                for outcome
                in outcomes
            ),
            "authoritative":
                False,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def execute(
        self,
        plan: ExecutionPlan,
        *,
        initial: Any = None,
        owner_commit_authorized:
            bool = False,
    ) -> dict[str, Any]:
        if (
            self.instance[
                "policy"
            ][
                "commit_gate_required"
            ]
            and plan.commit_allowed
            and not owner_commit_authorized
        ):
            raise DryveError(
                "owner commit authorization "
                "is required"
            )

        current = initial

        completed: list[
            tuple[
                Activity,
                Any,
            ]
        ] = []

        checkpoints: list[
            dict[str, Any]
        ] = []

        activity_results: list[
            dict[str, Any]
        ] = []

        failure: (
            dict[str, Any]
            | None
        ) = None

        for ordinal, activity_id in (
            enumerate(
                plan.activities,
                start=1,
            )
        ):
            activity = (
                self._activities[
                    activity_id
                ]
            )

            input_value = current

            outcome = (
                self._invoke_activity(
                    activity,
                    current,
                )
            )

            activity_result = {
                "ordinal":
                    ordinal,
                "activity_id":
                    activity_id,
                **outcome,
            }

            activity_results.append(
                activity_result
            )

            if (
                outcome[
                    "status"
                ]
                != "passed"
            ):
                failure = (
                    activity_result
                )
                break

            current = outcome[
                "result"
            ]

            completed.append(
                (
                    activity,
                    input_value,
                )
            )

            checkpoints.append(
                self.checkpoint(
                    plan=plan,
                    ordinal=ordinal,
                    value=current,
                    completed=[
                        item[
                            0
                        ].activity_id
                        for item
                        in completed
                    ],
                )
            )

        compensation = None

        if (
            failure is not None
            and self.instance[
                "policy"
            ][
                "compensation_enabled"
            ]
        ):
            compensation = (
                self.compensate(
                    completed=completed
                )
            )

        status = (
            "passed"
            if failure is None
            else "failed"
        )

        receipt_material = {
            "plan":
                plan.projection(),
            "activities":
                activity_results,
            "checkpoints":
                checkpoints,
            "status":
                status,
            "result":
                current,
            "failure":
                failure,
            "compensation":
                compensation,
            "owner_commit_authorized":
                owner_commit_authorized,
        }

        receipt_id = (
            "dryve-receipt:"
            + digest(
                receipt_material
            )[:24]
        )

        payload = {
            "schema": (
                "savant://runtime/"
                "dryve/receipt/1.0.0"
            ),
            "receipt_id":
                receipt_id,
            "plan_id":
                plan.plan_id,
            "status":
                status,
            "activities":
                activity_results,
            "checkpoints":
                checkpoints,
            "result":
                current,
            "failure":
                failure,
            "compensation":
                compensation,
            "owner_commit_authorized":
                owner_commit_authorized,
            "task_authority":
                False,
            "ai_execution_authority":
                False,
            "durable_commit_authority":
                False,
            "authoritative":
                False,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        self._receipts[
            receipt_id
        ] = payload

        return payload

    def replay(
        self,
        receipt:
            Mapping[str, Any],
    ) -> dict[str, Any]:
        material = {
            key:
                receipt.get(
                    key
                )
            for key in (
                "plan_id",
                "status",
                "activities",
                "checkpoints",
                "result",
                "failure",
                "compensation",
                "owner_commit_authorized",
                "task_authority",
                "ai_execution_authority",
                "durable_commit_authority",
                "authoritative",
            )
        }

        rebuilt = dict(
            receipt
        )

        expected = (
            receipt.get(
                "digest"
            )
        )

        actual = digest(
            {
                key:
                    value
                for key, value
                in rebuilt.items()
                if key != "digest"
            }
        )

        payload = {
            "schema": (
                "savant://runtime/"
                "dryve/replay/1.0.0"
            ),
            "receipt_id":
                receipt.get(
                    "receipt_id"
                ),
            "material":
                material,
            "expected_digest":
                expected,
            "actual_digest":
                actual,
            "diverged": (
                expected
                != actual
            ),
            "authoritative":
                False,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def health(
        self,
    ) -> dict[str, Any]:
        policy = (
            self.instance[
                "policy"
            ]
        )

        dimensions = {
            "instance_integrity":
                True,
            "identity_integrity":
                True,
            "workflow_integrity":
                True,
            "retry_integrity":
                policy[
                    "retry_bounded"
                ],
            "checkpoint_integrity":
                policy[
                    "checkpoint_enabled"
                ],
            "compensation_integrity":
                policy[
                    "compensation_enabled"
                ],
            "replay_integrity":
                policy[
                    "replay_enabled"
                ],
            "authority_boundary": (
                self.instance[
                    "authoritative"
                ]
                is False
                and self.instance[
                    "durable_commit_authorized"
                ]
                is False
            ),
            "niche_opus_boundary": (
                self.instance[
                    "task_authority_owned"
                ]
                is False
                and self.instance[
                    "ai_execution_owned"
                ]
                is False
            ),
        }

        payload = {
            "schema": (
                "savant://runtime/"
                "dryve/health/1.0.0"
            ),
            "dimensions": {
                name: {
                    "healthy":
                        bool(value)
                }
                for name, value
                in dimensions.items()
            },
            "healthy": all(
                dimensions.values()
            ),
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def validate(
        self,
    ) -> dict[str, Any]:
        checks = {
            "abilities": (
                len(
                    DRYVE_ABILITIES
                )
                == 18
            ),
            "pipeline": (
                len(
                    DRYVE_PIPELINE
                )
                == 18
            ),
            "health_dimensions": (
                len(
                    DRYVE_HEALTH_DIMENSIONS
                )
                == 9
            ),
            "validation_dimensions": (
                len(
                    DRYVE_VALIDATION_DIMENSIONS
                )
                == 9
            ),
            "projections": (
                len(
                    DRYVE_PROJECTIONS
                )
                == 9
            ),
            "enhancements": (
                self.enhancement_count
                == 27
            ),
            "task_boundary": (
                self.instance[
                    "task_authority_owned"
                ]
                is False
            ),
            "opus_boundary": (
                self.instance[
                    "ai_execution_owned"
                ]
                is False
            ),
            "commit_boundary": (
                self.instance[
                    "durable_commit_authorized"
                ]
                is False
            ),
        }

        payload = {
            "schema": (
                "savant://assurance/"
                "dryve/1.0.0"
            ),
            "valid": all(
                checks.values()
            ),
            "checks":
                checks,
            "ability_count":
                18,
            "pipeline_stage_count":
                18,
            "health_dimension_count":
                9,
            "validation_dimension_count":
                9,
            "projection_count":
                9,
            "enhancement_count":
                27,
            "task_authority_owned":
                False,
            "ai_execution_owned":
                False,
            "durable_commit_authorized":
                False,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def profile(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema":
                self.schema,
            "substrate_id":
                self.substrate_id,
            "name":
                "Dryve",
            "role": (
                "living execution-lifecycle "
                "substrate"
            ),
            "instance":
                self.instance,
            "abilities":
                list(
                    DRYVE_ABILITIES
                ),
            "pipeline":
                list(
                    DRYVE_PIPELINE
                ),
            "health_dimensions":
                list(
                    DRYVE_HEALTH_DIMENSIONS
                ),
            "validation_dimensions":
                list(
                    DRYVE_VALIDATION_DIMENSIONS
                ),
            "projections":
                list(
                    DRYVE_PROJECTIONS
                ),
            "enhancement_count":
                self.enhancement_count,
            "task_owner":
                "exile:niche",
            "ai_execution_owner":
                "exile:opus",
            "task_authority_owned":
                False,
            "ai_execution_owned":
                False,
            "durable_commit_authorized":
                False,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path("/root/savant-runtime")

GRAPH_PATH = (
    ROOT
    / "authority"
    / "task-graph"
    / "masterplan.json"
)

POLICY_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "policies"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "policies"
)

RUNTIME_ROOT = (
    ROOT
    / "runtime"
    / "masterplan"
    / "policies"
)

VOLATILE_FIELDS = {
    "generated_at",
    "created_at",
    "captured_at",
    "accepted_at",
    "occurred_at",
    "issued_at",
    "expires_at",
    "timestamp",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
}

ACCEPTED_AUTHORITY_STATES = {
    "accepted",
    "authoritative",
}

TERMINAL_STATES = {
    "completed",
    "archived",
    "superseded",
}

KNOWN_POLICY_KINDS = {
    "admission",
    "selection",
    "transition",
    "completion",
    "mutation",
    "projection",
    "security",
    "replay",
    "migration",
    "attestation",
}


class PolicyError(RuntimeError):
    pass


class PolicyValidationError(PolicyError):
    pass


class PolicyEvaluationError(PolicyError):
    pass


@dataclass(frozen=True)
class PolicyDecision:
    policy_id: str
    passed: bool
    code: str
    reason: str
    facts: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "passed": self.passed,
            "code": self.code,
            "reason": self.reason,
            "facts": self.facts,
        }


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def deterministic_projection(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: deterministic_projection(child)
            for key, child in sorted(
                value.items(),
                key=lambda item: item[0],
            )
            if key not in VOLATILE_FIELDS
        }

    if isinstance(value, list):
        return [
            deterministic_projection(child)
            for child in value
        ]

    if isinstance(value, tuple):
        return tuple(
            deterministic_projection(child)
            for child in value
        )

    return value


def semantic_digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_bytes(
            deterministic_projection(value)
        )
    ).hexdigest()


def sha256_path(path: Path) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(value, dict):
        raise PolicyValidationError(
            f"Expected JSON object: {path}"
        )

    return value


def atomic_write_text(
    path: Path,
    value: str,
    mode: int = 0o644,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )

    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(
            temporary_path,
            mode,
        )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_write_json(
    path: Path,
    value: Any,
) -> None:
    atomic_write_text(
        path,
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


def relative_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()

    except ValueError:
        return str(path)


def task_map(
    graph: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    values = graph.get(
        "records",
        [],
    )

    if not isinstance(values, list):
        raise PolicyValidationError(
            "Task graph records are invalid."
        )

    result: dict[str, dict[str, Any]] = {}

    for record in values:
        if not isinstance(record, dict):
            raise PolicyValidationError(
                "Task graph contains an invalid task."
            )

        identifier = record.get("id")

        if not isinstance(identifier, str):
            raise PolicyValidationError(
                "Task record has no string identity."
            )

        if identifier in result:
            raise PolicyValidationError(
                f"Duplicate task identity: {identifier}"
            )

        result[identifier] = record

    return result


def dependency_map(
    graph: dict[str, Any],
) -> dict[str, set[str]]:
    tasks = task_map(graph)

    result = {
        task_id: set()
        for task_id in tasks
    }

    segues = graph.get(
        "segues",
        [],
    )

    if not isinstance(segues, list):
        raise PolicyValidationError(
            "Task graph segues are invalid."
        )

    for segue in segues:
        if not isinstance(segue, dict):
            continue

        if segue.get("type") != "depends_on":
            continue

        source = segue.get("source")
        target = segue.get("target")

        if (
            isinstance(source, str)
            and isinstance(target, str)
            and source in tasks
            and target in tasks
        ):
            result[source].add(target)

    return result


def evidence_for_task(
    graph: dict[str, Any],
    task_id: str,
) -> list[dict[str, Any]]:
    values = graph.get(
        "evidence",
        [],
    )

    if not isinstance(values, list):
        raise PolicyValidationError(
            "Task graph evidence is invalid."
        )

    return [
        value
        for value in values
        if (
            isinstance(value, dict)
            and value.get("task_id")
            == task_id
        )
    ]


def attestations_for_task(
    graph: dict[str, Any],
    task_id: str,
) -> list[dict[str, Any]]:
    values = graph.get(
        "attestations",
        [],
    )

    if not isinstance(values, list):
        raise PolicyValidationError(
            "Task graph attestations are invalid."
        )

    return [
        value
        for value in values
        if (
            isinstance(value, dict)
            and value.get("task_id")
            == task_id
        )
    ]


def validate_authority(
    authority: Any,
) -> None:
    if not isinstance(authority, dict):
        raise PolicyValidationError(
            "Policy authority must be an object."
        )

    if authority.get("state") not in {
        "unknown",
        "observed",
        "proposed",
        "accepted",
        "authoritative",
        "rejected",
        "superseded",
    }:
        raise PolicyValidationError(
            "Policy authority state is invalid."
        )

    if not isinstance(
        authority.get("tier"),
        int,
    ):
        raise PolicyValidationError(
            "Policy authority tier is invalid."
        )


def validate_policy(
    policy: dict[str, Any],
) -> dict[str, Any]:
    required = {
        "id",
        "kind",
        "version",
        "title",
        "description",
        "authority",
        "effect",
        "conditions",
        "failure",
        "provenance",
    }

    missing = sorted(
        required
        - set(policy)
    )

    if missing:
        raise PolicyValidationError(
            "Policy missing fields: "
            + ", ".join(missing)
        )

    policy_id = policy["id"]

    if (
        not isinstance(policy_id, str)
        or not policy_id.startswith(
            "policy.masterplan."
        )
    ):
        raise PolicyValidationError(
            "Policy identity is invalid."
        )

    kind = policy["kind"]

    if kind not in KNOWN_POLICY_KINDS:
        raise PolicyValidationError(
            f"Unknown policy kind: {kind}"
        )

    if policy["effect"] not in {
        "allow",
        "deny",
        "require",
    }:
        raise PolicyValidationError(
            "Policy effect is invalid."
        )

    conditions = policy["conditions"]

    if not isinstance(conditions, list):
        raise PolicyValidationError(
            "Policy conditions must be a list."
        )

    for condition in conditions:
        if not isinstance(condition, dict):
            raise PolicyValidationError(
                "Policy condition must be an object."
            )

        if condition.get("operator") not in {
            "equals",
            "not_equals",
            "in",
            "not_in",
            "exists",
            "truthy",
            "falsy",
            "greater_or_equal",
            "less_or_equal",
            "contains",
            "subset",
        }:
            raise PolicyValidationError(
                "Policy condition operator is invalid."
            )

        if not isinstance(
            condition.get("fact"),
            str,
        ):
            raise PolicyValidationError(
                "Policy condition fact is invalid."
            )

    validate_authority(
        policy["authority"]
    )

    return {
        "passed": True,
        "policy_id": policy_id,
        "semantic_digest": (
            semantic_digest(policy)
        ),
    }


def fact_value(
    facts: dict[str, Any],
    path: str,
) -> Any:
    current: Any = facts

    for component in path.split("."):
        if not isinstance(current, dict):
            return None

        if component not in current:
            return None

        current = current[component]

    return current


def evaluate_condition(
    condition: dict[str, Any],
    facts: dict[str, Any],
) -> bool:
    actual = fact_value(
        facts,
        condition["fact"],
    )

    expected = condition.get("value")
    operator = condition["operator"]

    if operator == "equals":
        return actual == expected

    if operator == "not_equals":
        return actual != expected

    if operator == "in":
        return (
            isinstance(expected, list)
            and actual in expected
        )

    if operator == "not_in":
        return (
            isinstance(expected, list)
            and actual not in expected
        )

    if operator == "exists":
        return actual is not None

    if operator == "truthy":
        return bool(actual)

    if operator == "falsy":
        return not bool(actual)

    if operator == "greater_or_equal":
        try:
            return actual >= expected
        except TypeError:
            return False

    if operator == "less_or_equal":
        try:
            return actual <= expected
        except TypeError:
            return False

    if operator == "contains":
        try:
            return expected in actual
        except TypeError:
            return False

    if operator == "subset":
        if not isinstance(
            actual,
            (list, set, tuple),
        ):
            return False

        if not isinstance(
            expected,
            (list, set, tuple),
        ):
            return False

        return set(actual).issubset(
            set(expected)
        )

    raise PolicyEvaluationError(
        f"Unsupported operator: {operator}"
    )


def evaluate_policy(
    policy: dict[str, Any],
    facts: dict[str, Any],
) -> PolicyDecision:
    validate_policy(policy)

    results = [
        evaluate_condition(
            condition,
            facts,
        )
        for condition in policy[
            "conditions"
        ]
    ]

    mode = policy.get(
        "condition_mode",
        "all",
    )

    if mode == "all":
        matched = all(results)

    elif mode == "any":
        matched = any(results)

    else:
        raise PolicyValidationError(
            f"Unknown condition mode: {mode}"
        )

    effect = policy["effect"]

    if effect == "allow":
        passed = matched

    elif effect == "deny":
        passed = not matched

    elif effect == "require":
        passed = matched

    else:
        raise PolicyEvaluationError(
            f"Unknown policy effect: {effect}"
        )

    failure = policy.get(
        "failure",
        {},
    )

    code = (
        "masterplan.policy.passed"
        if passed
        else str(
            failure.get(
                "code",
                "masterplan.policy.denied",
            )
        )
    )

    reason = (
        str(
            policy.get(
                "success_reason",
                "Policy conditions passed.",
            )
        )
        if passed
        else str(
            failure.get(
                "message",
                "Policy conditions failed.",
            )
        )
    )

    return PolicyDecision(
        policy_id=policy["id"],
        passed=passed,
        code=code,
        reason=reason,
        facts=facts,
    )


def policy_files() -> tuple[Path, ...]:
    if not POLICY_ROOT.is_dir():
        return ()

    return tuple(
        sorted(
            (
                path
                for path in POLICY_ROOT.glob(
                    "*.json"
                )
                if path.is_file()
                and path.name
                not in {
                    "registry.json",
                    "latest-evaluation.json",
                }
            ),
            key=lambda path: path.name,
        )
    )


def load_policies() -> tuple[
    dict[str, Any],
    ...,
]:
    policies = [
        load_json(path)
        for path in policy_files()
    ]

    identities: set[str] = set()

    for policy in policies:
        validate_policy(policy)

        identifier = policy["id"]

        if identifier in identities:
            raise PolicyValidationError(
                f"Duplicate policy: {identifier}"
            )

        identities.add(identifier)

    return tuple(
        sorted(
            policies,
            key=lambda value: (
                value["kind"],
                value["id"],
            ),
        )
    )


def build_registry(
    policies: Iterable[
        dict[str, Any]
    ],
) -> dict[str, Any]:
    ordered_policies = sorted(
        list(policies),
        key=lambda policy: (
            str(
                policy.get(
                    "kind",
                    "",
                )
            ),
            str(
                policy.get(
                    "id",
                    "",
                )
            ),
            str(
                policy.get(
                    "version",
                    "",
                )
            ),
        ),
    )

    records = [
        {
            "id": policy["id"],
            "kind": policy["kind"],
            "version": policy["version"],
            "title": policy["title"],
            "authority": policy[
                "authority"
            ],
            "effect": policy["effect"],
            "path": relative_path(
                POLICY_ROOT
                / (
                    policy["id"]
                    .replace(".", "__")
                    + ".json"
                )
            ),
            "semantic_digest": (
                semantic_digest(policy)
            ),
        }
        for policy in ordered_policies
    ]

    registry: dict[str, Any] = {
        "schema": (
            "savant://niche/masterplan/"
            "policy-registry/1.0.0"
        ),
        "registry_id": (
            "registry.masterplan.policies"
        ),
        "policies": records,
        "statistics": {
            "policy_count": len(records),
            "kind_counts": {
                kind: sum(
                    record["kind"] == kind
                    for record in records
                )
                for kind in sorted(
                    KNOWN_POLICY_KINDS
                )
            },
        },
        "generated_at": utc_now(),
    }

    registry["semantic_digest"] = (
        semantic_digest(registry)
    )

    return registry

def unresolved_dependencies(
    graph: dict[str, Any],
    task_id: str,
) -> list[str]:
    tasks = task_map(graph)

    dependencies = dependency_map(
        graph
    ).get(
        task_id,
        set(),
    )

    return sorted(
        dependency
        for dependency in dependencies
        if (
            dependency not in tasks
            or tasks[
                dependency
            ].get(
                "status"
            )
            not in TERMINAL_STATES
        )
    )


def build_task_facts(
    graph: dict[str, Any],
    task_id: str,
    operation: str,
) -> dict[str, Any]:
    tasks = task_map(graph)

    if task_id not in tasks:
        raise KeyError(
            f"Unknown task: {task_id}"
        )

    task = tasks[task_id]

    authority = task.get(
        "authority",
        {},
    )

    passing_evidence = [
        evidence
        for evidence
        in evidence_for_task(
            graph,
            task_id,
        )
        if evidence.get("passed")
        is True
    ]

    passing_attestations = [
        attestation
        for attestation
        in attestations_for_task(
            graph,
            task_id,
        )
        if attestation.get("passed")
        is True
    ]

    outputs = task.get(
        "outputs",
        [],
    )

    if not isinstance(outputs, list):
        outputs = []

    acceptance = task.get(
        "acceptance",
        [],
    )

    if not isinstance(acceptance, list):
        acceptance = []

    unresolved = unresolved_dependencies(
        graph,
        task_id,
    )

    return {
        "operation": operation,
        "task": {
            "id": task_id,
            "status": task.get("status"),
            "authority_state": (
                authority.get("state")
                if isinstance(
                    authority,
                    dict,
                )
                else None
            ),
            "authority_tier": (
                authority.get("tier")
                if isinstance(
                    authority,
                    dict,
                )
                else None
            ),
            "priority_band": (
                (
                    task.get("priority")
                    or {}
                ).get("band")
                if isinstance(
                    task.get("priority"),
                    dict,
                )
                else None
            ),
            "output_count": len(outputs),
            "acceptance_count": len(
                acceptance
            ),
            "unresolved_dependencies": (
                unresolved
            ),
            "dependency_ready": (
                not unresolved
            ),
            "passing_evidence_count": (
                len(passing_evidence)
            ),
            "passing_attestation_count": (
                len(
                    passing_attestations
                )
            ),
            "has_passing_attestation": (
                bool(
                    passing_attestations
                )
            ),
        },
        "graph": {
            "schema_version": graph.get(
                "schema_version"
            ),
            "semantic_digest": (
                semantic_digest(graph)
            ),
        },
    }


def evaluate_operation(
    policies: Iterable[
        dict[str, Any]
    ],
    facts: dict[str, Any],
    operation: str,
) -> dict[str, Any]:
    applicable = [
        policy
        for policy in policies
        if operation in policy.get(
            "operations",
            [],
        )
    ]

    decisions = [
        evaluate_policy(
            policy,
            facts,
        )
        for policy in applicable
    ]

    passed = all(
        decision.passed
        for decision in decisions
    )

    result: dict[str, Any] = {
        "schema": (
            "savant://niche/masterplan/"
            "policy-evaluation/1.0.0"
        ),
        "operation": (
            "evaluate_masterplan_policies"
        ),
        "evaluated_operation": (
            operation
        ),
        "passed": passed,
        "facts": facts,
        "decisions": [
            decision.to_dict()
            for decision in decisions
        ],
        "statistics": {
            "applicable_policy_count": (
                len(applicable)
            ),
            "passed_policy_count": sum(
                decision.passed
                for decision in decisions
            ),
            "failed_policy_count": sum(
                not decision.passed
                for decision in decisions
            ),
        },
        "generated_at": utc_now(),
    }

    result["semantic_digest"] = (
        semantic_digest(result)
    )

    return result


def seed_authority() -> dict[str, Any]:
    return {
        "state": "accepted",
        "authority_class": (
            "project-owner-directed"
        ),
        "tier": 1,
        "source": (
            "docs/SAVANT_MASTER_TASKS.md"
        ),
        "accepted_by": "project-owner",
        "accepted_at": (
            "2026-08-01T22:03:54-04:00"
        ),
        "confidence": 1.0,
    }


def provenance() -> dict[str, Any]:
    return {
        "sources": [
            {
                "source_id": (
                    "docs/SAVANT_MASTER_TASKS.md"
                ),
                "source_kind": (
                    "accepted-masterplan-specification"
                ),
                "source_path": (
                    "docs/SAVANT_MASTER_TASKS.md"
                ),
                "authority_state": "accepted",
            }
        ],
        "transformations": [
            "masterplan_law_to_policy_record"
        ],
        "generated_by": (
            "prodigal.niche.masterplan."
            "masterplan_policy_runtime"
        ),
        "generated_at": (
            "2026-08-02T09:37:00-04:00"
        ),
        "contract_version": "1.0.0",
    }


def policy_record(
    *,
    policy_id: str,
    kind: str,
    title: str,
    description: str,
    effect: str,
    operations: list[str],
    conditions: list[
        dict[str, Any]
    ],
    failure_code: str,
    failure_message: str,
) -> dict[str, Any]:
    policy: dict[str, Any] = {
        "schema": (
            "savant://niche/masterplan/"
            "policy/1.0.0"
        ),
        "id": policy_id,
        "kind": kind,
        "version": "1.0.0",
        "title": title,
        "description": description,
        "authority": seed_authority(),
        "effect": effect,
        "condition_mode": "all",
        "operations": operations,
        "conditions": conditions,
        "failure": {
            "code": failure_code,
            "message": failure_message,
        },
        "provenance": provenance(),
        "extensions": {},
    }

    policy["semantic_digest"] = (
        semantic_digest(policy)
    )

    return policy


def default_policies() -> tuple[
    dict[str, Any],
    ...,
]:
    return (
        policy_record(
            policy_id=(
                "policy.masterplan."
                "task-authority-required"
            ),
            kind="admission",
            title=(
                "Accepted Task Authority Required"
            ),
            description=(
                "Executable task operations require "
                "accepted or authoritative task authority."
            ),
            effect="require",
            operations=[
                "task.activate",
                "task.complete",
                "task.mutate",
                "task.execute",
            ],
            conditions=[
                {
                    "fact": (
                        "task.authority_state"
                    ),
                    "operator": "in",
                    "value": [
                        "accepted",
                        "authoritative",
                    ],
                }
            ],
            failure_code=(
                "masterplan.policy."
                "task_authority_required"
            ),
            failure_message=(
                "Task authority is not accepted."
            ),
        ),
        policy_record(
            policy_id=(
                "policy.masterplan."
                "dependencies-complete"
            ),
            kind="selection",
            title=(
                "Dependencies Must Be Complete"
            ),
            description=(
                "Task activation and execution require "
                "all declared dependencies to be terminal."
            ),
            effect="require",
            operations=[
                "task.activate",
                "task.execute",
                "task.complete",
            ],
            conditions=[
                {
                    "fact": (
                        "task.dependency_ready"
                    ),
                    "operator": "truthy",
                }
            ],
            failure_code=(
                "masterplan.policy."
                "dependencies_incomplete"
            ),
            failure_message=(
                "Task has unresolved dependencies."
            ),
        ),
        policy_record(
            policy_id=(
                "policy.masterplan."
                "completion-evidence-required"
            ),
            kind="completion",
            title=(
                "Completion Evidence Required"
            ),
            description=(
                "Task completion requires at least one "
                "passing evidence record."
            ),
            effect="require",
            operations=[
                "task.complete",
            ],
            conditions=[
                {
                    "fact": (
                        "task.passing_evidence_count"
                    ),
                    "operator": (
                        "greater_or_equal"
                    ),
                    "value": 1,
                }
            ],
            failure_code=(
                "masterplan.policy."
                "completion_evidence_missing"
            ),
            failure_message=(
                "Task completion has no passing evidence."
            ),
        ),
        policy_record(
            policy_id=(
                "policy.masterplan."
                "completion-attestation-required"
            ),
            kind="attestation",
            title=(
                "Completion Attestation Required"
            ),
            description=(
                "Task completion requires a passing "
                "criterion-level attestation."
            ),
            effect="require",
            operations=[
                "task.complete",
            ],
            conditions=[
                {
                    "fact": (
                        "task.has_passing_attestation"
                    ),
                    "operator": "truthy",
                }
            ],
            failure_code=(
                "masterplan.policy."
                "completion_attestation_missing"
            ),
            failure_message=(
                "Task completion has no passing attestation."
            ),
        ),
        policy_record(
            policy_id=(
                "policy.masterplan."
                "terminal-task-mutation-denied"
            ),
            kind="mutation",
            title=(
                "Terminal Task Mutation Denied"
            ),
            description=(
                "Terminal task records cannot be "
                "mutated without explicit reopening "
                "or supersession authority."
            ),
            effect="deny",
            operations=[
                "task.mutate",
                "task.activate",
            ],
            conditions=[
                {
                    "fact": "task.status",
                    "operator": "in",
                    "value": sorted(
                        TERMINAL_STATES
                    ),
                }
            ],
            failure_code=(
                "masterplan.policy."
                "terminal_task_mutation_denied"
            ),
            failure_message=(
                "Terminal task mutation is denied."
            ),
        ),
        policy_record(
            policy_id=(
                "policy.masterplan."
                "graph-schema-required"
            ),
            kind="security",
            title=(
                "Graph Schema Version Required"
            ),
            description=(
                "Policy-governed operations require "
                "an explicit graph schema version."
            ),
            effect="require",
            operations=[
                "task.activate",
                "task.complete",
                "task.mutate",
                "task.execute",
                "graph.project",
                "graph.replay",
            ],
            conditions=[
                {
                    "fact": (
                        "graph.schema_version"
                    ),
                    "operator": "exists",
                }
            ],
            failure_code=(
                "masterplan.policy."
                "graph_schema_missing"
            ),
            failure_message=(
                "Graph schema version is missing."
            ),
        ),
    )


def seed_policies() -> dict[str, Any]:
    POLICY_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    written: list[
        dict[str, Any]
    ] = []

    for policy in default_policies():
        validate_policy(policy)

        path = (
            POLICY_ROOT
            / (
                policy["id"]
                .replace(".", "__")
                + ".json"
            )
        )

        if path.exists():
            existing = load_json(path)

            if (
                semantic_digest(existing)
                != semantic_digest(policy)
            ):
                raise PolicyError(
                    "Existing policy differs from "
                    f"seed authority: {policy['id']}"
                )

        else:
            atomic_write_json(
                path,
                policy,
            )

        written.append(
            {
                "id": policy["id"],
                "path": relative_path(path),
                "sha256": sha256_path(path),
                "semantic_digest": (
                    semantic_digest(policy)
                ),
            }
        )

    policies = load_policies()

    registry = build_registry(
        policies
    )

    registry_path = (
        POLICY_ROOT
        / "registry.json"
    )

    atomic_write_json(
        registry_path,
        registry,
    )

    return {
        "operation": (
            "seed_masterplan_policies"
        ),
        "passed": True,
        "written": written,
        "registry": {
            "path": relative_path(
                registry_path
            ),
            "sha256": sha256_path(
                registry_path
            ),
            "semantic_digest": (
                registry[
                    "semantic_digest"
                ]
            ),
        },
    }


def persist_result(
    name: str,
    result: dict[str, Any],
) -> dict[str, str]:
    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    RUNTIME_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = timestamp()

    historical = (
        REPORT_ROOT
        / f"{run_id}__{name}.json"
    )

    latest = (
        REPORT_ROOT
        / "latest.json"
    )

    runtime_latest = (
        RUNTIME_ROOT
        / "latest.json"
    )

    atomic_write_json(
        historical,
        result,
    )

    atomic_write_json(
        latest,
        result,
    )

    atomic_write_json(
        runtime_latest,
        result,
    )

    return {
        "historical": relative_path(
            historical
        ),
        "latest": relative_path(
            latest
        ),
        "runtime_latest": relative_path(
            runtime_latest
        ),
    }


def command_validate() -> dict[str, Any]:
    policies = load_policies()

    results = [
        validate_policy(policy)
        for policy in policies
    ]

    return {
        "operation": (
            "validate_masterplan_policies"
        ),
        "passed": True,
        "policy_count": len(policies),
        "policies": results,
        "collection_digest": (
            semantic_digest(
                results
            )
        ),
    }


def command_registry() -> dict[str, Any]:
    policies = load_policies()

    registry = build_registry(
        policies
    )

    path = (
        POLICY_ROOT
        / "registry.json"
    )

    atomic_write_json(
        path,
        registry,
    )

    return {
        "operation": (
            "build_masterplan_policy_registry"
        ),
        "passed": True,
        "registry": registry,
        "path": relative_path(path),
        "sha256": sha256_path(path),
    }


def command_evaluate(
    task_id: str,
    operation: str,
) -> dict[str, Any]:
    graph = load_json(
        GRAPH_PATH
    )

    facts = build_task_facts(
        graph,
        task_id,
        operation,
    )

    policies = load_policies()

    return evaluate_operation(
        policies,
        facts,
        operation,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Seed, validate, register, and evaluate "
            "graph-addressable Masterplan policies."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "seed"
    )

    subparsers.add_parser(
        "validate"
    )

    subparsers.add_parser(
        "registry"
    )

    evaluate_parser = subparsers.add_parser(
        "evaluate"
    )

    evaluate_parser.add_argument(
        "task_id"
    )

    evaluate_parser.add_argument(
        "operation"
    )

    arguments = parser.parse_args()

    try:
        if arguments.command == "seed":
            result = seed_policies()

        elif arguments.command == "validate":
            result = command_validate()

        elif arguments.command == "registry":
            result = command_registry()

        elif arguments.command == "evaluate":
            result = command_evaluate(
                arguments.task_id,
                arguments.operation,
            )

        else:
            return 2

        result["generated_at"] = utc_now()

        result["semantic_digest"] = (
            semantic_digest(result)
        )

        result["reports"] = persist_result(
            arguments.command,
            result,
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "masterplan_policy_runtime"
                    ),
                    "passed": False,
                    "error": {
                        "type": type(
                            exc
                        ).__name__,
                        "message": str(
                            exc
                        ),
                    },
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if result.get("passed")
        is True
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())

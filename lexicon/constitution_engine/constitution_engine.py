#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import yaml


LEXICON_ROOT = Path(
    __file__
).resolve().parents[1]

ROOT = (
    LEXICON_ROOT
    / "constitution_engine"
)

CONSTITUTION_REGISTRY = (
    ROOT
    / "constitution_registry.yaml"
)

INSTANCE_REGISTRY = (
    LEXICON_ROOT
    / "instances"
    / "instance_registry.yaml"
)

SEGUE_REGISTRY = (
    LEXICON_ROOT
    / "instances"
    / "segue_registry.yaml"
)

PROJECTION_REGISTRY = (
    LEXICON_ROOT
    / "projection_engine"
    / "projection_registry.yaml"
)

DEFAULT_OUTPUT = (
    ROOT
    / "runtime"
)


class ConstitutionError(
    RuntimeError
):
    pass


class ConstitutionEngine:

    def __init__(
        self,
    ) -> None:

        self.rules: dict[
            str,
            dict[str, Any],
        ] = {}

        self.instances: dict[
            str,
            dict[str, Any],
        ] = {}

        self.segues: dict[
            str,
            dict[str, Any],
        ] = {}

        self.projections: dict[
            str,
            dict[str, Any],
        ] = {}

        self.rule_dependencies: dict[
            str,
            list[str],
        ] = defaultdict(
            list
        )

        self.rule_dependents: dict[
            str,
            list[str],
        ] = defaultdict(
            list
        )

        self.scope_index: dict[
            str,
            list[str],
        ] = defaultdict(
            list
        )

        self.subject_index: dict[
            str,
            list[str],
        ] = defaultdict(
            list
        )

        self.load()

    def load_yaml(
        self,
        path: Path,
    ) -> dict[str, Any]:

        if not path.exists():

            raise FileNotFoundError(
                str(path)
            )

        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:

            data = yaml.safe_load(
                handle
            )

        if not isinstance(
            data,
            dict,
        ):

            raise ValueError(
                f"Invalid YAML root: {path}"
            )

        return data

    def load_registry(
        self,
        path: Path,
        collection_key: str,
    ) -> dict[str, dict[str, Any]]:

        data = self.load_yaml(
            path
        )

        records = data.get(
            collection_key,
            [],
        )

        if not isinstance(
            records,
            list,
        ):

            raise ConstitutionError(
                f"{collection_key} must be a list"
            )

        result: dict[
            str,
            dict[str, Any],
        ] = {}

        for record in records:

            if not isinstance(
                record,
                dict,
            ):

                continue

            reference = str(
                record.get(
                    "id",
                    "",
                )
            ).strip()

            if reference:

                result[
                    reference
                ] = record

        return result

    def load(
        self,
    ) -> None:

        self.instances = self.load_registry(
            INSTANCE_REGISTRY,
            "instances",
        )

        self.segues = self.load_registry(
            SEGUE_REGISTRY,
            "segues",
        )

        self.projections = self.load_registry(
            PROJECTION_REGISTRY,
            "projections",
        )

        constitution_data = self.load_yaml(
            CONSTITUTION_REGISTRY
        )

        records = constitution_data.get(
            "rules",
            [],
        )

        if not isinstance(
            records,
            list,
        ):

            raise ConstitutionError(
                "rules must be a list"
            )

        for record in records:

            if not isinstance(
                record,
                dict,
            ):

                continue

            rule_id = str(
                record.get(
                    "id",
                    "",
                )
            ).strip()

            if not rule_id:

                continue

            self.rules[
                rule_id
            ] = record

            scope = str(
                record.get(
                    "scope",
                    "global",
                )
            ).strip()

            self.scope_index[
                scope
            ].append(
                rule_id
            )

            subjects = record.get(
                "subjects",
                [],
            )

            if isinstance(
                subjects,
                list,
            ):

                for subject in subjects:

                    subject_id = str(
                        subject
                    ).strip()

                    if subject_id:

                        self.subject_index[
                            subject_id
                        ].append(
                            rule_id
                        )

            dependencies = record.get(
                "dependencies",
                [],
            )

            if isinstance(
                dependencies,
                list,
            ):

                for dependency in dependencies:

                    dependency_id = str(
                        dependency
                    ).strip()

                    if not dependency_id:

                        continue

                    self.rule_dependencies[
                        rule_id
                    ].append(
                        dependency_id
                    )

                    if dependency_id in self.rules:

                        self.rule_dependents[
                            dependency_id
                        ].append(
                            rule_id
                        )

        for index in (
            self.scope_index,
            self.subject_index,
            self.rule_dependencies,
            self.rule_dependents,
        ):

            for key in index:

                index[
                    key
                ] = sorted(
                    set(
                        index[
                            key
                        ]
                    )
                )

    def resolve(
        self,
        rule_id: str,
    ) -> dict[str, Any]:

        if rule_id not in self.rules:

            raise KeyError(
                rule_id
            )

        return self.rules[
            rule_id
        ]

    def read_path(
        self,
        source: Any,
        path: str,
        default: Any = None,
    ) -> Any:

        if not path:

            return source

        current = source

        for part in path.split(
            "."
        ):

            if isinstance(
                current,
                dict,
            ):

                if part not in current:

                    return default

                current = current[
                    part
                ]

                continue

            if isinstance(
                current,
                list,
            ):

                try:

                    index = int(
                        part
                    )

                except ValueError:

                    return default

                if (
                    index < 0
                    or index >= len(
                        current
                    )
                ):

                    return default

                current = current[
                    index
                ]

                continue

            return default

        return current

    def resolve_subject(
        self,
        subject_id: str,
    ) -> dict[str, Any]:

        if subject_id in self.instances:

            return {
                "type": "instance",
                "record": self.instances[
                    subject_id
                ],
            }

        if subject_id in self.segues:

            return {
                "type": "segue",
                "record": self.segues[
                    subject_id
                ],
            }

        if subject_id in self.projections:

            return {
                "type": "projection",
                "record": self.projections[
                    subject_id
                ],
            }

        if subject_id in self.rules:

            return {
                "type": "constitution",
                "record": self.rules[
                    subject_id
                ],
            }

        raise KeyError(
            subject_id
        )

    def condition_matches(
        self,
        source: dict[str, Any],
        condition: Any,
    ) -> bool:

        if isinstance(
            condition,
            bool,
        ):

            return condition

        if isinstance(
            condition,
            str,
        ):

            return bool(
                self.read_path(
                    source,
                    condition,
                )
            )

        if not isinstance(
            condition,
            dict,
        ):

            return False

        if "all" in condition:

            values = condition.get(
                "all"
            )

            if not isinstance(
                values,
                list,
            ):

                return False

            return all(
                self.condition_matches(
                    source,
                    child,
                )
                for child in values
            )

        if "any" in condition:

            values = condition.get(
                "any"
            )

            if not isinstance(
                values,
                list,
            ):

                return False

            return any(
                self.condition_matches(
                    source,
                    child,
                )
                for child in values
            )

        if "not" in condition:

            return not self.condition_matches(
                source,
                condition.get(
                    "not"
                ),
            )

        path = str(
            condition.get(
                "path",
                "",
            )
        ).strip()

        operator = str(
            condition.get(
                "operator",
                "equals",
            )
        ).strip()

        expected = condition.get(
            "value"
        )

        actual = self.read_path(
            source,
            path,
        )

        if operator == "equals":

            return actual == expected

        if operator == "not_equals":

            return actual != expected

        if operator == "exists":

            return actual is not None

        if operator == "missing":

            return actual is None

        if operator == "truthy":

            return bool(
                actual
            )

        if operator == "falsy":

            return not bool(
                actual
            )

        if operator == "contains":

            try:

                return expected in actual

            except TypeError:

                return False

        if operator == "in":

            try:

                return actual in expected

            except TypeError:

                return False

        if operator == "matches_type":

            return type(
                actual
            ).__name__ == str(
                expected
            )

        if operator == "greater_than":

            try:

                return actual > expected

            except TypeError:

                return False

        if operator == "greater_than_or_equal":

            try:

                return actual >= expected

            except TypeError:

                return False

        if operator == "less_than":

            try:

                return actual < expected

            except TypeError:

                return False

        if operator == "less_than_or_equal":

            try:

                return actual <= expected

            except TypeError:

                return False

        return False

    def rule_applies(
        self,
        rule: dict[str, Any],
        subject_id: str,
        subject_type: str,
        subject: dict[str, Any],
    ) -> bool:

        status = str(
            rule.get(
                "status",
                "active",
            )
        ).strip()

        if status != "active":

            return False

        scope = str(
            rule.get(
                "scope",
                "global",
            )
        ).strip()

        if scope not in {
            "global",
            subject_type,
            subject_id,
        }:

            return False

        subjects = rule.get(
            "subjects",
            [],
        )

        if (
            isinstance(
                subjects,
                list,
            )
            and subjects
            and subject_id not in subjects
            and subject_type not in subjects
            and "*" not in subjects
        ):

            return False

        conditions = rule.get(
            "conditions",
            [],
        )

        if not conditions:

            return True

        if not isinstance(
            conditions,
            list,
        ):

            return False

        return all(
            self.condition_matches(
                subject,
                condition,
            )
            for condition in conditions
        )

    def check_assertion(
        self,
        subject: dict[str, Any],
        assertion: dict[str, Any],
    ) -> tuple[bool, dict[str, Any]]:

        path = str(
            assertion.get(
                "path",
                "",
            )
        ).strip()

        operator = str(
            assertion.get(
                "operator",
                "exists",
            )
        ).strip()

        expected = assertion.get(
            "value"
        )

        condition = {
            "path": path,
            "operator": operator,
        }

        if "value" in assertion:

            condition[
                "value"
            ] = expected

        passed = self.condition_matches(
            subject,
            condition,
        )

        return passed, {
            "path": path,
            "operator": operator,
            "expected": expected,
            "actual": self.read_path(
                subject,
                path,
            ),
        }

    def evaluate_rule(
        self,
        rule_id: str,
        subject_id: str,
    ) -> dict[str, Any]:

        rule = self.resolve(
            rule_id
        )

        resolved_subject = self.resolve_subject(
            subject_id
        )

        subject_type = resolved_subject[
            "type"
        ]

        subject = resolved_subject[
            "record"
        ]

        applies = self.rule_applies(
            rule,
            subject_id,
            subject_type,
            subject,
        )

        if not applies:

            return {
                "rule": rule_id,
                "subject": subject_id,
                "subject_type": subject_type,
                "applies": False,
                "passed": True,
                "violations": [],
            }

        assertions = rule.get(
            "assertions",
            [],
        )

        if not isinstance(
            assertions,
            list,
        ):

            raise ConstitutionError(
                f"Assertions must be a list: "
                f"{rule_id}"
            )

        violations = []
        checks = []

        for position, assertion in enumerate(
            assertions
        ):

            if not isinstance(
                assertion,
                dict,
            ):

                violations.append(
                    {
                        "position": position,
                        "reason": (
                            "assertion_not_object"
                        ),
                    }
                )

                continue

            passed, details = self.check_assertion(
                subject,
                assertion,
            )

            check = {
                "position": position,
                "passed": passed,
                **details,
            }

            checks.append(
                check
            )

            if not passed:

                violations.append(
                    check
                )

        return {
            "rule": rule_id,
            "subject": subject_id,
            "subject_type": subject_type,
            "applies": True,
            "passed": not violations,
            "severity": rule.get(
                "severity",
                "error",
            ),
            "checks": checks,
            "violations": violations,
        }

    def applicable_rules(
        self,
        subject_id: str,
    ) -> list[str]:

        resolved_subject = self.resolve_subject(
            subject_id
        )

        subject_type = resolved_subject[
            "type"
        ]

        subject = resolved_subject[
            "record"
        ]

        result = []

        for rule_id, rule in sorted(
            self.rules.items()
        ):

            if self.rule_applies(
                rule,
                subject_id,
                subject_type,
                subject,
            ):

                result.append(
                    rule_id
                )

        return result

    def evaluate_subject(
        self,
        subject_id: str,
    ) -> dict[str, Any]:

        evaluations = [
            self.evaluate_rule(
                rule_id,
                subject_id,
            )
            for rule_id in self.applicable_rules(
                subject_id
            )
        ]

        violations = [
            evaluation
            for evaluation in evaluations
            if not evaluation.get(
                "passed",
                False,
            )
        ]

        return {
            "subject": subject_id,
            "passed": not violations,
            "rule_count": len(
                evaluations
            ),
            "violation_count": len(
                violations
            ),
            "evaluations": evaluations,
        }

    def all_subject_ids(
        self,
    ) -> list[str]:

        return sorted(
            {
                *self.instances.keys(),
                *self.segues.keys(),
                *self.projections.keys(),
                *self.rules.keys(),
            }
        )

    def evaluate_all(
        self,
    ) -> dict[str, Any]:

        subjects = {}

        for subject_id in self.all_subject_ids():

            subjects[
                subject_id
            ] = self.evaluate_subject(
                subject_id
            )

        failed = {
            subject_id: result
            for subject_id, result
            in subjects.items()
            if not result.get(
                "passed",
                False,
            )
        }

        return {
            "passed": not failed,
            "subject_count": len(
                subjects
            ),
            "failed_subject_count": len(
                failed
            ),
            "subjects": subjects,
        }

    def dependency_order(
        self,
    ) -> list[str]:

        indegree = {
            rule_id: 0
            for rule_id in self.rules
        }

        adjacency: dict[
            str,
            list[str],
        ] = defaultdict(
            list
        )

        for rule_id, dependencies in (
            self.rule_dependencies.items()
        ):

            for dependency in dependencies:

                if dependency not in self.rules:

                    continue

                adjacency[
                    dependency
                ].append(
                    rule_id
                )

                indegree[
                    rule_id
                ] += 1

        queue = deque(
            sorted(
                rule_id
                for rule_id, degree
                in indegree.items()
                if degree == 0
            )
        )

        ordered = []

        while queue:

            rule_id = queue.popleft()

            ordered.append(
                rule_id
            )

            for dependent in sorted(
                adjacency.get(
                    rule_id,
                    [],
                )
            ):

                indegree[
                    dependent
                ] -= 1

                if indegree[
                    dependent
                ] == 0:

                    queue.append(
                        dependent
                    )

        if len(
            ordered
        ) != len(
            self.rules
        ):

            cyclic = sorted(
                rule_id
                for rule_id, degree
                in indegree.items()
                if degree > 0
            )

            raise ConstitutionError(
                "Constitution dependency cycle: "
                + ", ".join(
                    cyclic
                )
            )

        return ordered

    def graph(
        self,
    ) -> dict[str, Any]:

        nodes = []

        edges = []

        for rule_id, rule in sorted(
            self.rules.items()
        ):

            nodes.append(
                {
                    "id": rule_id,
                    "type": "constitution",
                    "canonical": rule.get(
                        "canonical"
                    ),
                    "status": rule.get(
                        "status",
                        "active",
                    ),
                    "scope": rule.get(
                        "scope",
                        "global",
                    ),
                    "severity": rule.get(
                        "severity",
                        "error",
                    ),
                }
            )

            for dependency in sorted(
                self.rule_dependencies.get(
                    rule_id,
                    [],
                )
            ):

                edges.append(
                    {
                        "from": rule_id,
                        "to": dependency,
                        "relation": "depends_on",
                    }
                )

            subjects = rule.get(
                "subjects",
                [],
            )

            if isinstance(
                subjects,
                list,
            ):

                for subject in sorted(
                    str(
                        item
                    )
                    for item in subjects
                ):

                    edges.append(
                        {
                            "from": rule_id,
                            "to": subject,
                            "relation": "governs",
                        }
                    )

        return {
            "nodes": nodes,
            "edges": edges,
        }

    def snapshot(
        self,
    ) -> dict[str, Any]:

        graph = self.graph()

        evaluation = self.evaluate_all()

        digest = hashlib.sha256(
            json.dumps(
                {
                    "graph": graph,
                    "evaluation": evaluation,
                },
                sort_keys=True,
                separators=(
                    ",",
                    ":",
                ),
                default=str,
            ).encode(
                "utf-8"
            )
        ).hexdigest()

        return {
            "rule_count": len(
                self.rules
            ),
            "subject_count": len(
                self.all_subject_ids()
            ),
            "passed": evaluation[
                "passed"
            ],
            "failed_subject_count": (
                evaluation[
                    "failed_subject_count"
                ]
            ),
            "digest": digest,
        }

    def write_json(
        self,
        path: Path,
        payload: Any,
    ) -> None:

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = path.with_name(
            f".{path.name}.tmp"
        )

        temporary.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )

        os.replace(
            temporary,
            path,
        )

    def materialize(
        self,
        output: Path,
    ) -> dict[str, Any]:

        output.mkdir(
            parents=True,
            exist_ok=True,
        )

        graph = self.graph()
        evaluation = self.evaluate_all()
        snapshot = self.snapshot()
        order = self.dependency_order()

        payloads = {
            "constitution_graph.json": graph,
            "constitution_evaluation.json": (
                evaluation
            ),
            "constitution_snapshot.json": (
                snapshot
            ),
            "constitution_order.json": {
                "rules": order
            },
            "scope_index.json": {
                key: value
                for key, value in sorted(
                    self.scope_index.items()
                )
            },
            "subject_index.json": {
                key: value
                for key, value in sorted(
                    self.subject_index.items()
                )
            },
            "dependency_index.json": {
                key: value
                for key, value in sorted(
                    self.rule_dependencies.items()
                )
            },
        }

        for filename, payload in payloads.items():

            self.write_json(
                output
                / filename,
                payload,
            )

        manifest = {
            "output": str(
                output.resolve()
            ),
            "files": sorted(
                payloads
            ),
            "snapshot": snapshot,
        }

        self.write_json(
            output
            / "manifest.json",
            manifest,
        )

        return manifest


def main(
) -> int:

    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    resolve_parser = subparsers.add_parser(
        "resolve"
    )

    resolve_parser.add_argument(
        "rule_id"
    )

    rules_parser = subparsers.add_parser(
        "rules"
    )

    rules_parser.add_argument(
        "subject_id"
    )

    evaluate_parser = subparsers.add_parser(
        "evaluate"
    )

    evaluate_parser.add_argument(
        "subject_id"
    )

    check_parser = subparsers.add_parser(
        "check"
    )

    check_parser.add_argument(
        "rule_id"
    )

    check_parser.add_argument(
        "subject_id"
    )

    subparsers.add_parser(
        "evaluate-all"
    )

    subparsers.add_parser(
        "graph"
    )

    subparsers.add_parser(
        "order"
    )

    subparsers.add_parser(
        "snapshot"
    )

    materialize_parser = subparsers.add_parser(
        "materialize"
    )

    materialize_parser.add_argument(
        "--output",
        default=str(
            DEFAULT_OUTPUT
        ),
    )

    args = parser.parse_args()

    engine = ConstitutionEngine()

    if args.command == "resolve":

        result = engine.resolve(
            args.rule_id
        )

    elif args.command == "rules":

        result = {
            "subject": args.subject_id,
            "rules": engine.applicable_rules(
                args.subject_id
            ),
        }

    elif args.command == "evaluate":

        result = engine.evaluate_subject(
            args.subject_id
        )

    elif args.command == "check":

        result = engine.evaluate_rule(
            args.rule_id,
            args.subject_id,
        )

    elif args.command == "evaluate-all":

        result = engine.evaluate_all()

    elif args.command == "graph":

        result = engine.graph()

    elif args.command == "order":

        result = {
            "rules": engine.dependency_order()
        }

    elif args.command == "snapshot":

        result = engine.snapshot()

    elif args.command == "materialize":

        result = engine.materialize(
            Path(
                args.output
            )
        )

    else:

        raise RuntimeError(
            args.command
        )

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            default=str,
        )
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )

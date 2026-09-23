from __future__ import annotations

import hashlib
import inspect
import json
import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence


schema = "savant://runtime/urge/iteration/2.0.0"
owner = "exile:urge"


class iteration_error(ValueError):
    pass


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise iteration_error(
            "value must be canonical-json serializable"
        ) from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _finite(
    value: Any,
    *,
    name: str,
) -> float:
    if isinstance(value, bool):
        raise iteration_error(
            f"{name} must be numeric"
        )

    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise iteration_error(
            f"{name} must be numeric"
        ) from exc

    if not math.isfinite(number):
        raise iteration_error(
            f"{name} must be finite"
        )

    return number


def _nonempty(
    value: Any,
    *,
    name: str,
) -> str:
    text = str(
        value
        if value is not None
        else ""
    ).strip()

    if not text:
        raise iteration_error(
            f"{name} is required"
        )

    return text


def _unique_strings(
    values: Iterable[Any],
) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        text = str(value).strip()

        if text and text not in seen:
            seen.add(text)
            result.append(text)

    return tuple(result)


def _invoke(
    adapter: Callable[..., Any],
    *args: Any,
) -> Any:
    result = adapter(*args)

    if inspect.isawaitable(result):
        raise iteration_error(
            "async adapters require an async boundary outside urge"
        )

    return result


@dataclass(
    frozen=True,
    slots=True,
)
class criterion:
    id: str
    weight: float = 1.0
    target: float = 1.0
    required: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            _nonempty(
                self.id,
                name="criterion.id",
            ),
        )

        weight = _finite(
            self.weight,
            name=f"criterion[{self.id}].weight",
        )

        target = _finite(
            self.target,
            name=f"criterion[{self.id}].target",
        )

        if weight <= 0.0:
            raise iteration_error(
                "criterion weight must be greater than zero"
            )

        if not 0.0 <= target <= 1.0:
            raise iteration_error(
                "criterion target must be between zero and one"
            )

        object.__setattr__(
            self,
            "weight",
            weight,
        )

        object.__setattr__(
            self,
            "target",
            target,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class policy:
    max_cycles: int = 12
    branch_factor: int = 3
    min_improvement: float = 0.0025
    target_score: float = 0.985
    patience: int = 3
    max_candidates: int = 64
    max_failures: int = 8
    preserve_alternates: int = 3

    def __post_init__(self) -> None:
        for name in (
            "max_cycles",
            "branch_factor",
            "patience",
            "max_candidates",
            "max_failures",
            "preserve_alternates",
        ):
            value = getattr(
                self,
                name,
            )

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise iteration_error(
                    f"policy.{name} must be a non-negative integer"
                )

        if (
            self.max_cycles < 1
            or self.branch_factor < 1
            or self.max_candidates < 1
        ):
            raise iteration_error(
                "max_cycles, branch_factor, and max_candidates "
                "must be positive"
            )

        if self.branch_factor > self.max_candidates:
            raise iteration_error(
                "branch_factor cannot exceed max_candidates"
            )

        for name in (
            "min_improvement",
            "target_score",
        ):
            value = _finite(
                getattr(self, name),
                name=f"policy.{name}",
            )

            if not 0.0 <= value <= 1.0:
                raise iteration_error(
                    f"policy.{name} must be between zero and one"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class job:
    id: str
    objective: str
    payload: Any
    criteria: tuple[criterion, ...]
    constraints: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            _nonempty(
                self.id,
                name="job.id",
            ),
        )

        object.__setattr__(
            self,
            "objective",
            _nonempty(
                self.objective,
                name="job.objective",
            ),
        )

        criteria = tuple(
            self.criteria
        )

        if not criteria:
            raise iteration_error(
                "job.criteria requires at least one criterion"
            )

        ids = [
            item.id
            for item in criteria
        ]

        if len(ids) != len(set(ids)):
            raise iteration_error(
                "job.criteria ids must be unique"
            )

        object.__setattr__(
            self,
            "criteria",
            criteria,
        )

        object.__setattr__(
            self,
            "constraints",
            _unique_strings(
                self.constraints
            ),
        )

        object.__setattr__(
            self,
            "provenance",
            _unique_strings(
                self.provenance
            ),
        )

        object.__setattr__(
            self,
            "dependencies",
            _unique_strings(
                self.dependencies
            ),
        )

        _canonical_json(
            self.payload
        )

        _canonical_json(
            dict(self.metadata)
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        value = {
            "id": self.id,
            "objective": self.objective,
            "payload": self.payload,
            "criteria": [
                {
                    "id": item.id,
                    "weight": item.weight,
                    "target": item.target,
                    "required": item.required,
                }
                for item in self.criteria
            ],
            "constraints": list(
                self.constraints
            ),
            "provenance": list(
                self.provenance
            ),
            "dependencies": list(
                self.dependencies
            ),
            "metadata": dict(
                self.metadata
            ),
        }

        value["digest"] = _digest(
            value
        )

        return value


@dataclass(
    frozen=True,
    slots=True,
)
class assessment:
    scores: Mapping[str, float]
    findings: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )


@dataclass(
    frozen=True,
    slots=True,
)
class proposal:
    payload: Any
    rationale: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )


class engine:
    def __init__(
        self,
        *,
        evaluator: Callable[
            ...,
            assessment | Mapping[str, Any],
        ],
        reviser: Callable[
            ...,
            Sequence[
                proposal | Mapping[str, Any]
            ],
        ],
        run_policy: policy | None = None,
    ) -> None:
        if (
            not callable(evaluator)
            or not callable(reviser)
        ):
            raise iteration_error(
                "evaluator and reviser must be callable"
            )

        self.evaluator = evaluator
        self.reviser = reviser
        self.policy = (
            run_policy
            or policy()
        )

    @staticmethod
    def _normalize_assessment(
        value: assessment | Mapping[str, Any],
        work: job,
    ) -> dict[str, Any]:
        if isinstance(
            value,
            assessment,
        ):
            scores_source = value.scores
            findings = value.findings
            evidence = value.evidence
            metadata = value.metadata

        elif isinstance(
            value,
            Mapping,
        ):
            scores_source = value.get(
                "scores",
                {},
            )

            findings = tuple(
                value.get(
                    "findings",
                    (),
                )
            )

            evidence = tuple(
                value.get(
                    "evidence",
                    (),
                )
            )

            metadata = value.get(
                "metadata",
                {},
            )

        else:
            raise iteration_error(
                "evaluator must return assessment or mapping"
            )

        if not isinstance(
            scores_source,
            Mapping,
        ):
            raise iteration_error(
                "assessment.scores must be an object"
            )

        criterion_ids = {
            item.id
            for item in work.criteria
        }

        unknown = (
            set(scores_source)
            - criterion_ids
        )

        missing = (
            criterion_ids
            - set(scores_source)
        )

        if unknown or missing:
            raise iteration_error(
                "assessment score mismatch "
                f"missing={sorted(missing)} "
                f"unknown={sorted(unknown)}"
            )

        scores: dict[str, float] = {}
        weighted = 0.0
        weight_total = 0.0
        required_met = True
        gaps: list[
            dict[str, Any]
        ] = []

        for item in work.criteria:
            score = _finite(
                scores_source[
                    item.id
                ],
                name=(
                    f"score[{item.id}]"
                ),
            )

            if not 0.0 <= score <= 1.0:
                raise iteration_error(
                    "criterion scores must be between zero and one"
                )

            scores[
                item.id
            ] = score

            weighted += (
                score
                * item.weight
            )

            weight_total += (
                item.weight
            )

            gap = max(
                0.0,
                item.target
                - score,
            )

            if gap > 0.0:
                gaps.append(
                    {
                        "criterion": item.id,
                        "gap": round(
                            gap,
                            12,
                        ),
                        "required": (
                            item.required
                        ),
                        "weighted_pressure": round(
                            gap
                            * item.weight,
                            12,
                        ),
                    }
                )

            if (
                item.required
                and score
                < item.target
            ):
                required_met = False

        gaps.sort(
            key=lambda item: (
                -item["required"],
                -item[
                    "weighted_pressure"
                ],
                item["criterion"],
            )
        )

        result = {
            "scores": scores,
            "score": round(
                weighted
                / weight_total,
                12,
            ),
            "required_met": (
                required_met
            ),
            "gaps": gaps,
            "findings": list(
                _unique_strings(
                    findings
                )
            ),
            "evidence": list(
                _unique_strings(
                    evidence
                )
            ),
            "metadata": (
                dict(metadata)
                if isinstance(
                    metadata,
                    Mapping,
                )
                else {}
            ),
        }

        result["digest"] = _digest(
            result
        )

        return result

    @staticmethod
    def _normalize_proposals(
        values: Sequence[
            proposal | Mapping[str, Any]
        ],
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        if (
            isinstance(
                values,
                (str, bytes),
            )
            or not isinstance(
                values,
                Sequence,
            )
        ):
            raise iteration_error(
                "reviser must return a sequence"
            )

        normalized: list[
            dict[str, Any]
        ] = []

        seen: set[str] = set()

        for value in values[
            :limit
        ]:
            if isinstance(
                value,
                proposal,
            ):
                payload = value.payload
                rationale = value.rationale
                provenance = value.provenance
                metadata = value.metadata

            elif (
                isinstance(
                    value,
                    Mapping,
                )
                and "payload"
                in value
            ):
                payload = value[
                    "payload"
                ]

                rationale = tuple(
                    value.get(
                        "rationale",
                        (),
                    )
                )

                provenance = tuple(
                    value.get(
                        "provenance",
                        (),
                    )
                )

                metadata = value.get(
                    "metadata",
                    {},
                )

            else:
                raise iteration_error(
                    "proposal must contain payload"
                )

            _canonical_json(
                payload
            )

            payload_digest = _digest(
                payload
            )

            if payload_digest in seen:
                continue

            seen.add(
                payload_digest
            )

            item = {
                "payload": payload,
                "payload_digest": (
                    payload_digest
                ),
                "rationale": list(
                    _unique_strings(
                        rationale
                    )
                ),
                "provenance": list(
                    _unique_strings(
                        provenance
                    )
                ),
                "metadata": (
                    dict(metadata)
                    if isinstance(
                        metadata,
                        Mapping,
                    )
                    else {}
                ),
            }

            item["digest"] = _digest(
                item
            )

            normalized.append(
                item
            )

        return normalized

    @staticmethod
    def _candidate_key(
        candidate: Mapping[
            str,
            Any,
        ],
    ) -> tuple[Any, ...]:
        judged = candidate[
            "assessment"
        ]

        return (
            bool(
                judged[
                    "required_met"
                ]
            ),
            float(
                judged[
                    "score"
                ]
            ),
            tuple(
                sorted(
                    (
                        key,
                        float(value),
                    )
                    for (
                        key,
                        value,
                    )
                    in judged[
                        "scores"
                    ].items()
                )
            ),
            str(
                candidate[
                    "payload_digest"
                ]
            ),
        )

    def run(
        self,
        work: job,
        *,
        initial_payload: Any | None = None,
    ) -> dict[str, Any]:
        if not isinstance(
            work,
            job,
        ):
            raise iteration_error(
                "work must be a job"
            )

        started_ns = (
            time.monotonic_ns()
        )

        work_projection = (
            work.projection()
        )

        initial = (
            work.payload
            if initial_payload
            is None
            else initial_payload
        )

        _canonical_json(
            initial
        )

        failures: list[
            dict[str, Any]
        ] = []

        lineage: list[
            dict[str, Any]
        ] = []

        seen_payloads: set[
            str
        ] = set()

        candidate_count = 0

        def evaluate(
            payload: Any,
            *,
            cycle: int,
            parent_digest: str | None,
            rationale: Sequence[str] = (),
            provenance: Sequence[str] = (),
        ) -> dict[str, Any] | None:
            nonlocal candidate_count

            payload_digest = _digest(
                payload
            )

            if (
                payload_digest
                in seen_payloads
                or candidate_count
                >= self.policy.max_candidates
            ):
                return None

            seen_payloads.add(
                payload_digest
            )

            candidate_count += 1

            context = {
                "job": work_projection,
                "cycle": cycle,
                "candidate_index": (
                    candidate_count
                    - 1
                ),
                "payload_digest": (
                    payload_digest
                ),
                "parent_payload_digest": (
                    parent_digest
                ),
                "authority_effect": (
                    "none"
                ),
            }

            try:
                raw = _invoke(
                    self.evaluator,
                    payload,
                    context,
                )

                judged = (
                    self._normalize_assessment(
                        raw,
                        work,
                    )
                )

            except Exception as exc:
                failures.append(
                    {
                        "cycle": cycle,
                        "payload_digest": (
                            payload_digest
                        ),
                        "stage": (
                            "evaluate"
                        ),
                        "error_type": (
                            type(exc).__name__
                        ),
                        "error": str(exc),
                    }
                )

                if (
                    len(failures)
                    > self.policy.max_failures
                ):
                    raise iteration_error(
                        "failure budget exhausted"
                    ) from exc

                return None

            candidate = {
                "payload": payload,
                "payload_digest": (
                    payload_digest
                ),
                "assessment": judged,
                "cycle": cycle,
                "parent_payload_digest": (
                    parent_digest
                ),
                "rationale": list(
                    _unique_strings(
                        rationale
                    )
                ),
                "provenance": list(
                    _unique_strings(
                        provenance
                    )
                ),
            }

            candidate[
                "digest"
            ] = _digest(
                candidate
            )

            lineage.append(
                {
                    "candidate_digest": (
                        candidate[
                            "digest"
                        ]
                    ),
                    "payload_digest": (
                        payload_digest
                    ),
                    "parent_payload_digest": (
                        parent_digest
                    ),
                    "cycle": cycle,
                    "assessment_digest": (
                        judged[
                            "digest"
                        ]
                    ),
                }
            )

            return candidate

        best = evaluate(
            initial,
            cycle=0,
            parent_digest=None,
            provenance=(
                work.provenance
            ),
        )

        if best is None:
            raise iteration_error(
                "initial candidate could not be evaluated"
            )

        alternates: list[
            dict[str, Any]
        ] = []

        no_progress = 0
        stop_reason = (
            "max_cycles"
        )
        cycles_completed = 0

        for cycle in range(
            1,
            self.policy.max_cycles
            + 1,
        ):
            if (
                best[
                    "assessment"
                ][
                    "required_met"
                ]
                and best[
                    "assessment"
                ][
                    "score"
                ]
                >= self.policy.target_score
            ):
                stop_reason = (
                    "target_reached"
                )
                break

            if (
                no_progress
                >= self.policy.patience
            ):
                stop_reason = (
                    "no_progress"
                )
                break

            if (
                candidate_count
                >= self.policy.max_candidates
            ):
                stop_reason = (
                    "candidate_budget"
                )
                break

            pressure = {
                "cycle": cycle,
                "objective": (
                    work.objective
                ),
                "constraints": list(
                    work.constraints
                ),
                "gaps": (
                    best[
                        "assessment"
                    ][
                        "gaps"
                    ]
                ),
                "findings": (
                    best[
                        "assessment"
                    ][
                        "findings"
                    ]
                ),
                "current_score": (
                    best[
                        "assessment"
                    ][
                        "score"
                    ]
                ),
                "required_met": (
                    best[
                        "assessment"
                    ][
                        "required_met"
                    ]
                ),
                "current_payload_digest": (
                    best[
                        "payload_digest"
                    ]
                ),
                "job_digest": (
                    work_projection[
                        "digest"
                    ]
                ),
            }

            try:
                raw_proposals = (
                    _invoke(
                        self.reviser,
                        best[
                            "payload"
                        ],
                        pressure,
                    )
                )

                proposals = (
                    self._normalize_proposals(
                        raw_proposals,
                        limit=(
                            self.policy.branch_factor
                        ),
                    )
                )

            except Exception as exc:
                failures.append(
                    {
                        "cycle": cycle,
                        "payload_digest": (
                            best[
                                "payload_digest"
                            ]
                        ),
                        "stage": (
                            "revise"
                        ),
                        "error_type": (
                            type(exc).__name__
                        ),
                        "error": str(exc),
                    }
                )

                if (
                    len(failures)
                    > self.policy.max_failures
                ):
                    raise iteration_error(
                        "failure budget exhausted"
                    ) from exc

                no_progress += 1
                cycles_completed = cycle
                continue

            cycle_candidates: list[
                dict[str, Any]
            ] = []

            for item in proposals:
                candidate = evaluate(
                    item[
                        "payload"
                    ],
                    cycle=cycle,
                    parent_digest=(
                        best[
                            "payload_digest"
                        ]
                    ),
                    rationale=(
                        item[
                            "rationale"
                        ]
                    ),
                    provenance=(
                        item[
                            "provenance"
                        ]
                    ),
                )

                if candidate is not None:
                    cycle_candidates.append(
                        candidate
                    )

            cycles_completed = cycle

            if not cycle_candidates:
                no_progress += 1
                continue

            ranked = sorted(
                cycle_candidates,
                key=self._candidate_key,
                reverse=True,
            )

            challenger = ranked[0]

            improvement = round(
                challenger[
                    "assessment"
                ][
                    "score"
                ]
                - best[
                    "assessment"
                ][
                    "score"
                ],
                12,
            )

            required_upgrade = (
                challenger[
                    "assessment"
                ][
                    "required_met"
                ]
                and not best[
                    "assessment"
                ][
                    "required_met"
                ]
            )

            if (
                required_upgrade
                or improvement
                >= self.policy.min_improvement
            ):
                alternates.extend(
                    [
                        best,
                        *ranked[1:],
                    ]
                )

                best = challenger
                no_progress = 0

            else:
                alternates.extend(
                    ranked
                )

                no_progress += 1

            alternates = sorted(
                alternates,
                key=self._candidate_key,
                reverse=True,
            )[
                :self.policy.preserve_alternates
            ]

        duration_ns = (
            time.monotonic_ns()
            - started_ns
        )

        result = {
            "schema": schema,
            "owner": owner,
            "authority_effect": (
                "none"
            ),
            "projection_only": True,
            "deterministic_selection": (
                True
            ),
            "rebuildable_from_recorded_adapter_outputs": (
                True
            ),
            "job": work_projection,
            "policy": {
                "max_cycles": (
                    self.policy.max_cycles
                ),
                "branch_factor": (
                    self.policy.branch_factor
                ),
                "min_improvement": (
                    self.policy.min_improvement
                ),
                "target_score": (
                    self.policy.target_score
                ),
                "patience": (
                    self.policy.patience
                ),
                "max_candidates": (
                    self.policy.max_candidates
                ),
                "max_failures": (
                    self.policy.max_failures
                ),
                "preserve_alternates": (
                    self.policy.preserve_alternates
                ),
            },
            "best": best,
            "alternates": (
                alternates
            ),
            "lineage": lineage,
            "failures": failures,
            "metrics": {
                "cycles_completed": (
                    cycles_completed
                ),
                "candidates_evaluated": (
                    candidate_count
                ),
                "unique_payloads": (
                    len(
                        seen_payloads
                    )
                ),
                "failure_count": (
                    len(
                        failures
                    )
                ),
                "duration_ns": (
                    duration_ns
                ),
            },
            "stop_reason": (
                stop_reason
            ),
            "boundaries": {
                "declares_truth": False,
                "verifies_fact": False,
                "admits_evidence": False,
                "mutates_canon": False,
                "mutates_source": False,
                "creates_authority": False,
                "selects_provider": False,
                "executes_model": False,
            },
        }

        digestable = dict(
            result
        )

        digestable[
            "metrics"
        ] = dict(
            result[
                "metrics"
            ]
        )

        digestable[
            "metrics"
        ].pop(
            "duration_ns",
            None,
        )

        result[
            "digest"
        ] = _digest(
            digestable
        )

        return result

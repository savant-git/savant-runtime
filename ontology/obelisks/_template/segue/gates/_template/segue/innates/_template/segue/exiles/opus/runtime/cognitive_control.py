#!/usr/bin/env python3
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from cognitive_primitives import (
    Budget,
    digest,
)


@dataclass(frozen=True)
class ExecutionState:
    calls: int = 0
    rounds: int = 0
    cost: float = 0.0
    started_at: float = 0.0

    @classmethod
    def begin(
        cls,
    ) -> "ExecutionState":
        return cls(
            started_at=time.time()
        )


class BudgetController:
    def __init__(
        self,
        budget: Budget,
    ) -> None:
        self.budget = budget

    def reason(
        self,
        state: ExecutionState,
    ) -> str | None:
        if (
            state.calls
            >= self.budget.maximum_calls
        ):
            return "maximum_calls"

        if (
            state.rounds
            >= self.budget.maximum_rounds
        ):
            return "maximum_rounds"

        if (
            self.budget.maximum_cost
            is not None
            and state.cost
            >= self.budget.maximum_cost
        ):
            return "maximum_cost"

        if (
            self.budget.deadline_epoch
            is not None
            and time.time()
            >= self.budget.deadline_epoch
        ):
            return "deadline"

        return None

    def permits(
        self,
        state: ExecutionState,
    ) -> bool:
        return self.reason(state) is None


class InformationGainController:
    def __init__(
        self,
        *,
        minimum_gain: float = 0.08,
        stability_rounds: int = 2,
    ) -> None:
        self.minimum_gain = max(
            0.0,
            min(1.0, minimum_gain),
        )
        self.stability_rounds = max(
            1,
            stability_rounds,
        )

    @staticmethod
    def token_set(
        value: Any,
    ) -> set[str]:
        if isinstance(value, str):
            text = value
        else:
            text = str(value)

        return {
            token
            for token
            in text.lower().split()
            if token
        }

    def novelty(
        self,
        current: Any,
        prior: Iterable[Any],
    ) -> float:
        current_tokens = self.token_set(
            current
        )

        if not current_tokens:
            return 0.0

        prior_tokens: set[str] = set()

        for value in prior:
            prior_tokens.update(
                self.token_set(value)
            )

        novel = (
            current_tokens
            - prior_tokens
        )

        return len(novel) / max(
            1,
            len(current_tokens),
        )

    def converged(
        self,
        gains: Iterable[float],
    ) -> bool:
        values = list(gains)

        if (
            len(values)
            < self.stability_rounds
        ):
            return False

        tail = values[
            -self.stability_rounds:
        ]

        return all(
            value
            < self.minimum_gain
            for value in tail
        )


class DiversityController:
    def score(
        self,
        candidates: Iterable[
            Mapping[str, Any]
        ],
    ) -> dict[str, Any]:
        values = list(candidates)

        providers = {
            str(
                item.get("provider")
                or ""
            )
            for item in values
            if item.get("provider")
        }

        models = {
            str(
                item.get("model")
                or ""
            )
            for item in values
            if item.get("model")
        }

        roles = {
            str(
                item.get("role")
                or ""
            )
            for item in values
            if item.get("role")
        }

        denominator = max(
            1,
            len(values),
        )

        score = min(
            1.0,
            (
                len(providers)
                + len(models)
                + len(roles)
            )
            / (3.0 * denominator),
        )

        result = {
            "candidate_count": len(values),
            "provider_count": (
                len(providers)
            ),
            "model_count": len(models),
            "role_count": len(roles),
            "score": score,
        }

        result["digest"] = digest(result)
        return result


class ConfidenceCalibrator:
    @staticmethod
    def calibrated_support(
        *,
        support_count: int,
        challenge_count: int,
        independent_sources: int,
        unresolved_count: int,
    ) -> float:
        support = max(
            0,
            support_count,
        )
        challenge = max(
            0,
            challenge_count,
        )
        independent = max(
            0,
            independent_sources,
        )
        unresolved = max(
            0,
            unresolved_count,
        )

        evidence_mass = (
            support
            + challenge
            + unresolved
            + 1
        )

        raw = (
            support
            + math.log1p(independent)
        ) / evidence_mass

        penalty = (
            challenge
            + unresolved
        ) / evidence_mass

        return max(
            0.0,
            min(
                1.0,
                raw * (1.0 - penalty),
            ),
        )

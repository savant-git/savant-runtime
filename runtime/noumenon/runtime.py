from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from runtime.noumenon.admission import (
    AdmittedTransition,
    AdmissionDecision,
    admit_transition,
    candidate_digest,
    coda_mutation_payload,
    evaluate_admission,
    notary_admission_payload,
)
from runtime.noumenon.integrant import (
    IntegrantEnvelope,
    emit,
    request,
)
from runtime.noumenon.state import (
    NoumenonState,
    TransitionCandidate,
)
from runtime.noumenon.store import (
    NoumenonStore,
)


SCHEMA = "savant://noumenon/runtime/1"


@dataclass(frozen=True, slots=True)
class TransitionResult:
    decision: AdmissionDecision
    admitted_transition: (
        AdmittedTransition | None
    )

    @property
    def admitted(self) -> bool:
        return self.decision.admitted

    def projection(
        self,
    ) -> dict[str, Any]:
        admitted = (
            self.admitted_transition
        )

        return {
            "schema": (
                "savant://noumenon/"
                "transition-result/1"
            ),
            "admitted": (
                self.decision.admitted
            ),
            "decision": (
                self.decision.projection()
            ),
            "predecessor_state_digest": (
                self.decision
                .predecessor_digest
            ),
            "candidate_digest": (
                self.decision
                .candidate_digest
            ),
            "successor_state_digest": (
                admitted.successor.state_digest
                if admitted is not None
                else None
            ),
            "authority_effect": "none",
        }


class NoumenonRuntime:
    def __init__(
        self,
        store: NoumenonStore,
    ) -> None:
        self.store = store

    @classmethod
    def from_path(
        cls,
        path: str | Path,
    ) -> "NoumenonRuntime":
        return cls(
            NoumenonStore(path)
        )

    def initialize(self) -> None:
        self.store.initialize()

    def establish(
        self,
        state: NoumenonState,
    ) -> NoumenonState:
        self.store.append_state(
            state
        )

        persisted = (
            self.store.load_state(
                state.state_digest
            )
        )

        if persisted is None:
            raise RuntimeError(
                "genesis state was not "
                "persisted"
            )

        return persisted

    def current(
        self,
        noumenon_id: str,
    ) -> NoumenonState | None:
        lineage = self.store.lineage(
            noumenon_id
        )

        if not lineage:
            return None

        maximum_generation = max(
            state.generation
            for state in lineage
        )

        candidates = tuple(
            state
            for state in lineage
            if state.generation
            == maximum_generation
        )

        if len(candidates) != 1:
            return None

        return candidates[0]

    def transition(
        self,
        candidate: TransitionCandidate,
        *,
        notary_envelope: (
            IntegrantEnvelope | None
        ),
        coda_envelope: (
            IntegrantEnvelope | None
        ) = None,
    ) -> TransitionResult:
        persisted_predecessor = (
            self.store.load_state(
                candidate.predecessor
                .state_digest
            )
        )

        if persisted_predecessor is None:
            raise ValueError(
                "transition predecessor is "
                "not persisted"
            )

        if (
            persisted_predecessor
            .state_digest
            != candidate.predecessor
            .state_digest
        ):
            raise ValueError(
                "transition predecessor "
                "integrity mismatch"
            )

        decision = evaluate_admission(
            candidate,
            notary_envelope=(
                notary_envelope
            ),
            coda_envelope=(
                coda_envelope
            ),
        )

        if not decision.admitted:
            return TransitionResult(
                decision=decision,
                admitted_transition=None,
            )

        admitted = admit_transition(
            candidate,
            decision,
        )

        self.store.append_admitted_transition(
            admitted
        )

        persisted_successor = (
            self.store.load_state(
                admitted.successor
                .state_digest
            )
        )

        if persisted_successor is None:
            raise RuntimeError(
                "admitted successor was not "
                "persisted"
            )

        if (
            persisted_successor.state_digest
            != admitted.successor
            .state_digest
        ):
            raise RuntimeError(
                "persisted successor failed "
                "runtime verification"
            )

        return TransitionResult(
            decision=decision,
            admitted_transition=admitted,
        )

    def notary_request(
        self,
        candidate: TransitionCandidate,
    ) -> IntegrantEnvelope:
        payload = (
            notary_admission_payload(
                candidate,
                admitted=False,
                reason=(
                    "admission_requested"
                ),
            )
        )

        return request(
            "notary",
            (
                "noumenon."
                "transition-admission"
            ),
            payload,
            lineage_refs=(
                candidate.predecessor
                .state_digest,
            ),
        )

    def coda_request(
        self,
        candidate: TransitionCandidate,
        *,
        durable_dimensions: (
            tuple[str, ...]
        ),
    ) -> IntegrantEnvelope:
        payload = (
            coda_mutation_payload(
                candidate,
                durable_dimensions=(
                    durable_dimensions
                ),
            )
        )

        return request(
            "coda",
            (
                "noumenon."
                "durable-mutation"
            ),
            payload,
            lineage_refs=(
                candidate.predecessor
                .state_digest,
            ),
        )

    def state_projection(
        self,
        state: NoumenonState,
    ) -> IntegrantEnvelope:
        return emit(
            "memory",
            (
                "noumenon."
                "state-projection"
            ),
            {
                "schema": SCHEMA,
                "noumenon_id": (
                    state.noumenon_id
                ),
                "state_digest": (
                    state.state_digest
                ),
                "generation": (
                    state.generation
                ),
                "succession_status": (
                    state.succession_status
                ),
            },
            lineage_refs=(
                state.state_digest,
            ),
        )

    def status(
        self,
        noumenon_id: str,
    ) -> Mapping[str, Any]:
        lineage = self.store.lineage(
            noumenon_id
        )

        current = self.current(
            noumenon_id
        )

        generations: dict[
            int,
            int,
        ] = {}

        for state in lineage:
            generations[
                state.generation
            ] = (
                generations.get(
                    state.generation,
                    0,
                )
                + 1
            )

        branch_generations = tuple(
            sorted(
                generation
                for generation, count
                in generations.items()
                if count > 1
            )
        )

        return {
            "schema": SCHEMA,
            "noumenon_id": noumenon_id,
            "state_count": len(
                lineage
            ),
            "current_state_digest": (
                current.state_digest
                if current is not None
                else None
            ),
            "current_generation": (
                current.generation
                if current is not None
                else None
            ),
            "branch_generations": list(
                branch_generations
            ),
            "ambiguous_current": (
                bool(lineage)
                and current is None
            ),
        }


def transition_identity(
    candidate: TransitionCandidate,
) -> Mapping[str, str]:
    return {
        "predecessor_state_digest": (
            candidate.predecessor
            .state_digest
        ),
        "candidate_digest": (
            candidate_digest(
                candidate
            )
        ),
    }

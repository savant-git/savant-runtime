#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/ontology/obelisks/"
    "_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/envoy/"
    "runtime/trait_experiment.py"
)


def load_module():
    specification = (
        importlib.util
        .spec_from_file_location(
            "envoy_trait_experiment",
            MODULE_PATH,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise RuntimeError(
            "cannot load trait_experiment.py"
        )

    module = (
        importlib.util
        .module_from_spec(
            specification
        )
    )

    sys.modules[
        specification.name
    ] = module

    specification.loader.exec_module(
        module
    )

    return module


def build_plan(
    module,
    reverse: bool = False,
):
    dimensions = (
        module.default_dimensions()
    )

    task_a = module.EvaluationTask(
        task_id="analysis_001",
        prompt=(
            "Analyze the supplied claim and "
            "separate fact from inference."
        ),
        domains=(
            "research",
            "analysis",
        ),
        target_traits=(
            "uncertainty_calibration",
            "analytical_rigor",
        ),
        dimensions=dimensions,
    )

    task_b = module.EvaluationTask(
        task_id="implementation_001",
        prompt=(
            "Produce the minimum compatible "
            "implementation satisfying the "
            "specified constraints."
        ),
        domains=(
            "engineering",
            "code",
        ),
        target_traits=(
            "coding_precision",
            "tool_judgment",
        ),
        dimensions=dimensions,
    )

    participant_a = (
        module.ExperimentParticipant(
            participant_id="participant_a",
            provider_id="openai_text",
            model_id="model-a",
            model_version="v1",
        )
    )

    participant_b = (
        module.ExperimentParticipant(
            participant_id="participant_b",
            provider_id="provider_b",
            model_id="model-b",
            model_version="v1",
        )
    )

    tasks = (
        (task_b, task_a)
        if reverse
        else (task_a, task_b)
    )

    participants = (
        (
            participant_b,
            participant_a,
        )
        if reverse
        else (
            participant_a,
            participant_b,
        )
    )

    return module.ExperimentPlan(
        experiment_id=(
            "orobouros-evaluation-001"
        ),
        trait_ids=(
            "coding_precision",
            "analytical_rigor",
            "tool_judgment",
            "uncertainty_calibration",
        ),
        tasks=tasks,
        participants=participants,
        repetitions=3,
    )


def main() -> int:
    module = load_module()

    plan_a = build_plan(
        module,
        reverse=False,
    )

    plan_b = build_plan(
        module,
        reverse=True,
    )

    if (
        plan_a.plan_id
        != plan_b.plan_id
    ):
        raise RuntimeError(
            "plan identity changed "
            "under equivalent ordering"
        )

    if (
        plan_a.projection()
        != plan_b.projection()
    ):
        raise RuntimeError(
            "blinded projection changed "
            "under equivalent ordering"
        )

    packets_a = (
        plan_a.execution_packets()
    )

    packets_b = (
        plan_b.execution_packets()
    )

    if packets_a != packets_b:
        raise RuntimeError(
            "execution packet projection "
            "is not deterministic"
        )

    expected_count = (
        len(
            plan_a.tasks
        )
        * len(
            plan_a.participants
        )
        * plan_a.repetitions
    )

    if (
        len(
            packets_a
        )
        != expected_count
    ):
        raise RuntimeError(
            "execution packet count "
            "is incorrect"
        )

    blinded = plan_a.projection(
        blinded=True
    )

    text = str(
        blinded
    )

    if (
        "openai_text"
        in text
        or "model-a"
        in text
        or "provider_b"
        in text
        or "model-b"
        in text
    ):
        raise RuntimeError(
            "provider/model identity "
            "leaked into blinded projection"
        )

    status = module.status()

    required = {
        "execution_owner": (
            "exile:opus"
        ),
        "verification_owner": (
            "exile:notary"
        ),
        "blind_evaluation": True,
        "identical_task_packets": True,
        "repeated_trials": True,
        "automatic_champion_selection": (
            False
        ),
        "automatic_evidence_admission": (
            False
        ),
        "baseline_mutation": False,
        "crown_mutation": False,
        "authoritative": False,
    }

    for key, expected in (
        required.items()
    ):
        if (
            status.get(
                key
            )
            != expected
        ):
            raise RuntimeError(
                f"status mismatch: {key}"
            )

    print(
        "OROBOUROS TRAIT EXPERIMENT "
        "DETERMINISM: PASS"
    )

    print(
        "plan_id="
        + plan_a.plan_id
    )

    print(
        "packet_count="
        + str(
            len(
                packets_a
            )
        )
    )

    print(
        "blind_evaluation=true"
    )

    print(
        "execution_owner=exile:opus"
    )

    print(
        "verification_owner=exile:notary"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

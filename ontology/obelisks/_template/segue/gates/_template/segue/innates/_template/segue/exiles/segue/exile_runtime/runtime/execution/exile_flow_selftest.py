from __future__ import annotations

import json

from .exile_flow import (
    architecture_projection,
    compose_pipeline,
    create_flow,
    execute_hop,
    flow_contract,
    flow_limits,
    fork_flow,
    prepare_exile,
    replay_projection,
)


def _opus(
    payload,
):
    return {
        **payload,
        "opus":
            "orchestrated",
    }


def _envoy(
    payload,
):
    return {
        **payload,
        "envoy":
            "projected",
    }


def _palaver(
    payload,
):
    return {
        **payload,
        "palaver":
            "presented",
    }


def run() -> dict:
    limits = flow_limits(
        max_hops=32,
        max_payload_bytes=65536,
        max_history=64,
    )

    initial = create_flow(
        source="exile:urge",
        target="exile:opus",
        capability="exile:opus:orchestrate",
        payload={
            "objective":
                "improve candidate",
        },
        payload_schema="savant://test/input/1.0.0",
        provenance={
            "source":
                "selftest",
        },
        limits=limits,
    )

    opus_contract = flow_contract(
        capability="exile:opus:orchestrate",
        source="exile:urge",
        target="exile:opus",
        accepted_schemas=(
            "savant://test/input/1.0.0",
        ),
        emitted_schema="savant://test/opus/1.0.0",
        replayable=True,
    )

    completed = execute_hop(
        initial,
        contract=opus_contract,
        handler=_opus,
    )

    child = fork_flow(
        completed,
        target="exile:envoy",
        capability="exile:envoy:project",
        payload_schema="savant://test/opus/1.0.0",
    )

    prepared = prepare_exile(
        exile="exile:underscore",
        capabilities=(
            "exile:underscore:future",
        ),
        extensions={
            "specific_code":
                "reserved",
        },
    )

    pipeline = compose_pipeline(
        source="exile:urge",
        payload={
            "objective":
                "continuous-flow",
        },
        payload_schema="savant://test/input/1.0.0",
        limits=limits,
        steps=(
            (
                opus_contract,
                _opus,
                (),
            ),
            (
                flow_contract(
                    capability="exile:envoy:project",
                    source="exile:opus",
                    target="exile:envoy",
                    accepted_schemas=(
                        "savant://test/opus/1.0.0",
                    ),
                    emitted_schema="savant://test/envoy/1.0.0",
                ),
                _envoy,
                (),
            ),
            (
                flow_contract(
                    capability="exile:palaver:present",
                    source="exile:envoy",
                    target="exile:palaver",
                    accepted_schemas=(
                        "savant://test/envoy/1.0.0",
                    ),
                    emitted_schema="savant://test/palaver/1.0.0",
                ),
                _palaver,
                (),
            ),
        ),
    )

    replay = replay_projection(
        completed
    )

    architecture = (
        architecture_projection()
    )

    checks = {
        "single_hop_complete":
            completed.state
            == "complete",
        "payload_preserved":
            completed.payload[
                "objective"
            ]
            == "improve candidate",
        "opus_output_present":
            completed.payload[
                "opus"
            ]
            == "orchestrated",
        "lineage_present":
            bool(
                completed.lineage
            ),
        "history_present":
            len(
                completed.history
            )
            == 3,
        "trace_preserved_on_fork":
            child.trace_id
            == completed.trace_id,
        "parent_preserved_on_fork":
            child.parent_flow_id
            == completed.flow_id,
        "prepared_exile_has_no_behavior":
            prepared[
                "boundaries"
            ][
                "creates_exile_behavior"
            ]
            is False,
        "prepared_exile_has_extension_space":
            prepared[
                "boundaries"
            ][
                "extension_space_reserved"
            ]
            is True,
        "pipeline_complete":
            pipeline.state
            == "complete",
        "pipeline_reaches_palaver":
            pipeline.payload[
                "palaver"
            ]
            == "presented",
        "pipeline_preserves_opus":
            pipeline.payload[
                "opus"
            ]
            == "orchestrated",
        "pipeline_preserves_envoy":
            pipeline.payload[
                "envoy"
            ]
            == "projected",
        "replayable":
            replay[
                "replayable"
            ]
            is True,
        "zero_authority_creation":
            completed.projection()[
                "boundaries"
            ][
                "creates_authority"
            ]
            is False,
        "twenty_plus_enhancements":
            architecture[
                "enhancement_count"
            ]
            >= 20,
        "no_external_dependencies":
            architecture[
                "boundaries"
            ][
                "external_dependencies_added"
            ]
            is False,
    }

    return {
        "schema":
            "savant://runtime/exiles/flow-selftest/1.0.0",
        "ok":
            all(
                checks.values()
            ),
        "checks":
            checks,
        "flow":
            completed.projection(
                include_payload=False
            ),
        "pipeline":
            pipeline.projection(
                include_payload=False
            ),
        "prepared":
            prepared,
        "architecture":
            architecture,
    }


def main() -> None:
    result = run()

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    if not result[
        "ok"
    ]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

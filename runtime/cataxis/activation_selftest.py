import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.cataxis.activation import (
    activation_projection,
    activation_state,
)
from runtime.cataxis.core import Catalyst


def main() -> int:
    dormant = Catalyst(
        catalyst_ref="catalyst:dormant",
        pressure=0.5,
        threshold=1.0,
    )

    threshold = Catalyst(
        catalyst_ref="catalyst:threshold",
        pressure=1.0,
        threshold=1.0,
    )

    active = Catalyst(
        catalyst_ref="catalyst:active",
        pressure=2.0,
        threshold=1.0,
    )

    zero = Catalyst(
        catalyst_ref="catalyst:zero",
        pressure=0.0,
        threshold=0.0,
    )

    dormant_state = activation_state(
        dormant
    )

    threshold_state = activation_state(
        threshold
    )

    active_state = activation_state(
        active
    )

    zero_state = activation_state(
        zero
    )

    assert (
        dormant_state.state
        == "dormant"
    )

    assert dormant_state.margin == -0.5

    assert (
        dormant_state.activation_ratio
        == 0.5
    )

    assert (
        threshold_state.state
        == "threshold"
    )

    assert threshold_state.margin == 0.0

    assert (
        threshold_state.activation_ratio
        == 1.0
    )

    assert active_state.state == "active"
    assert active_state.margin == 1.0

    assert (
        active_state.activation_ratio
        == 2.0
    )

    assert zero_state.state == "threshold"

    assert (
        zero_state.activation_ratio
        == 0.0
    )

    projection = activation_projection(
        (
            active,
            dormant,
            zero,
            threshold,
        )
    )

    assert projection["state_count"] == 4
    assert projection["dormant_count"] == 1
    assert projection["threshold_count"] == 2
    assert projection["active_count"] == 1

    assert (
        projection[
            "activation_is_projection"
        ]
        is True
    )

    assert (
        projection[
            "activation_side_effect"
        ]
        is False
    )

    assert (
        projection["source_mutated"]
        is False
    )

    assert (
        projection[
            "automatic_reconciliation"
        ]
        is False
    )

    assert (
        projection["authority_transferred"]
        is False
    )

    assert (
        projection["model_independent"]
        is True
    )

    assert (
        projection["provider_independent"]
        is True
    )

    assert (
        projection["authoritative"]
        is False
    )

    assert (
        projection["authority_effect"]
        == "none"
    )

    repeated = activation_projection(
        (
            threshold,
            zero,
            dormant,
            active,
        )
    )

    assert (
        repeated["digest"]
        == projection["digest"]
    )

    assert len(projection["digest"]) == 64

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

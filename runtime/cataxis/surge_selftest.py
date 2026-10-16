import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.cataxis.activation import (
    activation_state,
)
from runtime.cataxis.core import Catalyst
from runtime.cataxis.surge import (
    surge_projection,
    surge_state,
)


def main() -> int:
    dormant = Catalyst(
        catalyst_ref="catalyst:dormant",
        pressure=0.5,
        threshold=1.0,
        polarity=-1.0,
        surge_limit=1.0,
    )

    bounded = Catalyst(
        catalyst_ref="catalyst:bounded",
        pressure=3.0,
        threshold=1.0,
        polarity=0.5,
        surge_limit=0.75,
    )

    open_state = Catalyst(
        catalyst_ref="catalyst:open",
        pressure=1.5,
        threshold=1.0,
        polarity=-0.5,
        surge_limit=2.0,
    )

    dormant_surge = surge_state(
        dormant
    )

    assert dormant_surge.raw_surge == 0.0

    assert (
        dormant_surge.projected_surge
        == 0.0
    )

    assert dormant_surge.clipped is False

    bounded_activation = activation_state(
        bounded
    )

    bounded_surge = surge_state(
        bounded,
        bounded_activation,
    )

    assert bounded_surge.raw_surge == 2.0

    assert (
        bounded_surge.projected_surge
        == 0.75
    )

    assert bounded_surge.clipped is True

    assert (
        bounded_surge.signed_surge
        == 0.375
    )

    open_surge = surge_state(
        open_state
    )

    assert open_surge.raw_surge == 0.5

    assert (
        open_surge.projected_surge
        == 0.5
    )

    assert open_surge.clipped is False

    assert (
        open_surge.signed_surge
        == -0.25
    )

    projection = surge_projection(
        (
            open_state,
            dormant,
            bounded,
        )
    )

    assert projection["state_count"] == 3

    assert (
        projection["raw_surge_total"]
        == 2.5
    )

    assert (
        projection[
            "projected_surge_total"
        ]
        == 1.25
    )

    assert (
        projection["signed_surge_total"]
        == 0.125
    )

    assert projection["clipped_count"] == 1

    assert (
        projection["surge_is_projection"]
        is True
    )

    assert (
        projection["pressure_mutated"]
        is False
    )

    assert (
        projection["activation_mutated"]
        is False
    )

    assert (
        projection["automatic_discharge"]
        is False
    )

    assert (
        projection[
            "automatic_reconciliation"
        ]
        is False
    )

    assert (
        projection["source_mutated"]
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

    repeated = surge_projection(
        (
            bounded,
            open_state,
            dormant,
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

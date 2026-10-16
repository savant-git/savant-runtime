import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.cataxis.balance import (
    PressureContribution,
    balance_pressure,
    balance_projection,
)
from runtime.cataxis.core import Catalyst


def main() -> int:
    first = Catalyst(
        catalyst_ref="catalyst:a",
        pressure=1.0,
        threshold=0.5,
        polarity=-1.0,
        surge_limit=0.25,
    )

    second = Catalyst(
        catalyst_ref="catalyst:b",
        pressure=3.0,
        threshold=4.0,
        polarity=1.0,
        surge_limit=1.0,
    )

    contributions = (
        PressureContribution(
            catalyst_ref="catalyst:a",
            weight=2.0,
        ),
        PressureContribution(
            catalyst_ref="catalyst:b",
            weight=1.0,
        ),
    )

    result = balance_pressure(
        (
            second,
            first,
        ),
        contributions,
    )

    assert result.total_pressure == 4.0

    assert (
        result.weighted_pressure
        == 5.0
    )

    assert (
        result.mean_pressure
        == 5.0 / 3.0
    )

    assert result.net_polarity == 0.5

    assert result.active_count == 1
    assert result.dormant_count == 1

    assert result.surge_total == 0.25

    assert len(result.catalyst_refs) == 2

    projection = balance_projection(
        (
            first,
            second,
        ),
        contributions,
    )

    assert (
        projection[
            "balance_is_projection"
        ]
        is True
    )

    assert (
        projection[
            "activation_state_mutated"
        ]
        is False
    )

    assert (
        projection["pressure_mutated"]
        is False
    )

    assert (
        projection[
            "automatic_rebalancing"
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

    assert len(projection["digest"]) == 64

    repeated = balance_projection(
        (
            second,
            first,
        ),
        contributions,
    )

    assert (
        repeated["digest"]
        == projection["digest"]
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

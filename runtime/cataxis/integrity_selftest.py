import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.cataxis.core import Catalyst
from runtime.cataxis.integrity import (
    inspect_integrity,
    integrity_receipt,
)


def main() -> int:
    clipped = Catalyst(
        catalyst_ref="catalyst:clipped",
        pressure=3.0,
        threshold=1.0,
        surge_limit=0.5,
    )

    zero_limit = Catalyst(
        catalyst_ref="catalyst:zero-limit",
        pressure=2.0,
        threshold=1.0,
        surge_limit=0.0,
    )

    zero_threshold = Catalyst(
        catalyst_ref="catalyst:zero-threshold",
        pressure=1.0,
        threshold=0.0,
        surge_limit=2.0,
    )

    duplicate_a = Catalyst(
        catalyst_ref="catalyst:duplicate",
        pressure=0.25,
        threshold=1.0,
    )

    duplicate_b = Catalyst(
        catalyst_ref="catalyst:duplicate",
        pressure=0.5,
        threshold=1.0,
    )

    catalysts = (
        zero_threshold,
        duplicate_b,
        clipped,
        zero_limit,
        duplicate_a,
    )

    findings = inspect_integrity(
        catalysts
    )

    codes = [
        finding.code
        for finding in findings
    ]

    assert (
        codes.count(
            "duplicate-catalyst-ref"
        )
        == 1
    )

    assert (
        codes.count("surge-clipped")
        == 2
    )

    assert (
        codes.count(
            "active-zero-surge-limit"
        )
        == 1
    )

    assert (
        codes.count(
            "zero-threshold-active"
        )
        == 1
    )

    receipt = integrity_receipt(
        catalysts
    )

    assert receipt["conflict_count"] == 1
    assert receipt["warning_count"] == 1
    assert receipt["info_count"] == 3

    assert (
        receipt["finding_count"]
        == 5
    )

    assert (
        receipt["conflicts_preserved"]
        is True
    )

    assert (
        receipt[
            "automatic_reconciliation"
        ]
        is False
    )

    assert (
        receipt["automatic_mutation"]
        is False
    )

    assert (
        receipt["source_mutated"]
        is False
    )

    assert (
        receipt["authority_transferred"]
        is False
    )

    assert (
        receipt["model_independent"]
        is True
    )

    assert (
        receipt["provider_independent"]
        is True
    )

    assert (
        receipt["authoritative"]
        is False
    )

    assert (
        receipt["authority_effect"]
        == "none"
    )

    repeated = integrity_receipt(
        tuple(reversed(catalysts))
    )

    assert (
        repeated["digest"]
        == receipt["digest"]
    )

    assert len(receipt["digest"]) == 64

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

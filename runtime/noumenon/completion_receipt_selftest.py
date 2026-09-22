import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.completion import (
    completion_projection,
    completion_receipt,
    validate_runtime_result,
)
from runtime.noumenon.integration import (
    MECHANISMS,
    mechanism_projection,
)
from runtime.noumenon.integration_runtime import (
    establish_integration,
)


def main() -> int:
    mechanisms = tuple(
        mechanism_projection(
            mechanism,
            {
                "mechanism": mechanism,
                "derived": True,
                "authoritative": False,
                "authority_effect": "none",
            },
            causal_refs=(
                "experience:completion",
            ),
        )
        for mechanism in sorted(
            MECHANISMS
        )
    )

    result = establish_integration(
        noumenon_id="noumenon:completion",
        generation=0,
        mechanisms=mechanisms,
        causal_refs=(
            "state:completion",
        ),
    )

    assert validate_runtime_result(
        result
    )

    receipt = completion_receipt(
        result.integration
    )

    assert receipt.complete is True
    assert receipt.absent_mechanisms == ()

    assert (
        len(receipt.present_mechanisms)
        == len(MECHANISMS)
    )

    assert (
        receipt.integration_ref
        in receipt.causal_refs
    )

    projection = completion_projection(
        receipt
    )

    assert projection["complete"] is True

    assert (
        projection[
            "missing_mechanism_count"
        ]
        == 0
    )

    assert (
        projection[
            "mechanism_coverage"
        ]
        == len(MECHANISMS)
    )

    assert (
        projection[
            "persistent_individual"
        ]
        == "noumenon:completion"
    )

    assert (
        projection[
            "model_is_identity"
        ]
        is False
    )

    assert (
        projection[
            "provider_is_identity"
        ]
        is False
    )

    assert (
        projection[
            "derived_state_is_external_fact"
        ]
        is False
    )

    assert (
        projection[
            "causal_continuity_required"
        ]
        is True
    )

    assert (
        projection[
            "authority_isolation_preserved"
        ]
        is True
    )

    assert (
        projection[
            "completion_is_authority"
        ]
        is False
    )

    assert (
        projection["authoritative"]
        is False
    )

    assert (
        projection["authority_effect"]
        == "none"
    )

    partial = establish_integration(
        noumenon_id="noumenon:partial",
        generation=0,
        mechanisms=(
            mechanisms[0],
        ),
        causal_refs=(
            "state:partial",
        ),
    )

    partial_receipt = completion_receipt(
        partial.integration
    )

    assert (
        partial_receipt.complete
        is False
    )

    assert (
        len(
            partial_receipt
            .absent_mechanisms
        )
        == len(MECHANISMS) - 1
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

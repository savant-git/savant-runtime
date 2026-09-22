import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.oid.completion import REQUIREMENTS
from runtime.oid.manifest import (
    MODULES,
    oid_manifest,
    validate_manifest,
)


def main() -> int:
    manifest = oid_manifest()

    assert validate_manifest()

    assert manifest["name"] == "oid"

    assert (
        manifest["semantic_scope"]
        == "temporal_coherence"
    )

    assert len(REQUIREMENTS) == 35

    assert (
        manifest["requirement_count"]
        == 35
    )

    assert (
        manifest["implemented_count"]
        == 35
    )

    assert (
        manifest["missing_requirements"]
        == []
    )

    assert manifest["complete"] is True

    required_modules = {
        "runtime.oid.core",
        "runtime.oid.frame",
        "runtime.oid.clock",
        "runtime.oid.constraint",
        "runtime.oid.store",
        "runtime.oid.recovery",
        "runtime.oid.runtime",
        "runtime.oid.projection",
        "runtime.oid.bridge",
        "runtime.oid.conversion",
        "runtime.oid.integrity",
        "runtime.oid.completion",
    }

    assert set(MODULES) == required_modules

    assert (
        manifest[
            "universal_single_present_claimed"
        ]
        is False
    )

    assert (
        manifest[
            "external_truth_authority"
        ]
        is False
    )

    assert (
        manifest[
            "external_chronology_authority"
        ]
        is False
    )

    assert (
        manifest[
            "automatic_reconciliation"
        ]
        is False
    )

    assert (
        manifest["authority_transferred"]
        is False
    )

    assert (
        manifest["model_independent"]
        is True
    )

    assert (
        manifest["provider_independent"]
        is True
    )

    assert (
        manifest["dependency_sovereign"]
        is True
    )

    assert (
        manifest["stdlib_capable"]
        is True
    )

    assert (
        manifest[
            "historical_halo_required"
        ]
        is False
    )

    assert (
        manifest["authoritative"]
        is False
    )

    assert (
        manifest["authority_effect"]
        == "none"
    )

    assert len(manifest["digest"]) == 64

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

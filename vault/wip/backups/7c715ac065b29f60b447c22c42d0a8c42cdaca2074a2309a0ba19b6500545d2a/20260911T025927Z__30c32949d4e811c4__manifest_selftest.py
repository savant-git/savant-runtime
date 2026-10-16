import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.catax.manifest import (
    MODULES,
    catax_manifest,
    validate_manifest,
)


def main() -> int:
    manifest = catax_manifest()

    assert manifest["name"] == "catax"

    assert (
        manifest["semantic_scope"]
        == "temporal_geometry"
    )

    assert (
        manifest["historical_kernel"]
        == "catax_applies_temporal_geometry"
    )

    assert len(MODULES) == 6

    assert manifest["module_count"] == 6

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

    assert (
        manifest[
            "historical_halo_required"
        ]
        is False
    )

    assert (
        manifest[
            "historical_catena_required"
        ]
        is False
    )

    assert (
        manifest[
            "metaphysical_rotation_required"
        ]
        is False
    )

    assert (
        manifest[
            "fixed_catax_taxonomy_required"
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
        manifest[
            "authority_transferred"
        ]
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
        manifest["authoritative"]
        is False
    )

    assert (
        manifest["authority_effect"]
        == "none"
    )

    assert len(manifest["digest"]) == 64

    assert validate_manifest() is True

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

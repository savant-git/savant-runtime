import sys

sys.path.insert(0, "/root/savant-runtime")

from runtime.glyph.composition import GlyphRegistry
from runtime.noumenon.state import (
    DevelopmentalConsequence,
    Experience,
    Significance,
    TransitionCandidate,
    continuity_receipt,
    empty_state,
)


def main() -> int:
    registry = GlyphRegistry()

    source = "noumenon"
    composition = registry.decompose_text(source)

    assert registry.materialize(composition) == source
    assert len(registry.values()) < len(source)

    before = empty_state("selftest")

    candidate = TransitionCandidate(
        predecessor=before,
        experience=Experience(
            id="experience:selftest",
            observed=True,
            owned=True,
        ),
        significance=Significance(
            dimensions={
                "personal": 0.5,
            }
        ),
        consequences=(
            DevelopmentalConsequence(
                dimension="trust",
                delta=0.1,
                causal_refs=(
                    "experience:selftest",
                ),
            ),
        ),
    )

    after = candidate.successor()

    receipt = continuity_receipt(
        before,
        after,
        transition_refs=after.lineage_refs,
    )

    assert after.generation == 1
    assert after.dimensions["trust"] == 0.1
    assert receipt["integrity_digest"]

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

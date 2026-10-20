
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from iteration_controller import digest, verify


schema = "savant://runtime/urge/iteration-lineage/1.0.0"


class lineage_error(ValueError):
    pass


def verify_lineage(
    session: Mapping[str, Any],
) -> dict[str, Any]:
    current = verify(session)
    predecessor = None

    for index, entry in enumerate(
        current["history"],
        1,
    ):
        if not isinstance(entry, Mapping):
            raise lineage_error(
                "invalid iteration entry"
            )

        if entry.get("iteration") != index:
            raise lineage_error(
                "iteration order mismatch"
            )

        if entry.get("previous") != predecessor:
            raise lineage_error(
                "iteration predecessor mismatch"
            )

        unsigned = dict(entry)
        signature = unsigned.pop("digest", None)

        if not isinstance(signature, str):
            raise lineage_error(
                "iteration digest is missing"
            )

        if digest(unsigned) != signature:
            raise lineage_error(
                "iteration digest mismatch"
            )

        evidence = entry.get("execution")

        if not isinstance(evidence, Mapping) or not evidence:
            raise lineage_error(
                "iteration execution evidence is missing"
            )

        predecessor = signature

    return current


def project_lineage(
    session: Mapping[str, Any],
) -> dict[str, Any]:
    current = verify_lineage(session)
    entries = current["history"]

    return {
        "schema": schema,
        "session_id": current["session_id"],
        "session_digest": current["digest"],
        "iteration_count": len(entries),
        "iteration_limit": current["iteration_limit"],
        "head_digest": (
            entries[-1]["digest"]
            if entries
            else None
        ),
        "entries": [
            {
                "iteration": entry["iteration"],
                "digest": entry["digest"],
                "previous": entry["previous"],
                "recorded_at": entry["recorded_at"],
            }
            for entry in entries
        ],
    }

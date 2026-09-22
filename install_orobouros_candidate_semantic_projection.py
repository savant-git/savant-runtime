#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path


TARGET = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/envoy/"
    "runtime/trait_evidence.py"
)

OLD_PROPERTIES = '''    @property
    def confidence_range(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        values = tuple(
            observation.confidence
            for observation
            in self.observations
        )

        return (
            min(
                values
            ),
            max(
                values
            ),
        )

    def projection(
'''

NEW_PROPERTIES = '''    @property
    def domains(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    domain
                    for observation
                    in self.observations
                    for domain
                    in observation.domains
                }
            )
        )

    @property
    def signals(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    signal
                    for observation
                    in self.observations
                    for signal
                    in observation.signals
                }
            )
        )

    @property
    def conflicts(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    conflict
                    for observation
                    in self.observations
                    for conflict
                    in observation.conflicts
                }
            )
        )

    @property
    def confidence_range(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        values = tuple(
            observation.confidence
            for observation
            in self.observations
        )

        return (
            min(
                values
            ),
            max(
                values
            ),
        )

    def projection(
'''

OLD_PROJECTION = '''            "description": (
                self.description
            ),
            "observation_ids": [
'''

NEW_PROJECTION = '''            "description": (
                self.description
            ),
            "domains": list(
                self.domains
            ),
            "signals": list(
                self.signals
            ),
            "conflicts": list(
                self.conflicts
            ),
            "observation_ids": [
'''

def replace_once(
    content: str,
    old: str,
    new: str,
    label: str,
) -> str:
    count = content.count(
        old
    )

    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one "
            f"match, found {count}"
        )

    return content.replace(
        old,
        new,
        1,
    )


def main() -> int:
    if not TARGET.is_file():
        raise RuntimeError(
            f"target missing: {TARGET}"
        )

    content = TARGET.read_text(
        encoding="utf-8"
    )

    already_installed = (
        "def domains(" in content
        and '"domains": list(' in content
        and '"signals": list(' in content
        and '"conflicts": list(' in content
    )

    if already_installed:
        print(
            "OROBOUROS CANDIDATE SEMANTIC "
            "PROJECTION: already installed"
        )
        return 0

    updated = replace_once(
        content,
        OLD_PROPERTIES,
        NEW_PROPERTIES,
        "candidate semantic properties",
    )

    updated = replace_once(
        updated,
        OLD_PROJECTION,
        NEW_PROJECTION,
        "candidate semantic projection",
    )

    TARGET.write_text(
        updated,
        encoding="utf-8",
    )

    print(
        "OROBOUROS CANDIDATE SEMANTIC "
        "PROJECTION: installed"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

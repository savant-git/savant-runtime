from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from runtime.leveled_earmarks import (
    earmark_error,
    leveled_earmark_registry,
)
from runtime.earmark_projection import (
    earmark_projection_registry,
    projection_error,
)


runtime_root = Path("/root/savant-runtime")


class living_lexicon_error(RuntimeError):
    pass


class living_lexicon:
    def __init__(self) -> None:
        self.earmarks = leveled_earmark_registry()
        self.projections = earmark_projection_registry()

    def find_level_zero(
        self,
        *,
        namespace: str,
        identity_seed: str,
    ) -> str | None:
        for identity, record in self.earmarks.registry["earmarks"].items():
            if (
                record["level"] == 0
                and record["namespace"] == namespace
                and record["identity_seed"] == identity_seed
            ):
                return identity

        return None

    def establish(
        self,
        *,
        namespace: str,
        value: str,
        identity_seed: str,
    ) -> dict[str, Any]:
        existing = self.find_level_zero(
            namespace=namespace,
            identity_seed=identity_seed,
        )

        if existing is None:
            identity = self.earmarks.establish_level_zero(
                namespace=namespace,
                value=value,
                identity_seed=identity_seed,
                metadata={
                    "owner": "lexicon",
                    "living": True,
                },
            )
        else:
            identity = existing

        return self.describe(identity)

    def change(
        self,
        *,
        identity: str,
        value: str,
    ) -> dict[str, Any]:
        before = self.earmarks.resolve(identity)

        change = self.earmarks.supersede_level_zero(
            identity,
            value,
            metadata={
                "owner": "lexicon",
                "living": True,
                "operation": "terminology-supersession",
            },
        )

        affected_earmarks = [
            identity,
            *change.get("affected", []),
        ]

        propagation = self.projections.render_for_earmarks(
            affected_earmarks
        )

        after = self.earmarks.resolve(identity)

        return {
            "changed": change["changed"],
            "earmark": identity,
            "previous_value": before.value,
            "value": after.value,
            "revision": after.revision,
            "affected_earmarks": sorted(
                set(affected_earmarks)
            ),
            "propagation": propagation,
        }

    def describe(self, identity: str) -> dict[str, Any]:
        record = self.earmarks.describe(identity)

        return {
            **record,
            "projection_dependents": self.projections.registry[
                "dependencies"
            ].get(identity, []),
        }

    def verify(self) -> dict[str, Any]:
        earmarks = self.earmarks.verify()
        projections = self.projections.verify()

        failures = [
            *[
                f"earmark: {failure}"
                for failure in earmarks["failures"]
            ],
            *[
                f"projection: {failure}"
                for failure in projections["failures"]
            ],
        ]

        return {
            "schema": "savant.living-lexicon.v1",
            "passed": not failures,
            "earmark_count": earmarks["earmark_count"],
            "glyph_count": earmarks["glyph_count"],
            "harmony_count": earmarks["harmony_count"],
            "projection_count": projections["projection_count"],
            "failures": failures,
        }


def print_json(value: Any) -> None:
    print(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )


def command_establish(args: argparse.Namespace) -> int:
    engine = living_lexicon()

    print_json(
        engine.establish(
            namespace=args.namespace,
            value=args.value,
            identity_seed=args.identity,
        )
    )

    return 0


def command_change(args: argparse.Namespace) -> int:
    engine = living_lexicon()

    print_json(
        engine.change(
            identity=args.earmark,
            value=args.value,
        )
    )

    return 0


def command_describe(args: argparse.Namespace) -> int:
    engine = living_lexicon()
    print_json(engine.describe(args.earmark))
    return 0


def command_verify(_: argparse.Namespace) -> int:
    engine = living_lexicon()
    result = engine.verify()
    print_json(result)
    return 0 if result["passed"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="living-lexicon",
        description=(
            "savant living terminology propagation through "
            "leveled earmarks"
        ),
    )

    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )

    establish = commands.add_parser("establish")
    establish.add_argument("namespace")
    establish.add_argument("value")
    establish.add_argument("identity")
    establish.set_defaults(function=command_establish)

    change = commands.add_parser("change")
    change.add_argument("earmark")
    change.add_argument("value")
    change.set_defaults(function=command_change)

    describe = commands.add_parser("describe")
    describe.add_argument("earmark")
    describe.set_defaults(function=command_describe)

    verify = commands.add_parser("verify")
    verify.set_defaults(function=command_verify)

    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        return int(args.function(args))
    except (
        earmark_error,
        projection_error,
        living_lexicon_error,
        OSError,
        UnicodeError,
    ) as error:
        print_json(
            {
                "passed": False,
                "error": type(error).__name__,
                "message": str(error),
            }
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

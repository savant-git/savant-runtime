#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, Sequence


schema = "savant://runtime/extr/pass-engine/1.0.0"
owner = "extr"
authority_effect = "none"


class pass_engine_error(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class pass_definition:
    id: str
    purpose: str

    def projection(self) -> dict[str, str]:
        return {
            "id": self.id,
            "purpose": self.purpose,
        }


@dataclass(frozen=True, slots=True)
class pass_receipt:
    pass_id: str
    input_digest: str
    output_digest: str
    processor: str
    deterministic: bool
    opus_used: bool
    authority_effect: str = "none"

    def projection(self) -> dict[str, Any]:
        return {
            "pass_id": self.pass_id,
            "input_digest": self.input_digest,
            "output_digest": self.output_digest,
            "processor": self.processor,
            "deterministic": self.deterministic,
            "opus_used": self.opus_used,
            "authority_effect": self.authority_effect,
        }


@dataclass(frozen=True, slots=True)
class pass_result:
    value: Any
    receipts: tuple[pass_receipt, ...]

    def projection(self) -> dict[str, Any]:
        return {
            "schema": schema,
            "owner": owner,
            "authority_effect": authority_effect,
            "authoritative": False,
            "rebuildable": True,
            "value": self.value,
            "receipts": [
                receipt.projection()
                for receipt in self.receipts
            ],
        }


processor = Callable[
    [Any, Mapping[str, Any]],
    Any,
]


class pass_engine:
    def __init__(
        self,
        definitions: Iterable[pass_definition],
    ) -> None:
        materialized = tuple(definitions)

        ids = tuple(
            definition.id
            for definition in materialized
        )

        if len(ids) != len(set(ids)):
            raise pass_engine_error(
                "duplicate pass id"
            )

        self._definitions = MappingProxyType(
            {
                definition.id: definition
                for definition in materialized
            }
        )

        self._processors: dict[
            str,
            tuple[
                processor,
                bool,
                bool,
            ]
        ] = {}

    @classmethod
    def from_file(
        cls,
        path: Path,
    ) -> "pass_engine":
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        raw_passes = payload.get(
            "passes",
            [],
        )

        definitions = []

        for raw in raw_passes:
            if not isinstance(raw, Mapping):
                continue

            pass_id = str(
                raw.get("id", "")
            ).strip()

            purpose = str(
                raw.get("purpose", "")
            ).strip()

            if not pass_id or not purpose:
                raise pass_engine_error(
                    "pass requires id and purpose"
                )

            definitions.append(
                pass_definition(
                    id=pass_id,
                    purpose=purpose,
                )
            )

        return cls(definitions)

    @property
    def definitions(
        self,
    ) -> Mapping[
        str,
        pass_definition,
    ]:
        return self._definitions

    def register(
        self,
        pass_id: str,
        handler: processor,
        *,
        deterministic: bool = True,
        opus_used: bool = False,
    ) -> None:
        if pass_id not in self._definitions:
            raise pass_engine_error(
                f"unknown pass: {pass_id}"
            )

        if not callable(handler):
            raise pass_engine_error(
                "handler must be callable"
            )

        self._processors[pass_id] = (
            handler,
            bool(deterministic),
            bool(opus_used),
        )

    def execute(
        self,
        value: Any,
        pass_ids: Sequence[str],
        *,
        context: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> pass_result:
        current = value
        receipts: list[
            pass_receipt
        ] = []

        safe_context = MappingProxyType(
            dict(context or {})
        )

        for pass_id in pass_ids:
            if pass_id not in self._definitions:
                raise pass_engine_error(
                    f"unknown pass: {pass_id}"
                )

            registered = self._processors.get(
                pass_id
            )

            if registered is None:
                raise pass_engine_error(
                    f"pass has no processor: {pass_id}"
                )

            handler, deterministic, opus_used = (
                registered
            )

            input_digest = digest(current)

            output = handler(
                current,
                safe_context,
            )

            output_digest = digest(output)

            receipts.append(
                pass_receipt(
                    pass_id=pass_id,
                    input_digest=input_digest,
                    output_digest=output_digest,
                    processor=(
                        f"{handler.__module__}."
                        f"{handler.__qualname__}"
                    ),
                    deterministic=deterministic,
                    opus_used=opus_used,
                )
            )

            current = output

        return pass_result(
            value=current,
            receipts=tuple(receipts),
        )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": schema,
            "owner": owner,
            "authority_effect": authority_effect,
            "authoritative": False,
            "passes": [
                definition.projection()
                for definition
                in self._definitions.values()
            ],
            "registered": sorted(
                self._processors
            ),
        }


def identity_processor(
    value: Any,
    context: Mapping[str, Any],
) -> Any:
    return value


def selftest() -> dict[str, Any]:
    definitions = (
        pass_definition(
            id="first",
            purpose="first test pass",
        ),
        pass_definition(
            id="second",
            purpose="second test pass",
        ),
    )

    engine = pass_engine(
        definitions
    )

    def first(
        value: Any,
        context: Mapping[str, Any],
    ) -> Any:
        return {
            "value": value,
            "first": True,
        }

    def second(
        value: Any,
        context: Mapping[str, Any],
    ) -> Any:
        return {
            "value": value,
            "second": True,
        }

    engine.register(
        "first",
        first,
    )

    engine.register(
        "second",
        second,
    )

    a = engine.execute(
        {"source": "x"},
        ("first", "second"),
    )

    b = engine.execute(
        {"source": "x"},
        ("first", "second"),
    )

    checks = {
        "deterministic":
            a.projection()
            == b.projection(),
        "two_receipts":
            len(a.receipts) == 2,
        "ordered":
            tuple(
                receipt.pass_id
                for receipt in a.receipts
            )
            == (
                "first",
                "second",
            ),
        "lineage_chained":
            a.receipts[0].output_digest
            == a.receipts[1].input_digest,
        "authority_none":
            all(
                receipt.authority_effect
                == "none"
                for receipt in a.receipts
            ),
    }

    return {
        "schema":
            "savant://runtime/extr/"
            "pass-engine-selftest/1.0.0",
        "ok": all(
            checks.values()
        ),
        "checks": checks,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            sort_keys=True,
            indent=2,
        )
    )

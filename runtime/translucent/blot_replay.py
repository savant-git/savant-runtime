#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


name = "blot."
schema = "savant.translucent.blot.replay.v1"
authority_effect = "none"
mutation_effect = "none"
projection_only = True


class BlotReplayError(ValueError):
    pass


def _canonical(
    value: Any,
) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise BlotReplayError(
            "value is not canonical-json compatible"
        ) from exc


def _digest(
    value: Any,
) -> str:
    if isinstance(
        value,
        bytes,
    ):
        raw = value
    elif isinstance(
        value,
        str,
    ):
        raw = value.encode(
            "utf-8"
        )
    else:
        raw = _canonical(
            value
        ).encode(
            "utf-8"
        )

    return hashlib.sha256(
        raw
    ).hexdigest()


def _text(
    value: Any,
    field_name: str,
) -> str:
    result = str(
        value or ""
    ).strip()

    if not result:
        raise BlotReplayError(
            f"{field_name} is required"
        )

    return result


def _unique(
    values: Iterable[Any],
) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        token = str(
            value or ""
        ).strip()

        if (
            not token
            or token in seen
        ):
            continue

        seen.add(
            token
        )

        result.append(
            token
        )

    return tuple(
        result
    )


@dataclass(frozen=True)
class ReplayBinding:
    source_digest: str
    construction_digest: str
    execution_digest: str
    profile_id: str
    projection_digest: str
    dependency_digests: tuple[
        str,
        ...
    ] = ()
    lineage: tuple[
        str,
        ...
    ] = ()
    provenance: tuple[
        str,
        ...
    ] = ()

    def normalized(
        self,
    ) -> dict[str, Any]:
        body = {
            "source_digest":
                _text(
                    self.source_digest,
                    "source_digest",
                ),

            "construction_digest":
                _text(
                    self.construction_digest,
                    "construction_digest",
                ),

            "execution_digest":
                _text(
                    self.execution_digest,
                    "execution_digest",
                ),

            "profile_id":
                _text(
                    self.profile_id,
                    "profile_id",
                ),

            "projection_digest":
                _text(
                    self.projection_digest,
                    "projection_digest",
                ),

            "dependency_digests":
                list(
                    _unique(
                        self.dependency_digests
                    )
                ),

            "lineage":
                list(
                    _unique(
                        self.lineage
                    )
                ),

            "provenance":
                list(
                    _unique(
                        self.provenance
                    )
                ),
        }

        return {
            **body,
            "digest":
                _digest(
                    body
                ),
        }


@dataclass(frozen=True)
class ReplayResult:
    binding_digest: str
    expected_projection_digest: str
    observed_projection_digest: str
    deterministic: bool

    def normalized(
        self,
    ) -> dict[str, Any]:
        expected = _text(
            self.expected_projection_digest,
            "expected_projection_digest",
        )

        observed = _text(
            self.observed_projection_digest,
            "observed_projection_digest",
        )

        deterministic = (
            expected
            == observed
        )

        if (
            bool(
                self.deterministic
            )
            != deterministic
        ):
            raise BlotReplayError(
                "deterministic state does not "
                "match projection digests"
            )

        body = {
            "schema":
                schema,

            "name":
                name,

            "binding_digest":
                _text(
                    self.binding_digest,
                    "binding_digest",
                ),

            "expected_projection_digest":
                expected,

            "observed_projection_digest":
                observed,

            "deterministic":
                deterministic,

            "authority_effect":
                authority_effect,

            "mutation_effect":
                mutation_effect,

            "projection_only":
                projection_only,
        }

        return {
            **body,
            "digest":
                _digest(
                    body
                ),
        }


def bind(
    *,
    source_digest: str,
    construction_digest: str,
    execution_digest: str,
    profile_id: str,
    projection: str | bytes,
    dependency_digests: Iterable[
        str
    ] = (),
    lineage: Iterable[
        str
    ] = (),
    provenance: Iterable[
        str
    ] = (),
) -> ReplayBinding:
    projection_digest = (
        _digest(
            projection
        )
    )

    binding = ReplayBinding(
        source_digest=
            source_digest,

        construction_digest=
            construction_digest,

        execution_digest=
            execution_digest,

        profile_id=
            profile_id,

        projection_digest=
            projection_digest,

        dependency_digests=
            tuple(
                dependency_digests
            ),

        lineage=
            tuple(
                lineage
            ),

        provenance=
            tuple(
                provenance
            ),
    )

    binding.normalized()

    return binding


def replay(
    binding: ReplayBinding
    | Mapping[str, Any],
    projection: str | bytes,
) -> ReplayResult:
    if isinstance(
        binding,
        ReplayBinding,
    ):
        normalized = (
            binding.normalized()
        )
    elif isinstance(
        binding,
        Mapping,
    ):
        normalized = dict(
            binding
        )
    else:
        raise BlotReplayError(
            "binding must be ReplayBinding "
            "or mapping"
        )

    binding_digest = str(
        normalized.get(
            "digest"
        )
        or _digest(
            normalized
        )
    ).strip()

    expected = _text(
        normalized.get(
            "projection_digest"
        ),
        "projection_digest",
    )

    observed = _digest(
        projection
    )

    result = ReplayResult(
        binding_digest=
            binding_digest,

        expected_projection_digest=
            expected,

        observed_projection_digest=
            observed,

        deterministic=
            expected
            == observed,
    )

    result.normalized()

    return result


def replay_manifest(
    binding: ReplayBinding
    | Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(
        binding,
        ReplayBinding,
    ):
        normalized = (
            binding.normalized()
        )
    elif isinstance(
        binding,
        Mapping,
    ):
        normalized = dict(
            binding
        )
    else:
        raise BlotReplayError(
            "binding must be ReplayBinding "
            "or mapping"
        )

    body = {
        "schema":
            f"{schema}.manifest",

        "name":
            name,

        "binding_digest":
            str(
                normalized.get(
                    "digest"
                )
                or _digest(
                    normalized
                )
            ),

        "source_digest":
            _text(
                normalized.get(
                    "source_digest"
                ),
                "source_digest",
            ),

        "construction_digest":
            _text(
                normalized.get(
                    "construction_digest"
                ),
                "construction_digest",
            ),

        "execution_digest":
            _text(
                normalized.get(
                    "execution_digest"
                ),
                "execution_digest",
            ),

        "profile_id":
            _text(
                normalized.get(
                    "profile_id"
                ),
                "profile_id",
            ),

        "projection_digest":
            _text(
                normalized.get(
                    "projection_digest"
                ),
                "projection_digest",
            ),

        "dependency_digests":
            list(
                normalized.get(
                    "dependency_digests",
                    (),
                )
            ),

        "lineage":
            list(
                normalized.get(
                    "lineage",
                    (),
                )
            ),

        "provenance":
            list(
                normalized.get(
                    "provenance",
                    (),
                )
            ),

        "authority_effect":
            authority_effect,

        "mutation_effect":
            mutation_effect,

        "projection_only":
            projection_only,

        "projection_is_authority":
            False,

        "reconstruct_from_projection":
            False,
    }

    return {
        **body,
        "digest":
            _digest(
                body
            ),
    }


def manifest() -> dict[str, Any]:
    body = {
        "schema":
            schema,

        "name":
            name,

        "authority_effect":
            authority_effect,

        "mutation_effect":
            mutation_effect,

        "projection_only":
            projection_only,

        "determinism":
            "sha256-byte-exact",

        "canonical_source":
            "construction-graph",

        "projection_is_authority":
            False,

        "reconstruct_from_projection":
            False,

        "deleting_projection_deletes_source":
            False,

        "lineage_preserved":
            True,

        "provenance_preserved":
            True,
    }

    return {
        **body,
        "digest":
            _digest(
                body
            ),
    }


__all__ = [
    "BlotReplayError",
    "ReplayBinding",
    "ReplayResult",
    "authority_effect",
    "bind",
    "manifest",
    "mutation_effect",
    "name",
    "projection_only",
    "replay",
    "replay_manifest",
    "schema",
]


if __name__ == "__main__":
    print(
        json.dumps(
            manifest(),
            indent=2,
            sort_keys=True,
        )
    )

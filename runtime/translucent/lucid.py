#!/usr/bin/env python3

from __future__ import annotations

import ast
import hashlib
import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .shard_ir import (
    SegueShard,
    Shard,
    ShardIRError,
    ShardProgram,
)


schema = "savant.translucent.lucid.v1"
authority_effect = "none"

FILE_EXTENSION = ".lucid"

MAX_SOURCE_CHARS = 2_000_000
MAX_LINES = 100_000
MAX_TOKENS_PER_LINE = 512


class LucidError(
    ValueError
):
    pass


@dataclass(
    slots=True,
)
class _ShardDraft:
    shard_id: str
    kind: str
    payload: dict[
        str,
        Any,
    ]
    bindings: dict[
        str,
        str,
    ]
    dependencies: list[
        str
    ]
    provenance: dict[
        str,
        Any,
    ]
    lineage: dict[
        str,
        Any,
    ]
    truth: str


def _strip_ref(
    value: str,
    field: str,
) -> str:
    text = str(
        value
        or ""
    ).strip()

    if (
        not text.startswith(
            "@"
        )
        or len(
            text
        )
        < 2
    ):
        raise LucidError(
            f"{field} must be an @reference"
        )

    return text[
        1:
    ].casefold()


def _tokens(
    line: str,
) -> list[
    str
]:
    lexer = shlex.shlex(
        line,
        posix=False,
    )

    lexer.whitespace_split = True
    lexer.commenters = ""

    try:
        values = list(
            lexer
        )

    except ValueError as exc:
        raise LucidError(
            f"invalid lucid line: {exc}"
        ) from exc

    if (
        len(
            values
        )
        > MAX_TOKENS_PER_LINE
    ):
        raise LucidError(
            "line exceeds "
            f"{MAX_TOKENS_PER_LINE} tokens"
        )

    result: list[
        str
    ] = []

    for raw in values:
        if (
            len(
                raw
            )
            >= 2
            and raw[
                0
            ]
            in {
                "'",
                '"',
            }
            and raw[
                -1
            ]
            == raw[
                0
            ]
        ):
            try:
                value = (
                    ast.literal_eval(
                        raw
                    )
                )

            except (
                SyntaxError,
                ValueError,
            ) as exc:
                raise LucidError(
                    "invalid quoted token: "
                    f"{raw!r}"
                ) from exc

            if not isinstance(
                value,
                str,
            ):
                raise LucidError(
                    "quoted token must "
                    "resolve to a string"
                )

            result.append(
                value
            )

        else:
            result.append(
                raw
            )

    return result


def _literal(
    tokens: Iterable[
        str
    ],
) -> Any:
    values = list(
        tokens
    )

    if not values:
        raise LucidError(
            "value is required"
        )

    raw = " ".join(
        values
    )

    if (
        len(
            values
        )
        == 1
        and values[
            0
        ].startswith(
            "@"
        )
    ):
        return {
            "$ref":
                _strip_ref(
                    values[
                        0
                    ],
                    "value",
                )
        }

    lowered = (
        raw.casefold()
    )

    if lowered == "true":
        return True

    if lowered == "false":
        return False

    if lowered == "null":
        return None

    try:
        return json.loads(
            raw
        )

    except json.JSONDecodeError:
        return raw


def _assignment(
    tokens: list[
        str
    ],
    start: int = 0,
) -> tuple[
    str,
    Any,
]:
    if (
        len(
            tokens
        )
        <= start + 2
        or tokens[
            start + 1
        ]
        != "="
    ):
        raise LucidError(
            "assignment form is: "
            "with <name> = <value>"
        )

    key = str(
        tokens[
            start
        ]
    ).strip().casefold()

    if not key:
        raise LucidError(
            "assignment name is required"
        )

    return (
        key,
        _literal(
            tokens[
                start + 2:
            ]
        ),
    )


def _provenance(
    source_name: str,
    source_digest: str,
    line: int,
) -> dict[
    str,
    Any,
]:
    return {
        "source":
            source_name,

        "source_digest":
            source_digest,

        "line":
            line,

        "language":
            "translucent",

        "surface":
            "lucid",
    }


class LucidCompiler:
    """
    Compile .lucid Translucent source into canonical
    shard/segue-shard IR.

    The syntax is deliberately graph-native rather than
    javascript-like.

        lucid 1

        @input :: data
          with value = 41
          truth supported

        @work :: operation
          bind source -> @input
          needs @input
          with verb = "increment"

        @input => @work :: feeds

    Every executable declaration becomes a shard or
    segue shard.
    """

    def __init__(
        self,
        *,
        grammar_version: str = "1",
    ) -> None:
        self.grammar_version = str(
            grammar_version
        )

    def compile(
        self,
        source: str,
        *,
        source_name: str = "memory.lucid",
    ) -> ShardProgram:
        if (
            len(
                source
            )
            > MAX_SOURCE_CHARS
        ):
            raise LucidError(
                "source exceeds "
                f"{MAX_SOURCE_CHARS} characters"
            )

        lines = (
            source.splitlines()
        )

        if (
            len(
                lines
            )
            > MAX_LINES
        ):
            raise LucidError(
                "source exceeds "
                f"{MAX_LINES} lines"
            )

        source_digest = (
            hashlib.sha256(
                source.encode(
                    "utf-8"
                )
            ).hexdigest()
        )

        drafts: dict[
            str,
            _ShardDraft,
        ] = {}

        segues: list[
            SegueShard
        ] = []

        current: (
            _ShardDraft
            | None
        ) = None

        header_seen = False

        for (
            line_number,
            raw_line,
        ) in enumerate(
            lines,
            1,
        ):
            stripped = (
                raw_line.strip()
            )

            if (
                not stripped
                or stripped.startswith(
                    "#"
                )
            ):
                continue

            indent = (
                len(
                    raw_line
                )
                - len(
                    raw_line.lstrip(
                        " "
                    )
                )
            )

            if (
                "\t"
                in raw_line[
                    :indent
                ]
            ):
                raise LucidError(
                    "tabs are forbidden for "
                    "indentation at line "
                    f"{line_number}"
                )

            tokens = _tokens(
                stripped
            )

            if not header_seen:
                if (
                    len(
                        tokens
                    )
                    != 2
                    or tokens[
                        0
                    ].casefold()
                    != "lucid"
                ):
                    raise LucidError(
                        "first executable line "
                        "must be: lucid <version>"
                    )

                if (
                    tokens[
                        1
                    ]
                    != self.grammar_version
                ):
                    raise LucidError(
                        "unsupported lucid grammar "
                        f"{tokens[1]!r}; expected "
                        f"{self.grammar_version!r}"
                    )

                header_seen = True

                continue

            if indent == 0:
                current = None

                if (
                    len(
                        tokens
                    )
                    >= 3
                    and tokens[
                        0
                    ].startswith(
                        "@"
                    )
                    and tokens[
                        1
                    ]
                    == "::"
                ):
                    shard_id = (
                        _strip_ref(
                            tokens[
                                0
                            ],
                            "shard.id",
                        )
                    )

                    kind = str(
                        tokens[
                            2
                        ]
                    ).strip().casefold()

                    if (
                        shard_id
                        in drafts
                    ):
                        raise LucidError(
                            "duplicate shard identity: "
                            f"{shard_id}"
                        )

                    draft = _ShardDraft(
                        shard_id=shard_id,
                        kind=kind,
                        payload={},
                        bindings={},
                        dependencies=[],
                        provenance=_provenance(
                            source_name,
                            source_digest,
                            line_number,
                        ),
                        lineage={},
                        truth="unknown",
                    )

                    drafts[
                        shard_id
                    ] = draft

                    current = draft

                    continue

                if (
                    len(
                        tokens
                    )
                    >= 5
                    and tokens[
                        0
                    ].startswith(
                        "@"
                    )
                    and tokens[
                        1
                    ]
                    == "=>"
                ):
                    source_id = _strip_ref(
                        tokens[
                            0
                        ],
                        "segue.source",
                    )

                    target_id = _strip_ref(
                        tokens[
                            2
                        ],
                        "segue.target",
                    )

                    if (
                        tokens[
                            3
                        ]
                        != "::"
                    ):
                        raise LucidError(
                            "segue line "
                            f"{line_number} "
                            "requires :: before "
                            "relation"
                        )

                    relation = str(
                        tokens[
                            4
                        ]
                    ).strip().casefold()

                    segue_id: (
                        str
                        | None
                    ) = None

                    if (
                        len(
                            tokens
                        )
                        > 5
                    ):
                        if (
                            len(
                                tokens
                            )
                            != 7
                            or tokens[
                                5
                            ].casefold()
                            != "as"
                        ):
                            raise LucidError(
                                "segue line "
                                f"{line_number} "
                                "suffix must be: "
                                "as @id"
                            )

                        segue_id = (
                            _strip_ref(
                                tokens[
                                    6
                                ],
                                "segue.id",
                            )
                        )

                    segues.append(
                        SegueShard.build(
                            source=source_id,
                            target=target_id,
                            relation=relation,
                            segue_id=segue_id,
                            provenance=_provenance(
                                source_name,
                                source_digest,
                                line_number,
                            ),
                        )
                    )

                    continue

                raise LucidError(
                    "unsupported top-level "
                    "lucid form at line "
                    f"{line_number}"
                )

            if current is None:
                raise LucidError(
                    "indented line "
                    f"{line_number} "
                    "has no shard declaration"
                )

            command = (
                tokens[
                    0
                ].casefold()
            )

            if command == "with":
                (
                    key,
                    value,
                ) = _assignment(
                    tokens,
                    1,
                )

                if (
                    key
                    in current.payload
                ):
                    raise LucidError(
                        "duplicate shard property "
                        f"{key!r} at line "
                        f"{line_number}"
                    )

                current.payload[
                    key
                ] = value

            elif command == "bind":
                if (
                    len(
                        tokens
                    )
                    != 4
                    or tokens[
                        2
                    ]
                    != "->"
                ):
                    raise LucidError(
                        "binding form is: "
                        "bind <name> -> @target"
                    )

                name = str(
                    tokens[
                        1
                    ]
                ).strip().casefold()

                if (
                    name
                    in current.bindings
                ):
                    raise LucidError(
                        "duplicate binding "
                        f"{name!r} at line "
                        f"{line_number}"
                    )

                current.bindings[
                    name
                ] = _strip_ref(
                    tokens[
                        3
                    ],
                    "binding.target",
                )

            elif command == "needs":
                if (
                    len(
                        tokens
                    )
                    != 2
                ):
                    raise LucidError(
                        "dependency form is: "
                        "needs @target"
                    )

                target = _strip_ref(
                    tokens[
                        1
                    ],
                    "dependency",
                )

                if (
                    target
                    not in current.dependencies
                ):
                    current.dependencies.append(
                        target
                    )

            elif command == "truth":
                if (
                    len(
                        tokens
                    )
                    != 2
                ):
                    raise LucidError(
                        "truth form is: "
                        "truth <state>"
                    )

                current.truth = (
                    tokens[
                        1
                    ].casefold()
                )

            elif command == "from":
                if (
                    len(
                        tokens
                    )
                    < 2
                ):
                    raise LucidError(
                        "from requires a "
                        "provenance value"
                    )

                current.provenance[
                    "declared_source"
                ] = " ".join(
                    tokens[
                        1:
                    ]
                )

            elif command == "lineage":
                (
                    key,
                    value,
                ) = _assignment(
                    tokens,
                    1,
                )

                if (
                    key
                    in current.lineage
                ):
                    raise LucidError(
                        "duplicate lineage key "
                        f"{key!r} at line "
                        f"{line_number}"
                    )

                current.lineage[
                    key
                ] = value

            else:
                raise LucidError(
                    "unsupported shard clause "
                    f"{command!r} at line "
                    f"{line_number}"
                )

        if not header_seen:
            raise LucidError(
                "lucid header is missing"
            )

        shards = [
            Shard.build(
                shard_id=draft.shard_id,
                kind=draft.kind,
                payload=draft.payload,
                bindings=draft.bindings,
                dependencies=(
                    draft.dependencies
                ),
                provenance=(
                    draft.provenance
                ),
                lineage=(
                    draft.lineage
                ),
                truth=draft.truth,
                semantic_refs={
                    "language":
                        (
                            "lex:language:"
                            "translucent"
                        ),
                },
            )
            for draft
            in drafts.values()
        ]

        try:
            return ShardProgram.build(
                language="translucent",
                version=(
                    self.grammar_version
                ),
                shards=shards,
                segues=segues,
                source=source,
            )

        except ShardIRError as exc:
            raise LucidError(
                str(
                    exc
                )
            ) from exc

    def compile_path(
        self,
        path: (
            str
            | Path
        ),
    ) -> ShardProgram:
        source_path = Path(
            path
        )

        if (
            source_path.suffix.casefold()
            != FILE_EXTENSION
        ):
            raise LucidError(
                "translucent source must use "
                f"{FILE_EXTENSION}"
            )

        return self.compile(
            source_path.read_text(
                encoding="utf-8"
            ),
            source_name=str(
                source_path
            ),
        )


def language_manifest() -> dict[
    str,
    Any,
]:
    return {
        "schema":
            schema,

        "language":
            "translucent",

        "source_extension":
            FILE_EXTENSION,

        "grammar_version":
            "1",

        "runtime_primitives":
            [
                "shard",
                "segue_shard",
            ],

        "semantic_shard":
            "lex:primitive:shard",

        "semantic_segue":
            "lex:core:segue",

        "host_language_dependency":
            None,

        "arbitrary_host_execution":
            False,

        "authority_effect":
            authority_effect,
    }


def selftest() -> dict[
    str,
    Any,
]:
    source = """lucid 1

@seed :: data
  with value = 41
  truth supported

@work :: operation
  bind source -> @seed
  needs @seed
  with verb = "increment"

@view :: projection
  bind source -> @work
  needs @work
  with renderer = "blot"

@seed => @work :: feeds
@work => @view :: projects
"""

    compiler = (
        LucidCompiler()
    )

    first = compiler.compile(
        source
    )

    second = compiler.compile(
        source
    )

    checks = {
        "authority_none":
            (
                authority_effect
                == "none"
            ),

        "three_shards":
            (
                len(
                    first.shards
                )
                == 3
            ),

        "two_segues":
            (
                len(
                    first.segues
                )
                == 2
            ),

        "stable_semantics":
            (
                first.semantic_digest
                == second.semantic_digest
            ),

        "lucid_extension":
            (
                FILE_EXTENSION
                == ".lucid"
            ),

        "shard_ir":
            all(
                item.semantic_refs.get(
                    "shard"
                )
                == "lex:primitive:shard"
                for item
                in first.shards
            ),
    }

    return {
        "schema":
            (
                "savant.translucent."
                "lucid-selftest.v1"
            ),

        "ok":
            all(
                checks.values()
            ),

        "checks":
            checks,

        "semantic_digest":
            first.semantic_digest,

        "authority_effect":
            authority_effect,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )

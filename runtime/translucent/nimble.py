#!/usr/bin/env python3

from __future__ import annotations

import ast
import hashlib
import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .shard_ir import (
    SegueShard,
    Shard,
    ShardIRError,
    ShardProgram,
)


schema = "savant.translucent.nimble.v1"
authority_effect = "none"

FILE_EXTENSION = ".nimble"

MAX_SOURCE_CHARS = 2_000_000
MAX_LINES = 100_000
MAX_CLAUSES = 1_000_000


class NimbleError(
    ValueError
):
    pass


@dataclass(
    slots=True,
)
class _OperationDraft:
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
    truth: str


def _ref(
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
        raise NimbleError(
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
        raw_values = list(
            lexer
        )

    except ValueError as exc:
        raise NimbleError(
            f"invalid nimble line: {exc}"
        ) from exc

    values: list[
        str
    ] = []

    for raw in raw_values:
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
                raise NimbleError(
                    "invalid quoted token: "
                    f"{raw!r}"
                ) from exc

            if not isinstance(
                value,
                str,
            ):
                raise NimbleError(
                    "quoted token must "
                    "decode to a string"
                )

            values.append(
                value
            )

        else:
            values.append(
                raw
            )

    return values


def _literal(
    tokens: list[
        str
    ],
) -> Any:
    if not tokens:
        raise NimbleError(
            "value is required"
        )

    raw = " ".join(
        tokens
    )

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
    start: int,
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
        raise NimbleError(
            "assignment requires "
            "<path> = <value>"
        )

    path = str(
        tokens[
            start
        ]
    ).strip()

    if not path:
        raise NimbleError(
            "assignment path is required"
        )

    return (
        path,
        _literal(
            tokens[
                start + 2:
            ]
        ),
    )


def _prov(
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
            "nimble",

        "surface":
            "nimble",
    }


class NimbleCompiler:
    """
    Compile .nimble Datrix programs into the
    same shard/segue-shard IR used by Translucent.

    Nimble is intentionally not SQL-shaped.

        @facts := datrix "runtime/facts.datrix" profile knowledge

        @seed +> @facts :: fact
          field payload.score = 12

        @hot << @facts
          kind fact
          keep payload.score gte 10

        @near >> @facts @seed

        @rev ~= @facts @seed -> @seed-v2
          set payload.score = 20

        @gone !~ @facts @seed-v2

        @join <> @left @right inner
          on id = id

        @fold %% @hot
          by payload.category
          metric total count *

        @tx && @facts @rev @gone

        @undo !! @facts @tx

    Every declaration becomes a shard.
    Dataflow and ownership become segue shards.
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
        source_name: str = "memory.nimble",
    ) -> ShardProgram:
        if (
            len(
                source
            )
            > MAX_SOURCE_CHARS
        ):
            raise NimbleError(
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
            raise NimbleError(
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
            _OperationDraft,
        ] = {}

        edges: list[
            SegueShard
        ] = []

        current: (
            _OperationDraft
            | None
        ) = None

        header_seen = False
        clauses = 0
        ordinal = 0

        def add_draft(
            shard_id: str,
            kind: str,
            line_number: int,
        ) -> _OperationDraft:
            nonlocal ordinal

            if (
                shard_id
                in drafts
            ):
                raise NimbleError(
                    "duplicate nimble identity: "
                    f"{shard_id}"
                )

            ordinal += 1

            draft = _OperationDraft(
                shard_id=shard_id,
                kind=kind,
                payload={
                    "ordinal":
                        ordinal,
                },
                bindings={},
                dependencies=[],
                provenance=_prov(
                    source_name,
                    source_digest,
                    line_number,
                ),
                truth="unknown",
            )

            drafts[
                shard_id
            ] = draft

            return draft

        def depend(
            draft: _OperationDraft,
            ref_id: str,
            relation: str,
            line_number: int,
        ) -> None:
            if (
                ref_id
                not in draft.dependencies
            ):
                draft.dependencies.append(
                    ref_id
                )

            edges.append(
                SegueShard.build(
                    source=ref_id,
                    target=draft.shard_id,
                    relation=relation,
                    provenance=_prov(
                        source_name,
                        source_digest,
                        line_number,
                    ),
                )
            )

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
                raise NimbleError(
                    "tabs are forbidden at line "
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
                    != "nimble"
                ):
                    raise NimbleError(
                        "first executable line must be: "
                        "nimble <version>"
                    )

                if (
                    tokens[
                        1
                    ]
                    != self.grammar_version
                ):
                    raise NimbleError(
                        "unsupported nimble grammar "
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
                    >= 4
                    and tokens[
                        1
                    ]
                    == ":="
                    and tokens[
                        2
                    ].casefold()
                    == "datrix"
                ):
                    shard_id = _ref(
                        tokens[
                            0
                        ],
                        "datrix.id",
                    )

                    draft = add_draft(
                        shard_id,
                        "datrix.binding",
                        line_number,
                    )

                    draft.payload[
                        "path"
                    ] = tokens[
                        3
                    ]

                    if (
                        len(
                            tokens
                        )
                        > 4
                    ):
                        if (
                            len(
                                tokens
                            )
                            != 6
                            or tokens[
                                4
                            ].casefold()
                            != "profile"
                        ):
                            raise NimbleError(
                                "datrix suffix is: "
                                "profile <name[,name]>"
                            )

                        draft.payload[
                            "profiles"
                        ] = [
                            item.strip()
                            .casefold()
                            for item
                            in tokens[
                                5
                            ].split(
                                ","
                            )
                            if item.strip()
                        ]

                    else:
                        draft.payload[
                            "profiles"
                        ] = [
                            "knowledge"
                        ]

                    current = draft

                    continue

                if (
                    len(
                        tokens
                    )
                    >= 4
                    and tokens[
                        1
                    ]
                    == "+>"
                    and tokens[
                        3
                    ]
                    == "::"
                ):
                    shard_id = _ref(
                        tokens[
                            0
                        ],
                        "seed.id",
                    )

                    datrix_ref = _ref(
                        tokens[
                            2
                        ],
                        "seed.datrix",
                    )

                    if (
                        len(
                            tokens
                        )
                        != 5
                    ):
                        raise NimbleError(
                            "seed form is: "
                            "@id +> @datrix :: <kind>"
                        )

                    draft = add_draft(
                        shard_id,
                        "datrix.seed",
                        line_number,
                    )

                    draft.bindings[
                        "datrix"
                    ] = datrix_ref

                    draft.payload[
                        "record_kind"
                    ] = (
                        tokens[
                            4
                        ].casefold()
                    )

                    draft.payload[
                        "record_id"
                    ] = shard_id

                    depend(
                        draft,
                        datrix_ref,
                        "writes_to",
                        line_number,
                    )

                    current = draft

                    continue

                if (
                    len(
                        tokens
                    )
                    == 3
                    and tokens[
                        1
                    ]
                    == "<<"
                ):
                    shard_id = _ref(
                        tokens[
                            0
                        ],
                        "gather.id",
                    )

                    datrix_ref = _ref(
                        tokens[
                            2
                        ],
                        "gather.datrix",
                    )

                    draft = add_draft(
                        shard_id,
                        "datrix.gather",
                        line_number,
                    )

                    draft.bindings[
                        "datrix"
                    ] = datrix_ref

                    draft.payload.update(
                        {
                            "where":
                                [],

                            "shape":
                                [],

                            "pace":
                                [],

                            "view":
                                "current",
                        }
                    )

                    depend(
                        draft,
                        datrix_ref,
                        "reads_from",
                        line_number,
                    )

                    current = draft

                    continue

                if (
                    len(
                        tokens
                    )
                    == 4
                    and tokens[
                        1
                    ]
                    == ">>"
                ):
                    shard_id = _ref(
                        tokens[
                            0
                        ],
                        "walk.id",
                    )

                    datrix_ref = _ref(
                        tokens[
                            2
                        ],
                        "walk.datrix",
                    )

                    subject = _ref(
                        tokens[
                            3
                        ],
                        "walk.subject",
                    )

                    draft = add_draft(
                        shard_id,
                        "datrix.walk",
                        line_number,
                    )

                    draft.bindings[
                        "datrix"
                    ] = datrix_ref

                    draft.payload.update(
                        {
                            "subject":
                                subject,

                            "direction":
                                "both",

                            "depth":
                                1,
                        }
                    )

                    depend(
                        draft,
                        datrix_ref,
                        "reads_from",
                        line_number,
                    )

                    current = draft

                    continue

                if (
                    len(
                        tokens
                    )
                    == 5
                    and tokens[
                        1
                    ]
                    == "<>"
                ):
                    shard_id = _ref(
                        tokens[
                            0
                        ],
                        "weave.id",
                    )

                    left = _ref(
                        tokens[
                            2
                        ],
                        "weave.left",
                    )

                    right = _ref(
                        tokens[
                            3
                        ],
                        "weave.right",
                    )

                    mode = (
                        tokens[
                            4
                        ].casefold()
                    )

                    if mode not in {
                        "inner",
                        "left",
                        "right",
                        "full",
                        "semi",
                        "anti",
                    }:
                        raise NimbleError(
                            "weave mode must be "
                            "inner/left/right/full/semi/anti"
                        )

                    draft = add_draft(
                        shard_id,
                        "datrix.weave",
                        line_number,
                    )

                    draft.bindings.update(
                        {
                            "left":
                                left,

                            "right":
                                right,
                        }
                    )

                    draft.payload.update(
                        {
                            "mode":
                                mode,

                            "on":
                                [],
                        }
                    )

                    depend(
                        draft,
                        left,
                        "consumes",
                        line_number,
                    )

                    depend(
                        draft,
                        right,
                        "consumes",
                        line_number,
                    )

                    current = draft

                    continue

                if (
                    len(
                        tokens
                    )
                    == 3
                    and tokens[
                        1
                    ]
                    == "%%"
                ):
                    shard_id = _ref(
                        tokens[
                            0
                        ],
                        "fold.id",
                    )

                    source_ref = _ref(
                        tokens[
                            2
                        ],
                        "fold.source",
                    )

                    draft = add_draft(
                        shard_id,
                        "datrix.fold",
                        line_number,
                    )

                    draft.bindings[
                        "source"
                    ] = source_ref

                    draft.payload.update(
                        {
                            "by":
                                [],

                            "metrics":
                                [],
                        }
                    )

                    depend(
                        draft,
                        source_ref,
                        "consumes",
                        line_number,
                    )

                    current = draft

                    continue

                if (
                    len(
                        tokens
                    )
                    == 6
                    and tokens[
                        1
                    ]
                    == "~="
                    and tokens[
                        4
                    ]
                    == "->"
                ):
                    shard_id = _ref(
                        tokens[
                            0
                        ],
                        "evolve.id",
                    )

                    datrix_ref = _ref(
                        tokens[
                            2
                        ],
                        "evolve.datrix",
                    )

                    subject = _ref(
                        tokens[
                            3
                        ],
                        "evolve.subject",
                    )

                    successor = _ref(
                        tokens[
                            5
                        ],
                        "evolve.successor",
                    )

                    draft = add_draft(
                        shard_id,
                        "datrix.evolve",
                        line_number,
                    )

                    draft.bindings[
                        "datrix"
                    ] = datrix_ref

                    draft.payload.update(
                        {
                            "subject":
                                subject,

                            "successor":
                                successor,

                            "set":
                                {},

                            "unset":
                                [],
                        }
                    )

                    depend(
                        draft,
                        datrix_ref,
                        "writes_to",
                        line_number,
                    )

                    current = draft

                    continue

                if (
                    len(
                        tokens
                    )
                    == 4
                    and tokens[
                        1
                    ]
                    == "!~"
                ):
                    shard_id = _ref(
                        tokens[
                            0
                        ],
                        "retire.id",
                    )

                    datrix_ref = _ref(
                        tokens[
                            2
                        ],
                        "retire.datrix",
                    )

                    subject = _ref(
                        tokens[
                            3
                        ],
                        "retire.subject",
                    )

                    draft = add_draft(
                        shard_id,
                        "datrix.retire",
                        line_number,
                    )

                    draft.bindings[
                        "datrix"
                    ] = datrix_ref

                    draft.payload.update(
                        {
                            "subject":
                                subject,

                            "reason":
                                "",
                        }
                    )

                    depend(
                        draft,
                        datrix_ref,
                        "writes_to",
                        line_number,
                    )

                    current = draft

                    continue

                if (
                    len(
                        tokens
                    )
                    >= 4
                    and tokens[
                        1
                    ]
                    == "&&"
                ):
                    shard_id = _ref(
                        tokens[
                            0
                        ],
                        "transaction.id",
                    )

                    datrix_ref = _ref(
                        tokens[
                            2
                        ],
                        "transaction.datrix",
                    )

                    operation_refs = [
                        _ref(
                            token,
                            "transaction.operation",
                        )
                        for token
                        in tokens[
                            3:
                        ]
                    ]

                    if not operation_refs:
                        raise NimbleError(
                            "transaction requires "
                            "at least one operation"
                        )

                    draft = add_draft(
                        shard_id,
                        "datrix.transaction",
                        line_number,
                    )

                    draft.bindings[
                        "datrix"
                    ] = datrix_ref

                    draft.payload[
                        "operations"
                    ] = operation_refs

                    depend(
                        draft,
                        datrix_ref,
                        "writes_to",
                        line_number,
                    )

                    for (
                        operation_ref
                    ) in operation_refs:
                        depend(
                            draft,
                            operation_ref,
                            "contains",
                            line_number,
                        )

                    current = draft

                    continue

                if (
                    len(
                        tokens
                    )
                    == 4
                    and tokens[
                        1
                    ]
                    == "!!"
                ):
                    shard_id = _ref(
                        tokens[
                            0
                        ],
                        "rollback.id",
                    )

                    datrix_ref = _ref(
                        tokens[
                            2
                        ],
                        "rollback.datrix",
                    )

                    commit_ref = _ref(
                        tokens[
                            3
                        ],
                        "rollback.commit",
                    )

                    draft = add_draft(
                        shard_id,
                        "datrix.rollback",
                        line_number,
                    )

                    draft.bindings[
                        "datrix"
                    ] = datrix_ref

                    draft.bindings[
                        "commit"
                    ] = commit_ref

                    depend(
                        draft,
                        datrix_ref,
                        "writes_to",
                        line_number,
                    )

                    depend(
                        draft,
                        commit_ref,
                        "reverses",
                        line_number,
                    )

                    current = draft

                    continue

                if (
                    len(
                        tokens
                    )
                    >= 6
                    and tokens[
                        1
                    ]
                    == "=>"
                    and tokens[
                        3
                    ]
                    == "->"
                    and tokens[
                        5
                    ]
                    == "::"
                ):
                    shard_id = _ref(
                        tokens[
                            0
                        ],
                        "segue.id",
                    )

                    datrix_ref = _ref(
                        tokens[
                            2
                        ],
                        "segue.datrix",
                    )

                    source_id = _ref(
                        tokens[
                            4
                        ],
                        "segue.source",
                    )

                    if (
                        len(
                            tokens
                        )
                        != 8
                    ):
                        raise NimbleError(
                            "segue form is: "
                            "@edge => @datrix -> "
                            "@source :: <relation> @target"
                        )

                    relation = (
                        tokens[
                            6
                        ].casefold()
                    )

                    target_id = _ref(
                        tokens[
                            7
                        ],
                        "segue.target",
                    )

                    draft = add_draft(
                        shard_id,
                        "datrix.segue",
                        line_number,
                    )

                    draft.bindings[
                        "datrix"
                    ] = datrix_ref

                    draft.payload.update(
                        {
                            "source":
                                source_id,

                            "target":
                                target_id,

                            "relation":
                                relation,
                        }
                    )

                    depend(
                        draft,
                        datrix_ref,
                        "writes_to",
                        line_number,
                    )

                    current = draft

                    continue

                raise NimbleError(
                    "unsupported top-level "
                    "nimble form at line "
                    f"{line_number}"
                )

            if current is None:
                raise NimbleError(
                    "indented line "
                    f"{line_number} "
                    "has no operation"
                )

            clauses += 1

            if (
                clauses
                > MAX_CLAUSES
            ):
                raise NimbleError(
                    "clause count exceeds "
                    f"{MAX_CLAUSES}"
                )

            command = (
                tokens[
                    0
                ].casefold()
            )

            if command == "field":
                (
                    path,
                    value,
                ) = _assignment(
                    tokens,
                    1,
                )

                fields = (
                    current.payload
                    .setdefault(
                        "fields",
                        {},
                    )
                )

                if path in fields:
                    raise NimbleError(
                        "duplicate field "
                        f"{path!r}"
                    )

                fields[
                    path
                ] = value

            elif command == "depends":
                if (
                    len(
                        tokens
                    )
                    != 2
                ):
                    raise NimbleError(
                        "depends form is: "
                        "depends @identity"
                    )

                current.payload.setdefault(
                    "record_dependencies",
                    [],
                ).append(
                    _ref(
                        tokens[
                            1
                        ],
                        "depends",
                    )
                )

            elif command == "kind":
                if (
                    len(
                        tokens
                    )
                    != 2
                ):
                    raise NimbleError(
                        "kind form is: "
                        "kind <record-kind>"
                    )

                current.payload[
                    "match_kind"
                ] = (
                    tokens[
                        1
                    ].casefold()
                )

            elif command == "keep":
                if (
                    len(
                        tokens
                    )
                    < 4
                ):
                    raise NimbleError(
                        "keep form is: "
                        "keep <path> <op> <value>"
                    )

                current.payload.setdefault(
                    "where",
                    [],
                ).append(
                    {
                        "path":
                            tokens[
                                1
                            ],

                        "op":
                            tokens[
                                2
                            ].casefold(),

                        "value":
                            _literal(
                                tokens[
                                    3:
                                ]
                            ),
                    }
                )

            elif command == "shape":
                if (
                    len(
                        tokens
                    )
                    < 2
                ):
                    raise NimbleError(
                        "shape requires at "
                        "least one path"
                    )

                current.payload[
                    "shape"
                ] = tokens[
                    1:
                ]

            elif command == "pace":
                if (
                    len(
                        tokens
                    )
                    != 3
                    or tokens[
                        2
                    ].casefold()
                    not in {
                        "asc",
                        "desc",
                    }
                ):
                    raise NimbleError(
                        "pace form is: "
                        "pace <path> asc|desc"
                    )

                current.payload.setdefault(
                    "pace",
                    [],
                ).append(
                    {
                        "path":
                            tokens[
                                1
                            ],

                        "direction":
                            tokens[
                                2
                            ].casefold(),
                    }
                )

            elif command == "skip":
                if (
                    len(
                        tokens
                    )
                    != 2
                    or not tokens[
                        1
                    ].isdigit()
                ):
                    raise NimbleError(
                        "skip requires a "
                        "non-negative integer"
                    )

                current.payload[
                    "skip"
                ] = int(
                    tokens[
                        1
                    ]
                )

            elif command == "take":
                if (
                    len(
                        tokens
                    )
                    != 2
                    or not tokens[
                        1
                    ].isdigit()
                ):
                    raise NimbleError(
                        "take requires a "
                        "non-negative integer"
                    )

                current.payload[
                    "take"
                ] = int(
                    tokens[
                        1
                    ]
                )

            elif command == "view":
                if (
                    len(
                        tokens
                    )
                    != 2
                    or tokens[
                        1
                    ].casefold()
                    not in {
                        "current",
                        "history",
                    }
                ):
                    raise NimbleError(
                        "view must be current "
                        "or history"
                    )

                current.payload[
                    "view"
                ] = (
                    tokens[
                        1
                    ].casefold()
                )

            elif command == "relation":
                if (
                    len(
                        tokens
                    )
                    != 2
                ):
                    raise NimbleError(
                        "relation requires one "
                        "relation kind"
                    )

                current.payload[
                    "relation"
                ] = (
                    tokens[
                        1
                    ].casefold()
                )

            elif command == "direction":
                if (
                    len(
                        tokens
                    )
                    != 2
                    or tokens[
                        1
                    ].casefold()
                    not in {
                        "in",
                        "out",
                        "both",
                    }
                ):
                    raise NimbleError(
                        "direction must be "
                        "in, out, or both"
                    )

                current.payload[
                    "direction"
                ] = (
                    tokens[
                        1
                    ].casefold()
                )

            elif command == "depth":
                if (
                    len(
                        tokens
                    )
                    != 2
                    or not tokens[
                        1
                    ].isdigit()
                ):
                    raise NimbleError(
                        "depth requires a "
                        "non-negative integer"
                    )

                current.payload[
                    "depth"
                ] = int(
                    tokens[
                        1
                    ]
                )

            elif command == "on":
                if (
                    len(
                        tokens
                    )
                    != 4
                    or tokens[
                        2
                    ]
                    not in {
                        "=",
                        "==",
                    }
                ):
                    raise NimbleError(
                        "on form is: "
                        "on <left-path> = <right-path>"
                    )

                current.payload.setdefault(
                    "on",
                    [],
                ).append(
                    {
                        "left":
                            tokens[
                                1
                            ],

                        "right":
                            tokens[
                                3
                            ],
                    }
                )

            elif command == "by":
                if (
                    len(
                        tokens
                    )
                    < 2
                ):
                    raise NimbleError(
                        "by requires one or "
                        "more paths"
                    )

                current.payload[
                    "by"
                ] = tokens[
                    1:
                ]

            elif command == "metric":
                if (
                    len(
                        tokens
                    )
                    not in {
                        3,
                        4,
                    }
                ):
                    raise NimbleError(
                        "metric form is: "
                        "metric <alias> <fn> [path]"
                    )

                current.payload.setdefault(
                    "metrics",
                    [],
                ).append(
                    {
                        "alias":
                            tokens[
                                1
                            ].casefold(),

                        "fn":
                            tokens[
                                2
                            ].casefold(),

                        "path":
                            (
                                tokens[
                                    3
                                ]
                                if (
                                    len(
                                        tokens
                                    )
                                    == 4
                                )
                                else "*"
                            ),
                    }
                )

            elif command == "set":
                (
                    path,
                    value,
                ) = _assignment(
                    tokens,
                    1,
                )

                patch = (
                    current.payload
                    .setdefault(
                        "set",
                        {},
                    )
                )

                if path in patch:
                    raise NimbleError(
                        "duplicate patch path "
                        f"{path!r}"
                    )

                patch[
                    path
                ] = value

            elif command == "unset":
                if (
                    len(
                        tokens
                    )
                    != 2
                ):
                    raise NimbleError(
                        "unset form is: "
                        "unset <path>"
                    )

                current.payload.setdefault(
                    "unset",
                    [],
                ).append(
                    tokens[
                        1
                    ]
                )

            elif command == "expect":
                if (
                    len(
                        tokens
                    )
                    != 2
                ):
                    raise NimbleError(
                        "expect requires one digest"
                    )

                current.payload[
                    "expected_digest"
                ] = (
                    tokens[
                        1
                    ].casefold()
                )

            elif command == "because":
                if (
                    len(
                        tokens
                    )
                    < 2
                ):
                    raise NimbleError(
                        "because requires a reason"
                    )

                current.payload[
                    "reason"
                ] = " ".join(
                    tokens[
                        1:
                    ]
                )

            elif command == "truth":
                if (
                    len(
                        tokens
                    )
                    != 2
                ):
                    raise NimbleError(
                        "truth form is: "
                        "truth <state>"
                    )

                current.truth = (
                    tokens[
                        1
                    ].casefold()
                )

            else:
                raise NimbleError(
                    "unsupported nimble clause "
                    f"{command!r} at line "
                    f"{line_number}"
                )

        if not header_seen:
            raise NimbleError(
                "nimble header is missing"
            )

        shards = [
            Shard.build(
                shard_id=(
                    draft.shard_id
                ),
                kind=draft.kind,
                payload=(
                    draft.payload
                ),
                bindings=(
                    draft.bindings
                ),
                dependencies=(
                    draft.dependencies
                ),
                provenance=(
                    draft.provenance
                ),
                truth=draft.truth,
                semantic_refs={
                    "language":
                        "lex:language:nimble",
                },
            )
            for draft
            in drafts.values()
        ]

        try:
            return ShardProgram.build(
                language="nimble",
                version=(
                    self.grammar_version
                ),
                shards=shards,
                segues=edges,
                source=source,
            )

        except ShardIRError as exc:
            raise NimbleError(
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
            raise NimbleError(
                "nimble source must use "
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
            "nimble",

        "source_extension":
            FILE_EXTENSION,

        "grammar_version":
            "1",

        "datrix_native":
            True,

        "sql_derived":
            False,

        "javascript_derived":
            False,

        "runtime_primitives":
            [
                "shard",
                "segue_shard",
            ],

        "semantic_shard":
            "lex:primitive:shard",

        "semantic_segue":
            "lex:core:segue",

        "authority_effect":
            authority_effect,
    }


def selftest() -> dict[
    str,
    Any,
]:
    source = """nimble 1

@facts := datrix "runtime/facts.datrix" profile knowledge

@seed +> @facts :: fact
  field payload.score = 12
  field payload.category = "alpha"
  truth claimed

@hot << @facts
  kind fact
  keep payload.score gte 10
  shape id payload.score
  pace payload.score desc
  take 25
  view current

@near >> @facts @seed
  relation depends_on
  direction both
  depth 2

@rev ~= @facts @seed -> @seed-v2
  set payload.score = 20
  expect abc123

@tx && @facts @rev
"""

    compiler = (
        NimbleCompiler()
    )

    first = compiler.compile(
        source
    )

    second = compiler.compile(
        source
    )

    kinds = {
        item.kind
        for item
        in first.shards
    }

    checks = {
        "authority_none":
            (
                authority_effect
                == "none"
            ),

        "nimble_extension":
            (
                FILE_EXTENSION
                == ".nimble"
            ),

        "stable_semantics":
            (
                first.semantic_digest
                == second.semantic_digest
            ),

        "datrix_binding":
            (
                "datrix.binding"
                in kinds
            ),

        "gather_shard":
            (
                "datrix.gather"
                in kinds
            ),

        "evolve_shard":
            (
                "datrix.evolve"
                in kinds
            ),

        "transaction_shard":
            (
                "datrix.transaction"
                in kinds
            ),

        "segue_objects":
            (
                len(
                    first.segues
                )
                >= 5
            ),

        "not_sql":
            (
                "select"
                not in source.casefold()
                and "from "
                not in source.casefold()
            ),
    }

    return {
        "schema":
            (
                "savant.translucent."
                "nimble-selftest.v1"
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

#!/usr/bin/env python3

from __future__ import annotations

import ast
import hashlib
import json
import shlex
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence
from xml.etree import ElementTree as ET

from runtime.translucent.svg import SVG_NS, TL_NS


schema = "savant.translucent.datrix-text.v1"
authority_effect = "none"
MAX_SOURCE_CHARS = 2_000_000
MAX_STATEMENTS = 10_000
MAX_TOKENS_PER_STATEMENT = 512


class DatrixTextError(ValueError):
    pass


class _TextToken(str):
    __slots__ = ("quoted",)

    def __new__(cls, value: str, *, quoted: bool = False) -> "_TextToken":
        item = str.__new__(cls, value)
        item.quoted = bool(quoted)
        return item

    def upper(self) -> str:
        value = super().upper()
        return ("\x00" + value) if self.quoted else value


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _clean(value: Any, field: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise DatrixTextError(f"{field} is required")
    return result


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _bool_text(value: str) -> str:
    normalized = str(value).strip().casefold()
    if normalized in {"true", "1", "yes"}:
        return "true"
    if normalized in {"false", "0", "no"}:
        return "false"
    raise DatrixTextError(f"invalid boolean: {value!r}")


def _normalize_op(value: str) -> str:
    token = str(value or "").strip().casefold()
    aliases = {
        "=": "eq",
        "==": "eq",
        "!=": "ne",
        "<>": "ne",
        ">": "gt",
        ">=": "gte",
        "<": "lt",
        "<=": "lte",
        "notin": "not-in",
        "startswith": "prefix",
        "endswith": "suffix",
    }
    return aliases.get(token, token)


def _split_statements(source: str) -> list[str]:
    if len(source) > MAX_SOURCE_CHARS:
        raise DatrixTextError(
            f"text source exceeds {MAX_SOURCE_CHARS} characters"
        )
    statements: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escaped = False
    for char in source:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\" and quote is not None:
            current.append(char)
            escaped = True
            continue
        if quote is not None:
            current.append(char)
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            current.append(char)
            continue
        if char == ";":
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
                if len(statements) > MAX_STATEMENTS:
                    raise DatrixTextError(
                        f"text source exceeds {MAX_STATEMENTS} statements"
                    )
            current = []
            continue
        current.append(char)
    if quote is not None:
        raise DatrixTextError("unterminated quoted string")
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    if len(statements) > MAX_STATEMENTS:
        raise DatrixTextError(
            f"text source exceeds {MAX_STATEMENTS} statements"
        )
    return statements


def _tokens(statement: str) -> list[str]:
    lexer = shlex.shlex(statement, posix=False)
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        raw_values = list(lexer)
    except ValueError as exc:
        raise DatrixTextError(f"invalid text statement: {exc}") from exc
    values: list[str] = []
    for raw in raw_values:
        quoted = (
            len(raw) >= 2
            and raw[0] in {"'", '"'}
            and raw[-1] == raw[0]
        )
        if quoted:
            try:
                value = ast.literal_eval(raw)
            except (SyntaxError, ValueError) as exc:
                raise DatrixTextError(f"invalid quoted token: {raw!r}") from exc
            if not isinstance(value, str):
                raise DatrixTextError("quoted token must decode to a string")
            values.append(_TextToken(value, quoted=True))
        else:
            values.append(_TextToken(raw, quoted=False))
    if len(values) > MAX_TOKENS_PER_STATEMENT:
        raise DatrixTextError(
            f"statement exceeds {MAX_TOKENS_PER_STATEMENT} tokens"
        )
    if not values:
        raise DatrixTextError("empty statement")
    return values


def _element(
    parent: ET.Element,
    local: str,
    attrs: Mapping[str, Any] | None = None,
) -> ET.Element:
    element = ET.SubElement(
        parent,
        f"{{{TL_NS}}}{local}",
    )

    for key, value in sorted(
        (
            attrs
            or {}
        ).items()
    ):
        if value is None:
            continue

        text = str(
            value
        )

        if text == "":
            continue

        element.set(
            str(
                key
            ),
            text,
        )

    return element


def _field(
    parent: ET.Element,
    name: str,
    value: Any,
) -> None:
    attrs: dict[
        str,
        str,
    ] = {
        "name":
            str(
                name
            )
    }

    if isinstance(
        value,
        Mapping,
    ):
        element = _element(
            parent,
            "field",
            attrs,
        )

        for child_name in sorted(
            value
        ):
            _field(
                element,
                str(
                    child_name
                ),
                value[
                    child_name
                ],
            )

        return

    if isinstance(
        value,
        list,
    ):
        attrs[
            "type"
        ] = "json"

        attrs[
            "value"
        ] = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
            allow_nan=False,
        )

    elif value is None:
        attrs[
            "type"
        ] = "null"

        attrs[
            "value"
        ] = "null"

    elif isinstance(
        value,
        bool,
    ):
        attrs[
            "type"
        ] = "boolean"

        attrs[
            "value"
        ] = (
            "true"
            if value
            else "false"
        )

    elif isinstance(
        value,
        int,
    ):
        attrs[
            "type"
        ] = "integer"

        attrs[
            "value"
        ] = str(
            value
        )

    elif isinstance(
        value,
        float,
    ):
        attrs[
            "type"
        ] = "number"

        attrs[
            "value"
        ] = repr(
            value
        )

    else:
        attrs[
            "type"
        ] = "string"

        attrs[
            "value"
        ] = str(
            value
        )

    _element(
        parent,
        "field",
        attrs,
    )


def _json_object(
    value: str,
    field: str,
) -> dict[
    str,
    Any,
]:
    try:
        parsed = json.loads(
            value
        )

    except json.JSONDecodeError as exc:
        raise DatrixTextError(
            f"{field} must be valid json: {exc}"
        ) from exc

    if not isinstance(
        parsed,
        dict,
    ):
        raise DatrixTextError(
            f"{field} must be a json object"
        )

    return parsed


def _emit_object(
    parent: ET.Element,
    local: str,
    value: Mapping[
        str,
        Any,
    ],
) -> None:
    container = _element(
        parent,
        local,
    )

    for key in sorted(
        value
    ):
        _field(
            container,
            str(
                key
            ),
            value[
                key
            ],
        )


def _parse_common_tail(
    tokens: Sequence[
        str
    ],
    start: int,
    admitted: Iterable[
        str
    ],
) -> dict[
    str,
    list[
        list[
            str
        ]
    ],
]:
    allowed = {
        item.upper()
        for item
        in admitted
    }

    result: dict[
        str,
        list[
            list[
                str
            ]
        ],
    ] = {}

    index = start

    while index < len(
        tokens
    ):
        key = tokens[
            index
        ].upper()

        if key not in allowed:
            raise DatrixTextError(
                f"unexpected clause {tokens[index]!r}"
            )

        index += 1

        values: list[
            str
        ] = []

        while (
            index
            < len(
                tokens
            )
            and tokens[
                index
            ].upper()
            not in allowed
        ):
            values.append(
                tokens[
                    index
                ]
            )

            index += 1

        result.setdefault(
            key,
            [],
        ).append(
            values
        )

    return result


@dataclass(
    slots=True
)
class DatrixTextFrontend:
    grammar_version: str = "2"

    def manifest(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        result = {
            "schema":
                schema,

            "surface":
                "sql-like-text-adapter",

            "execution_owner":
                "translucent-compiler",

            "canonical_execution_surface":
                "svg-translucent",

            "grammar_version":
                self.grammar_version,

            "transaction_form":
                (
                    "begin/"
                    "mutation-statements/"
                    "commit"
                ),

            "statement_limit":
                MAX_STATEMENTS,

            "source_char_limit":
                MAX_SOURCE_CHARS,

            "parallel_execution_engine":
                False,

            "authority_effect":
                authority_effect,
        }

        result[
            "digest"
        ] = hashlib.sha256(
            json.dumps(
                result,
                ensure_ascii=False,
                sort_keys=True,
                separators=(
                    ",",
                    ":",
                ),
            ).encode(
                "utf-8"
            )
        ).hexdigest()

        return result

    def _open(
        self,
        program: ET.Element,
        tokens: Sequence[
            str
        ],
    ) -> ET.Element:
        if (
            len(
                tokens
            )
            < 4
            or tokens[
                2
            ].upper()
            != "PATH"
        ):
            raise DatrixTextError(
                "OPEN syntax: "
                "OPEN <ref> PATH <path> "
                "[PROFILES <csv>]"
            )

        attrs: dict[
            str,
            str,
        ] = {
            "ref":
                tokens[
                    1
                ],

            "path":
                tokens[
                    3
                ],
        }

        if len(
            tokens
        ) > 4:
            clauses = (
                _parse_common_tail(
                    tokens,
                    4,
                    {
                        "PROFILES"
                    },
                )
            )

            values = clauses.get(
                "PROFILES",
                [],
            )

            if (
                len(
                    values
                )
                != 1
                or len(
                    values[
                        0
                    ]
                )
                != 1
            ):
                raise DatrixTextError(
                    "PROFILES requires one "
                    "comma-separated value"
                )

            attrs[
                "profiles"
            ] = values[
                0
            ][
                0
            ]

        return _element(
            program,
            "open",
            attrs,
        )

    def _put(
        self,
        parent: ET.Element,
        tokens: Sequence[
            str
        ],
    ) -> ET.Element:
        if (
            len(
                tokens
            )
            < 6
            or tokens[
                2
            ].upper()
            != "ID"
            or tokens[
                4
            ].upper()
            != "KIND"
        ):
            raise DatrixTextError(
                "PUT syntax: "
                "PUT <datrix> ID <id> "
                "KIND <kind> ..."
            )

        attrs: dict[
            str,
            str,
        ] = {
            "datrix":
                tokens[
                    1
                ],

            "id":
                tokens[
                    3
                ],

            "kind":
                tokens[
                    5
                ],
        }

        clauses = (
            _parse_common_tail(
                tokens,
                6,
                {
                    "STATUS",
                    "TRUTH",
                    "AUTHORITY",
                    "AUTHORITY-TYPE",
                    "PAYLOAD",
                    "METADATA",
                    "DEPENDS",
                    "EVIDENCE",
                    "AS",
                },
            )
        )

        scalar_map = {
            "STATUS":
                "status",

            "TRUTH":
                "truth-state",

            "AUTHORITY":
                "authority",

            "AUTHORITY-TYPE":
                "authority-type",

            "AS":
                "as",
        }

        for (
            keyword,
            attr,
        ) in scalar_map.items():
            values = clauses.get(
                keyword,
                [],
            )

            if values:
                if (
                    len(
                        values
                    )
                    != 1
                    or len(
                        values[
                            0
                        ]
                    )
                    != 1
                ):
                    raise DatrixTextError(
                        f"{keyword} requires one value"
                    )

                attrs[
                    attr
                ] = values[
                    0
                ][
                    0
                ]

        element = _element(
            parent,
            "put",
            attrs,
        )

        for (
            keyword,
            local,
        ) in (
            (
                "PAYLOAD",
                "payload",
            ),
            (
                "METADATA",
                "metadata",
            ),
        ):
            values = clauses.get(
                keyword,
                [],
            )

            if values:
                if (
                    len(
                        values
                    )
                    != 1
                    or len(
                        values[
                            0
                        ]
                    )
                    != 1
                ):
                    raise DatrixTextError(
                        f"{keyword} requires one "
                        "quoted json object"
                    )

                _emit_object(
                    element,
                    local,
                    _json_object(
                        values[
                            0
                        ][
                            0
                        ],
                        keyword.lower(),
                    ),
                )

        for group in clauses.get(
            "DEPENDS",
            [],
        ):
            if len(
                group
            ) != 1:
                raise DatrixTextError(
                    "DEPENDS requires a "
                    "comma-separated reference list"
                )

            for ref in _split_csv(
                group[
                    0
                ]
            ):
                _element(
                    element,
                    "depends",
                    {
                        "ref":
                            ref
                    },
                )

        for group in clauses.get(
            "EVIDENCE",
            [],
        ):
            if len(
                group
            ) != 1:
                raise DatrixTextError(
                    "EVIDENCE requires a "
                    "comma-separated reference list"
                )

            for ref in _split_csv(
                group[
                    0
                ]
            ):
                _element(
                    element,
                    "evidence-ref",
                    {
                        "ref":
                            ref
                    },
                )

        return element

    def _segue(
        self,
        parent: ET.Element,
        tokens: Sequence[
            str
        ],
    ) -> ET.Element:
        if len(
            tokens
        ) < 10:
            raise DatrixTextError(
                "SEGUE syntax: SEGUE <datrix> "
                "ID <id> FROM <id> TO <id> "
                "RELATION <type> ..."
            )

        expected = {
            2:
                "ID",

            4:
                "FROM",

            6:
                "TO",

            8:
                "RELATION",
        }

        for (
            index,
            keyword,
        ) in expected.items():
            if (
                tokens[
                    index
                ].upper()
                != keyword
            ):
                raise DatrixTextError(
                    f"SEGUE expected {keyword} "
                    f"at token {index + 1}"
                )

        attrs = {
            "datrix":
                tokens[
                    1
                ],

            "id":
                tokens[
                    3
                ],

            "from":
                tokens[
                    5
                ],

            "to":
                tokens[
                    7
                ],

            "relation":
                tokens[
                    9
                ],
        }

        clauses = (
            _parse_common_tail(
                tokens,
                10,
                {
                    "PAYLOAD",
                    "AS",
                },
            )
        )

        if clauses.get(
            "AS"
        ):
            values = clauses[
                "AS"
            ]

            if (
                len(
                    values
                )
                != 1
                or len(
                    values[
                        0
                    ]
                )
                != 1
            ):
                raise DatrixTextError(
                    "AS requires one "
                    "result reference"
                )

            attrs[
                "as"
            ] = values[
                0
            ][
                0
            ]

        element = _element(
            parent,
            "segue",
            attrs,
        )

        if clauses.get(
            "PAYLOAD"
        ):
            values = clauses[
                "PAYLOAD"
            ]

            if (
                len(
                    values
                )
                != 1
                or len(
                    values[
                        0
                    ]
                )
                != 1
            ):
                raise DatrixTextError(
                    "PAYLOAD requires one "
                    "quoted json object"
                )

            payload = _json_object(
                values[
                    0
                ][
                    0
                ],
                "payload",
            )

            for key in sorted(
                payload
            ):
                _field(
                    element,
                    str(
                        key
                    ),
                    payload[
                        key
                    ],
                )

        return element

    def _update(
        self,
        parent: ET.Element,
        tokens: Sequence[
            str
        ],
    ) -> ET.Element:
        if (
            len(
                tokens
            )
            < 6
            or tokens[
                2
            ].upper()
            != "SUBJECT"
            or tokens[
                4
            ].upper()
            != "SUCCESSOR"
        ):
            raise DatrixTextError(
                "UPDATE syntax: "
                "UPDATE <datrix> "
                "SUBJECT <id> "
                "SUCCESSOR <id> ..."
            )

        attrs: dict[
            str,
            str,
        ] = {
            "datrix":
                tokens[
                    1
                ],

            "subject":
                tokens[
                    3
                ],

            "successor":
                tokens[
                    5
                ],
        }

        clauses = (
            _parse_common_tail(
                tokens,
                6,
                {
                    "EXPECT",
                    "STATUS",
                    "TRUTH",
                    "SET",
                    "UNSET",
                    "EVIDENCE",
                    "AS",
                },
            )
        )

        for (
            keyword,
            attr,
        ) in {
            "EXPECT":
                "expected-digest",

            "STATUS":
                "status",

            "TRUTH":
                "truth-state",

            "AS":
                "as",
        }.items():
            values = clauses.get(
                keyword,
                [],
            )

            if values:
                if (
                    len(
                        values
                    )
                    != 1
                    or len(
                        values[
                            0
                        ]
                    )
                    != 1
                ):
                    raise DatrixTextError(
                        f"{keyword} requires one value"
                    )

                attrs[
                    attr
                ] = values[
                    0
                ][
                    0
                ]

        element = _element(
            parent,
            "update",
            attrs,
        )

        for values in clauses.get(
            "SET",
            [],
        ):
            if len(
                values
            ) != 3:
                raise DatrixTextError(
                    "SET requires "
                    "<path> <type> <value>"
                )

            _element(
                element,
                "set",
                {
                    "path":
                        values[
                            0
                        ],

                    "type":
                        values[
                            1
                        ],

                    "value":
                        values[
                            2
                        ],
                },
            )

        for values in clauses.get(
            "UNSET",
            [],
        ):
            if len(
                values
            ) != 1:
                raise DatrixTextError(
                    "UNSET requires one path"
                )

            _element(
                element,
                "unset",
                {
                    "path":
                        values[
                            0
                        ]
                },
            )

        for group in clauses.get(
            "EVIDENCE",
            [],
        ):
            if len(
                group
            ) != 1:
                raise DatrixTextError(
                    "EVIDENCE requires a "
                    "comma-separated reference list"
                )

            for ref in _split_csv(
                group[
                    0
                ]
            ):
                _element(
                    element,
                    "evidence-ref",
                    {
                        "ref":
                            ref
                    },
                )

        return element

    def _retire(
        self,
        parent: ET.Element,
        tokens: Sequence[
            str
        ],
    ) -> ET.Element:
        if (
            len(
                tokens
            )
            < 6
            or tokens[
                2
            ].upper()
            != "SUBJECT"
            or tokens[
                4
            ].upper()
            != "TOMBSTONE"
        ):
            raise DatrixTextError(
                "RETIRE syntax: "
                "RETIRE <datrix> "
                "SUBJECT <id> "
                "TOMBSTONE <id> ..."
            )

        attrs: dict[
            str,
            str,
        ] = {
            "datrix":
                tokens[
                    1
                ],

            "subject":
                tokens[
                    3
                ],

            "tombstone":
                tokens[
                    5
                ],
        }

        clauses = (
            _parse_common_tail(
                tokens,
                6,
                {
                    "EXPECT",
                    "REASON",
                    "TRUTH",
                    "EVIDENCE",
                    "AS",
                },
            )
        )

        for (
            keyword,
            attr,
        ) in {
            "EXPECT":
                "expected-digest",

            "REASON":
                "reason",

            "TRUTH":
                "truth-state",

            "AS":
                "as",
        }.items():
            values = clauses.get(
                keyword,
                [],
            )

            if values:
                if (
                    len(
                        values
                    )
                    != 1
                    or len(
                        values[
                            0
                        ]
                    )
                    != 1
                ):
                    raise DatrixTextError(
                        f"{keyword} requires one value"
                    )

                attrs[
                    attr
                ] = values[
                    0
                ][
                    0
                ]

        element = _element(
            parent,
            "retire",
            attrs,
        )

        for group in clauses.get(
            "EVIDENCE",
            [],
        ):
            if len(
                group
            ) != 1:
                raise DatrixTextError(
                    "EVIDENCE requires a "
                    "comma-separated reference list"
                )

            for ref in _split_csv(
                group[
                    0
                ]
            ):
                _element(
                    element,
                    "evidence-ref",
                    {
                        "ref":
                            ref
                    },
                )

        return element

    def _select(
        self,
        parent: ET.Element,
        tokens: Sequence[
            str
        ],
    ) -> ET.Element:
        if len(
            tokens
        ) < 2:
            raise DatrixTextError(
                "SELECT requires a "
                "datrix reference"
            )

        attrs: dict[
            str,
            str,
        ] = {
            "datrix":
                tokens[
                    1
                ]
        }

        clauses = (
            _parse_common_tail(
                tokens,
                2,
                {
                    "VIEW",
                    "MATCH",
                    "WHERE",
                    "ORDER",
                    "DISTINCT",
                    "OFFSET",
                    "LIMIT",
                    "PROJECT",
                    "TRUTH",
                    "AS",
                },
            )
        )

        for (
            keyword,
            attr,
        ) in {
            "VIEW":
                "view",

            "TRUTH":
                "truth-minimum",

            "AS":
                "as",
        }.items():
            values = clauses.get(
                keyword,
                [],
            )

            if values:
                if (
                    len(
                        values
                    )
                    != 1
                    or len(
                        values[
                            0
                        ]
                    )
                    != 1
                ):
                    raise DatrixTextError(
                        f"{keyword} requires one value"
                    )

                attrs[
                    attr
                ] = values[
                    0
                ][
                    0
                ]

        element = _element(
            parent,
            "select",
            attrs,
        )

        for values in clauses.get(
            "MATCH",
            [],
        ):
            if len(
                values
            ) != 1:
                raise DatrixTextError(
                    "MATCH requires one "
                    "comma-separated kind list"
                )

            _element(
                element,
                "match",
                {
                    "kind":
                        values[
                            0
                        ]
                },
            )

        for values in clauses.get(
            "WHERE",
            [],
        ):
            if len(
                values
            ) != 4:
                raise DatrixTextError(
                    "WHERE requires "
                    "<path> <op> <type> <value>"
                )

            _element(
                element,
                "where",
                {
                    "path":
                        values[
                            0
                        ],

                    "op":
                        _normalize_op(
                            values[
                                1
                            ]
                        ),

                    "type":
                        values[
                            2
                        ],

                    "value":
                        values[
                            3
                        ],
                },
            )

        for values in clauses.get(
            "ORDER",
            [],
        ):
            if len(
                values
            ) not in {
                1,
                2,
            }:
                raise DatrixTextError(
                    "ORDER requires "
                    "<path> [asc|desc]"
                )

            _element(
                element,
                "order",
                {
                    "by":
                        values[
                            0
                        ],

                    "direction":
                        (
                            values[
                                1
                            ]
                            if len(
                                values
                            )
                            == 2
                            else "asc"
                        ),
                },
            )

        values = clauses.get(
            "DISTINCT",
            [],
        )

        if values:
            if (
                len(
                    values
                )
                != 1
                or len(
                    values[
                        0
                    ]
                )
                > 1
            ):
                raise DatrixTextError(
                    "DISTINCT accepts zero or "
                    "one comma-separated path list"
                )

            _element(
                element,
                "distinct",
                {
                    "fields":
                        (
                            values[
                                0
                            ][
                                0
                            ]
                            if values[
                                0
                            ]
                            else ""
                        )
                },
            )

        for (
            keyword,
            local,
            attr,
        ) in (
            (
                "OFFSET",
                "offset",
                "count",
            ),
            (
                "LIMIT",
                "limit",
                "count",
            ),
        ):
            values = clauses.get(
                keyword,
                [],
            )

            if values:
                if (
                    len(
                        values
                    )
                    != 1
                    or len(
                        values[
                            0
                        ]
                    )
                    != 1
                ):
                    raise DatrixTextError(
                        f"{keyword} requires one integer"
                    )

                _element(
                    element,
                    local,
                    {
                        attr:
                            values[
                                0
                            ][
                                0
                            ]
                    },
                )

        values = clauses.get(
            "PROJECT",
            [],
        )

        if values:
            if (
                len(
                    values
                )
                != 1
                or len(
                    values[
                        0
                    ]
                )
                != 1
            ):
                raise DatrixTextError(
                    "PROJECT requires one "
                    "comma-separated field list"
                )

            _element(
                element,
                "project",
                {
                    "fields":
                        values[
                            0
                        ][
                            0
                        ]
                },
            )

        return element

    def _join(
        self,
        parent: ET.Element,
        tokens: Sequence[
            str
        ],
    ) -> ET.Element:
        if (
            len(
                tokens
            )
            < 4
            or tokens[
                2
            ].upper()
            != "WITH"
        ):
            raise DatrixTextError(
                "JOIN syntax: "
                "JOIN <left-ref> "
                "WITH <right-ref> ..."
            )

        attrs: dict[
            str,
            str,
        ] = {
            "left":
                tokens[
                    1
                ],

            "right":
                tokens[
                    3
                ],
        }

        clauses = (
            _parse_common_tail(
                tokens,
                4,
                {
                    "TYPE",
                    "ON",
                    "AS",
                },
            )
        )

        if clauses.get(
            "TYPE"
        ):
            values = clauses[
                "TYPE"
            ]

            if (
                len(
                    values
                )
                != 1
                or len(
                    values[
                        0
                    ]
                )
                != 1
            ):
                raise DatrixTextError(
                    "TYPE requires one join type"
                )

            attrs[
                "type"
            ] = values[
                0
            ][
                0
            ]

        if clauses.get(
            "AS"
        ):
            values = clauses[
                "AS"
            ]

            if (
                len(
                    values
                )
                != 1
                or len(
                    values[
                        0
                    ]
                )
                != 1
            ):
                raise DatrixTextError(
                    "AS requires one "
                    "result reference"
                )

            attrs[
                "as"
            ] = values[
                0
            ][
                0
            ]

        element = _element(
            parent,
            "join",
            attrs,
        )

        if not clauses.get(
            "ON"
        ):
            raise DatrixTextError(
                "JOIN requires at least "
                "one ON clause"
            )

        for values in clauses[
            "ON"
        ]:
            if len(
                values
            ) != 3:
                raise DatrixTextError(
                    "ON requires "
                    "<left-path> <op> "
                    "<right-path>"
                )

            _element(
                element,
                "on",
                {
                    "left":
                        values[
                            0
                        ],

                    "op":
                        _normalize_op(
                            values[
                                1
                            ]
                        ),

                    "right":
                        values[
                            2
                        ],
                },
            )

        return element

    def _distinct(
        self,
        parent: ET.Element,
        tokens: Sequence[
            str
        ],
    ) -> ET.Element:
        if len(
            tokens
        ) < 2:
            raise DatrixTextError(
                "DISTINCT requires a "
                "source result reference"
            )

        attrs: dict[
            str,
            str,
        ] = {
            "source":
                tokens[
                    1
                ]
        }

        clauses = (
            _parse_common_tail(
                tokens,
                2,
                {
                    "BY",
                    "AS",
                },
            )
        )

        if clauses.get(
            "BY"
        ):
            values = clauses[
                "BY"
            ]

            if (
                len(
                    values
                )
                != 1
                or len(
                    values[
                        0
                    ]
                )
                != 1
            ):
                raise DatrixTextError(
                    "BY requires one "
                    "comma-separated path list"
                )

            attrs[
                "by"
            ] = values[
                0
            ][
                0
            ]

        if clauses.get(
            "AS"
        ):
            values = clauses[
                "AS"
            ]

            if (
                len(
                    values
                )
                != 1
                or len(
                    values[
                        0
                    ]
                )
                != 1
            ):
                raise DatrixTextError(
                    "AS requires one "
                    "result reference"
                )

            attrs[
                "as"
            ] = values[
                0
            ][
                0
            ]

        return _element(
            parent,
            "distinct",
            attrs,
        )

    def _aggregate(
        self,
        parent: ET.Element,
        tokens: Sequence[
            str
        ],
    ) -> ET.Element:
        if len(
            tokens
        ) < 2:
            raise DatrixTextError(
                "AGGREGATE requires a "
                "source result reference"
            )

        element = _element(
            parent,
            "aggregate",
            {
                "source":
                    tokens[
                        1
                    ]
            },
        )

        clauses = (
            _parse_common_tail(
                tokens,
                2,
                {
                    "BY",
                    "METRIC",
                    "HAVING",
                    "ORDER",
                    "OFFSET",
                    "LIMIT",
                    "AS",
                },
            )
        )

        if clauses.get(
            "BY"
        ):
            values = clauses[
                "BY"
            ]

            if (
                len(
                    values
                )
                != 1
                or len(
                    values[
                        0
                    ]
                )
                != 1
            ):
                raise DatrixTextError(
                    "BY requires one "
                    "comma-separated field list"
                )

            _element(
                element,
                "group",
                {
                    "fields":
                        values[
                            0
                        ][
                            0
                        ]
                },
            )

        for values in clauses.get(
            "METRIC",
            [],
        ):
            if len(
                values
            ) not in {
                2,
                3,
            }:
                raise DatrixTextError(
                    "METRIC requires "
                    "<alias> <fn> [path|*]"
                )

            _element(
                element,
                "metric",
                {
                    "alias":
                        values[
                            0
                        ],

                    "fn":
                        values[
                            1
                        ],

                    "path":
                        (
                            ""
                            if (
                                len(
                                    values
                                )
                                == 2
                                or values[
                                    2
                                ]
                                == "*"
                            )
                            else values[
                                2
                            ]
                        ),
                },
            )

        for values in clauses.get(
            "HAVING",
            [],
        ):
            if len(
                values
            ) != 4:
                raise DatrixTextError(
                    "HAVING requires "
                    "<path> <op> <type> <value>"
                )

            _element(
                element,
                "having",
                {
                    "path":
                        values[
                            0
                        ],

                    "op":
                        _normalize_op(
                            values[
                                1
                            ]
                        ),

                    "type":
                        values[
                            2
                        ],

                    "value":
                        values[
                            3
                        ],
                },
            )

        for values in clauses.get(
            "ORDER",
            [],
        ):
            if len(
                values
            ) not in {
                1,
                2,
            }:
                raise DatrixTextError(
                    "ORDER requires "
                    "<path> [asc|desc]"
                )

            _element(
                element,
                "order",
                {
                    "by":
                        values[
                            0
                        ],

                    "direction":
                        (
                            values[
                                1
                            ]
                            if len(
                                values
                            )
                            == 2
                            else "asc"
                        ),
                },
            )

        for (
            keyword,
            local,
        ) in (
            (
                "OFFSET",
                "offset",
            ),
            (
                "LIMIT",
                "limit",
            ),
        ):
            values = clauses.get(
                keyword,
                [],
            )

            if values:
                if (
                    len(
                        values
                    )
                    != 1
                    or len(
                        values[
                            0
                        ]
                    )
                    != 1
                ):
                    raise DatrixTextError(
                        f"{keyword} requires one integer"
                    )

                _element(
                    element,
                    local,
                    {
                        "count":
                            values[
                                0
                            ][
                                0
                            ]
                    },
                )

        if clauses.get(
            "AS"
        ):
            values = clauses[
                "AS"
            ]

            if (
                len(
                    values
                )
                != 1
                or len(
                    values[
                        0
                    ]
                )
                != 1
            ):
                raise DatrixTextError(
                    "AS requires one "
                    "result reference"
                )

            element.set(
                "as",
                values[
                    0
                ][
                    0
                ],
            )

        return element

    def _window(
        self,
        parent: ET.Element,
        tokens: Sequence[
            str
        ],
    ) -> ET.Element:
        if (
            len(
                tokens
            )
            < 4
            or tokens[
                2
            ].upper()
            != "FN"
        ):
            raise DatrixTextError(
                "WINDOW syntax: "
                "WINDOW <source> FN <function> ..."
            )

        attrs: dict[
            str,
            str,
        ] = {
            "source":
                tokens[
                    1
                ],

            "fn":
                tokens[
                    3
                ],
        }

        clauses = (
            _parse_common_tail(
                tokens,
                4,
                {
                    "ALIAS",
                    "PARTITION",
                    "ORDER",
                    "AS",
                },
            )
        )

        if clauses.get(
            "ALIAS"
        ):
            values = clauses[
                "ALIAS"
            ]

            if (
                len(
                    values
                )
                != 1
                or len(
                    values[
                        0
                    ]
                )
                != 1
            ):
                raise DatrixTextError(
                    "ALIAS requires one field name"
                )

            attrs[
                "alias"
            ] = values[
                0
            ][
                0
            ]

        if clauses.get(
            "AS"
        ):
            values = clauses[
                "AS"
            ]

            if (
                len(
                    values
                )
                != 1
                or len(
                    values[
                        0
                    ]
                )
                != 1
            ):
                raise DatrixTextError(
                    "AS requires one "
                    "result reference"
                )

            attrs[
                "as"
            ] = values[
                0
            ][
                0
            ]

        element = _element(
            parent,
            "window",
            attrs,
        )

        if clauses.get(
            "PARTITION"
        ):
            values = clauses[
                "PARTITION"
            ]

            if (
                len(
                    values
                )
                != 1
                or len(
                    values[
                        0
                    ]
                )
                != 1
            ):
                raise DatrixTextError(
                    "PARTITION requires one "
                    "comma-separated field list"
                )

            _element(
                element,
                "partition",
                {
                    "fields":
                        values[
                            0
                        ][
                            0
                        ]
                },
            )

        for values in clauses.get(
            "ORDER",
            [],
        ):
            if len(
                values
            ) not in {
                1,
                2,
            }:
                raise DatrixTextError(
                    "ORDER requires "
                    "<path> [asc|desc]"
                )

            _element(
                element,
                "order",
                {
                    "by":
                        values[
                            0
                        ],

                    "direction":
                        (
                            values[
                                1
                            ]
                            if len(
                                values
                            )
                            == 2
                            else "asc"
                        ),
                },
            )

        return element

    def _simple(
        self,
        parent: ET.Element,
        tokens: Sequence[
            str
        ],
    ) -> ET.Element:
        keyword = tokens[
            0
        ].upper()

        if keyword in {
            "UNION",
            "INTERSECT",
            "DIFF",
        }:
            if len(
                tokens
            ) < 2:
                raise DatrixTextError(
                    f"{keyword} requires "
                    "comma-separated refs"
                )

            attrs = {
                "refs":
                    tokens[
                        1
                    ]
            }

            clauses = (
                _parse_common_tail(
                    tokens,
                    2,
                    {
                        "AS"
                    },
                )
            )

            if clauses.get(
                "AS"
            ):
                values = clauses[
                    "AS"
                ]

                if (
                    len(
                        values
                    )
                    != 1
                    or len(
                        values[
                            0
                        ]
                    )
                    != 1
                ):
                    raise DatrixTextError(
                        "AS requires one "
                        "result reference"
                    )

                attrs[
                    "as"
                ] = values[
                    0
                ][
                    0
                ]

            return _element(
                parent,
                keyword.casefold(),
                attrs,
            )

        if keyword == "WALK":
            if (
                len(
                    tokens
                )
                < 4
                or tokens[
                    2
                ].upper()
                != "FROM"
            ):
                raise DatrixTextError(
                    "WALK syntax: "
                    "WALK <datrix> FROM <id> ..."
                )

            attrs = {
                "datrix":
                    tokens[
                        1
                    ],

                "from":
                    tokens[
                        3
                    ],
            }

            clauses = (
                _parse_common_tail(
                    tokens,
                    4,
                    {
                        "RELATION",
                        "DIRECTION",
                        "DEPTH",
                        "TRUTH",
                        "AS",
                    },
                )
            )

            for (
                key,
                attr,
            ) in {
                "RELATION":
                    "relation",

                "DIRECTION":
                    "direction",

                "DEPTH":
                    "depth",

                "TRUTH":
                    "truth-minimum",

                "AS":
                    "as",
            }.items():
                values = clauses.get(
                    key,
                    [],
                )

                if values:
                    if (
                        len(
                            values
                        )
                        != 1
                        or len(
                            values[
                                0
                            ]
                        )
                        != 1
                    ):
                        raise DatrixTextError(
                            f"{key} requires one value"
                        )

                    attrs[
                        attr
                    ] = values[
                        0
                    ][
                        0
                    ]

            return _element(
                parent,
                "walk",
                attrs,
            )

        if keyword == "PROJECT":
            if (
                len(
                    tokens
                )
                < 4
                or tokens[
                    2
                ].upper()
                != "TYPE"
            ):
                raise DatrixTextError(
                    "PROJECT syntax: "
                    "PROJECT <datrix> TYPE <type> "
                    "[AS <ref>]"
                )

            attrs = {
                "datrix":
                    tokens[
                        1
                    ],

                "type":
                    tokens[
                        3
                    ],
            }

            clauses = (
                _parse_common_tail(
                    tokens,
                    4,
                    {
                        "FIELDS",
                        "AS",
                    },
                )
            )

            for (
                key,
                attr,
            ) in {
                "FIELDS":
                    "fields",

                "AS":
                    "as",
            }.items():
                values = clauses.get(
                    key,
                    [],
                )

                if values:
                    if (
                        len(
                            values
                        )
                        != 1
                        or len(
                            values[
                                0
                            ]
                        )
                        != 1
                    ):
                        raise DatrixTextError(
                            f"{key} requires one value"
                        )

                    attrs[
                        attr
                    ] = values[
                        0
                    ][
                        0
                    ]

            return _element(
                parent,
                "project",
                attrs,
            )

        if keyword == "ASSERT":
            if (
                len(
                    tokens
                )
                < 4
                or tokens[
                    2
                ].upper()
                != "PATH"
            ):
                raise DatrixTextError(
                    "ASSERT syntax: "
                    "ASSERT <ref> PATH <path> ..."
                )

            attrs = {
                "ref":
                    tokens[
                        1
                    ],

                "path":
                    tokens[
                        3
                    ],
            }

            clauses = (
                _parse_common_tail(
                    tokens,
                    4,
                    {
                        "OP",
                        "TYPE",
                        "VALUE",
                    },
                )
            )

            for (
                key,
                attr,
            ) in {
                "OP":
                    "op",

                "TYPE":
                    "type",

                "VALUE":
                    "value",
            }.items():
                values = clauses.get(
                    key,
                    [],
                )

                if values:
                    if (
                        len(
                            values
                        )
                        != 1
                        or len(
                            values[
                                0
                            ]
                        )
                        != 1
                    ):
                        raise DatrixTextError(
                            f"{key} requires one value"
                        )

                    attrs[
                        attr
                    ] = (
                        _normalize_op(
                            values[
                                0
                            ][
                                0
                            ]
                        )
                        if key
                        == "OP"
                        else values[
                            0
                        ][
                            0
                        ]
                    )

            return _element(
                parent,
                "assert",
                attrs,
            )

        if keyword == "TRUTHGATE":
            if len(
                tokens
            ) < 2:
                raise DatrixTextError(
                    "TRUTHGATE requires "
                    "a result ref"
                )

            attrs = {
                "ref":
                    tokens[
                        1
                    ]
            }

            clauses = (
                _parse_common_tail(
                    tokens,
                    2,
                    {
                        "MINIMUM",
                        "ALLOWEMPTY",
                        "AS",
                    },
                )
            )

            for (
                key,
                attr,
            ) in {
                "MINIMUM":
                    "minimum",

                "ALLOWEMPTY":
                    "allow-empty",

                "AS":
                    "as",
            }.items():
                values = clauses.get(
                    key,
                    [],
                )

                if values:
                    if (
                        len(
                            values
                        )
                        != 1
                        or len(
                            values[
                                0
                            ]
                        )
                        != 1
                    ):
                        raise DatrixTextError(
                            f"{key} requires one value"
                        )

                    attrs[
                        attr
                    ] = (
                        _bool_text(
                            values[
                                0
                            ][
                                0
                            ]
                        )
                        if key
                        == "ALLOWEMPTY"
                        else values[
                            0
                        ][
                            0
                        ]
                    )

            return _element(
                parent,
                "truth-gate",
                attrs,
            )

        if keyword in {
            "CHECKPOINT",
            "HEALTH",
        }:
            if len(
                tokens
            ) < 2:
                raise DatrixTextError(
                    f"{keyword} requires "
                    "a datrix ref"
                )

            attrs = {
                "datrix":
                    tokens[
                        1
                    ]
            }

            clauses = (
                _parse_common_tail(
                    tokens,
                    2,
                    {
                        "AS"
                    },
                )
            )

            if clauses.get(
                "AS"
            ):
                values = clauses[
                    "AS"
                ]

                if (
                    len(
                        values
                    )
                    != 1
                    or len(
                        values[
                            0
                        ]
                    )
                    != 1
                ):
                    raise DatrixTextError(
                        "AS requires one "
                        "result reference"
                    )

                attrs[
                    "as"
                ] = values[
                    0
                ][
                    0
                ]

            return _element(
                parent,
                keyword.casefold(),
                attrs,
            )

        if keyword == "EXPLAIN":
            if len(
                tokens
            ) != 2:
                raise DatrixTextError(
                    "EXPLAIN requires exactly "
                    "one result ref"
                )

            return _element(
                parent,
                "explain",
                {
                    "ref":
                        tokens[
                            1
                        ]
                },
            )

        if keyword == "ROLLBACK":
            if (
                len(
                    tokens
                )
                < 4
                or tokens[
                    2
                ].upper()
                != "REF"
            ):
                raise DatrixTextError(
                    "ROLLBACK syntax: "
                    "ROLLBACK <datrix> "
                    "REF <transaction-ref> "
                    "[AS <ref>]"
                )

            attrs = {
                "datrix":
                    tokens[
                        1
                    ],

                "ref":
                    tokens[
                        3
                    ],
            }

            clauses = (
                _parse_common_tail(
                    tokens,
                    4,
                    {
                        "AS"
                    },
                )
            )

            if clauses.get(
                "AS"
            ):
                values = clauses[
                    "AS"
                ]

                if (
                    len(
                        values
                    )
                    != 1
                    or len(
                        values[
                            0
                        ]
                    )
                    != 1
                ):
                    raise DatrixTextError(
                        "AS requires one "
                        "result reference"
                    )

                attrs[
                    "as"
                ] = values[
                    0
                ][
                    0
                ]

            return _element(
                parent,
                "rollback",
                attrs,
            )

        raise DatrixTextError(
            "unsupported text statement: "
            f"{keyword}"
        )

    def _statement(
        self,
        parent: ET.Element,
        tokens: Sequence[
            str
        ],
    ) -> ET.Element:
        keyword = tokens[
            0
        ].upper()

        if keyword == "OPEN":
            return self._open(
                parent,
                tokens,
            )

        if keyword == "PUT":
            return self._put(
                parent,
                tokens,
            )

        if keyword == "SEGUE":
            return self._segue(
                parent,
                tokens,
            )

        if keyword == "UPDATE":
            return self._update(
                parent,
                tokens,
            )

        if keyword == "RETIRE":
            return self._retire(
                parent,
                tokens,
            )

        if keyword == "SELECT":
            return self._select(
                parent,
                tokens,
            )

        if keyword == "JOIN":
            return self._join(
                parent,
                tokens,
            )

        if keyword == "DISTINCT":
            return self._distinct(
                parent,
                tokens,
            )

        if keyword == "AGGREGATE":
            return self._aggregate(
                parent,
                tokens,
            )

        if keyword == "WINDOW":
            return self._window(
                parent,
                tokens,
            )

        return self._simple(
            parent,
            tokens,
        )

    def to_svg(
        self,
        source: str,
        *,
        program_id: str = "datrix-text",
        truth_minimum: str | None = None,
    ) -> dict[
        str,
        Any,
    ]:
        source_text = str(
            source
        )

        statements = (
            _split_statements(
                source_text
            )
        )

        if not statements:
            raise DatrixTextError(
                "text source contains "
                "no statements"
            )

        ET.register_namespace(
            "",
            SVG_NS,
        )

        ET.register_namespace(
            "tl",
            TL_NS,
        )

        root = ET.Element(
            f"{{{SVG_NS}}}svg"
        )

        metadata = ET.SubElement(
            root,
            f"{{{SVG_NS}}}metadata",
        )

        program_attrs = {
            "id":
                _clean(
                    program_id,
                    "program_id",
                ),

            "grammar-version":
                self.grammar_version,
        }

        if truth_minimum is not None:
            program_attrs[
                "truth-minimum"
            ] = str(
                truth_minimum
            )

        program = _element(
            metadata,
            "program",
            program_attrs,
        )

        transaction: (
            ET.Element
            | None
        ) = None

        transaction_datrix: (
            str
            | None
        ) = None

        for (
            statement_index,
            statement,
        ) in enumerate(
            statements,
            start=1,
        ):
            tokens = _tokens(
                statement
            )

            keyword = tokens[
                0
            ].upper()

            if keyword == "BEGIN":
                if transaction is not None:
                    raise DatrixTextError(
                        "nested BEGIN is forbidden"
                    )

                if (
                    len(
                        tokens
                    )
                    < 4
                    or tokens[
                        2
                    ].upper()
                    != "ID"
                ):
                    raise DatrixTextError(
                        "BEGIN syntax: "
                        "BEGIN <datrix> ID <id> "
                        "[AS <ref>]"
                    )

                attrs: dict[
                    str,
                    str,
                ] = {
                    "datrix":
                        tokens[
                            1
                        ],

                    "id":
                        tokens[
                            3
                        ],
                }

                clauses = (
                    _parse_common_tail(
                        tokens,
                        4,
                        {
                            "AS"
                        },
                    )
                )

                if clauses.get(
                    "AS"
                ):
                    values = clauses[
                        "AS"
                    ]

                    if (
                        len(
                            values
                        )
                        != 1
                        or len(
                            values[
                                0
                            ]
                        )
                        != 1
                    ):
                        raise DatrixTextError(
                            "BEGIN AS requires "
                            "one result reference"
                        )

                    attrs[
                        "as"
                    ] = values[
                        0
                    ][
                        0
                    ]

                transaction = _element(
                    program,
                    "transaction",
                    attrs,
                )

                transaction_datrix = (
                    tokens[
                        1
                    ]
                )

                continue

            if keyword == "COMMIT":
                if len(
                    tokens
                ) != 1:
                    raise DatrixTextError(
                        "COMMIT takes no arguments"
                    )

                if transaction is None:
                    raise DatrixTextError(
                        "COMMIT without BEGIN"
                    )

                transaction = None
                transaction_datrix = None

                continue

            parent = (
                transaction
                if transaction
                is not None
                else program
            )

            element = self._statement(
                parent,
                tokens,
            )

            if transaction is not None:
                local = element.tag.split(
                    "}",
                    1,
                )[
                    -1
                ]

                if local not in {
                    "put",
                    "segue",
                    "update",
                    "retire",
                }:
                    raise DatrixTextError(
                        "transaction statement "
                        f"{statement_index} "
                        "is not a mutation: "
                        f"{local}"
                    )

                if (
                    element.get(
                        "datrix"
                    )
                    != transaction_datrix
                ):
                    raise DatrixTextError(
                        "transaction mutation "
                        "must target the BEGIN datrix"
                    )

        if transaction is not None:
            raise DatrixTextError(
                "BEGIN transaction is "
                "missing COMMIT"
            )

        svg = ET.tostring(
            root,
            encoding="unicode",
            short_empty_elements=True,
        )

        return {
            "schema":
                schema,

            "source_digest":
                _digest_text(
                    source_text
                ),

            "svg_digest":
                _digest_text(
                    svg
                ),

            "statement_count":
                len(
                    statements
                ),

            "svg":
                svg,

            "authority_effect":
                authority_effect,
        }


text_frontend = (
    DatrixTextFrontend()
)


__all__ = [
    "DatrixTextError",
    "DatrixTextFrontend",
    "MAX_SOURCE_CHARS",
    "MAX_STATEMENTS",
    "MAX_TOKENS_PER_STATEMENT",
    "authority_effect",
    "schema",
    "text_frontend",
]




#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import hashlib
import html
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import re
import sys
import unicodedata
from typing import Any, Iterable, Iterator, Mapping


schema = "savant.extr.universal.v1"

text_suffixes = frozenset(
    {
        ".txt",
        ".text",
        ".md",
        ".markdown",
        ".rst",
        ".log",
        ".cfg",
        ".conf",
        ".ini",
        ".env",
        ".toml",
        ".yaml",
        ".yml",
        ".csv",
        ".tsv",
        ".json",
        ".jsonl",
        ".ndjson",
        ".json5",
        ".html",
        ".htm",
        ".xml",
        ".xhtml",
        ".svg",
        ".rtf",
        ".sql",
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".c",
        ".h",
        ".cpp",
        ".hpp",
        ".rs",
        ".go",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".ps1",
        ".properties",
        ".csv",
        ".tsv",
    }
)

json_suffixes = frozenset(
    {
        ".json",
        ".jsonl",
        ".ndjson",
        ".json5",
    }
)

zero_width = re.compile(
    "[\u200b\u200c\u200d\u2060\ufeff]"
)

horizontal_space = re.compile(
    r"[^\S\r\n]+"
)

excess_blank_lines = re.compile(
    r"\n{4,}"
)

fenced_json = re.compile(
    r"```(?:json|json5)?\s*(.*?)```",
    re.IGNORECASE | re.DOTALL,
)

obvious_noise_lines = (
    re.compile(r"^\s*$"),
    re.compile(r"^\s*[-_=*#]{8,}\s*$"),
)

repeated_punctuation = re.compile(
    r"([!?.,;:])\1{4,}"
)

token_pattern = re.compile(
    r"[\w][\w'-]{1,}",
    re.UNICODE,
)


try:
    from charset_normalizer import (
        from_bytes as charset_from_bytes,
    )
except Exception:
    charset_from_bytes = None


try:
    import ftfy
except Exception:
    ftfy = None


try:
    import orjson
except Exception:
    orjson = None


try:
    import json5
except Exception:
    json5 = None


try:
    from rapidfuzz import fuzz
except Exception:
    fuzz = None


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> None:
        del attrs

        lowered

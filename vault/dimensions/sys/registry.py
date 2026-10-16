#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path


class Registry:

    def __init__(self, sys_root: Path):
        self.sys_root = sys_root

    def load_json(self, name: str) -> dict:
        return json.loads(
            (
                self.sys_root / name
            ).read_text(
                encoding="utf-8"
            )
        )

    def dimensions(self):
        return self.load_json(
            "dimension_registry.json"
        )

    def occurrences(self):
        return self.load_json(
            "occurrence_classes.json"
        )

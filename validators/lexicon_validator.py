#!/usr/bin/env python3

from pathlib import Path
import yaml
import sys

ROOT = Path.home() / "savant-runtime" / "lexicon"

registry = yaml.safe_load((ROOT / "registry.yaml").read_text())

seen = set()

for word in registry["lexicon"]:

    lw = word.lower()

    if lw in seen:
        print(f"DUPLICATE LEXEME: {word}")
        sys.exit(1)

    seen.add(lw)

print("Lexicon OK")

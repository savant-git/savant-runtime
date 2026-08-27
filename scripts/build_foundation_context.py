#!/usr/bin/env python3
from pathlib import Path

ROOT = Path("/root/savant-runtime")
OUT = ROOT / "context/FOUNDATION_CONTEXT.md"

parts = []
parts.append("# SAVANT FOUNDATION CONTEXT\n")
parts.append("Generated. Do not edit manually.\n")

for path in sorted((ROOT / "canon/foundation").glob("*.md")):
    parts.append("\n---\n")
    parts.append(f"\nSOURCE: {path.relative_to(ROOT)}\n\n")
    parts.append(path.read_text(encoding="utf-8", errors="replace"))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
print(OUT)

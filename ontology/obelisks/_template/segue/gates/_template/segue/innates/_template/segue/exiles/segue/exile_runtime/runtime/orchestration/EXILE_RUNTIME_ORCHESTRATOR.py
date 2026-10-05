from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]

EXILES = ROOT.parent

BOOT_ORDER = [
    "registry",
    "graph",
    "authority",
    "canon",
    "composition",
    "facets",
    "interface",
    "runtime",
    "observatory",
]


def boot():
    print("=== EXILE RUNTIME ===")

    for subsystem in BOOT_ORDER:
        print(f"[BOOT] {subsystem}")

    print()

    for exile in sorted(EXILES.iterdir()):
        if exile.is_dir() and exile.name != "segue":
            print(f"[READY] {exile.name}")


if __name__ == "__main__":
    boot()

#!/usr/bin/env python3

from __future__ import annotations

import os
import re
import stat
from pathlib import Path


ROOT = Path.home() / "savant-runtime"
LEXICON_ROOT = ROOT / "lexicon"
BIN_ROOT = LEXICON_ROOT / "bin"

LEXICON_VALIDATOR = (
    LEXICON_ROOT
    / "validators"
    / "lexicon_validator.py"
)


def repair_dataclass_field_collision() -> None:
    source = LEXICON_VALIDATOR.read_text(
        encoding="utf-8"
    )

    original = source

    source = re.sub(
        r"from dataclasses import ([^\n]+)",
        lambda match: replace_dataclasses_import(
            match.group(0)
        ),
        source,
        count=1,
    )

    source = re.sub(
        r"(?<![\w.])field\(",
        "dataclass_field(",
        source,
    )

    if source == original:
        print(
            "lexicon_validator.py: "
            "no dataclass repair required"
        )
        return

    backup = LEXICON_VALIDATOR.with_suffix(
        ".py.before_runtime_repair"
    )

    if not backup.exists():
        backup.write_text(
            original,
            encoding="utf-8",
        )

    LEXICON_VALIDATOR.write_text(
        source,
        encoding="utf-8",
    )

    print(
        "lexicon_validator.py: repaired "
        "dataclasses.field collision"
    )


def replace_dataclasses_import(
    import_line: str,
) -> str:
    if "dataclass_field" in import_line:
        return import_line

    prefix = "from dataclasses import "
    imported = import_line[len(prefix):]

    names = [
        name.strip()
        for name in imported.split(",")
        if name.strip()
    ]

    replaced = []

    for name in names:
        if name == "field":
            replaced.append(
                "field as dataclass_field"
            )
        else:
            replaced.append(
                name
            )

    if not any(
        name.startswith("field")
        for name in names
    ):
        replaced.append(
            "field as dataclass_field"
        )

    return (
        prefix
        + ", ".join(replaced)
    )


CONTROLLER_TEMPLATE = r'''#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


SUBSYSTEM = "__SUBSYSTEM__"

LEXICON_ROOT = Path(
    __file__
).resolve().parents[1]

THIS_FILE = Path(
    __file__
).resolve()


def executable_candidates() -> list[Path]:
    return [
        LEXICON_ROOT
        / SUBSYSTEM
        / "bin"
        / f"{SUBSYSTEM}ctl",

        LEXICON_ROOT
        / SUBSYSTEM
        / f"{SUBSYSTEM}ctl",

        LEXICON_ROOT
        / f"{SUBSYSTEM}_engine"
        / "bin"
        / f"{SUBSYSTEM}ctl",

        LEXICON_ROOT
        / f"{SUBSYSTEM}_engine"
        / f"{SUBSYSTEM}ctl",
    ]


def engine_candidates() -> list[Path]:
    return [
        LEXICON_ROOT
        / SUBSYSTEM
        / f"{SUBSYSTEM}_engine.py",

        LEXICON_ROOT
        / SUBSYSTEM
        / "runtime"
        / f"{SUBSYSTEM}_engine.py",

        LEXICON_ROOT
        / f"{SUBSYSTEM}_engine"
        / f"{SUBSYSTEM}_engine.py",

        LEXICON_ROOT
        / f"{SUBSYSTEM}_engine"
        / "runtime"
        / f"{SUBSYSTEM}_engine.py",
    ]


def validator_candidates() -> list[Path]:
    return [
        LEXICON_ROOT
        / SUBSYSTEM
        / f"{SUBSYSTEM}_validator.py",

        LEXICON_ROOT
        / SUBSYSTEM
        / "validators"
        / f"{SUBSYSTEM}_validator.py",

        LEXICON_ROOT
        / f"{SUBSYSTEM}_engine"
        / f"{SUBSYSTEM}_validator.py",

        LEXICON_ROOT
        / f"{SUBSYSTEM}_engine"
        / "validators"
        / f"{SUBSYSTEM}_validator.py",
    ]


def first_existing(
    candidates: list[Path],
) -> Path | None:
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue

        if resolved == THIS_FILE:
            continue

        if candidate.is_file():
            return candidate

    return None


def execute(
    command: list[str],
) -> int:
    return subprocess.run(
        command,
        cwd=str(
            LEXICON_ROOT
        ),
        check=False,
    ).returncode


def run_controller(
    controller: Path,
    arguments: list[str],
) -> int:
    if os.access(
        controller,
        os.X_OK,
    ):
        return execute(
            [
                str(controller),
                *arguments,
            ]
        )

    return execute(
        [
            sys.executable,
            str(controller),
            *arguments,
        ]
    )


def run_python(
    script: Path,
    arguments: list[str],
) -> int:
    return execute(
        [
            sys.executable,
            str(script),
            *arguments,
        ]
    )


def usage() -> None:
    print(
        f"""
{SUBSYSTEM}ctl validate
{SUBSYSTEM}ctl compile
{SUBSYSTEM}ctl integrity
{SUBSYSTEM}ctl <engine-command> [arguments...]
"""
    )


def main() -> int:
    arguments = sys.argv[1:]

    if not arguments:
        usage()
        return 1

    if arguments[0] in {
        "help",
        "--help",
        "-h",
    }:
        usage()
        return 0

    controller = first_existing(
        executable_candidates()
    )

    if controller is not None:
        return run_controller(
            controller,
            arguments,
        )

    command = arguments[0]
    remaining = arguments[1:]

    engine = first_existing(
        engine_candidates()
    )

    validator = first_existing(
        validator_candidates()
    )

    if command == "validate":
        if validator is not None:
            return run_python(
                validator,
                remaining,
            )

        if engine is not None:
            return run_python(
                engine,
                [
                    "validate",
                    *remaining,
                ],
            )

    if command == "compile":
        if validator is not None:
            status = run_python(
                validator,
                [],
            )

            if status:
                return status

        if engine is not None:
            return run_python(
                engine,
                [
                    "compile",
                    *remaining,
                ],
            )

    if command == "integrity":
        if validator is not None:
            status = run_python(
                validator,
                [],
            )

            if status:
                return status

        if engine is not None:
            return run_python(
                engine,
                [
                    "integrity",
                    *remaining,
                ],
            )

    if engine is not None:
        return run_python(
            engine,
            arguments,
        )

    print(
        f"Unable to locate the {SUBSYSTEM} "
        f"controller, engine, or validator.",
        file=sys.stderr,
    )

    print(
        "Searched:",
        file=sys.stderr,
    )

    for candidate in (
        executable_candidates()
        + engine_candidates()
        + validator_candidates()
    ):
        print(
            f"  {candidate}",
            file=sys.stderr,
        )

    return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
'''


def install_controller(
    subsystem: str,
) -> None:
    destination = (
        BIN_ROOT
        / f"{subsystem}ctl"
    )

    if destination.exists():
        print(
            f"{destination.name}: already exists"
        )
        return

    content = CONTROLLER_TEMPLATE.replace(
        "__SUBSYSTEM__",
        subsystem,
    )

    destination.write_text(
        content,
        encoding="utf-8",
    )

    current_mode = destination.stat().st_mode

    destination.chmod(
        current_mode
        | stat.S_IXUSR
        | stat.S_IXGRP
        | stat.S_IXOTH
    )

    print(
        f"{destination.name}: installed "
        "compatibility controller"
    )


def main() -> int:
    BIN_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    repair_dataclass_field_collision()

    for subsystem in (
        "ontology",
        "kindred",
        "instance",
        "segue",
        "projection",
        "constitution",
    ):
        install_controller(
            subsystem
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

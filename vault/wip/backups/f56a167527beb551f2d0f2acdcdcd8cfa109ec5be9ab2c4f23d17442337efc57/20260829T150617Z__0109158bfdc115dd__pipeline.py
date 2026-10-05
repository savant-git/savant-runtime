#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import Any


runtime_root = Path(
    "/root/savant-runtime"
)

extr_runtime = (
    runtime_root
    / "tools"
    / "extr-enterprise"
    / "runtime"
)

sys.path.insert(
    0,
    str(
        extr_runtime
    ),
)

import corpus
import coherence


schema = "savant.extr.pipeline.v1"


def timestamp() -> str:
    return time.strftime(
        "%Y%m%dT%H%M%SZ",
        time.gmtime(),
    ).casefold()


def run_pipeline(
    source: Path,
    destination: Path,
) -> dict[str, Any]:
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    staging = Path(
        tempfile.mkdtemp(
            prefix=".extr-pipeline-",
            dir=str(
                destination.parent
            ),
        )
    )

    corpus_root = (
        staging
        / "corpus"
    )

    coherence_root = (
        staging
        / "coherent"
    )

    try:
        corpus_manifest = (
            corpus.corpus_extract(
                source,
                corpus_root,
            )
        )

        coherence_manifest = (
            coherence.refine_corpus(
                corpus_root,
                coherence_root,
            )
        )

        output_root = (
            staging
            / "output"
        )

        output_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        os.replace(
            corpus_root,
            output_root
            / "corpus",
        )

        os.replace(
            coherence_root,
            output_root
            / "coherent",
        )

        manifest = {
            "schema":
                schema,
            "projection_only":
                True,
            "authority_effect":
                "none",
            "generated_at":
                timestamp(),
            "source":
                str(
                    source.resolve()
                ),
            "destination":
                str(
                    destination.resolve()
                ),
            "corpus_digest":
                corpus_manifest.get(
                    "manifest_digest"
                ),
            "coherence_digest":
                coherence_manifest.get(
                    "digest"
                ),
            "statistics": {
                "files_discovered":
                    corpus_manifest.get(
                        "source",
                        {},
                    ).get(
                        "files_discovered",
                        0,
                    ),
                "segments_ingested":
                    corpus_manifest.get(
                        "statistics",
                        {},
                    ).get(
                        "segments_ingested",
                        0,
                    ),
                "projects":
                    len(
                        coherence_manifest.get(
                            "projects",
                            [],
                        )
                    ),
            },
            "semantics": {
                "source_mutated":
                    False,
                "projection_only":
                    True,
                "authority_created":
                    False,
                "duplicate_evidence_preserved":
                    True,
                "quarantined_material_preserved":
                    True,
                "contradictions_preserved":
                    True,
                "older_versions_preserved":
                    True,
            },
        }

        with (
            output_root
            / "manifest.json"
        ).open(
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                manifest,
                handle,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )

            handle.write(
                "\n"
            )

        previous = (
            destination.parent
            / (
                destination.name
                + ".previous"
            )
        )

        if previous.exists():
            if previous.is_dir():
                shutil.rmtree(
                    previous
                )
            else:
                previous.unlink()

        if destination.exists():
            os.replace(
                destination,
                previous,
            )

        os.replace(
            output_root,
            destination,
        )

        return manifest

    finally:
        shutil.rmtree(
            staging,
            ignore_errors=True,
        )


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        prog="extr-pipeline"
    )

    value.add_argument(
        "source"
    )

    value.add_argument(
        "destination",
        nargs="?",
    )

    return value


def main() -> int:
    arguments = parser().parse_args()

    source = Path(
        os.path.expanduser(
            os.path.expandvars(
                arguments.source
            )
        )
    ).resolve()

    if not source.is_dir():
        print(
            (
                "extr-pipeline: source "
                f"is not a directory: {source}"
            ),
            file=sys.stderr,
        )

        return 1

    destination = (
        Path(
            os.path.expanduser(
                os.path.expandvars(
                    arguments.destination
                )
            )
        ).resolve()
        if arguments.destination
        else source.parent
        / (
            source.name
            + ".extr"
        )
    )

    try:
        manifest = run_pipeline(
            source,
            destination,
        )

    except Exception as error:
        print(
            (
                "extr-pipeline: "
                f"{type(error).__name__}: "
                f"{error}"
            ),
            file=sys.stderr,
        )

        return 1

    print(
        json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


palaver_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/palaver"
)

legacy = (
    palaver_root
    / "apps"
    / "webui_ultra"
    / "server.py"
)

canonical_payload = (
    palaver_root
    / "runtime"
    / "server_native.py"
)

receipt = (
    palaver_root
    / "runtime"
    / "server_native.receipt.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


def main() -> int:
    if not legacy.is_file():
        raise RuntimeError(
            f"legacy implementation missing: {legacy}"
        )

    canonical_payload.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        legacy,
        canonical_payload,
    )

    source_digest = sha256(
        legacy
    )

    destination_digest = sha256(
        canonical_payload
    )

    if source_digest != destination_digest:
        raise RuntimeError(
            "palaver native promotion digest mismatch"
        )

    payload = {
        "schema":
            "savant.palaver.native-promotion.v1",
        "authority_effect":
            "none",
        "source":
            str(legacy),
        "destination":
            str(canonical_payload),
        "source_sha256":
            source_digest,
        "destination_sha256":
            destination_digest,
        "identical":
            True,
        "purpose":
            (
                "preserve verified webui_ultra behavior "
                "while reversing canonical dependency direction"
            ),
    }

    receipt.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            payload,
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

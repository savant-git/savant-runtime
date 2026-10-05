import sys
from pathlib import Path


ROOT = Path(
    "/root/savant-runtime"
).resolve()

PALAVER_RUNTIME = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/exiles/"
    "palaver/runtime"
).resolve()


for path in (
    ROOT,
    PALAVER_RUNTIME,
):
    value = str(path)

    if value not in sys.path:
        sys.path.insert(
            0,
            value,
        )


from runtime.constitution import ConstitutionalRegistry
from runtime.memory import MemoryAssertion
from runtime.scrybe import Scrybe

import scrybe_bridge
import server


def main() -> int:
    print(
        "runtime_package="
        + str(
            sys.modules[
                "runtime"
            ].__file__
        )
    )

    try:
        legacy = server.bootstrap()

    except Exception as exc:
        print(
            "bootstrap_error_type="
            + type(exc).__name__
        )
        print(
            "bootstrap_error="
            + str(exc)
        )
        return 1

    try:
        result = legacy.call_openai(
            "Return exactly: SAVANT_OPUS_OK",
            "",
        )

    except Exception as exc:
        print(
            "error_type="
            + type(exc).__name__
        )
        print(
            "error="
            + str(exc)
        )
        print(
            "diagnostic="
            + str(
                getattr(
                    exc,
                    "diagnostic",
                    None,
                )
            )
        )
        print(
            "error_code="
            + str(
                getattr(
                    exc,
                    "code",
                    None,
                )
            )
        )
        return 1

    print(
        "opus_result=success"
    )
    print(
        "response="
        + str(result)
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

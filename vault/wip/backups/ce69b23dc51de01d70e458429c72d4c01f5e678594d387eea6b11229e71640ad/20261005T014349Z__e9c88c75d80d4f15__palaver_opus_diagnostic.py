import sys


PALAVER_RUNTIME = (
    "/root/savant-runtime/ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/exiles/"
    "palaver/runtime"
)


def main() -> int:
    if PALAVER_RUNTIME not in sys.path:
        sys.path.insert(
            0,
            PALAVER_RUNTIME,
        )

    import server

    legacy = server.bootstrap()

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

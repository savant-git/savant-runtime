
from __future__ import annotations

import importlib.util
from pathlib import Path
from threading import Event, Thread


source = Path(__file__).resolve().with_name(
    "session_control.py"
)

spec = importlib.util.spec_from_file_location(
    "urge_session_control",
    source,
)

if spec is None or spec.loader is None:
    raise RuntimeError(
        "cannot load session control"
    )

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise AssertionError(message)


control = module.controller()

entered = Event()
release = Event()
finished = Event()

outcome: list[str] = []


def worker() -> None:
    try:
        control.checkpoint()
        entered.set()

        if not release.wait(2):
            raise RuntimeError(
                "worker release timed out"
            )

        control.checkpoint()
        outcome.append("completed")

    except module.session_cancelled:
        outcome.append("cancelled")

    finally:
        finished.set()


control.start()
control.pause()

thread = Thread(
    target=worker,
    daemon=True,
)
thread.start()

require(
    not entered.wait(0.1),
    "paused worker advanced unexpectedly",
)

control.resume()

require(
    entered.wait(2),
    "worker did not resume",
)

control.cancel()
release.set()

require(
    finished.wait(2),
    "worker did not terminate",
)

thread.join(timeout=2)

require(
    not thread.is_alive(),
    "worker remains active",
)

require(
    outcome == ["cancelled"],
    f"unexpected worker outcome: {outcome}",
)

require(
    control.projection()["status"]
    == "cancelled",
    "controller did not retain cancelled state",
)

require(
    issubclass(
        module.session_cancelled,
        BaseException,
    ),
    "cancellation must inherit BaseException",
)

require(
    not issubclass(
        module.session_cancelled,
        Exception,
    ),
    "cancellation must bypass Exception handlers",
)

print(
    "session control: pause, resume, "
    "cancellation passed"
)


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
    raise RuntimeError("cannot load session control")

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

control = module.controller()
entered = Event()
finished = Event()
outcome = []


def worker() -> None:
    try:
        control.checkpoint()
        entered.set()
        control.checkpoint()
        outcome.append("completed")
    except module.session_cancelled:
        outcome.append("cancelled")
    finally:
        finished.set()


control.start()
control.pause()

thread = Thread(target=worker, daemon=True)
thread.start()

assert not entered.wait(0.1), (
    "paused worker advanced unexpectedly"
)

control.resume()

assert entered.wait(2), (
    "worker did not resume"
)

control.cancel()

assert finished.wait(2), (
    "worker did not terminate"
)

thread.join(timeout=2)

assert not thread.is_alive(), (
    "worker remains active"
)

assert outcome == ["cancelled"], outcome

assert control.projection()["status"] == (
    "cancelled"
)

assert issubclass(
    module.session_cancelled,
    BaseException,
)

assert not issubclass(
    module.session_cancelled,
    Exception,
)

print(
    "session control: pause, resume, "
    "cancellation passed"
)

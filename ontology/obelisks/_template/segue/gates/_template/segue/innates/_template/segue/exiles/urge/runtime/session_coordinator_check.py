
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from threading import Event


runtime = Path(__file__).resolve().parent
package_name = "_urge_coordinator_check"

package = types.ModuleType(package_name)
package.__path__ = [str(runtime)]
package.__package__ = package_name
sys.modules[package_name] = package


def load(name: str):
    fullname = f"{package_name}.{name}"
    path = runtime / f"{name}.py"

    spec = importlib.util.spec_from_file_location(
        fullname,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"cannot load {name}"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[fullname] = module

    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(fullname, None)
        raise

    return module


iteration = load("iteration")
load("session_timeline")
load("session_control")
load("session_execution")
coordinator_module = load("session_coordinator")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


work = iteration.job(
    id="coordinator-check",
    objective="verify session coordination",
    payload={"value": 0},
    criteria=(
        iteration.criterion(
            id="quality",
            required=True,
        ),
    ),
)


def evaluate(payload, context):
    return {
        "scores": {
            "quality": 1.0,
        },
        "evidence": (
            "deterministic evaluation",
        ),
    }


def revise(payload, pressure):
    return ()


runner = iteration.engine(
    evaluator=evaluate,
    reviser=revise,
    run_policy=iteration.policy(
        max_cycles=1,
        branch_factor=1,
        max_candidates=2,
    ),
)

sessions = coordinator_module.coordinator(
    max_sessions=2
)

sessions.start(
    session_id="completed-check",
    work=work,
    runner=runner,
)

completed = sessions.wait(
    "completed-check",
    timeout=3,
)

require(
    completed["finished"],
    "completed session did not finish",
)

require(
    completed["status"] == "completed",
    f"unexpected status: {completed['status']}",
)

require(
    completed["iteration_count"] == 1,
    "expected one recorded iteration",
)

require(
    completed["selected"] is not None,
    "selected candidate missing",
)

require(
    completed["error"] is None,
    f"execution failed: {completed['error']}",
)

require(
    completed["selected"]["iteration_id"]
    == completed["timeline"]["active"][0],
    "selected iteration identity differs",
)

entered = Event()
release = Event()


def blocked_evaluate(payload, context):
    entered.set()

    if not release.wait(3):
        raise RuntimeError(
            "evaluation release timed out"
        )

    return evaluate(payload, context)


blocked_runner = iteration.engine(
    evaluator=blocked_evaluate,
    reviser=revise,
    run_policy=runner.policy,
)

sessions.start(
    session_id="cancelled-check",
    work=work,
    runner=blocked_runner,
)

try:
    require(
        entered.wait(3),
        "blocked evaluator was not entered",
    )

    cancelled = sessions.cancel(
        "cancelled-check"
    )

    require(
        cancelled["status"] == "cancelled",
        "cancellation state was not published",
    )

finally:
    release.set()

cancelled = sessions.wait(
    "cancelled-check",
    timeout=3,
)

require(
    cancelled["finished"],
    "cancelled session did not finish",
)

require(
    cancelled["status"] == "cancelled",
    "cancelled status was not preserved",
)

require(
    cancelled["error"] is None,
    f"unexpected error: {cancelled['error']}",
)

require(
    cancelled["selected"] is None,
    "cancelled execution selected a candidate",
)

require(
    sessions.sessions()
    == ["cancelled-check", "completed-check"],
    "session registry differs",
)

sessions.release("completed-check")
sessions.release("cancelled-check")

require(
    sessions.sessions() == [],
    "released sessions remain registered",
)

print(
    "urge session coordinator: "
    "completion, selection, cancellation, "
    "and release passed"
)

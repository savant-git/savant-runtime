
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


runtime = Path(__file__).resolve().parent
package_name = "_urge_session_api_check"

package = types.ModuleType(package_name)
package.__path__ = [str(runtime)]
package.__package__ = package_name
sys.modules[package_name] = package


def load(name: str):
    fullname = f"{package_name}.{name}"
    spec = importlib.util.spec_from_file_location(
        fullname,
        runtime / f"{name}.py",
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")

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
api_module = load("session_api")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


work = iteration.job(
    id="session-api-check",
    objective="verify session request dispatch",
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
        "scores": {"quality": 1.0},
        "evidence": ("deterministic evaluation",),
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


def resolve_work(payload):
    require(
        payload.get("job_id") == "session-api-check",
        "unexpected job identity",
    )
    return work, runner


sessions = coordinator_module.coordinator(
    max_sessions=2
)

api = api_module.session_api(
    sessions=sessions,
    resolve_work=resolve_work,
)

started = api.safe_dispatch(
    action="start",
    payload={
        "session_id": "api-check-1",
        "job_id": "session-api-check",
    },
)

require(
    started["ok"] is True,
    f"session start failed: {started}",
)

completed = sessions.wait(
    "api-check-1",
    timeout=3,
)

require(
    completed["finished"] is True,
    "session did not finish",
)

require(
    completed["status"] == "completed",
    f"unexpected execution status: {completed}",
)

snapshot = api.safe_dispatch(
    action="snapshot",
    payload={"session_id": "api-check-1"},
)

require(
    snapshot["ok"] is True,
    "snapshot request failed",
)

require(
    snapshot["session"]["selected"] is not None,
    "selected candidate is missing",
)

require(
    snapshot["session"]["iteration_count"] == 1,
    "iteration count differs",
)

duplicate = api.safe_dispatch(
    action="start",
    payload={
        "session_id": "api-check-1",
        "job_id": "session-api-check",
    },
)

require(
    duplicate["ok"] is False,
    "duplicate session identity was accepted",
)

unknown = api.safe_dispatch(
    action="snapshot",
    payload={"session_id": "missing-session"},
)

require(
    unknown["ok"] is False,
    "unknown session was accepted",
)

unsupported = api.safe_dispatch(
    action="rewind",
    payload={"session_id": "api-check-1"},
)

require(
    unsupported["ok"] is False,
    "unsupported rewind was accepted",
)

released = api.safe_dispatch(
    action="release",
    payload={"session_id": "api-check-1"},
)

require(
    released["ok"] is True,
    "release request failed",
)

require(
    sessions.sessions() == [],
    "released session remains registered",
)

print(
    "urge session api: start, snapshot, "
    "selection, error handling, and release passed"
)

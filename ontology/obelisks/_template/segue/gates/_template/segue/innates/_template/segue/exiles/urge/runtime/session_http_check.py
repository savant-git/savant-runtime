
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path


runtime = Path(__file__).resolve().parent
package_name = "_urge_session_http_check"

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
        raise RuntimeError(
            f"cannot load {name}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

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
http_module = load("session_http")


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise AssertionError(message)


work = iteration.job(
    id="session-http-check",
    objective="verify session http transport",
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


def resolve_work(payload):
    require(
        payload.get("job_id")
        == "session-http-check",
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

transport = http_module.session_http(
    api=api
)


def request(
    action: str,
    payload: dict,
    *,
    authorized: bool = True,
):
    result = transport.dispatch(
        method="POST",
        request_path=http_module.path,
        body=json.dumps(
            {
                "action": action,
                "payload": payload,
            }
        ).encode("utf-8"),
        authorized=authorized,
    )

    require(
        result is not None,
        "request was not handled",
    )

    status, headers, body = result

    require(
        int(headers["Content-Length"])
        == len(body),
        "response length differs",
    )

    return status, json.loads(
        body.decode("utf-8")
    )


status, denied = request(
    "snapshot",
    {"session_id": "check"},
    authorized=False,
)

require(
    status == 403,
    "unauthorized request was accepted",
)

require(
    denied["ok"] is False,
    "authorization error missing",
)

status, started = request(
    "start",
    {
        "session_id": "http-check",
        "job_id": "session-http-check",
    },
)

require(
    status == 200 and started["ok"],
    "session start failed",
)

completed = sessions.wait(
    "http-check",
    timeout=3,
)

require(
    completed["finished"],
    "execution did not finish",
)

require(
    completed["status"] == "completed",
    f"execution failed: {completed}",
)

status, snapshot = request(
    "snapshot",
    {"session_id": "http-check"},
)

require(
    status == 200 and snapshot["ok"],
    "snapshot failed",
)

require(
    snapshot["session"]["selected"]
    is not None,
    "selected candidate missing",
)

require(
    snapshot["session"]["iteration_count"]
    == 1,
    "iteration count differs",
)

status, unsupported = request(
    "rewind",
    {"session_id": "http-check"},
)

require(
    status == 400,
    "unsupported rewind was accepted",
)

status, released = request(
    "release",
    {"session_id": "http-check"},
)

require(
    status == 200 and released["ok"],
    "session release failed",
)

require(
    sessions.sessions() == [],
    "session remains registered",
)

unrelated = transport.dispatch(
    method="POST",
    request_path="/api/chat",
    body=b"{}",
    authorized=True,
)

require(
    unrelated is None,
    "unrelated route was intercepted",
)

print(
    "urge session http: authorization, "
    "start, snapshot, selection, "
    "release, and route isolation passed"
)

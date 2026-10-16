
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from threading import Event, Thread


runtime = Path(__file__).resolve().parent
package_name = "_urge_session_execution_check"

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
timeline = load("session_timeline")
control_module = load("session_control")
execution = load("session_execution")


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise AssertionError(message)


work = iteration.job(
    id="urge-session-check",
    objective="verify session execution",
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
            "quality": float(payload["value"]),
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

observations = []

result = execution.execute(
    message_id="urge-check-complete",
    work=work,
    runner=runner,
    on_iteration=observations.append,
)

require(
    result["status"] == "completed",
    "execution did not complete",
)

require(
    len(observations) == 1,
    "expected one evaluated candidate",
)

require(
    result["selected"]["payload"]
    == {"value": 0},
    "selected payload differs",
)

require(
    result["selected"]["iteration_id"]
    == result["timeline"]["active"][0],
    "selected timeline identity differs",
)

require(
    result["control"]["status"]
    == "completed",
    "controller did not complete",
)

require(
    not result["observation_failures"],
    "observation callback failed",
)

require(
    timeline.verify(
        result["timeline"]
    )["digest"]
    == result["timeline"]["digest"],
    "timeline integrity differs",
)


entered = Event()
release = Event()
outcome = []


def blocked_evaluate(payload, context):
    entered.set()

    if not release.wait(3):
        raise RuntimeError(
            "evaluation release timed out"
        )

    return evaluate(payload, context)


cancel_runner = iteration.engine(
    evaluator=blocked_evaluate,
    reviser=revise,
    run_policy=runner.policy,
)

cancel_control = control_module.controller()


def worker():
    try:
        outcome.append(
            execution.execute(
                message_id="urge-check-cancel",
                work=work,
                runner=cancel_runner,
                control=cancel_control,
            )
        )
    except BaseException as exc:
        outcome.append(exc)


thread = Thread(
    target=worker,
    daemon=True,
)

thread.start()

try:
    require(
        entered.wait(3),
        "evaluator was not entered",
    )

    cancel_control.cancel()

finally:
    release.set()

thread.join(timeout=3)

require(
    not thread.is_alive(),
    "cancelled worker remains active",
)

require(
    len(outcome) == 1,
    "unexpected cancellation outcome",
)

require(
    isinstance(outcome[0], dict),
    f"cancellation raised: {outcome[0]!r}",
)

require(
    outcome[0]["status"] == "cancelled",
    "execution ignored cancellation",
)

require(
    outcome[0]["control"]["status"]
    == "cancelled",
    "controller status differs",
)

print(
    "urge session execution: "
    "selection and cancellation passed"
)

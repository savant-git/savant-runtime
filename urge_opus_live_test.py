import json
import traceback

from ontology.obelisks._template.segue.gates._template.segue.innates._template.segue.exiles.urge.runtime.execution_binding import execute


payload = {
    "objective": (
        "Create a distinctive identity concept for Savant that avoids "
        "generic AI, brain, circuit, spark, infinity, and neural-network tropes."
    ),
    "mode": "logo",
    "name": "savant",
    "brief": {
        "name": "savant",
    },
    "constraints": [],
    "invariants": [],
    "cliches": [
        "brain",
        "circuit",
        "neural network",
        "spark",
        "infinity symbol",
        "generic futuristic gradient",
    ],
    "baselines": [],
    "context": {
        "surface": "focused-live-test",
        "instance": "exile:urge",
    },
    "creative_policy": {},
}


try:
    result = execute(payload)
    print(
        json.dumps(
            result,
            indent=2,
        )
    )
except Exception:
    traceback.print_exc()

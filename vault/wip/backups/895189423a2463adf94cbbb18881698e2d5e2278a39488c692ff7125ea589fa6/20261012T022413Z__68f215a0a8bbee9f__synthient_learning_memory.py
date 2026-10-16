
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/root/syntools")
MEMORY_FILE = ROOT / "synthient_learning_memory.json"


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class LearningMemory:
    def __init__(self, path=MEMORY_FILE):
        self.path = Path(path)
        self.data = self.load()

    def load(self):
        if not self.path.exists():
            return {
                "version": 1,
                "sites": {},
                "events": [],
            }

        with self.path.open(encoding="utf-8") as handle:
            data = json.load(handle)

        if not isinstance(data, dict):
            raise ValueError("Invalid memory document")

        if data.get("version") != 1:
            raise ValueError("Unsupported memory version")

        if not isinstance(data.get("sites"), dict):
            raise ValueError("Invalid sites collection")

        if not isinstance(data.get("events"), list):
            raise ValueError("Invalid events collection")

        return data

    def site(self, url):
        site = self.data["sites"].setdefault(
            url,
            {
                "states": {},
                "transitions": [],
            },
        )

        site.setdefault("states", {})
        site.setdefault("transitions", [])
        site.setdefault("visits", {})
        site.setdefault("outcomes", [])

        return site

    def record_state(self, url, state):
        site = self.site(url)
        signature = state["signature"]
        previous = site["states"].get(signature, {})

        state["first_seen"] = previous.get(
            "first_seen",
            timestamp(),
        )

        site["states"][signature] = state

        visits = site["visits"]
        visits[signature] = visits.get(signature, 0) + 1

    def record_transition(
        self,
        url,
        source_signature,
        action,
        destination,
    ):
        site = self.site(url)
        transitions = site["transitions"]

        for item in transitions:
            if (
                item["from"] == source_signature
                and item["action"] == action
                and item["destination"] == destination
            ):
                return

        transitions.append({
            "from": source_signature,
            "action": action,
            "destination": destination,
            "observed_at": timestamp(),
        })

    def record_outcome(
        self,
        url,
        destination,
        signature,
        title,
    ):
        self.site(url)["outcomes"][destination] = {
            "signature": signature,
            "title": title,
            "last_observed": timestamp(),
        }

    def known_destination(self, url, destination):
        return destination in self.site(url)["outcomes"]

    def record_event(
        self,
        event_type,
        site_url,
        state_signature,
    ):
        self.data["events"].append({
            "type": event_type,
            "site": site_url,
            "state": state_signature,
            "time": timestamp(),
        })

    def save(self):
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = self.path.with_suffix(".tmp")

        with temporary.open(
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                self.data,
                handle,
                indent=2,
                ensure_ascii=False,
            )

        temporary.replace(self.path)

    def get_states(self, url):
        return self.site(url)["states"]

    def get_transitions(self, url):
        return self.site(url)["transitions"]

    def get_events(self):
        return self.data["events"]

    def statistics(self, url):
        site = self.site(url)

        return {
            "states": len(site["states"]),
            "transitions": len(site["transitions"]),
            "known_destinations": len(site["outcomes"]),
            "observations": sum(site["visits"].values()),
        }

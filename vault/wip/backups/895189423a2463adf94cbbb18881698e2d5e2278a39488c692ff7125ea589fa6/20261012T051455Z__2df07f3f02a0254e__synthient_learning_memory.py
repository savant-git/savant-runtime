
import copy
import fcntl
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/root/syntools")
MEMORY_FILE = ROOT / "synthient_learning_memory.json"


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def digest(value):
    return hashlib.sha256(
        canonical(value).encode("utf-8")
    ).hexdigest()


class MemoryConflictError(RuntimeError):
    pass


class LearningMemory:
    def __init__(self, path=MEMORY_FILE):
        self.path = Path(path)
        self.data = self.load()
        self._baseline = digest(self.data)

    def load(self):
        if not self.path.exists():
            return {
                "version": 1,
                "sites": {},
                "events": [],
            }

        with self.path.open(
            "r", encoding="utf-8"
        ) as handle:
            data = json.load(handle)

        self._validate(data)
        return data

    @staticmethod
    def _validate(data):
        if not isinstance(data, dict):
            raise ValueError("Invalid memory document")

        if data.get("version") != 1:
            raise ValueError(
                "Unsupported memory version"
            )

        if not isinstance(
            data.get("sites"), dict
        ):
            raise ValueError(
                "Invalid sites collection"
            )

        if not isinstance(
            data.get("events"), list
        ):
            raise ValueError(
                "Invalid events collection"
            )

        for site in data["sites"].values():
            if not isinstance(site, dict):
                raise ValueError(
                    "Invalid site document"
                )

            for key, kind in (
                ("states", dict),
                ("transitions", list),
                ("visits", dict),
            ):
                if (
                    key in site
                    and not isinstance(
                        site[key], kind
                    )
                ):
                    raise ValueError(
                        f"Invalid site field: {key}"
                    )

            outcomes = site.get(
                "outcomes", {}
            )

            if not (
                isinstance(outcomes, dict)
                or outcomes == []
            ):
                raise ValueError(
                    "Invalid outcomes collection"
                )

    def site(self, url):
        if not isinstance(url, str):
            raise TypeError(
                "Site identifier must be text"
            )

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
        site.setdefault("outcomes", {})

        if isinstance(
            site["outcomes"], list
        ):
            if site["outcomes"]:
                raise ValueError(
                    "Cannot convert nonempty outcomes list"
                )

            site["outcomes"] = {}

        return site

    def record_state(self, url, state):
        if not isinstance(state, dict):
            raise TypeError(
                "State must be a dictionary"
            )

        signature = state["signature"]

        if not isinstance(
            signature, str
        ) or not signature:
            raise ValueError(
                "Invalid state signature"
            )

        site = self.site(url)
        previous = site["states"].get(
            signature, {}
        )

        now = timestamp()
        stored = copy.deepcopy(state)

        stored["first_seen"] = previous.get(
            "first_seen", now
        )
        stored["last_seen"] = now

        site["states"][signature] = stored

        visits = site["visits"]
        visits[signature] = (
            visits.get(signature, 0) + 1
        )

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
                and item["destination"]
                == destination
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
        site = self.site(url)
        previous = site[
            "outcomes"
        ].get(destination, {})

        now = timestamp()

        site["outcomes"][destination] = {
            "signature": signature,
            "title": title,
            "first_observed": previous.get(
                "first_observed",
                previous.get(
                    "last_observed", now
                ),
            ),
            "last_observed": now,
        }

    def known_destination(
        self, url, destination
    ):
        return destination in self.site(
            url
        )["outcomes"]

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
        self._validate(self.data)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        lock_path = self.path.with_name(
            self.path.name + ".lock"
        )

        descriptor = os.open(
            lock_path,
            os.O_CREAT | os.O_RDWR,
            0o600,
        )

        temporary = None

        try:
            with os.fdopen(
                descriptor, "r+"
            ) as lock:
                fcntl.flock(
                    lock.fileno(),
                    fcntl.LOCK_EX,
                )

                current = self.load()

                if (
                    digest(current)
                    != self._baseline
                ):
                    raise MemoryConflictError(
                        "Memory changed since loading; "
                        "reload before saving"
                    )

                payload = (
                    json.dumps(
                        self.data,
                        ensure_ascii=False,
                        indent=2,
                        allow_nan=False,
                    )
                    + "\n"
                )

                fd, temporary = tempfile.mkstemp(
                    prefix=".syntools-memory-",
                    suffix=".tmp",
                    dir=str(self.path.parent),
                )

                with os.fdopen(
                    fd, "w", encoding="utf-8"
                ) as handle:
                    os.fchmod(
                        handle.fileno(), 0o600
                    )
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())

                os.replace(
                    temporary, self.path
                )
                temporary = None

                directory = os.open(
                    self.path.parent,
                    os.O_RDONLY,
                )

                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)

                self._baseline = digest(
                    self.data
                )

        finally:
            if temporary is not None:
                try:
                    os.unlink(temporary)
                except FileNotFoundError:
                    pass

    def reload(self):
        self.data = self.load()
        self._baseline = digest(
            self.data
        )
        return self.data

    def get_states(self, url):
        return self.site(url)["states"]

    def get_transitions(self, url):
        return self.site(url)["transitions"]

    def get_events(self):
        return self.data["events"]

    def statistics(self, url):
        site = self.site(url)

        return {
            "states": len(
                site["states"]
            ),
            "transitions": len(
                site["transitions"]
            ),
            "known_destinations": len(
                site["outcomes"]
            ),
            "observations": sum(
                site["visits"].values()
            ),
        }

    def transition_index(self, url):
        result = {}

        for transition in self.site(
            url
        )["transitions"]:
            result.setdefault(
                transition["from"], []
            ).append(transition)

        return result

    def state_history(self, url, signature):
        site = self.site(url)

        return {
            "state": copy.deepcopy(
                site["states"].get(signature)
            ),
            "visits": site[
                "visits"
            ].get(signature, 0),
            "transitions": [
                copy.deepcopy(item)
                for item in site["transitions"]
                if item["from"] == signature
            ],
        }

    def strategy_ranking(self, url):
        strategies = self.site(
            url
        ).get("strategies", [])

        if not isinstance(
            strategies, list
        ):
            raise ValueError(
                "Invalid strategies collection"
            )

        valid = [
            item
            for item in strategies
            if isinstance(item, dict)
            and isinstance(
                item.get("actions"), list
            )
        ]

        return sorted(
            valid,
            key=lambda item: (
                -item.get("successes", 0),
                item.get("failures", 0),
                len(item["actions"]),
                canonical(item["actions"]),
            ),
        )

    def snapshot(self):
        return copy.deepcopy(
            self.data
        )

    def integrity_digest(self):
        return digest(self.data)

from __future__ import annotations

from collections import defaultdict


class EventBus:

    def __init__(self):
        self._handlers = defaultdict(list)

    def subscribe(self, event: str, handler):
        self._handlers[event].append(handler)

    def publish(self, event: str, payload=None):

        payload = payload or {}

        for handler in self._handlers[event]:
            handler(payload)


bus = EventBus()

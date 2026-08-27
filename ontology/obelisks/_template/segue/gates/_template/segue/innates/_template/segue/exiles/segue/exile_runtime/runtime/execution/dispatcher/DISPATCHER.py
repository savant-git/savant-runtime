from __future__ import annotations


class Dispatcher:

    def __init__(self):
        self.routes = {}

    def register(self, capability, handler):
        self.routes[capability] = handler

    def dispatch(self, capability, payload):

        if capability not in self.routes:
            raise KeyError(capability)

        return self.routes[capability](payload)


dispatcher = Dispatcher()

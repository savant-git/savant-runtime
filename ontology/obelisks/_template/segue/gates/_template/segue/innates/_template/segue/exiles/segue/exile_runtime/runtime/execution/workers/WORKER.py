from __future__ import annotations


class Worker:

    def __init__(self, name):
        self.name = name

    def execute(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)

from __future__ import annotations

import heapq


class Scheduler:

    def __init__(self):
        self.queue = []

    def schedule(self, priority, fn, *args, **kwargs):
        heapq.heappush(
            self.queue,
            (priority, fn, args, kwargs)
        )

    def run(self):

        while self.queue:
            _, fn, args, kwargs = heapq.heappop(self.queue)
            fn(*args, **kwargs)


scheduler = Scheduler()
